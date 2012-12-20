#!/usr/bin/python

import numpy as np
import random
import matplotlib.pyplot as plt
import time
import scipy
import scipy.stats
import scipy.stats.distributions
import math

class Cost:
    """ Class contains cost function.
    """
    def __init__(self, cost_type='top-k'):
        self.cost_type = cost_type

    def calculate(self, i, k, id2rank):
        # ranking starts from 0, so first k rank are 0, 1, ..., k - 1
        if self.cost_type == 'top-k':
            if id2rank[i] < k:
                return 1
            else:
                return 0
        elif self.cost_type == 'one_over_rank':
            return  1./( 1 + id2rank[i])
        elif self.cost_type == 'two_steps':
            if id2rank[i] < k:
                return 1
            if id2rank[i] < 3 * k / 2:
                return 0.5
            return 0
        elif self.cost_type == 'piecewise':
            a = 0.25
            x = id2rank[i]
            if x < k:
                return (-1) * a / k * x + 1 + a
            if x < 2 * k:
                return - 1. / k * x + 2
            return 0
        elif self.cost_type == 'smooth-top-k':
            beta = 2
            return 1.0 / (1 + (id2rank[i]/float(k)) ** beta)
        else:
            raise Exception('Cost funtion type is not specified')


class Rank:
    """ Class contains methods for ranking items based on items comparison.
    """
    def __init__(self, items, alpha=0.9, num_bins=2001,
                 cost_obj=None, init_dist_type='gauss'):
        """
        Arguments:
            - items is a list of original items id.
              function. If cost_obj is None then we don't use any
              reward function and treat each item equally.
            - alpha is the annealing coefficient for distribution update.
            - num_bins is the number of histogram bins.
            - cost_obj is an object of type Cost, in other words it is reward
            - init_distr_type is type of ditribution we use for initialization
              quality distributions
        """
        # items are indexed by 0, 1, ..., num_items - 1 in the class but
        # "outside" they have ids from orig_items_id, so orig_items_id[n]
        # is original id of item n.
        self.orig_items_id = items
        num_items = len(items)
        self.num_items = num_items
        self.num_bins = num_bins
        self.cost_obj = cost_obj
        self.alpha = alpha
        # qdistr is numpy two dimensional array which represents quality
        # distribution, i-th row is a distribution for an item with id equals i.
        # qdistr is initialized as uniform distribution.
        if init_dist_type == 'unif':
            self.qdistr = np.zeros((num_items ,num_bins)) + 1./num_bins
        elif init_dist_type == 'gauss':
            # Does a Gaussian distribution centered in the center.
            print num_items, num_bins
            x, y = np.mgrid[0:num_items, 0:num_bins]
            self.qdistr = scipy.stats.distributions.norm.pdf(y, loc=num_bins / 2, scale = num_bins / 8)

            # Normalization.
            self.qdistr = self.qdistr / np.sum(self.qdistr, 1) [:, np.newaxis]
            self.qdistr_init = self.qdistr.copy()
            # Plotting, for testing.
            #plt.plot(self.qdistr[0, :])
            #plt.draw()
            #time.sleep(2)
            #plt.close('all')

        self.rank2id, self.id2rank = self.compute_ranks(self.qdistr)
        # generate true items quality and rank
        self.generate_true_items_quality()
        self.rank2id_true, self.id2rank_true = \
                                            self.compute_ranks(self.qdistr_true)
        # Computing true quality vector; quality_true[i] is true quality
        # of item i.
        #self.quality_true = self.avg(self.qdistr_true)
        self.quality_true = self.num_items - self.id2rank_true

    @classmethod
    def from_qdistr_param(cls, items, qdistr_param, alpha=0.9,
                         num_bins=2001, cost_obj=None):
        """ Alternative constructor for creating rank object
        from quality distributions parameters.
        Arguments are the same like in __init__ method but qdistr_param
        is a list with mean and stdev for each item such that qdistr_param[2*i]
        and qdistr[2*i + 1] are mean and stdev for items[i].
        """
        result = cls(items, alpha, num_bins, cost_obj, init_dist_type='gauss')
        result.restore_qdistr_from_parameters(qdistr_param)
        return result

    def plot_distributions(self, hold=False, **kwargs):
        plt.clf()
        for i in range(self.num_items):
            plt.plot(self.qdistr[i, :])
        #plt.title(self.get_title_for_plot(**kwargs))
        if hold:
            plt.show()
        else:
            plt.ioff()
            plt.draw()
        time.sleep(.3)

    def get_title_for_plot(self, **kwargs):
        result = ''
        for key in kwargs:
            result += '%s %s, ' % (key, kwargs[key])
        result += 'raking error %s %%, ' % self.get_ranking_error()
        result += 'quality metric %s ' % self.get_quality_metric()
        return result


    def generate_true_items_quality(self):
        identity = np.eye(self.num_items)
        zeros = np.zeros((self.num_items, self.num_bins - self.num_items))
        self.qdistr_true = np.hstack((identity, zeros))


    def compute_ranks(self, quality_distr):
        """ Returns two vectors: id2rank and rank2id.
        id2rank[i] is a rank of an item with id i.
        rank2id[i] is an id of an item with rank i.
        """
        avg = self.avg(quality_distr)
        rank2id = avg.argsort()[::-1]
        id2rank = rank2id.argsort()
        return rank2id, id2rank

    def compute_percentile(self):
        # Rank is from 0, 1, ..., num_items - 1
        val = 100 / float(self.num_items)
        id2percentile = [val * (self.num_items - self.id2rank[i])
                                        for i in range(self.num_items)]
        return id2percentile

    def avg(self, quality_distr):
        """ returns vector v with average qualities for each item.
        v[i] is the average quality of the item with id i.
        """
        # grid_b is a matrix consisting of vertically stacked vector
        # (0, 1, ..., num_bins - 1)
        grid_b, _ = np.meshgrid(np.arange(self.num_bins),
                                     np.arange(self.num_items))
        # Actually values are from 1 to num_bins.
        grid_b = grid_b + 1
        # avg[i] is expected value of quality distribution for item with id i.
        avg = np.sum(quality_distr * grid_b, 1)
        return avg


    def update(self, sorted_items, new_item):
        """ Main update function.
        Given sorted_items and new_item it updates quality distributions and
        items ranks.
        Method returns dictionary d such that d['sumbission id'] is a list
        [percentile, average, stdev], i.e. percentile of the submission,
        average and stdev of quaility distribution of it.

        Arguments:
            - sorted_items is a list of items sorted by user such that
            rank(sorted_items[i]) > rank(sorted_items[j]) for i > j

            - new_item is an id of a submission from sorted_items which was new
            to the user. If sorted_items contains only two elements then
            new_item is None.
        """
        # todo(michael): For now, we don't care about new item.
        sorted_ids = [self.orig_items_id.index(x) for x in sorted_items]
        self.n_comparisons_update(sorted_ids)
        id2percentile = self.compute_percentile()
        qdistr_param = self.get_qdistr_parameters()
        result = {}
        for idx in xrange(self.num_items):
            avrg = qdistr_param[2 * idx]
            stdev = qdistr_param[2 * idx + 1]
            result[self.orig_items_id[idx]] = (id2percentile[idx], avrg, stdev)
        print 'rank2id'
        print self.rank2id
        return result

    def n_comparisons_update(self, descend_list):
        """ Updates quality distributions given n ordered items.
        Item id is from set {0, 1, ..., num_items - 1}
        Bins are 0, 1, ..., num_bins - 1

        descend_list is a list of id's such that
        rank(descend_list[i]) > rank(descend_list[j]) if i > j
        """
        n = len(descend_list)
        factorial = math.factorial(n)
        # Let's denote quality of element descend_list[i] as zi, then
        # z0 < z1 < ... < z(n-1) where n is length of descend_list.

        # v[0, x] = Pr(x < z(n-1))
        # v[1, x] = Pr(x < z(n-2) < z(n-1))
        # v[i, x] = Pr(x < z(n-1-i) < ... < z(n-1))
        # v[n-2, x] = Pr(x < z1 < ... < z(n-1))
        v = np.zeros((n - 1, self.num_bins))
        q = self.qdistr[descend_list[n-1], :]
        v[0,:] = 1 - np.cumsum(q)

        # w[0, x] = Pr(z0 < x)
        # w[1, x] = Pr(z0 < z1 < x)
        # w[i, x] = Pr(z0 < z1 < ... < z(i) < x)
        # w[n-2, x] = Pr(z0 < z1 < ... < z(n-2) < x)
        w = np.zeros((n - 1, self.num_bins))
        q = self.qdistr[descend_list[0], :]
        w[0,:] = np.cumsum(q) - q

        # Filling v and w.
        for idx in xrange(1, n - 1, 1):
            # Matrix v.
            # Calculating v[idx,:] given v[idx-1,:].
            t = self.qdistr[descend_list[n - 1 - idx], :] * v[idx - 1, :]
            t = t[::-1]
            t = np.cumsum(t)
            # Shift.
            t = self.shift_vector(t)
            v[idx,:] = t[::-1]

            # Matrix w.
            # Calculating w[idx,:] given w[idx-1,:].
            t = self.qdistr[descend_list[idx], :] * w[idx - 1, :]
            t = np.cumsum(t)
            t = self.shift_vector(t)
            w[idx,:] = t
        # Updating distributions.
        # Update first distributions.
        idx = descend_list[0]
        q = self.qdistr[idx,:]
        q_prime = q * v[-1, :]
        self.qdistr[idx,:] = (1.0/factorial) * (1 - self.alpha) * q + \
                                                           self.alpha * q_prime
        self.qdistr[idx,:] = self.qdistr[idx,:] / np.sum(self.qdistr[idx,:])
        # Update last distributions.
        idx = descend_list[-1]
        q = self.qdistr[idx,:]
        q_prime = q * w[-1, :]
        self.qdistr[idx,:] = (1.0/factorial) * (1 - self.alpha) * q + \
                                                           self.alpha * q_prime
        self.qdistr[idx,:] = self.qdistr[idx,:] / np.sum(self.qdistr[idx,:])
        # Update the rest of distributions.
        for i in range(1, n - 1, 1):
            idx = descend_list[i]
            q = self.qdistr[idx,:]
            q_prime = q * w[i - 1, :] * v[-(i+1), :]
            self.qdistr[idx,:] = (1.0/factorial) * (1 - self.alpha) * q + \
                                                           self.alpha * q_prime
            self.qdistr[idx,:] = self.qdistr[idx,:] / np.sum(self.qdistr[idx,:])

        # Update id2rank and rank2id vectors.
        self.rank2id, self.id2rank = self.compute_ranks(self.qdistr)

    def sample(self):
        """ Returns two items to compare.
        Sampling by loss-driven comparison
        algorithm.
        """
        # l is num_items^2 array; l[idx] is expected loss of for items with ids
        # idx/num_items and idx%num_items
        l = np.zeros(self.num_items ** 2)
        for i in xrange(self.num_items):
            for j in xrange(self.num_items):
                    # We are choosing pairs (i, j) such that p(i) < p(j)
                    if self.id2rank[i] < self.id2rank[j]:
                        l[i * self.num_items + j] = self.get_expected_loss(i, j)
                    else:
                        l[i * self.num_items + j] = 0
        # normalization
        l /= l.sum()

        # randomly choosing a pair
        cs = l.cumsum()
        rn = np.random.uniform()
        idx = cs.searchsorted(rn)
        i, j = idx/self.num_items, idx%self.num_items
        # sanity check
        if self.id2rank[i] >= self.id2rank[j]:
            raise Exception('There is an error in sampling!')
        return i, j

    def sample_n_items(self, n):
        items = set()
        while True:
            i,j = self.sample()
            items.add(i)
            items.add(j)
            if len(items) == n:
                return list(items)
            if len(items) > n:
                items.remove(i if random.random() < 0.5 else j)
                return list(items)

    def sample_item(self, old_items):
        """ Method samples an item given items the user receivd before.
        If old_items is None then method returns 2 items to compare.
        """
        if old_items == None:
            l = self.sample_n_items(2)
            return [self.orig_items_id[x] for x in l]

        taken_ids = [idx for idx in range(self.num_items) if \
                        self.orig_items_id[idx] in old_items]
        free_ids = [idx for idx in range(self.num_items) if \
                        not self.orig_items_id[idx] in old_items]
        # l[idx] is expected loss of for items with ids
        # idx/len(taken_ids) and idx%len(taken_ids)
        l = np.zeros(len(taken_ids) * len(free_ids))
        for i in xrange(len(taken_ids)):
            for j in xrange(len(free_ids)):
                    ii = taken_ids[i]
                    jj = free_ids[j]
                    if self.id2rank[ii] < self.id2rank[jj]:
                        l[i * len(free_ids) + j] = self.get_expected_loss(ii, jj)
                    else:
                        l[i * len(free_ids) + j] = self.get_expected_loss(jj, ii)
        # normalization
        #print l
        l /= l.sum()

        # randomly choosing a pair
        cs = l.cumsum()
        rn = np.random.uniform()
        idx = cs.searchsorted(rn)
        i, j = idx/len(free_ids), idx%len(free_ids)
        ii = taken_ids[i]
        jj = free_ids[j]
        # sanity check
        #if self.id2rank[ii] >= self.id2rank[jj]:
        #    raise Exception('There is an error in sampling!')
        return self.orig_items_id[jj]

    def shift_vector(self, vec):
        """ Shifts vector one position right filling the most left element
        with zero.
        """
        vec[1:] = vec[:-1]
        vec[0] = 0
        return vec

    def get_expected_loss(self, i, j):
        """ Calculate expected loss l(i, j) between items i and j.
        It is implied that r(i) < r(j).
        """
        if self.cost_obj == None:
            return self.get_missrank_prob(i, j)
        c_i = self.get_cost(i, self.k, self.id2rank)
        c_j = self.get_cost(j, self.k, self.id2rank)
        #return abs(c_i + c_j - c_i * c_j) * self.get_missrank_prob(i, j)
        return abs(c_i - c_j) * self.get_missrank_prob(i, j)

    def get_cost(self, i, j, id2rank):
        return self.cost_obj.calculate(i, j, id2rank)

    def get_missrank_prob(self, i, k):
        """ Method returns probability that r(i) > r(k) where r(i) is a rank
        of an item with id i.
        """
        q_k = self.qdistr[k, :]
        Q_i = np.cumsum(self.qdistr[i, :])
        prob = np.dot(q_k, Q_i)
        return prob

    def get_quality_metric(self):
        """ Returns quality metric for current quality distribution.
        """
        q_true = np.sum(self.quality_true[self.rank2id_true[0:self.k]])
        q_alg = np.sum(self.quality_true[self.rank2id[0:self.k]])
        val = (q_true - q_alg) / float(self.k)
        return val

    def get_ranking_error(self):
        """ Get ranking error, i.e. ratio of number of items which wrongly
        have rank less than k to the constant k.
        """
        counter = 0
        for idx in xrange(self.num_items):
            if self.id2rank_true[idx] >= self.k and self.id2rank[idx] < self.k:
                counter += 1
        return 100 * float(counter)/self.k

    def get_qdistr_parameters(self):
        """ Method returns array w such that w[2*i], w[2*i+1] are mean and
        standard deviation of quality distribution of item i (self.qdist[i])
        """
        w = np.zeros(2 * self.num_items)
        val = range(self.num_bins)
        for i in xrange(self.num_items):
            p = self.qdistr[i,:]
            w[2 * i] = np.sum(p * val)
            w[2 * i + 1] = np.sqrt(np.sum(p * (val - w[2 * i]) ** 2))
        return w

    def restore_qdistr_from_parameters(self, w):
        """ Method restores quality distributions from array w returned by
        get_qdistr_parameters: w such that w[2*i], w[2*i+1] are mean and
        standard deviation of quality distribution of item i
        """
        self.qdist = np.zeros((self.num_items, self.num_bins))
        y = range(self.num_bins)
        for i in xrange(self.num_items):
            mean = w[2 * i]
            std = w[2 * i + 1]
            self.qdistr[i,:] = scipy.stats.distributions.norm.pdf(y, loc=mean,
                                                                scale=std)
            if np.sum(self.qdistr[i,:]) == 0:
                print 'ERROR, sum should not be zero !!!'
        # Normalization.
        self.qdistr = self.qdistr / np.sum(self.qdistr, 1) [:, np.newaxis]


    def sort_items_truthfully(self, items):
        """ Method is for testing purposes.
        It simulates sorting by a truthful user.
        Returns sorted list of items so rank(result[i]) > rank(result[j])
        if i > j.
        """
        items_ids = [idx for idx in range(self.num_items) if \
                        self.orig_items_id[idx] in items]
        values = np.array(self.quality_true)[items_ids]
        idx = np.argsort(values)
        return [self.orig_items_id[x] for x in np.array(items_ids)[idx]]
