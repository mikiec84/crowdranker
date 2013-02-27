# coding: utf8

import access
import util

@auth.requires_login()
def index():
    """Produces a list of the feedback obtained for a given venue,
    or for all venues."""
    venue_id = request.args(0)
    if venue_id == 'all':
        q = (db.submission.user == auth.user.email)
    else:
        q = ((db.submission.user == auth.user.email) 
            & (db.submission.venue_id == venue_id))
    db.submission.venue_id.readable = False # prevents use in form
    db.submission.title.represent = lambda x, r: A(x, _href=URL('submission', 'view_own_submission', args=[r.id]))
    grid = SQLFORM.grid(q,
        fields=[db.submission.id, db.submission.title, db.submission.date_created,
		db.submission.date_updated, db.submission.venue_id],
        csv=False, details=False, create=False, editable=False, deletable=False,
        args=request.args[:1],
        user_signature=False,
        links=[
            dict(header=T('Venue'), body = lambda r: 
                A(get_venue_name(r.venue_id), _href=URL('venues', 'view_venue', args=[r.venue_id]))),
            dict(header=T('Feedback'), body = lambda r:
                A(T('View'), _class='btn', _href=URL('feedback', 'view_feedback', args=[r.id]))),
            ],
        )
    return dict(grid=grid)

def get_venue_name(venue_id):
    n = db(db.venue.id == venue_id).select(db.venue.name).first()
    if n == None:
        return ''
    return n.name

@auth.requires_login()
def view_feedback():
    """Shows detailed information and feedback for a given submission."""
    subm = db.submission(request.args(0)) or redirect(URL('default', 'index'))
    # Checks whether the user is a manager for the venue.
    c = db.venue(subm.venue_id) or redirect(URL('default', 'index'))
    props = db(db.user_properties.user == auth.user.email).select().first()
    if props == None:
	session.flash = T('Not authorized.')
	redirect(URL('default', 'index'))
    is_author = (subm.user == auth.user.email)
    can_view_feedback = access.can_view_feedback(c, props) or is_author
    if (not can_view_feedback):
        session.flash = T('Not authorized.')
        redirect(URL('default', 'index'))
    if can_view_feedback and (
	    not ((datetime.utcnow() > c.rate_close_date) or c.feedback_accessible_immediately)):
        session.flash = T('The ratings are not yet available.')
        redirect(URL('feedback', 'index', args=['all']))
    if is_author:
        download_link = A(T('Download'), _class='btn', 
		      _href=URL('submission', 'download_author', args=[subm.id, subm.content]))
    else:
        download_link = A(T('Download'), _class='btn', 
		      _href=URL('submission', 'download_manager', args=[subm.id, subm.content]))
    venue_link = A(c.name, _href=URL('venues', 'view_venue', args=[c.id]))
    subm_link = None
    if c.allow_link_submission:
	subm_link = A(subm.link, _href=subm.link)
    db.submission.identifier.readable = True
    db.submission.percentile.readable = True
    db.submission.comment.readable = True
    db.submission.feedback.readable = True
    if access.can_observe(c, props):
	db.submission.quality.readable = True
	db.submission.error.readable = True
    # Reads the grade information.
    percentile = None
    if c.latest_rank_update_date is not None and c.latest_rank_update_date < datetime.utcnow():
	percentile = represent_percentage(subm.percentile, None)
    final_grade = None
    if c.latest_final_grades_evaluation_date is not None and c.latest_final_grades_evaluation_date < datetime.utcnow():
	fg = db((db.grades.user == subm.user) & (db.grades.venue_id == c.id)).select(db.grades.grade).first()
	if fg != None:
	    final_grade = represent_percentage(fg.grade, None)
    review_accuracy = None
    if c.latest_reviewers_evaluation_date is not None and c.latest_reviewers_evaluation_date < datetime.utcnow():
	ra = db((db.user_accuracy.user == subm.user) & (db.user_accuracy.venue_id == c.id)).select().first()
	if ra != None:
	    review_accuracy = represent_percentage(ra.reputation * 100.0, None)
    # Makes a grid of comments.
    db.task.submission_name.readable = False
    db.task.assigned_date.readable = False
    db.task.completed_date.readable = False
    db.task.rejected.readable = True
    db.task.is_bogus.readable = db.task.is_bogus.writable = True
    db.task.why_bogus.readable = db.task.why_bogus.writable = True
    db.task.why_bogus.label = T('Reason why the review is bogus')
    # Prevent editing the comments; the only thing editable should be the "is bogus" field.
    db.task.comments.writable = False
    db.task.rejection_comment.writable = False
    if access.can_observe(c, props):
	db.task.user.readable = True
	db.task.completed_date.readable = True
	links = [
	    dict(header=T('Review'), body= lambda r:
		 A(T('View'), _class='btn', _href=URL('ranking', 'view_comparison', args=[r.id]))),
	    ]
	details = False
    else:
	links = []
	details = True
    q = (db.task.submission_id == subm.id)
    grid = SQLFORM.grid(q,
	details = details,
        csv=False, create=False, editable=True, deletable=False, searchable=False,
	links=links,
	user_signature=False,
        args=request.args[:1],
        )
    return dict(subm=subm, download_link=download_link, subm_link=subm_link,
		percentile=percentile, final_grade=final_grade, review_accuracy=review_accuracy,
		venue_link=venue_link, grid=grid)
