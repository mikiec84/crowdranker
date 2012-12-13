# coding: utf8

import util

@auth.requires_login()
def submissions_contest():
    """This allows people to create a new submission for a contest."""
    # Gets information on this specific contest.
    c = db.contest(request.args(0)) or redirect(URL('default', 'index'))
    # Gets information on the user.
    props = db(db.user_properties.email == auth.user.email).select().first()
    if props == None: 
        contest_ids = []
    else:
        contest_ids = util.get_list(props.contests_can_submit)
    # Is the contest open for submission?
    if not (c.submit_constraint == None or c.id in contest_ids):
        session.flash = T('You cannot submit to this contest.')
        redirect(URL('default', 'index'))
    # Checks if the submission deadline has passed.
    t = datetime.utcnow()
    if not (c.is_active and c.open_date <= t and c.close_date >= t):
        # Send to view feedback.
        session.flash = T('The submission deadline has passed.')
        redirect(URL('feedback', 'index', args=[c.id]))
    # Gets the list of all submissions to the given contest.
    q = (db.submission.author == auth.user_id 
            & db.submission.contest_id == c.id)
    can_add = db(q).count() == 0 or c.allow_multiple_submissions
    grid = SQLFORM.grid(q,
        field_id = db.submission.id,
        fields = [db.submission.title],
        create = False,
        details = False,
        csv = False,
        editable = False,
        deletable = False,
        links = [
            # dict(header = T('Contest'), body = lambda r:
            #     A(T('contest'), _href=URL('contests', 'view_contest', args=[r.contest_id]))),
            dict(header = T('Resubmit'), body = lambda r:
                A(T('resubmit'), _href=URL('resubmit', args=[r.id]))),
            dict(header = T('Feedback'), body = lambda r:
                A(T('feedback'), _href=URL('feedback', 'submission', args=[r.id]))),
            ]
        )
    # TODO(luca): check can_add to see if we can include a link to submit, below.
    return dict(grid=grid, contest=c, can_add=can_add)
        

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
    # The author can access the title.
    db.submission.title.readable = db.submission.title.writable = True
    # Produces an identifier for the submission.  This will make it anonymous.
    random_id = util.get_random_id()
    add_submission_comments('bogus')
    form = SQLFORM(db.submission, sub, deletable=True, upload=URL('download'))
    form.vars.contest_id = c.id
    form.vars.identifier = random_id
    # TODO(luca): once on appengine, see http://stackoverflow.com/questions/8008213/web2py-upload-with-original-filename
    # for changing the name of the file to the random_id.
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
         
         
@auth.requires_login()
def resubmit():
    """Resubmit a particular submission, if the deadline is still open."""
    sub = db.submission(request.args(0)) or redirect(URL('default', 'index'))
    c = db.contest(sub.contest_id) or redirect(URL('default', 'index'))
    if (sub.author != auth.user_id):
        redirect(URL('default', 'index'))
    # Checks if the submission deadline has passed.
    t = datetime.utcnow()
    if not (c.is_active and c.open_date <= t and c.close_date >= t):
        # Send to view feedback.
        session.flash = T('The submission deadline has passed.')
        redirect(URL('feedback', 'index', args=[c.id]))
    # The author can access the title.
    db.submission.title.readable = db.submission.title.writable = True
    add_submission_comments('bogus')
    form = SQLFORM(db.submission, sub, deletable=True, upload=URL('download'))
    form.vars.contest_id = sub.contest_id
    if form.process().accepted:
        response.flash = T('Your resubmission has been accepted.')
        redirect(URL('default', 'index'))
    return dict(form=form)
         

@auth.requires_login()
def view_submission():
    """Allows viewing a submission by someone who has the task to review it.
    This function is accessed by task, not submission, to check access."""
    t = db.task(request.args(0)) or redirect(URL('default', 'index'))
    if t.user_id != auth.user_id:
        redirect(URL('default', 'index'))
    subm = db.submission(t.submission_id) or redirect(URL('default', 'index'))
    # Shows the submission, except for the title.
    form = crud.read(db.submission, t.submission_id)
    return dict(form=form, subm=subm)

   
@auth.requires_login()
def view_own_submission():
    """Allows viewing a submission by the submission owner."""
    subm = db.submission(request.args(0)) or redirect(URL('default', 'index'))
    if subm.author != auth.user_id:
        session.flash = T('You cannot view this submission.')
        redirect(URL('default', 'index'))
    form = crud.read(db.submission, subm.id)
    form.addbutton(T('View contest'), URL('contests', 'view_contest', args=[subm.contest_id]))
    form.addbutton(T('View feedback'), URL('feedback', 'view_feedback', args=[subm.id]))
    return dict(form=form)
   
def add_submission_comments(bogus):
   db.submission.title.comment = T('The title is visible to you only.') 
   
def download():
    return response.download(request, db)
