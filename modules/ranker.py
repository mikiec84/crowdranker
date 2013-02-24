#!/usr/bin/env python
# coding: utf8
from gluon import *
from rank import Rank
from rank import Cost
import util
from datetime import datetime
import numpy as np
import random

NUM_BINS = 2001
AVRG = NUM_BINS / 2
STDEV = NUM_BINS / 8

def get_all_items_qdistr_param_and_users(db, venue_id):
    """ Returns a tuple (items, qdistr_param) where:
        - itmes is a list of submissions id.
        - qdistr_param[2*i] and qdistr_param[2*i + 1] are mean and standard
        deviation for a submission items[i].
    """
    # List of all submissions id for given venue.
    items = []
    sub_records = db(db.submission.venue_id == venue_id).select()
    # Fetching quality distributions parametes for each submission.
    users_list = []
    qdistr_param = []
    for sub_row in sub_records:
        users_list.append(sub_row.user)
        items.append(sub_row.id)
        if sub_row.quality is None or sub_row.error is None:
            qdistr_param.append(AVRG)
            qdistr_param.append(STDEV)
        else:
            qdistr_param.append(sub_row.quality)
            qdistr_param.append(sub_row.error)
    # Get rid of duplicates. It can be a case when users have multiple submission.
    users_list = list(set(users_list))
    # Ok, items, qdistr_param  and users_list are filled.
    return items, qdistr_param, users_list

def get_qdistr_param(db, venue_id, items_id):
    if items_id == None:
        return None
    qdistr_param = []
    for x in items_id:
        quality_row = db((db.submission.venue_id == venue_id) &
                  (db.submission.id == x)).select(db.submission.quality,
                  db.submission.error).first()
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

def get_item(db, venue_id, user, old_items,
             can_rank_own_submissions=False,
             rank_cost_coefficient=0):
    """
    If a user did not have items to rank then old_items is None or empty string.

    If rank_cost_coefficient is equal zero then no cost function is used which
    corresponds to treating each submission equally.

    Description of a sampling method:
        For each submission we count how many time it was assigned as a task.
        Choose subset (rare_items) of submissions which have the smallest frequency.
        Then we compute probability of all possible mistaken comparisons
        between rare_items and old_items (item from previous tasks).
        After that we randomly sample an item proportional of probability of
        a mistake with the item.

        Note that code wich randomly samples item is in Rank.sample_item(...).
        To ensure that sampled item is from rare_items we initialize
        Rank object (rankobj) only with pool items which is a union of
        rare_items  and old_items.
        This way item is sampled as described above.
    """
    if old_items is None:
        old_items = []
    items, qdistr_param, _ = get_all_items_qdistr_param_and_users(db, venue_id)
    # If items is None then some submission does not have qualities yet,
    # we need to know qualities of for all submission to correctly choose an
    # item.
    if items == None or len(items) == 0:
        return None
    # Specifying cost object which implements cost function.
    cost_obj = Cost(cost_type='rank_power_alpha',
                   rank_cost_coefficient=rank_cost_coefficient)
    if rank_cost_coefficient == 0:
        cost_obj = None
    if not can_rank_own_submissions:
        # Find submission that is authored by the user.
        submission_ids = db((db.submission.venue_id == venue_id) &
                                (db.submission.user == user)).select(db.submission.id)
        users_submission_ids = [x.id for x in submission_ids]
    else:
        users_submission_ids = []
    # Counting how many times each submission was assigned.
    # TODO(michael): use the field in the submissions, once we confirm that this works.
    frequency = []
    for subm_id in items:
        if (subm_id not in users_submission_ids and
            subm_id not in old_items):
            count = db((db.task.submission_id == subm_id) &
                       (db.task.venue_id == venue_id)).count()
            frequency.append((subm_id, count))
    # Do we have items to sample from?
    if len(frequency) == 0:
        return None
    # Now let's find submissions which have the smalles count number.
    min_count = min([x[1] for x in frequency])
    rare_items = [x[0] for x in frequency if x[1] == min_count]
    if len(rare_items) == 1:
        return rare_items[0]
    # Constructing pool of items.
    pool_items = rare_items[:]
    pool_items.extend(old_items)
    # Fetching quality distribution parameters.
    qdistr_param_pool = []
    for subm_id in pool_items:
        idx = items.index(subm_id)
        qdistr_param_pool.append(qdistr_param[2 * idx])
        qdistr_param_pool.append(qdistr_param[2 * idx + 1])
    rankobj = Rank.from_qdistr_param(pool_items, qdistr_param_pool,
                                     cost_obj=cost_obj)
    return rankobj.sample_item(old_items, black_items=[])

