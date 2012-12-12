# coding: utf8

import util

@auth.requires_login()
def contest_index():
    """Produces a list of the feedback obtained for a given contest.
    This is somewhat overkill, but in general, a user can have many
    submissions for the same contest."""
    contest_id = request.args(0)
    if contest_id == None:
        redirect(URL('default', 'index'))
    q = (db.submission.author == auth.user_id 
        & db.submission.contest_id == contest_id)
    grid = SQLFORM.grid(q,
        fields=[db.submission.id, db.submission.date],
        csv=False, details=False, create=False, editable=False,
        links=[dict(header='Contest',
