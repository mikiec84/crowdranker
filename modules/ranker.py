#!/usr/bin/env python
# coding: utf8
from gluon import *
from rank import Rank

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
        qdistr_param.append(quality.average)
        qdistr_param.append(quality.stdev)
    # Ok, items and qdistr_param are filled.
    return items, qdistr_param

def get_init_average_stdev():
    """ Method returns tuple with average and stdev for initializin
    field in table quality.
    """
    num_bins = 2001
    avrg = num_bins / 2
    stdev = num_bins / 8
    return avrg , stdev

def init_qdistr(db, contest_id, dist_type='gauss'):
    """ Initializing average and stdev values in table quality for each
    submission in given contest.
    """
    if dist_type == 'gauss':
        num_bins = 2001
        avrg = num_bins / 2
        stdev = num_bins / 8
        db(db.quality.contest_id == contest_id).update(average=avrg, stdev=stdev)
    else:
        raise Exception("Type of init distribution is not known.")


def get_item(db, contest_id, user_id, old_items):
    """
    If a user did not have items to rank then old_items is None. In this case
    function returns two items to compare.
    """
    items, qdistr_param = get_all_items_and_qdistr_param(db, contest_id)
    rankobj = Rank.from_qdistr_param(items, qdistr_param)
    return rankobj.sample_item(old_items)

def process_comparison(db, contest_id, user_id, sorted_items, new_item):
    """ Function updates quality distributions and rank of submissions (items).

    Arguments:
        - sorted_items is a list of submissions id sorted by user such that
        rank(sorted_items[i]) > rank(sorted_items[j]) for i > j

        - new_item is an id of a submission from sorted_items which was new
        to the user. If sorted_items contains only two elements then
        new_item is None.
    """
    # todo(michael): discuss concurrency issue
    # as an example (db(query).select(..., for_update=True))
    items, qdistr_param = get_all_items_and_qdistr_param(db, contest_id)
    rankobj = Rank.from_qdistr_param(items, qdistr_param)
    result = rankobj.update(sorted_items, new_item)
    # Updating the DB.
    for x in items:
        perc, avrg, stdev = result[x]
        db((db.quality.contest_id == contest_id) &
           (db.quality.submission_id == x)).update(average=avrg,
                                                     stdev=stdev,
                                                percentile=perc)
