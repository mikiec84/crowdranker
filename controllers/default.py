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
    props = db(db.user_properties.user == auth.user_id).select().first()
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
    list_ids_l = db(db.user_properties.user == auth.user_id).select(db.user_properties.user_lists).first()
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
        ondelete=delete_user_list)
    return dict(grid=grid)
    

def validate_user_list(form):
    if isinstance(form.vars.email_list, basestring):
        form.vars.email_list = [form.vars.email_list]
    if isinstance(form.vars.managers, basestring):
        form.vars.managers = [form.vars.managers]
    logger.debug("email_list:" + str(form.vars.email_list) + " managers:" + str(form.vars.managers))
    if auth.user.email not in form.vars.managers:
        form.vars.managers = [auth.user.email] + form.vars.managers

def create_user_list(form):
    u = db(db.user_properties.user == auth.user_id).select().first()
    if u == None:
        db.user_properties.insert(user = auth.user_id)
        ul = []
    else:
        ul = u.user_lists
    ul = util.append_unique(ul, form.vars.id)
    db(db.user_properties.user == auth.user_id).update(user_lists=ul)
    db.commit()
    
def delete_user_list(table, id):
    u = db(db.user_properties.user == auth.user_id).select().first()
    if u == None:
        db.user_properties.insert(user = auth.user_id)
    else:
        ul = util.list_remove(u.user_lists, id)
        db(db.user_properties.user == auth.user_id).update(user_lists=ul)
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
