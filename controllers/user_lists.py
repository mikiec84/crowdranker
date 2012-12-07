# coding: utf8

import util

@auth.requires_login()
def index():
    """Index of user list one can manage or use."""
    # Reads the list of ids of lists managed by the user.
    list_ids_l = db(db.user_properties.email == auth.user.email).select(db.user_properties.managed_user_lists).first()
    list_ids = util.get_list(list_ids_l.managed_user_lists)
    # Keeps track of old managers, if this is an update.
    if len(request.args) > 2 and request.args[-3] == 'edit':
        ul = db.user_list[request.args[-1]]
        old_managers = ul.managers
        old_members = ul.email_list
    else:
        old_managers = []
        old_members = []
    # Gets the lists.
    q = (db.user_list.id.belongs(list_ids))
    grid = SQLFORM.grid(q, 
        field_id = db.user_list.id,
        csv=False, details=True,
        deletable=False,
        oncreate=create_user_list,
        onvalidation=validate_user_list,
        onupdate=update_user_list(old_managers, old_members),
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
    
def update_user_list(old_managers, old_members):
    """We return a callback that takes a form argument."""
    def f(form):
        logger.debug("Old managers: " + str(old_managers))
        logger.debug("New managers: " + str(form.vars.managers))
        add_user_list_managers(form.vars.id, util.list_diff(form.vars.managers, old_managers))
        delete_user_list_managers(form.vars.id, util.list_diff(old_managers, form.vars.managers))
        # If the list membership has been modified, we may need to update all the users
        # for which the list was used as contest constraint.
        added_users = util.list_diff(form.vars.email_list, old_members)
        removed_users = util.list_diff(old_members, email_list)
        if len(added_users) + len(removed_users) > 0:
            # Otherwise, no point wasting time.
            # Submit constraint.
            contests = db(db.contest.submit_constraint == form.vars.id).select()
            # These contests were using the list as submit constraint.
            for c in contests:
                add_contest_to_user_submit(c.id, added_users)
                delete_contest_from_submitters(c.id, removed_users)
            # Rate constraint.
            contests= db(db.contest.rate_constraint == form.vars.id).select()
            for c in contests:
                add_contest_to_user_rate(c.id, added_users)
                delete_contest_from_raters(c.id, removed_users)
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
        u = db(db.user_properties.email == m).select(db.user_properties.managed_user_lists).first()
        if u == None:
            # We never heard of this user, but we still create the permission.
            logger.debug("Creating user properties for email:" + str(m) + "<")
            db.user_properties.insert(email=m, managed_user_lists=[])
            db.commit()
            managed_lists = []
        else:
            managed_lists = u.managed_user_lists
        managed_lists = util.list_append_unique(managed_lists, id)
        db(db.user_properties.email == m).update(managed_user_lists = managed_lists)
    db.commit()
            
def delete_user_list_managers(id, managers):
    for m in managers:
        u = db(db.user_properties.email == m).select(db.user_properties.managed_user_lists).first()
        if u != None:
            managed_lists = util.list_remove(u.managed_user_lists, id)
            db(db.user_properties.email == m).update(managed_user_lists = managed_lists)
    db.commit()
