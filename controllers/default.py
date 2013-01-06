# -*- coding: utf-8 -*-

import util
from datetime import date, timedelta


from gluon.custom_import import track_changes; track_changes(True)

def index():
    """
    Main index.
    """
    if auth.user_id != None:
        redirect( URL( 'default', 'dashboard' ) )

    user_is_admin = is_user_admin(auth)
    return dict(user_is_admin=user_is_admin)


@auth.requires_login()
def dashboard():
    """ mbrich - The dashboard is the homepage for users that have logged in. """

    # Get the user's properties    
    props = db( db.user_properties.email == auth.user.email ).select( db.user_properties.contests_can_submit ).first()

    submit_list = [] if props == None else props

    # Select all contests that the user can submit to, that are open right now,
    # and that will be closed within 7 days.
    time_limit = datetime.utcnow() + timedelta( days = 30 )
    sub_deadlines = db( ( db.contest.id != None ) 
        & ( db.contest.is_active == True ) 
        & ( db.contest.open_date < datetime.utcnow() )
        & ( db.contest.close_date > datetime.utcnow() )
        & ( db.contest.close_date < time_limit ) ).select( orderby=~ db.contest.close_date )


    deadlines = dict()
    for sub in sub_deadlines:
        deadlines[sub.id] = dict( name = sub.name )

    # Get duties that the user must perform.
    duties = db( db.reviewing_duties.contest_id != None ).select()

    #todo_list = duties if duties != None else []
    return dict( todo_list = duties, sub_deadlines = sub_deadlines )
                                                
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
