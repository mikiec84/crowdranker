# coding: utf8

import util

@auth.requires_login()
def index():
    """Produces a list of the feedback obtained for a given venue,
    or for all venues."""
    venue_id = request.args(0)
    if venue_id == 'all':
        q = (db.submission.author == auth.user_id)
    else:
        q = ((db.submission.author == auth.user_id) 
            & (db.submission.venue_id == venue_id))
    db.submission.venue_id.readable = False # prevents use in form
    db.submission.title.readable = False
    grid = SQLFORM.grid(q,
        fields=[db.submission.id, db.submission.title, db.submission.date, db.submission.venue_id],
        csv=False, details=False, create=False, editable=False, deletable=False,
        args=request.args[:1],
        user_signature=False,
        links=[
            dict(header=T('Venue'), body = lambda r: 
                A(get_venue_name(r.venue_id), _href=URL('venues', 'view_venue', args=[r.venue_id]))),
            dict(header=T('Submission'), body = lambda r: 
                A(r.title, _href=URL('submission', 'view_own_submission', args=[r.id]))),
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
    is_manager = (auth.user.email in util.get_list(c.managers))
    if is_manager:
        download_link = A(T('Download'), _class='btn', 
		      _href=URL('submission', 'download_manager', args=[subm.id, subm.content]))
    else:
        download_link = A(T('Download'), _class='btn', 
		      _href=URL('submission', 'download_author', args=[subm.id, subm.content]))
    if (not is_manager) and subm.author != auth.user_id:
        session.flash = T('Not authorized.')
        redirect(URL('default', 'index'))
    # Checks whether we have the permission to show the feedback already.
    c = db.venue(subm.venue_id) or redirect(URL('default', 'index'))
    if (not is_manager) and (not ((datetime.utcnow() > c.rate_close_date) or c.feedback_accessible_immediately)):
        session.flash = T('The ratings are not yet available.')
        redirect(URL('feedback', 'index', args=['all']))
    venue_link = A(c.name, _href=URL('venues', 'view_venue', args=[c.id]))
    subm_link = None
    if c.allow_link_submission:
	subm_link = A(subm.link, _href=subm.link)
    db.submission.quality.readable = True
    db.submission.identifier.readable = True
    db.submission.error.readable = True
    db.submission.percentile.readable = True
    db.submission.comment.readable = True

    # Makes a grid of comments.
    db.task.submission_name.readable = False
    db.task.assigned_date.readable = False
    db.task.completed_date.readable = False
    db.task.rejected.readable = True
    q = (db.task.submission_id == subm.id)
    grid = SQLFORM.grid(q,
	details=True, 
        csv=False, create=False, editable=False, deletable=False, searchable=False,
	user_signature=False,
        args=request.args[:1],
        )
    return dict(subm=subm, download_link=download_link, subm_link=subm_link,
		venue_link=venue_link, grid=grid)
