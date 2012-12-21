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
    grid = SQLFORM.grid(q,
        fields=[db.submission.id, db.submission.date],
        csv=False, details=False, create=False, editable=False,
        args=request.args[1:],
        links=[
            dict(header=T('Contest'), body = lambda r: 
                A(T('Contest'), _href=URL('contests', 'view_contest', args=[r.contest_id]))),
            dict(header=T('Submission'), body = lambda r: 
                A(T('submission'), _href=URL('submission', 'view_own_submission', args=[r.id]))),
            dict(header=T('Feedback'), body = lambda r:
                A(T('feedback'), _href=URL('view_feedback', args=[r.id]))),
            ],
        )
    return form(grid=grid)
    

@auth.requires_login()
def view_feedback():
    """Shows detailed information and feedback for a given submission."""
    sub = db.submission(request.args(0)) or redirect(URL('default', 'index'))
    if sub.author != auth.user_id:
        redirect(URL('default', 'index'))
    # Checks whether we have the permission to show the feedback already.
    c = db.contest(sub.contest_id) or redirect(URL('default', 'index'))
    if not (datetime.utcnow() > c.rate_close_date | c.feedback_accessible_immediately):
        session.flash = T('The contest is still running.')
        redirect(URL('default', 'index'))
    # Makes a grid of comments.
    q = (db.comment.submission_id == sub_id)
    grid = SQLFORM.grid(q,
        fields=[], details=True, 
        csv=False, create=False, editable=False,
        args=request.args[1:],
        )
    # Reads the quality of the submission.
    qual = db(db.quality.submission_id == sub.id).select().first()
    return dict(sub=sub, grid=grid, quality=qual)
