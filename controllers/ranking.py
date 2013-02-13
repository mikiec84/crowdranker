# coding: utf8

import access
import util
from datetime import datetime
import numpy as np

@auth.requires_login()
def view_venue():
    """This function enables the view of the ranking of items submitted to a
    venue.  It is assumed that the people accessing this can have full
    information about the venue, including the identity of the submitters."""
    c = db.venue(request.args(0)) or redirect(URL('default', 'index'))
    props = db(db.user_properties.email == auth.user.email).select().first()
    if not access.can_view_submissions(c, props):
	session.flash = T('You do not have access to the submissions of this venue.')
	redirect(URL('venues', 'view_venue', args=[c.id]))
    can_view_ratings = access.can_view_ratings(c, props)
    # Prepares the query for the grid.
    q = (db.submission.venue_id == c.id)
    db.submission.quality.readable = can_view_ratings
    db.submission.error.readable = can_view_ratings
    db.submission.content.readable = False
    db.submission.title.writable = False
    db.submission.content.writable = False
    if c.allow_link_submission:
	db.submission.link.readable = True
    is_editable = False
    fields=[db.submission.title, db.submission.email, db.submission.quality, db.submission.percentile,
	    db.submission.n_completed_reviews, db.submission.error, db.submission.content]
    if access.can_enter_true_quality:
	fields.append(db.submission.true_quality)
	is_editable = True
	db.submission.true_quality.readable = db.submission.true_quality.writable = True
    links = [
	# dict(header=T('N. reviews'), body = lambda r: get_num_reviews(r.id, c.id)),
	dict(header=T('Download'), body = lambda r:
	     A(T('Download'), _class='btn',
	       _href=URL('submission', 'download_viewer', args=[r.id, r.content])))]
    if access.can_view_feedback(c, props):
	links.append(dict(header=T('Feedback'), body = lambda r:
			  A(T('Read comments'), 
			    _href=URL('feedback', 'view_feedback', args=[r.id]))))
    grid = SQLFORM.grid(q,
	field_id=db.submission.id,
	csv=True,
	args=request.args[:1],
	user_signature=False,
	details=False, create=False,
	editable=is_editable,
	deletable=False,
	fields=fields,
	links=links,
	)
    title = A(c.name, _href=URL('venues', 'view_venue', args=[c.id]))
    return dict(title=title, grid=grid)


def get_num_reviews(subm_id, venue_id):
    """This function is used to heal old databases, and produce the count
    of completed reviews for each submission.
    In future releases, this is computed automatically by the review function."""
    # Tries to answer fast.
    subm = db.submission(subm_id)
    if subm.n_completed_reviews is not None:
	return subm.n_completed_reviews
    # Computes the number of reviews for each item.
    n = db((db.task.venue_id == venue_id) &
	   (db.task.submission_id == subm.id) &
	   (db.task.completed_date < datetime.utcnow())).count()
    # Stores it in the submission.
    subm.n_completed_reviews = n
    subm.update_record()
    db.commit()
    return n


@auth.requires_login()
def view_raters():
    """This function shows the contribution of each user to the total ranking of a venue."""
    c = db.venue(request.args(0)) or redirect(URL('default', 'index'))
    props = db(db.user_properties.email == auth.user.email).select().first()
    if not access.can_view_rating_contributions(c, props):
	session.flash = T('You do not have access to the rater contributions for this venue.')
	redirect(URL('venues', 'view_venue', args=[c.id]))
    # Prepares the query for the grid.
    q = (db.user_accuracy.venue_id == c.id)
    grid = SQLFORM.grid(q,
	args=request.args[:1],
	user_signature=False, details=True,
	create=False, editable=False, deletable=False,
	fields=[db.user_accuracy.user_id, db.user_accuracy.accuracy, db.user_accuracy.n_ratings],
	)
    title = A(c.name, _href=URL('venues', 'view_venue', args=[c.id]))
    return dict(grid=grid, title=title)


@auth.requires_login()
def view_final_grades():
    """This function shows the final grade of each user.
    """
    c = db.venue(request.args(0)) or redirect(URL('default', 'index'))
    props = db(db.user_properties.email == auth.user.email).select().first()
    if not access.can_view_ratings(c, props):
	session.flash = T('You do not have access to the final grades for this venue.')
	redirect(URL('venues', 'view_venue', args=[c.id]))
    # Checking that final grades are recent and don't need recomputation.
    venue_row = db(db.venue.id == c.id).select().first()
    final_grades_date = venue_row.latest_final_grades_evaluation_date
    reviewers_eval_date = venue_row.latest_reviewers_evaluation_date
    rank_update_date = venue_row.latest_rank_update_date
    if (rank_update_date is None or
        reviewers_eval_date is None or
        final_grades_date is None or
        reviewers_eval_date < rank_update_date or
        final_grades_date < rank_update_date or
        final_grades_date < reviewers_eval_date):
        session.flash = T('Grades are not updated/computed. Please compute final grades')
        redirect(URL('venues', 'view_venue', args=[c.id]))
    # Okay, final grades are computed and are updated.
    # Prepares the query for the grid.
    q = (db.grades.venue_id == c.id)
    grid = SQLFORM.grid(q,
	args=request.args[:1],
	user_signature=False, details=True,
	create=False, editable=False, deletable=False,
	fields=[db.grades.author, db.grades.grade],
	)
    title = A(c.name, _href=URL('venues', 'view_venue', args=[c.id]))
    histogram_link = A("View gistogram of final grades",
                  _href=URL('ranking', 'view_grades_histogram', args=[c.id]))
    return dict(grid=grid, title=title, histogram_link=histogram_link)

@auth.requires_login()
def view_grades_histogram():
    c = db.venue(request.args(0)) or redirect(URL('default', 'index'))
    props = db(db.user_properties.email == auth.user.email).select().first()
    if not access.can_view_ratings(c, props):
        session.flash = T('You do not have access to the final grades for this venue.')
        redirect(URL('venues', 'view_venue', args=[c.id]))
    # TODO(michael): if we want to optimize db access we can save all grades in
    # one row.
    # Fetching grades.
    grades_records = db(db.grades.venue_id == c.id).select(db.grades.grade)
    grades = [x.grade for x in grades_records]
    # Building histogram.
    hist, bins = np.histogram(grades, bins=50 , range=(0, 100))
    hist = [(bins[i], hist[i]) for i in xrange(len(hist))]
    title = A(c.name, _href=URL('venues', 'view_venue', args=[c.id]))
    return dict(sub_title=title, hist=hist)