def process_comparison(db, venue_id, user, sorted_items, new_item,
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
        # Updating submission table with its quality and error.
        db((db.submission.id == x) &
           (db.submission.venue_id == venue_id)).update(quality=avrg, error=stdev)
        # Saving then latest rank update date.
        db(db.venue.id == venue_id).update(latest_rank_update_date = datetime.utcnow())


def evaluate_contributors(db, venue_id):
    """This function evaluates reviewers for a venue.
    Currently, this based on last comparisons made by each reviewer.
    TODO(luca,michael): should we use all comparisons instead?"""

    items, qdistr_param, _ = get_all_items_qdistr_param_and_users(db, venue_id)
    if items == None or len(items) == 0:
        return None
    # Obtaining list of users who did comparisons.
    comp_r = db(db.comparison.venue_id == venue_id).select(db.comparison.user)
    list_of_users = [x.user for x in comp_r]
    list_of_users = list(set(list_of_users))

    rankobj = Rank.from_qdistr_param(items, qdistr_param, cost_obj=None)
    for user in list_of_users:
        last_comparison = db((db.comparison.user == user)
            & (db.comparison.venue_id == venue_id)).select(orderby=~db.comparison.date).first()
        if last_comparison == None:
            # Deleting the db.user_accuracy fot this venu_id and user.
            db((db.user_accuracy.venue_id == venue_id) & (db.user_accuracy.user == user)).delete()
            continue
        ordering = util.get_list(last_comparison.ordering)
        ordering = ordering[::-1]
        val = rankobj.evaluate_ordering(ordering)
        # Normalization
        num_subm_r = db(db.venue.id == venue_id).select(db.venue.number_of_submissions_per_reviewer).first()
        if num_subm_r is None or num_subm_r.number_of_submissions_per_reviewer is None:
            # For compatability with venues which do not have the constant.
            num_subm = 5
        else:
            num_subm = num_subm_r.number_of_submissions_per_reviewer
        # TODO(michael): num_subm can be zero, take care of it.
        val = min(1, val/float(num_subm))
        # Writing to the DB.
        db.user_accuracy.update_or_insert((db.user_accuracy.venue_id == venue_id) &
                                          (db.user_accuracy.user == user),
                                           venue_id = venue_id,
                                           user = user,
                                           accuracy = val,
                                           reputation = None,
                                           n_ratings = len(ordering) )
    # Saving the latest user evaluation date.
    db(db.venue.id == venue_id).update(latest_reviewers_evaluation_date = datetime.utcnow())


def rerun_processing_comparisons(db, venue_id, alpha_annealing=0.5, run_twice=False):

    # We reset the ranking to the initial values.
    # Gets a ranker object to do the ranking, initialized with all the submissions with
    # their default stdev and avg. 
    sub = db(db.submission.venue_id == venue_id).select(db.submission.id)
    items = []
    qdistr_param = []
    for x in sub:
        items.append(x.id)
        qdistr_param.append(AVRG)
        qdistr_param.append(STDEV)
    rankobj = Rank.from_qdistr_param(items, qdistr_param, alpha=alpha_annealing)

    # Processes the list of comparisons.
    result = None
    comparison_list = db(db.comparison.venue_id == venue_id).select(orderby=db.comparison.date)
    for comp in comparison_list:
	# Processes the comparison, if valid.
	if comp.is_valid is None or comp.is_valid == True:
	    # Reverses the list.
	    sorted_items = util.get_list(comp.ordering)[::-1]
	    if len(sorted_items) < 2:
		continue
	    result = rankobj.update(sorted_items, new_item=comp.new_item)
    if run_twice:
	comparison_list = db(db.comparison.venue_id == venue_id).select(orderby=~db.comparison.date)
	for comp in comparison_list:
	    # Processes the comparison, if valid.
	    if comp.is_valid is None or comp.is_valid == True:
		# Reverses the list.
		sorted_items = util.get_list(comp.ordering)[::-1]
		if len(sorted_items) < 2:
		    continue
		result = rankobj.update(sorted_items, new_item=comp.new_item)

    # Writes the updated statistics to the db.  Note that result contains the result for
    # all the ids, due to how the rankobj has been initialized.
    if result is None:
        return
    for x in items:
        perc, avrg, stdev = result[x]
        db((db.submission.id == x) &
           (db.submission.venue_id == venue_id)).update(quality=avrg, error=stdev, percentile=perc)
    # Saving the latest rank update date.
    db(db.venue.id == venue_id).update(latest_rank_update_date = datetime.utcnow())


def compute_final_grades(db, venue_id):
    # Assume that each user has only one submission
    list2sort = []
    submission_recods = db(db.submission.venue_id == venue_id).select()
    if submission_recods is None:
        return
    for sub_row in submission_recods:
        list2sort.append((sub_row.user, sub_row.quality))
    list2sort = sorted(list2sort, key=lambda x : x[1], reverse=True)
    ##id_to_rank = {}
    rank_grade = {}
    rank = 1
    for x in list2sort:
        ##id_to_rank[x[0]] = rank
        rank_grade[x[0]] = (len(list2sort) - rank + 1)/float(len(list2sort))
        rank += 1
    # Obtaining reviewers grade.
    user_accuracy_records = db(db.user_accuracy.venue_id == venue_id).select()
    reviewer_grade = {}
    for r in user_accuracy_records:
	# We use the reputation, not the reviewing accuracy.
        reviewer_grade[r.user] = r.reputation
    # Computing final grade
    final_grades = {}
    for user in rank_grade:
        val = (2/3.0) * rank_grade[user]
        if reviewer_grade.has_key(user):
            val += (1/3.0) * reviewer_grade[user]
        final_grades[user] = val * 100
    # Writting result to the DB.
    for user_id in final_grades:
        db.grades.update_or_insert((db.grades.venue_id == venue_id) &
                                   (db.grades.user == user),
                                   venue_id = venue_id,
                                   author = user_id,
                                   grade = final_grades[user])
    # Saving the latest date when final grades were evaluated.
    db(db.venue.id == venue_id).update(latest_final_grades_evaluation_date = datetime.utcnow())

def run_reputation_system(db, venue_id, alpha_annealing=0.5,
                          num_of_iterations=4, last_compar_param=10,
                          average_result=False):
    """ Function calculates:
            - reputation for each user
            - user precision (quality as a reviewer)

        last_compar_param affects on how we use user's comparisons.
            If it is None then we user all comparisons one time.
            Else:
            Case average_result is False then:
                For each reviewer we user ONLY the last comparison n times.
            Case average_result is True, then:
                We do regular updates with ONLY last comparisons
                last_compar_param times and in the take average.

        average_result affects the way we average calculations (calculations
            depends on the order we process comparisons). If value is
            - True then we do regular comparisons and average final results
            - False then we do multiple updates with small alpha.



    """
    # Fetching submission id and authors.
    # TODO(michael): take care of a case when a user has multiple submission.
    sub = db(db.submission.venue_id == venue_id).select(db.submission.id,
                                                        db.submission.user)
    items = []
    author2item = {}
    qdistr_param_default = []
    for x in sub:
        items.append(x.id)
        author2item[x.user] = x.id
        qdistr_param_default.append(AVRG)
        qdistr_param_default.append(STDEV)
    # Fetching list of comparisons.
    comparison_list_r = db(db.comparison.venue_id == venue_id).select(orderby=db.comparison.date)
    # Creating dictionaries
    # author: reputation
    # author: accuracy (confedence or reviewer's grade)
    # author: last ordering
    author2rep, author2accuracy, author2ordering = {}, {}, {}
    # Ordering list is a list of tuples (ordering, author of the orderingj).
    ordering_list = []
    # Initializing these dictionaries and ordering_list.
    for comp in comparison_list_r:
        # Check if comparison is valid.
        if comp.is_valid is None or comp.is_valid == True:
            # Reverses the list.
            sorted_items = util.get_list(comp.ordering)[::-1]
            if len(sorted_items) < 2:
                continue
            author2ordering[comp.user] = sorted_items
            # Initializing reviewers reputation and accuracy.
            author2rep[comp.author] = alpha_annealing
            author2accuracy[comp.user] = -1
            ordering_list.append((sorted_items, comp.user))
    # If we want to use only last comparisons.
    if not last_compar_param is None:
        ordering_list = [(ordering, author) for author, ordering in
                                                    author2ordering.iteritems()]
    # Okay, now we are ready to run main iterations.
    result = None
    for it in xrange(num_of_iterations):
        # In the beginning of iteration initialize rankobj with default
        # items qualities.
        rankobj = Rank.from_qdistr_param(items, qdistr_param_default,
                                         alpha=alpha_annealing)
        # Okay, now we update quality distributions with comparisons
        # using reputation of users as annealing coefficient.
        if last_compar_param is None:
            for ordering, author in ordering_list:
                alpha = author2rep[author]
                result = rankobj.update(ordering, alpha_annealing=alpha)
        else:
            if not average_result:
                ######## iterate many times with small alpha ##########
                for i in xrange(last_compar_param):
                    idxs = range(len(ordering_list))
                    random.shuffle(idxs)
                    for idx in idxs:
                        ordering, author = ordering_list[idx]
                        alpha = author2rep[author]
                        alpha = 1 - (1 - alpha) ** (1.0/(4*last_compar_param))
                        #alpha = alpha / float(2*last_compar_param)
                        result = rankobj.update(ordering, alpha_annealing=alpha)
                #######################################################
            else:
                #### Do regular update multiple times and calculate average values.
                result_avrg = {}
                n = 0
                for i in xrange(last_compar_param):
                    rankobj = Rank.from_qdistr_param(items,
                                                     qdistr_param_default,
                                                     alpha=alpha_annealing)
                    result = None
                    idxs = range(len(ordering_list))
                    random.shuffle(idxs)
                    for idx in idxs:
                        ordering, author = ordering_list[idx]
                        alpha = author2rep[author]
                        result = rankobj.update(ordering, alpha_annealing=alpha)
                    # Update average values.
                    if result is None:
                        continue
                    for item in result:
                        perc, avrg, stdev = result[item]
                        if not result_avrg.has_key(item):
                            result_avrg[item] = [-1, 0 , 0]
                        perc_, avrg_, stdev_ = result_avrg[item]
                        avrg_ = ((avrg_ * n) + avrg) / float(n + 1)
                        stdev_ = ((stdev_ * n) + stdev) / float(n + 1)
                        result_avrg[item] = (perc_, avrg_, stdev_)
                    n += 1
                # Obtaining percentile out of average quality.
                l = np.array([result_avrg[x][1] for x in result_avrg.iterkeys()])
                rank2idx = l.argsort()[::-1]
                idx2rank = rank2idx.argsort()
                val = 100 / float(len(idx2rank))
                idx = 0
                for x in result_avrg.iterkeys():
                    percentile = val * (len(idx2rank) - idx2rank[idx])
                    result_avrg[x] = (percentile, result_avrg[x][1],
                                                  result_avrg[x][2])
                    idx += 1
                result = result_avrg

        # In the end of the iteration compute reputation to use in the next iteration.
        if result is None:
            return
        for user in author2rep:
            if author2item.has_key(user):
                perc, avrg, stdev = result[author2item[user]]
                rank = perc / 100.0
            else:
                rank = 1 # TODO(michael): Should we trust unknown reviewer?
            ordering = author2ordering[user]
            accuracy = rankobj.evaluate_ordering_using_dirichlet(ordering)
            author2accuracy[user] = accuracy
            # Computer user's reputation.
            author2rep[user] = (rank * accuracy) ** 0.5
    # Updating the DB with submission ranking, users' accuracy and reputation.
    for x in items:
        perc, avrg, stdev = result[x]
        db((db.submission.id == x) &
           (db.submission.venue_id == venue_id)).update(quality=avrg, error=stdev, percentile=perc)
    for user_id in author2accuracy:
        db.user_accuracy.update_or_insert((db.user_accuracy.venue_id == venue_id) &
                                  (db.user_accuracy.user == user),
                                   venue_id = venue_id,
                                   user = user,
                                   accuracy = author2accuracy[user],
                                   reputation = author2rep[user],
                                   n_ratings = len(author2ordering[user]) )
    # Saving evaluation date.
    t = datetime.utcnow()
    db(db.venue.id == venue_id).update(latest_reviewers_evaluation_date = t,
                                       latest_rank_update_date = t)
    # Computing final grades for convenience.
    # TODO(michael): instead of calling method we can compute final directly
    # to optimize db access.
    compute_final_grades(db, venue_id)
