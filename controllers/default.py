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
def contest_index():
    """
    We can want several type of contests.
    We may want: 
    * 'subopen': open for submission.
    * 'revopen': open for review.
    * 'submitted': to whom the author has submitted.
    * 'managed' for which the author is a manager.
    """
    # Builds the correct query type.
    props = db(db.user_properties.email == auth.user.email).select().first()
    q_type = request.args(0) or redirect(index)
    if q_type == 'subopen':
        msg = T('Contests open for submission')
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
    elif q_type == 'revopen':
        msg = T('Contests open for review')
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
    elif q_type == 'submitted':
        msg = T('Contests to which you submitted')
        q = (db.contest.id.belongs(props.contests_has_submitted))
    elif q_type == 'managed':
        msg = T('Contests you manage')
        q = (db.contest.id.belongs(props.contest_can_manage))
    else:
        # Invalid query type.
        redirect(index)
    # At this point, we have a query.
    grid = SQLFORM.grid(q,
        field_id=db.contest.id,
        fields=[],
        csv=False,
        details=False,
        create=False,
        links=[dict(header='Name', body = lambda r: A(r.name, _href=URL('view_contest', args=[r.id]))),],
        )
    return dict(grid=grid, msg=msg)
    
    
@auth.requires_login()
def user_list_index():
    """Index of user list one can manage or use."""
    # Reads the list of ids of lists managed by the user.
    list_ids_l = db(db.user_properties.email == auth.user.email).select(db.user_properties.user_lists).first()
    if list_ids_l == None:
        list_ids = []
    else:
        list_ids = list_ids_l['user_lists']
    # Gets the lists.
    q = (db.user_list.id.belongs(list_ids))
    grid = SQLFORM.grid(q, 
        field_id = db.user_list.id,
        csv=False, details=True,
        oncreate=create_user_list,
        onvalidation=validate_user_list,
        onupdate=update_user_list,
        ondelete=delete_user_list)
    return dict(grid=grid)
    

def validate_user_list(form):
    """Splits emails on the same line, and adds the user creating the list to its managers."""
    form.vars.email_list = util.normalize_email_list(form.vars.email_list)
    form.vars.managers = util.normalize_email_list(form.vars.managers)
    if auth.user.email not in form.vars.managers:
        form.vars.managers = [auth.user.email] + form.vars.managers

def get_old_managers(id):
    old_user_list = db(db.user_list.id == form.vars.id).select(db.user_list.managers).first()
    if old_user_list == None:
        return []
    else:
        return old_user_list.managers

def update_user_list(form):
    # Produces the list of people who are no longer managers.
    old_managers = get_old_managers(form.vars.id)
    add_user_list_managers(form.vars.id, util.list_diff(form.vars.managers, old_managers))
    delete_user_list_managers(form.vars.id, util.list_diff(old_managers, form.vars.managers))

def create_user_list(form):
    add_user_list_managers(form.vars.id, form.vars.managers)

def delete_user_list(table, id):
    delete_user_list_managers(id, get_old_managers(id))

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
