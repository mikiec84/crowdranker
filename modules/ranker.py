#!/usr/bin/env python
# coding: utf8
from gluon import *
from rank import Rank
from rank import Cost
import util

NUM_BINS = 2001
AVRG = NUM_BINS / 2
STDEV = NUM_BINS / 8

def get_all_items_and_qdistr_param(db, venue_id):
    """ Returns a tuple (items, qdistr_param) where:
        - itmes is a list of submissions id.
        - qdistr_param[2*i] and qdistr_param[2*i + 1] are mean and standard
        deviation for a submission items[i].
    """
    # List of all submissions id for given venue.
    items = []
    sub = db(db.submission.venue_id == venue_id).select(db.submission.id)
    # Fetching quality distributions parametes for each submission.
    qdistr_param = []
    for x in sub:
        items.append(x.id)
        quality_row = db((db.submission.venue_id == venue_id) &
                  (db.submission.id == x.id)).select(db.submission.quality,
                  db.submission.error).first()
        #quality = db((db.quality.venue_id == venue_id) &
        #          (db.quality.submission_id == x.id)).select(db.quality.average,
        #          db.quality.stdev).first()
        if (quality_row is None or quality_row.quality is None or
           quality_row.error is None):
            qdistr_param.append(AVRG)
            qdistr_param.append(STDEV)
        else:
            qdistr_param.append(quality_row.quality)
            qdistr_param.append(quality_row.error)
    # Ok, items and qdistr_param are filled.
    return items, qdistr_param

def get_qdistr_param(db, venue_id, items_id):
    if items_id == None:
        return None
    qdistr_param = []
    for x in items_id:
        quality_row = db((db.submission.venue_id == venue_id) &
                  (db.submission.id == x)).select(db.submission.quality,
                  db.submission.error).first()
        #quality = db((db.quality.venue_id == venue_id) &
        #          (db.quality.submission_id == x)).select(db.quality.average,
        #          db.quality.stdev).first()
        if (quality_row is None or quality_row.quality is None or
           quality_row.error is None):
            qdistr_param.append(AVRG)
            qdistr_param.append(STDEV)
        else:
            qdistr_param.append(quality_row.quality)
            qdistr_param.append(quality_row.error)
    return qdistr_param

def get_init_average_stdev():
    """ Method returns tuple with average and stdev for initializing
    field in table quality.
    """
    return AVRG, STDEV

def get_item(db, venue_id, user_id, old_items,
             can_rank_own_submissions=False,
             rank_cost_coefficient=0):
    """
    If a user did not have items to rank then old_items is None or empty string.

    If rank_cost_coefficient is equal zero then no cost function is used which
    corresponds to treating each submission equally.
    """
    items, qdistr_param = get_all_items_and_qdistr_param(db, venue_id)
    # If items is None then some submission does not have qualities yet,
    # we need to know qualities of for all submission to correctly choose an
    # item.
    if items == None or len(items) == 0:
        return None
    # Specifying cost object which has cost function.
    cost_obj = Cost(cost_type='rank_power_alpha',
                   rank_cost_coefficient=rank_cost_coefficient)
    if rank_cost_coefficient == 0:
        cost_obj = None
    rankobj = Rank.from_qdistr_param(items, qdistr_param, cost_obj=cost_obj)
    if not can_rank_own_submissions:
        # Find submission that is authored by the user.
        submission_ids = db((db.submission.venue_id == venue_id) &
                                (db.submission.author == user_id)).select(db.submission.id)
        users_submission_ids = [x.id for x in submission_ids]
    else:
        users_submission_ids = None
    return rankobj.sample_item(old_items, users_submission_ids)

