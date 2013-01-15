# coding: utf8

import util

@auth.requires_login()
def view_venue():
    """This function enables the view of the ranking of items submitted to a
    venue.  It is assumed that the people accessing this can have full
    information about the venue, including the identity of the submitters."""
    c = db.venue(request.args(0)) or redirect(URL('default', 'index'))
    props = db(db.user_properties.email == auth.user.email).select().first()
    can_manage = c.id in util.get_list(props.venues_can_manage)
    can_observe = c.id in util.get_list(props.venues_can_observe)
    can_view_ratings = can_manage or c.rating_available_to_all or can_observe
    if not can_view_ratings:
	session.flash = T('You do not have access to the ranking of this venue.')
	redirect(URL('default', 'index'))
    # Prepares the query for the grid.
    q = (db.submission.venue_id == c.id)
    db.submission.quality.readable = True
    db.submission.error.readable = True
    db.submission.content.readable = False
    if c.allow_link_submission:
	db.submission.link.readable = True
    grid = SQLFORM.grid(q,
	field_id=db.submission.id,
	csv=True,
	args=request.args[:1],
	user_signature=False,
	details=False, create=False, editable=False, deletable=False,
	fields=[db.submission.title, db.submission.email, db.submission.quality,
		db.submission.error, db.submission.content],
	links=[
	    dict(header=T('Download'),
		 body = lambda r: A(T('Download'), _class='btn',
				    _href=URL('submission', 'download_viewer',
					      args=[r.id, r.content]))),
	    ],
	)
    # TODO(luca): Add a link to download the submission.
    title = A(c.name, _href=URL('venues', 'view_venue', args=[c.id]))
    return dict(title=title, grid=grid)
