# coding: utf8

import util

@auth.requires_login()
def index():
    """Produces a list of the feedback obtained for a given contest,
    or for all contests."""
    contest_id = request.args(0)
    if contest_id == 'all':
        q = (db.submission.author == auth.user_id)
    else:
        q = ((db.submission.author == auth.user_id) 
            & (db.submission.contest_id == contest_id))
    db.submission.contest_id.readable = False # prevents use in form
    db.submission.title.readable = False
    grid = SQLFORM.grid(q,
        fields=[db.submission.id, db.submission.title, db.submission.date, db.submission.contest_id],
        csv=False, details=False, create=False, editable=False, deletable=False,
        args=request.args[:1],
        user_signature=False,
        links=[
            dict(header=T('Contest'), body = lambda r: 
                A(get_contest_name(r.contest_id), _href=URL('contests', 'view_contest', args=[r.contest_id]))),
            dict(header=T('Submission'), body = lambda r: 
                A(r.title, _href=URL('submission', 'view_own_submission', args=[r.id]))),
            dict(header=T('Feedback'), body = lambda r:
                A(T('view'), _href=URL('feedback', 'view_feedback', args=[r.id]))),
            ],
        )
    return dict(grid=grid)

def get_contest_name(contest_id):
    n = db(db.contest.id == contest_id).select(db.contest.name).first()
    if n == None:
        return ''
    return n.name

@auth.requires_login()
def view_feedback():
    """Shows detailed information and feedback for a given submission."""
    subm = db.submission(request.args(0)) or redirect(URL('default', 'index'))
    download_link = A(T('Download'), _class='btn', 
		      _href=URL('submission', 'download_author', args=[subm.id, subm.content]))
    if subm.author != auth.user_id:
        session.flash = T('This is not your submission.')
        redirect(URL('feedback', 'index', args=['all']))
    # Checks whether we have the permission to show the feedback already.
    c = db.contest(subm.contest_id) or redirect(URL('default', 'index'))
    if not ((datetime.utcnow() > c.rate_close_date) or c.feedback_accessible_immediately):
        session.flash = T('The contest is still open to submissions.')
        redirect(URL('feedback', 'index', args=['all']))
    c = db.contest(subm.contest_id) or redirect(URL('default', 'index'))
    contest_link = A(c.name, _href=URL('contests', 'view_contest', args=[c.id]))
    # Makes a grid of comments.
    db.comment.id.readable = False
    db.submission.quality.readable = True
    db.submission.identifier.readable = True
    db.submission.error.readable = True
    db.comment.content.label = T('Comments')
    q = (db.comment.submission_id == subm.id)
    grid = SQLFORM.grid(q,
	details=True, 
        csv=False, create=False, editable=False, deletable=False, searchable=False,
	user_signature=False,
        args=request.args[:1],
        )
    return dict(subm=subm, download_link=download_link,
		contest_link=contest_link, grid=grid)
