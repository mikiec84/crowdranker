# coding: utf8

import util

@auth.requires_login()
def subopen_index():
    props = db(db.user_properties.email == auth.user.email).select().first()
    q_all = ((db.contest.open_date < datetime.utcnow()) &
             (db.contest.close_date > datetime.utcnow()) &
             (db.contest.is_active) &
             (db.contest.submit_constraint == None))
    q_user = ((db.contest.open_date < datetime.utcnow()) &
              (db.contest.close_date > datetime.utcnow()) &
              (db.contest.is_active) &
              (db.contest.id.belongs(props.contests_can_submit)))
    c_all = db(q_all).select().as_list()
    c_user = db(q_user).select().as_list()
    c = util.union_id_list(c_all, c_user)
    q = (db.contest.id.belongs(c))

@auth.requires_login()
def rateopen_index():
    props = db(db.user_properties.email == auth.user.email).select().first()
    q_all = ((db.contest.rate_open_date < datetime.utcnow()) &
             (db.contest.rate_close_date > datetime.utcnow()) &
             (db.contest.is_active) &
             (db.contest.rate_constraint == None))
    q_user = ((db.contest.rate_open_date < datetime.utcnow()) &
              (db.contest.rate_close_date > datetime.utcnow()) &
              (db.contest.is_active) &
              (db.contest.id.belongs(props.contests_can_rate)))
    c_all = db(q_all).select().as_list()
    c_user = db(q_user).select().as_list()
    c = util.union_id_list(c_all, c_user)
    q = (db.contest.id.belongs(c))
        
@auth.requires_login()
def submitted_index():
    props = db(db.user_properties.email == auth.user.email).select().first()
    q = (db.contest.id.belongs(props.contests_has_submitted))
    
@auth.requires_login()
def managed_index():
    props = db(db.user_properties.email == auth.user.email).select().first()
    managed_contest_list = props.contests_can_manage
    if managed_contest_list == None:
        managed_contest_list = []
    q = (db.contest.id.belongs(managed_contest_list))    
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
    grid = SQLFORM.grid(q,
        field_id=db.contest.id,
        csv=False,
        details=True,
        create=True,
        deletable=False, # Disabled; cannot delete contests with submissions.
        onvalidation=validate_contest,
        oncreate=create_contest,
        onupdate=update_contest(old_managers, old_submit_constraint, old_rate_constraint),
        )
    return dict(grid=grid)
    
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
    if form.vars.submit_constraint != None:
        user_list = db.user_list[form.vars.submit_constraint].email_list
        # We need to add everybody in that list to submit.
        add_contest_to_user_submit(form.vars.id, user_list)
    # If there is a rating constraint, we need to allow all the users
    # in the list to rate.
    if form.vars.rate_constraint != None:
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
            if old_submit_constraint != None:
                user_list = db.user_list[old_submit_constraint]
                delete_contest_from_submitters(form.vars.id, user_list)
            if form.vars.submit_constraint != None:
                user_list = db.user_list[form.vars.submit_constraint]
                add_contest_to_user_submit(form.vars.id, user_list)
        # Raters.
        if old_rate_constraint != form.vars.rate_constraint:
            # We need to update.
            if old_rate_constraint != None:
                user_list = db.user_list[old_rate_constraint]
                delete_contest_from_raters(form.vars.id, user_list)
            if form.vars.rate_constraint != None:
                user_list = db.user_list[form.vars.rate_constraint]
                add_contest_to_user_rate(form.vars.id, user_list)
    return f
                
def delete_contest(table, id):
    c = db.contest[id]
    delete_contest_from_managers(id, c.managers)
    if c.submit_constraint != None:
        user_list = db.user_list[c.submit_constraint]
        delete_contest_from_submitters(id, user_list)
    if c.rate_constraint != None:
        user_list = db.user_list[c.rate_constraint]
        delete_contest_from_raters(id, user_list)