def process_comparison(db, venue_id, user_id, sorted_items, new_item,
                       alpha_annealing=0.6):
    """ Function updates quality distributions and rank of submissions (items).

    Arguments:
        - sorted_items is a list of submissions id sorted by user such that
        rank(sorted_items[i]) > rank(sorted_items[j]) for i > j

        - new_item is an id of a submission from sorted_items which was new
        to the user. If sorted_items contains only two elements then
        new_item is None.
    """
    if sorted_items == None or len(sorted_items) <= 1:
        return None
    qdistr_param = get_qdistr_param(db, venue_id, sorted_items)
    # If qdistr_param is None then some submission does not have qualities yet,
    # therefore we cannot process comparison.
    if qdistr_param == None:
        return None
    rankobj = Rank.from_qdistr_param(sorted_items, qdistr_param,
                                     alpha=alpha_annealing)
    result = rankobj.update(sorted_items, new_item)
    # Updating the DB.
    for x in sorted_items:
        perc, avrg, stdev = result[x]
        #db((db.quality.venue_id == venue_id) &
        #   (db.quality.submission_id == x)).update(average=avrg, stdev=stdev, percentile=perc)
        # Updating submission table with its quality and error.
        db((db.submission.id == x) &
           (db.submission.venue_id == venue_id)).update(quality=avrg, error=stdev)

def evaluate_contributors(db, venue_id, list_of_users):
    # Obtaining list of submissions.
    items, qdistr_param = get_all_items_and_qdistr_param(db, venue_id)
    if items == None or len(items) == 0:
        return None
    rankobj = Rank.from_qdistr_param(items, qdistr_param, cost_obj=None)
    for user_id in list_of_users:
        last_comparison = db((db.comparison.author == user_id)
            & (db.comparison.venue_id == venue_id)).select(orderby=~db.comparison.date).first()
        if last_comparison == None:
            continue;
        ordering = util.get_list(last_comparison.ordering)
        ordering = ordering[::-1]
        val = rankobj.evaluate_ordering(ordering)
        # Writting to the DB.
        counter = db((db.user_accuracy.venue_id == venue_id) &
           (db.user_accuracy.user_id == user_id)).update(accuracy=val)
        if counter == 0:
            db.user_accuracy.insert(venue_id = venue_id, user_id = user_id, accuracy=val)


def rerun_processing_comparisons(db, venue_id, list_of_users,
                                 alpha_annealing=0.6):
    # Obtaining list of submissions.
    comparisons = []
    for user_id in list_of_users:
        comp_rows = db((db.comparison.author == user_id)
            & (db.comparison.venue_id == venue_id)).select(db.comparison.ordering, db.comparison.date)
        if comp_rows is None or len(comp_rows) == 0:
            # The user did not make any comparisons, so skip it.
            continue
        comp = [(util.get_list(x.ordering), x.date) for x in comp_rows]
        comparisons.extend(comp)
    comparisons = sorted(comparisons, key=lambda x : x[1])
    # Reversing order in comparisons.
    comparisons = [x[0][::-1] for x in comparisons]
    # Okay, we have comparisons in increasing order.
    # Fetching a lit of items.
    sub = db(db.submission.venue_id == venue_id).select(db.submission.id)
    items = []
    qdistr_param = []
    for x in sub:
        items.append(x.id)
        qdistr_param.append(AVRG)
        qdistr_param.append(STDEV)
    rankobj = Rank.from_qdistr_param(items, qdistr_param,
                                     alpha=alpha_annealing)
    # Updating.
    for sorted_items in comparisons:
        # TODO(michael): for now a new_item is just the first item
        # in a comparison because we don't use it now,
        # but fix it if we use new_item.
        if len(sorted_items) < 2:
            continue
        result = rankobj.update(sorted_items, new_item=sorted_items[0])
        ## Uncomment next lines if we want to load/reload qdist parameters.
        ##qdist = []
        ##for x in items:
        ##    perc, avrg, stdev = result[x]
        ##    qdist.append(avrg)
        ##    qdist.append(stdev)
        ##rankobj = Rank.from_qdistr_param(items, qdist, alpha=alpha_annealing)
    # Updating the DB.
    for x in items:
        perc, avrg, stdev = result[x]
        #db((db.quality.venue_id == venue_id) &
        #   (db.quality.submission_id == x)).update(average=avrg, stdev=stdev, percentile=perc)
        # Updating submission table with its quality and error.
        db((db.submission.id == x) &
           (db.submission.venue_id == venue_id)).update(quality=avrg, error=stdev)
