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
        csv=False, details=False, create=False, editable=False,
        args=request.args[1:],
        user_signature=False,
        links=[
            dict(header=T('Contest'), body = lambda r: 
                A(get_contest_name(r.contest_id), _href=URL('contests', 'view_contest', args=[r.contest_id]))),
            dict(header=T('Submission'), body = lambda r: 
                A(r.title, _href=URL('submission', 'view_own_submission', args=[r.id]))),
            dict(header=T('Feedback'), body = lambda r:
                A(T('view'), _href=URL('view_feedback', args=[r.id]))),
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
    if sub.author != auth.user_id:
        session.flash = T('This is not your submission.')
        redirect(URL('feedback', 'index', args=['all']))
    # Checks whether we have the permission to show the feedback already.
    c = db.contest(subm.contest_id) or redirect(URL('default', 'index'))
    if not ((datetime.utcnow() > c.rate_close_date) or c.feedback_accessible_immediately):
        session.flash = T('The contest is still open to submissions.')
        redirect(URL('feedback', 'index', args=['all']))
    # Makes a grid of comments.
    q = (db.comment.submission_id == subm.id)
    grid = SQLFORM.grid(q,
        fields=[], details=True, 
        csv=False, create=False, editable=False,
        args=request.args[1:],
        )
    # Reads the quality of the submission.
    qual = db(db.quality.submission_id == subm.id).select().first()
    return dict(subm=subm, grid=grid, quality=qual)
