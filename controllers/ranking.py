# coding: utf8

import util

@auth.requires_login()
def view_contest():
    """This function enables the view of the ranking of items submitted to a
    contest.  It is assumed that the people accessing this can have full
    information about the contest, including the identity of the submitters."""
    c = db.contest(request.args(0)) or redirect(URL('default', 'index'))
    props = db(db.user_properties.email == auth.user.email).select().first()
    can_manage = c.id in util.get_list(props.contests_can_manage)
    can_view_ratings = can_manage or c.rating_available_to_all
    if not can_view_ratings:
	session.flash = T('You do not have access to the ranking of this contest.')
	redirect(URL('default', 'index'))
    # Prepares the query for the grid.
    q = (db.submission.contest_id == c.id)
    grid = SQLFORM.grid(q,
	field_id=db.submission.id,
	csv=True,
	details=False, create=False, editable=False, deletable=False,
	fields=[db.submission.title, db.submission.email, db.submission.quality,
		db.submission.error],
	)
    # TODO(luca): Add a link to download the submission.
    title = A(c.title, _href=URL('contests', 'view_contest', args=[c.id]))
    return dict(title=title, grid=grid)
