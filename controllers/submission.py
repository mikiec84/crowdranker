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
    # Produces an identifier for the submission.
    random_id = util.get_random_id()
    form = SQLFORM(db.submission, sub, deletable=True, upload=URL('download'))
    form.vars.contest_id = c.id
    form.vars.identifier = random_id
    if request.vars.content != None:
        form.vars.original_filename = request.vars.content.filename
    # TODO(luca): once on appengine, see http://stackoverflow.com/questions/8008213/web2py-upload-with-original-filename
    # for changing the name of the file to the random_id.
    if form.process().accepted:
        # Adds the contest to the list of contests where the user submitted.
        # TODO(luca): Note that a user can then delete the submission.
        submitted_ids = util.id_list(util.get_list(props.contests_has_submitted))
        submitted_ids = util.list_append_unique(submitted_ids, c.id)
        props.update_record(contests_has_submitted = submitted_ids)
        db.commit()
        session.flash = T('Your submission has been accepted.')
        redirect(URL('feedback', 'index', args=['all']))
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
        session.flash = T('The contest is not open to submissions.')
        redirect(URL('feedback', 'index', args=[c.id]))
    # The author can access the title.
    db.submission.title.readable = db.submission.title.writable = True
    form = SQLFORM(db.submission, sub, deletable=True, upload=URL('download'))
    form.vars.contest_id = sub.contest_id
    if request.vars.content != None:
        form.vars.original_filename = request.vars.content.filename
    if form.process().accepted:
        session.flash = T('Your resubmission has been accepted.')
        redirect(URL('feedback', 'index', args=['all']))
    return dict(form=form)
         

@auth.requires_login()
def view_submission():
    """Allows viewing a submission by someone who has the task to review it.
    This function is accessed by task id, not submission id, to check access
    and anonymize the submission."""
    # TODO(mbrich): here we need to be able to download the submission, and:
    # * For the author, download it under the original name.
    # * For a user, download it as t.submission_name + the original extension of the file.
    t = db.task(request.args(0)) or redirect(URL('default', 'index'))
    if t.user_id != auth.user_id:
        session.flash(T('Not authorized.'))
        redirect(URL('default', 'index'))
    subm = db.submission(t.submission_id) or redirect(URL('default', 'index'))
    # Shows the submission, except for the title (unless we are showing it to the author).
    if subm.author != auth.user_id:
        db.submission.title.readable = False
    form = SQLFORM(db.submission, record = subm, readonly=True)
    return dict(form=form)

   
@auth.requires_login()
def view_own_submission():
    """Allows viewing a submission by the submission owner.
    The argument is the submission id."""
    subm = db.submission(request.args(0)) or redirect(URL('default', 'index'))
    if subm.author != auth.user_id:
        session.flash = T('You cannot view this submission.')
        redirect(URL('default', 'index'))
    # If the contest is still open for submissions, then we allow editing of the submission.
    c = db.contest(subm.contest_id) or redirect(URL('default', 'index'))
    t = datetime.utcnow()
    download_link = None
    if (c.is_active and c.open_date <= t and c.close_date >= t):
        form = SQLFORM(db.submission, subm, upload=URL('download'))
        if request.vars.content != None:
            form.vars.original_filename = request.vars.content.filename
        if form.process().accepted:
            session.flash = T('Your submission has been updated.')
            redirect(URL('feedback', 'index', args=['all']))
    else:
        db.submission.content.readable = False
        form = SQLFORM(db.submission, subm, readonly=True, upload=URL('download'), buttons=[])
        if subm.content != None and len(subm.content) > 0:
            download_link = URL('download', args=[subm.content])
    return dict(form=form, subm=subm, download_link=download_link)

   
def download():
    return response.download(request, db)
