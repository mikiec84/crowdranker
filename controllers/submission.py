# coding: utf8

import util

@auth.requires_login()
def submit():
    # Gets the information on the contest.
    c = db.contest(request.args[0]) or redirect(URL('default', 'index'))
    # Gets information on the user.
    props = db(db.user_properties.email == auth.user.email).select(db.user_properties.contests_can_submit).first()
    if props == None: 
        contest_ids = []
    else:
        contest_ids = util.id_list(util.get_list(props.contests_can_submit))
    # Is the contest open for submission?
    if not (c.submit_constraint == None or c.id in contest_ids):
        redirect('closed', args=['permission'])
    if not (c.is_active and c.open_date < datetime.utcnow() and c.close_date > datetime.utcnow()):
        redirect('closed', args=['deadline'])
    # Ok, the user can submit.  Looks for previous submissions.
    logger.debug('Ok, generating crud')
    sub = db((db.submission.author == auth.user_id) & (db.submission.contest_id == c.id)).select().first() 
    form = crud.update(db, 
        record=sub,
        deletable=True,
        next=URL('default', 'index'),
        )
    return dict(form=form)
         
        
def closed():
    if args[0] == 'deadline':
        msg = T('The submission deadline has passed.')
    else:
        msg = T('You do not have permission to submit to this contest.')
    return dict(msg=msg)
