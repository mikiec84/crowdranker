#!/usr/bin/env python
# coding: utf8
from gluon import *
from rank import Rank

NUM_BINS = 2001
AVRG = num_bins / 2
STDEV = num_bins / 8

def get_all_items_and_qdistr_param(db, contest_id):
    """ Returns a tuple (items, qdistr_param) where:
        - itmes is a list of submissions id.
        - qdistr_param[2*i] and qdistr_param[2*i + 1] are mean and standard
        deviation for a submission items[i].
    """
    # List of all submissions id for given contest.
    items = []
    sub = db(db.submission.contest_id == contest_id).select(db.submission.id)
    # Fetching quality distributions parametes for each submission.
    qdistr_param = []
    for x in sub:
        items.append(x.id)
        quality = db((db.quality.contest_id == contest_id) &
                  (db.quality.submission_id == x.id)).select(db.quality.average,
                  db.quality.stdev).first()
        # TODO(mshavlov): check that I correctly deal with quality == None
        if quality == None:
            return None, None
        qdistr_param.append(quality.average)
        qdistr_param.append(quality.stdev)
    # Ok, items and qdistr_param are filled.
    return items, qdistr_param

def get_init_average_stdev():
    """ Method returns tuple with average and stdev for initializing
    field in table quality.
    """
    return AVRG, STDEV

def get_item(db, contest_id, user_id, old_items):
    """
    If a user did not have items to rank then old_items is None. In this case
    function returns two items to compare.
    """
    items, qdistr_param = get_all_items_and_qdistr_param(db, contest_id)
    # If items is None then some submission does not have qualities yet,
    # we need to know qualities of for all submission to correctly choose an
    # item.
    if items == None:
        return None
    rankobj = Rank.from_qdistr_param(items, qdistr_param)
    # Find submission that is authored by the user.
    user_submission_id = db((db.submission.contest_id == contest_id) &
                            (db.submission.author == user_id)).select(db.submissions.id).first()
    return rankobj.sample_item(old_items, user_submission_id)

def process_comparison(db, contest_id, user_id, sorted_items, new_item):
    """ Function updates quality distributions and rank of submissions (items).

    Arguments:
        - sorted_items is a list of submissions id sorted by user such that
        rank(sorted_items[i]) > rank(sorted_items[j]) for i > j

        - new_item is an id of a submission from sorted_items which was new
        to the user. If sorted_items contains only two elements then
        new_item is None.
    """
    # TODO(mshavlov): discuss concurrency issue
    # as an example (db(query).select(..., for_update=True))
    items, qdistr_param = get_all_items_and_qdistr_param(db, contest_id)
    # If items is None then some submission does not have qualities yet,
    # therefore we cannot process comparison.
    if items == None:
        return None
    rankobj = Rank.from_qdistr_param(items, qdistr_param)
    result = rankobj.update(sorted_items, new_item)
    # Updating the DB.
    for x in items:
        perc, avrg, stdev = result[x]
        db((db.quality.contest_id == contest_id) &
           (db.quality.submission_id == x)).update(average=avrg,
                                                     stdev=stdev,
                                                percentile=perc)
