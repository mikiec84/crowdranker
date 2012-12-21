# coding: utf8

import util

@auth.requires_login()
def view_contest():
    c = db.contest(request.args(0)) or redirect(URL('default', 'index'))
    props = db(db.user_properties.email == auth.user.email).select().first()
    if props == None: 
        can_submit = False
        can_rate = False
        has_submitted = False
        has_rated = False
        can_manage = False
    else:
        can_submit = c.id in util.get_list(props.contests_can_submit) or util.is_none(c.submit_constraint)
        can_rate = c.id in util.get_list(props.contests_can_rate) or util.is_none(c.rate_constraint)
        has_submitted = c.id in util.get_list(props.contests_has_submitted)
        has_rated = c.id in util.get_list(props.contests_has_rated)
        can_manage = c.id in util.get_list(props.contests_can_manage)
    contest_form = SQLFORM(db.contest, record=c, readonly=True)
    button_form = SQLFORM.factory()
    if can_submit:
        button_form.add_button(T('Submit to this contest'), URL('submission', 'submissions_contest', args=[c.id]))
    if can_rate:
        button_form.add_button(T('Rate submissions'), URL('rating', 'accept_review', args=[c.id]))
    if has_submitted:
        button_form.add_button(T('View submission feedback'), URL('feedback', 'index', args=[c.id]))
    if can_manage:
        button_form.add_button(T('Edit'), URL('manage_contest', args=[c.id]))
    return dict(contest_form=contest_form, button_form=button_form,contest=c, has_rated=has_rated)

                
@auth.requires_login()
def manage_contest():
    c = db.contest(request.args(0)) or redirect(URL('default', 'index'))
    props = db(db.user_properties.email == auth.user.email).select().first()
    if props == None or c.id not in util.get_list(props.contests_can_manage):
        session.flash = T('You cannot manage this contest')
        redirect(URL('default', 'index'))
    # Generates a form for editing.
    add_help_for_contest('bogus')
    # Creates a function used to process the update.
    updater = update_contest(c.managers, c.submit_constraint, c_rate_constraint)
    form = SQLFORM(db.contest)
    if form.process(onvalidate=validate_contest).accepted():
        # Fix the permissions.
        updater(form)
        db.commit()
        redirect(URL('view_contest', args=[c.id]))
    return dict(form=form)
        

@auth.requires_login()
def subopen_index():
    props = db(db.user_properties.email == auth.user.email).select(db.user_properties.contests_can_submit).first()
    if props == None: 
        l = []
    else:
        l = util.get_list(props.contests_can_submit)
    q_all = ((db.contest.open_date < datetime.utcnow())
             & (db.contest.close_date > datetime.utcnow()) 
             & (db.contest.is_active == True) 
             & (db.contest.submit_constraint == None)
             )
    c_all = db(q_all).select(db.contest.id).as_list()
    if len(l) > 0:
        q_user = ((db.contest.open_date < datetime.utcnow())
                  & (db.contest.close_date > datetime.utcnow())
                  & (db.contest.is_active == True)
                  & (db.contest.id.belongs(l))
                  )
        c_user = db(q_user).select(db.contest.id).as_list()
        c = util.union_id_list(c_all, c_user)
    else:
        c = util.id_list(c_all)
    q = (db.contest.id.belongs(c))
    grid = SQLFORM.grid(q,
        field_id=db.contest.id,
        fields=[db.contest.name, db.contest.close_date],
        csv=False,
        details=True,
        create=False,
        editable=False,
        deletable=False,
        links=[dict(header=T('Submit'), 
            body = lambda r: A(T('submit'), _href=URL('submission', 'submit', args=[r.id])))],
        )
    return dict(grid=grid)


@auth.requires_login()
def rateopen_index():
    props = db(db.user_properties.email == auth.user.email).select(db.user_properties.contests_can_rate).first()
    if props == None:
        l = []
    else:
        l = util.get_list(props.contests_can_rate)
    q_all = ((db.contest.rate_open_date < datetime.utcnow())
             & (db.contest.rate_close_date > datetime.utcnow()) 
             & (db.contest.is_active == True) 
             & (db.contest.rate_constraint == None)
             )
    c_all = db(q_all).select(db.contest.id).as_list()
    if len(l) > 0:
        q_user = ((db.contest.rate_open_date < datetime.utcnow())
                  & (db.contest.rate_close_date > datetime.utcnow())
                  & (db.contest.is_active == True)
                  & (db.contest.id.belongs(l))
                  )
        c_user = db(q_user).select(db.contest.id).as_list()
        c = util.union_id_list(c_all, c_user)
    else:
        c = util.id_list(c_all)
    q = (db.contest.id.belongs(c))
    grid = SQLFORM.grid(q,
        field_id=db.contest.id,
        fields=[db.contest.name, db.contest.close_date],
        csv=False,
        details=True,
        create=False,
        editable=False,
        deletable=False,
        links=[dict(header='Review', 
            body = lambda r: A(T('Accept reviewing task'), _href=URL('rating', 'accept_review', args=[r.id])))],
        )
    return dict(grid=grid)

                
