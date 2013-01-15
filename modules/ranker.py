#!/usr/bin/env python
# coding: utf8
from gluon import *
from rank import Rank

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
        quality = db((db.quality.venue_id == venue_id) &
                  (db.quality.submission_id == x.id)).select(db.quality.average,
                  db.quality.stdev).first()
        if quality == None:
            return None, None
        qdistr_param.append(quality.average)
        qdistr_param.append(quality.stdev)
    # Ok, items and qdistr_param are filled.
    return items, qdistr_param

def get_qdistr_param(db, venue_id, items_id):
    if items_id == None:
        return None
    qdistr_param = []
    for x in items_id:
        quality = db((db.quality.venue_id == venue_id) &
                  (db.quality.submission_id == x)).select(db.quality.average,
                  db.quality.stdev).first()
        if quality == None:
            return None
        qdistr_param.append(quality.average)
        qdistr_param.append(quality.stdev)
    return qdistr_param

def get_init_average_stdev():
    """ Method returns tuple with average and stdev for initializing
    field in table quality.
    """
    return AVRG, STDEV

def get_item(db, venue_id, user_id, old_items, can_rank_own_submissions=False):
    """
    If a user did not have items to rank then old_items is None or empty string.
    """
    items, qdistr_param = get_all_items_and_qdistr_param(db, venue_id)
    # If items is None then some submission does not have qualities yet,
    # we need to know qualities of for all submission to correctly choose an
    # item.
    if items == None or len(items) == 0:
        return None
    rankobj = Rank.from_qdistr_param(items, qdistr_param)
    if not can_rank_own_submissions:
        # Find submission that is authored by the user.
        users_submission_id = db((db.submission.venue_id == venue_id) &
                                (db.submission.author == user_id)).select(db.submission.id).first().id
    else:
        users_submission_id = None
    return rankobj.sample_item(old_items, users_submission_id)

def process_comparison(db, venue_id, user_id, sorted_items, new_item):
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
    rankobj = Rank.from_qdistr_param(sorted_items, qdistr_param)
    result = rankobj.update(sorted_items, new_item)
    # Updating the DB.
    for x in sorted_items:
        perc, avrg, stdev = result[x]
        db((db.quality.venue_id == venue_id) &
           (db.quality.submission_id == x)).update(average=avrg, stdev=stdev, percentile=perc)
        # Updating submission table with its quality and error.
        db((db.submission.id == x) &
           (db.submission.venue_id == venue_id)).update(quality=avrg, error=stdev)
