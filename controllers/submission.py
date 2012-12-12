# coding: utf8

import util

@auth.requires_login()
def submit():
    # Gets the information on the contest.
    c = db.contest(request.args[0]) or redirect(URL('default', 'index'))
    # Gets information on the user.
    props = db(db.user_properties.email == auth.user.email).select().first()
    if props == None: 
        contest_ids = []
    else:
        contest_ids = util.get_list(props.contests_can_submit)
    # Is the contest open for submission?
    if not (c.submit_constraint == None or c.id in contest_ids):
        redirect('closed', args=['permission'])
    t = datetime.utcnow()
    if not (c.is_active and c.open_date <= t and c.close_date >= t):
        redirect('closed', args=['deadline'])
    # Ok, the user can submit.  Looks for previous submissions.
    logger.debug('Ok, generating crud')
    sub = db((db.submission.author == auth.user_id) & (db.submission.contest_id == c.id)).select().first()
    form = SQLFORM(db.submission, sub, deletable=True, upload=URL('download'))
    form.vars.contest_id = c.id
    if form.process().accepted:
        # Adds the contest to the list of contests where the user submitted.
        # TODO(luca): Note that a user can then delete the submission.
        submitted_ids = util.id_list(util.get_list(props.contests_has_submitted))
        submitted_ids = util.list_append_unique(submitted_ids, c.id)
        props.update_record(contests_has_submitted = submitted_ids)
        db.commit()
        response.flash = T('Your submission has been accepted.')
        redirect(URL('default', 'index'))
    return dict(form=form)
         
         
def download():
    return response.download(request, db)
         
        
def closed():
    if args[0] == 'deadline':
        msg = T('The submission deadline has passed.')
    else:
        msg = T('You do not have permission to submit to this contest.')
    return dict(msg=msg)