@auth.requires_login()
def submitted_index():
    props = db(db.user_properties.email == auth.user.email).select(db.user_properties.contests_has_submitted).first()
    if props == None: 
        l = []
    else:
        l = util.id_list(util.get_list(props.contests_has_submitted))
    q = (db.contest.id.belongs(l))
    grid = SQLFORM.grid(q,
        field_id=db.contest.id,
        fields=[db.contest.name, db.contest.rate_open_date, db.contest.rate_close_date, db.contest.feedback_accessible_immediately],
        csv=False,
        details=True,
        create=False,
        editable=False,
        deletable=False,
        links=[dict(header='Feedback', body = lambda r: link_feedback(r))],
        )
    return dict(grid=grid)

def link_feedback(contest):
    """Decides if it can show feedback for this contest."""
    if ((contest.rate_close_date < datetime.utcnow()) | contest.feedback_accessible_immediately):
        return A(T('View feedback'), _href=URL('feedback', 'index', args=[contest.id]))
    else:
        return T('Not yet available')
        
        
@auth.requires_login()
def managed_index():
    props = db(db.user_properties.email == auth.user.email).select().first()
    if props == None:
        managed_contest_list = []
        managed_user_lists = []
    else:
        managed_contest_list = util.get_list(props.contests_can_manage)
        managed_user_lists = util.get_list(props.managed_user_lists)
    q = (db.contest.id.belongs(managed_contest_list))    
    # Constrains the user lists to those managed by the user.
    list_q = (db.user_list.id.belongs(managed_user_lists))
    db.contest.submit_constraint.requires = IS_EMPTY_OR(IS_IN_DB(
        db(list_q), 'user_list.id', '%(name)s', zero=T('-- Everybody --')))
    db.contest.rate_constraint.requires = IS_EMPTY_OR(IS_IN_DB(
        db(list_q), 'user_list.id', '%(name)s', zero=T('-- Everybody --')))
    # Keeps track of old managers, if this is an update.
    if len(request.args) > 2 and request.args[-3] == 'edit':
        c = db.contest[request.args[-1]]
        old_managers = c.managers
        old_submit_constraint = c.submit_constraint
        old_rate_constraint = c.rate_constraint
    else:
        old_managers = []
        old_submit_constraint = None
        old_rate_constraint = None
    if len(request.args) > 0 and (request.args[0] == 'edit' or request.args[0] == 'new'):
        # Adds some editing help
        add_help_for_contest('bogus')
    grid = SQLFORM.grid(q,
        field_id=db.contest.id,
        fields=[db.contest.name, db.contest.managers, db.contest.is_active],
        csv=False,
        details=True,
        create=True,
        deletable=False, # Disabled; cannot delete contests with submissions.
        onvalidation=validate_contest,
        oncreate=create_contest,
        onupdate=update_contest(old_managers, old_submit_constraint, old_rate_constraint),
        )
    return dict(grid=grid)
    
def add_help_for_contest(bogus):
    # Let's add a bit of help for editing
    db.contest.is_active.comment = 'Uncheck to prevent all access to this contest.'
    db.contest.managers.comment = 'Email addresses of contest managers.'
    db.contest.name.comment = 'Name of the contest'
    db.contest.allow_multiple_submissions.comment = (
        'Allow users to submit multiple independent pieces of work to this contest.')
    db.contest.feedback_accessible_immediately.comment = (
        'The feedback can be accessible immediately, or once '
        'the contest closes.')
    db.contest.rating_available_to_all.comment = (
        'The ratings will be publicly visible.')
    db.contest.feedback_available_to_all.comment = (
        'The feedback to submissions will be available to all.')
    db.contest.feedback_is_anonymous.comment = (
        'The identity of users providing feedback is not revealed.')
    db.contest.submissions_are_anonymized.comment = (
        'The identities of submission authors are not revealed to the raters.')

    
def validate_contest(form):
    """Validates the form contest, splitting managers listed on the same line."""
    form.vars.managers = util.normalize_email_list(form.vars.managers)
    if auth.user.email not in form.vars.managers:
        form.vars.managers = [auth.user.email] + form.vars.managers
    

def add_contest_to_user_managers(id, user_list):
    for m in user_list:
        u = db(db.user_properties.email == m).select(db.user_properties.contests_can_manage).first()
        if u == None:
            # We never heard of this user, but we still create the permission.
            logger.debug("Creating user properties for email:" + str(m) + "<")
            db.user_properties.insert(email=m)
            db.commit()
            l = []
        else:
            l = u.contests_can_manage
        l = util.list_append_unique(l, id)
        db(db.user_properties.email == m).update(contests_can_manage = l)
    db.commit()
        
