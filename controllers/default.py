# -*- coding: utf-8 -*-

import controller_util
import util

from gluon.custom_import import track_changes; track_changes(True)

def index():
    """
    Main index.
    """
    response.flash = None
    user_is_admin = is_user_admin(auth)
    return dict(user_is_admin=user_is_admin)
    
@auth.requires_login()
def contest_subopen_index():
    props = db(db.user_properties.email == auth.user.email).select().first()
    q_all = ((db.contest.open_date < datetime.utcnow()) &
             (db.contest.close_date > datetime.utcnow()) &
             (db.contest.submit_constraint == None))
    q_user = ((db.contest.open_date < datetime.utcnow()) &
              (db.contest.close_date > datetime.utcnow()) &
              (db.contest.id.belongs(props.contests_can_submit)))
    c_all = db(q_all).select().as_list()
    c_user = db(q_user).select().as_list()
    c = util.union_id_list(c_all, c_user)
    q = (db.contest.id.belongs(c))

@auth.requires_login()
def contest_revopen_index():
    props = db(db.user_properties.email == auth.user.email).select().first()
    q_all = ((db.contest.rate_open_date < datetime.utcnow()) &
             (db.contest.rate_close_date > datetime.utcnow()) &
             (db.contest.rate_constraint == None))
    q_user = ((db.contest.rate_open_date < datetime.utcnow()) &
              (db.contest.rate_close_date > datetime.utcnow()) &
              (db.contest.id.belongs(props.contests_can_rate)))
    c_all = db(q_all).select().as_list()
    c_user = db(q_user).select().as_list()
    c = util.union_id_list(c_all, c_user)
    q = (db.contest.id.belongs(c))
        
@auth.requires_login()
def contest_submitted_index():
    props = db(db.user_properties.email == auth.user.email).select().first()
    q = (db.contest.id.belongs(props.contests_has_submitted))
    
@auth.requires_login()
def contest_managed_index():
    props = db(db.user_properties.email == auth.user.email).select().first()
    q = (db.contest.id.belongs(props.contest_can_manage))    
    # Keeps track of old managers, if this is an update.
    if len(request.args) > 2 and request.args[-3] == 'edit':
        c = db.contest[request.args[-1]]
        old_managers = c.managers
        old_submit_constraint = c.submit_constraint
        old_rate_constraint = c.rate_constraint
    else:
        old_managers = []
    grid = SQLFORM.grid(q,
        field_id=db.contest.id,
        csv=False,
        details=True,
        create=True,
        deletable=False, # Disabled; cannot delete contests with submissions.
        onvalidate=validate_contest,
        oncreate=create_contest,
        onupdate=update_contest(old_managers, old_submit_constrant, old_rate_constraint),
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
                
                                                
        
@auth.requires_login()
def user_list_index():
    """Index of user list one can manage or use."""
    # Reads the list of ids of lists managed by the user.
    list_ids_l = db(db.user_properties.email == auth.user.email).select(db.user_properties.user_lists).first()
    if list_ids_l == None:
        list_ids = []
    else:
        list_ids = list_ids_l['user_lists']
    # Keeps track of old managers, if this is an update.
    if len(request.args) > 2 and request.args[-3] == 'edit':
        id = request.args[-1]
        old_managers = db.user_list[id].managers
    else:
        old_managers = []
    # Gets the lists.
    q = (db.user_list.id.belongs(list_ids))
    grid = SQLFORM.grid(q, 
        field_id = db.user_list.id,
        csv=False, details=True,
        oncreate=create_user_list,
        onvalidation=validate_user_list,
        onupdate=update_user_list(old_managers),
        ondelete=delete_user_list,
        )
    return dict(grid=grid)
    

def validate_user_list(form):
    """Splits emails on the same line, and adds the user creating the list to its managers."""
    logger.debug("form.vars: " + str(form.vars))
    form.vars.email_list = util.normalize_email_list(form.vars.email_list)
    form.vars.managers = util.normalize_email_list(form.vars.managers)
    if auth.user.email not in form.vars.managers:
        form.vars.managers = [auth.user.email] + form.vars.managers
    logger.debug("At the end of validation: email_list: " + str(form.vars.email_list) + "; managers: " + str(form.vars.managers))
    
def update_user_list(old_managers):
    ### TODO(Luca): This takes care of updating the managers. 
    # But, we also need to propagate the changes to the email list for all contests that use
    # this list for access or rating control.
    """We return a callback that takes a form argument."""
    def f(form):
        logger.debug("Old managers: " + str(old_managers))
        logger.debug("New managers: " + str(form.vars.managers))
        add_user_list_managers(form.vars.id, util.list_diff(form.vars.managers, old_managers))
        delete_user_list_managers(form.vars.id, util.list_diff(old_managers, form.vars.managers))
    return f

def create_user_list(form):
    add_user_list_managers(form.vars.id, form.vars.managers)

def delete_user_list(table, id):
    # TODO(luca): What do we have to do for the contests that were using this list for access control?
    old_managers = db.user_list[id].managers
    logger.debug("On delete, the old managers were: " + str(old_managers))
    delete_user_list_managers(id, old_managers)

def add_user_list_managers(id, managers):
    for m in managers:
        u = db(db.user_properties.email == m).select(db.user_properties.user_lists).first()
        if u == None:
            # We never heard of this user, but we still create the permission.
            logger.debug("Creating user properties for email:" + str(m) + "<")
            db.user_properties.insert(email=m, user_lists=[])
            db.commit()
            managed_lists = []
        else:
            managed_lists = u.user_lists
        managed_lists = util.list_append_unique(managed_lists, id)
        db(db.user_properties.email == m).update(user_lists = managed_lists)
    db.commit()
            
def delete_user_list_managers(id, managers):
    for m in managers:
        u = db(db.user_properties.email == m).select(db.user_properties.user_lists).first()
        if u != None:
            managed_lists = util.list_remove(u.user_lists, id)
            db(db.user_properties.email == m).update(user_lists = managed_lists)
    db.commit()
                        

def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    """
    return dict(form=auth())


def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()


@auth.requires_signature()
def data():
    """
    http://..../[app]/default/data/tables
    http://..../[app]/default/data/create/[table]
    http://..../[app]/default/data/read/[table]/[id]
    http://..../[app]/default/data/update/[table]/[id]
    http://..../[app]/default/data/delete/[table]/[id]
    http://..../[app]/default/data/select/[table]
    http://..../[app]/default/data/search/[table]
    but URLs must be signed, i.e. linked with
      A('table',_href=URL('data/tables',user_signature=True))
    or with the signed load operator
      LOAD('default','data.load',args='tables',ajax=True,user_signature=True)
    """
    return dict(form=crud())