def add_contest_to_user_submit(id, user_list):
    for m in user_list:
        u = db(db.user_properties.email == m).select(db.user_properties.contests_can_submit).first()
        if u == None:
            # We never heard of this user, but we still create the permission.
            logger.debug("Creating user properties for email:" + str(m) + "<")
            db.user_properties.insert(email=m)
            db.commit()
            l = []
        else:
            l = u.contests_can_submit
        l = util.list_append_unique(l, id)
        db(db.user_properties.email == m).update(contests_can_submit = l)
    db.commit()
        
def add_contest_to_user_rate(id, user_list):
    for m in user_list:
        u = db(db.user_properties.email == m).select(db.user_properties.contests_can_rate).first()
        if u == None:
            # We never heard of this user, but we still create the permission.
            logger.debug("Creating user properties for email:" + str(m) + "<")
            db.user_properties.insert(email=m)
            db.commit()
            l = []
        else:
            l = u.contests_can_rate
        l = util.list_append_unique(l, id)
        db(db.user_properties.email == m).update(contests_can_rate = l)
    db.commit()

def delete_contest_from_managers(id, managers):
    for m in managers:
        u = db(db.user_properties.email == m).select(db.user_properties.contests_can_manage).first()
        if u != None:
            l = util.list_remove(u.contests_can_manage, id)
            db(db.user_properties.email == m).update(contests_can_manage = l)
    db.commit()
       
def delete_contest_from_submitters(id, users):
    for m in users:
        u = db(db.user_properties.email == m).select(db.user_properties.contests_can_submit).first()
        if u != None:
            l = util.list_remove(u.contests_can_submit, id)
            db(db.user_properties.email == m).update(contests_can_submit = l)
    db.commit()
       
def delete_contest_from_raters(id, users):
    for m in users:
        u = db(db.user_properties.email == m).select(db.user_properties.contests_can_rate).first()
        if u != None:
            l = util.list_remove(u.contests_can_rate, id)
            db(db.user_properties.email == m).update(contests_can_rate = l)
    db.commit()
                        
def create_contest(form):
    """Processes the creation of a context, propagating the effects."""
    # First, we need to add the context for the new managers.
    add_contest_to_user_managers(form.vars.id, form.vars.managers)
    # If there is a submit constraint, we need to allow all the users
    # in the list to submit.
    if not util.is_none(form.vars.submit_constraint):
        logger.debug("form.vars.submit_contraints is:" + str(form.vars.submit_constraint) + "<")
        user_list = db.user_list[form.vars.submit_constraint].email_list
        # We need to add everybody in that list to submit.
        add_contest_to_user_submit(form.vars.id, user_list)
    # If there is a rating constraint, we need to allow all the users
    # in the list to rate.
    if not util.is_none(form.vars.rate_constraint):
        user_list = db.user_list[form.vars.rate_constraint].email_list
        add_contest_to_user_rate(form.vars.id, user_list)
                
def update_contest(old_managers, old_submit_constraint, old_rate_constraint):
    """A contest is being updated.  We need to return a callback for the form,
    that will produce the proper update, taking into account the change in permissions."""
    def f(form):
        # Managers.
        add_contest_to_user_managers(form.vars.id, util.list_diff(form.vars.managers, old_managers))
        delete_contest_from_managers(form.vars.id, util.list_diff(old_managers, form.vars.managers))
        # Submitters.
        if old_submit_constraint != form.vars.submit_constraint:
            # We need to update.
            if not util.is_none(old_submit_constraint):
                user_list = db.user_list[old_submit_constraint]
                delete_contest_from_submitters(form.vars.id, user_list)
            if not util.is_none(form.vars.submit_constraint):
                user_list = db.user_list[form.vars.submit_constraint]
                add_contest_to_user_submit(form.vars.id, user_list)
        # Raters.
        if old_rate_constraint != form.vars.rate_constraint:
            # We need to update.
            if not util.is_none(old_rate_constraint):
                user_list = db.user_list[old_rate_constraint]
                delete_contest_from_raters(form.vars.id, user_list)
            if not util.is_none(form.vars.rate_constraint):
                user_list = db.user_list[form.vars.rate_constraint]
                add_contest_to_user_rate(form.vars.id, user_list)
    return f
                
def delete_contest(table, id):
    c = db.contest[id]
    delete_contest_from_managers(id, c.managers)
    if not util.is_none(c.submit_constraint):
        user_list = db.user_list[c.submit_constraint]
        delete_contest_from_submitters(id, user_list)
    if not util.is_none(c.rate_constraint):
        user_list = db.user_list[c.rate_constraint]
        delete_contest_from_raters(id, user_list)
