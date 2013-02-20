# coding: utf8

import access
import util

@auth.requires_login()
def view_venue():
    c = db.venue(request.args(0)) or redirect(URL('default', 'index'))
    props = db(db.user_properties.email == auth.user.email).select().first()
    if props == None: 
        can_submit = False
        can_rate = False
        has_submitted = False
        has_rated = False
        can_manage = False
	can_observe = False
        can_view_ratings = False
    else:
        can_submit = c.id in util.get_list(props.venues_can_submit) or util.is_none(c.submit_constraint)
        can_rate = c.id in util.get_list(props.venues_can_rate) or util.is_none(c.rate_constraint)
        has_submitted = c.id in util.get_list(props.venues_has_submitted)
        has_rated = c.id in util.get_list(props.venues_has_rated)
        can_manage = c.id in util.get_list(props.venues_can_manage)
        can_observe = c.id in util.get_list(props.venues_can_observe)
	# MAYDO(luca): Add option to allow only raters, or only submitters, to view
	# all ratings.
	can_view_ratings = access.can_view_ratings(c, props)
    venue_form = SQLFORM(db.venue, record=c, readonly=True)
    link_list = []
    if can_submit:
        link_list.append(A(T('Submit to this venue'), _href=URL('submission', 'submit', args=[c.id])))
    if can_rate:
        link_list.append(A(T('Review a submission'), _href=URL('rating', 'accept_review', args=[c.id])))
    if has_submitted:
        link_list.append(A(T('View my submissions'), _href=URL('submission', 'my_submissions_index', args=[c.id])))
    if can_manage:
        link_list.append(A(T('Edit'), _href=URL('managed_index', vars=dict(cid=c.id))))
	link_list.append(A(T('Add submission'), _href=URL('submission', 'manager_submit', args=[c.id])))
        link_list.append(A(T('Recompute submission ranking'), _href=URL('rating', 'recompute_ranks', args=[c.id])))
        link_list.append(A(T('Run reputation system'), _href=URL('rating', 'run_rep_system', args=[c.id])))
        link_list.append(A(T('Evaluate reviewers'), _href=URL('rating', 'evaluate_reviewers', args=[c.id])))
        link_list.append(A(T('Compute final grades'), _href=URL('rating', 'compute_final_grades', args=[c.id])))
    if can_observe or can_manage:
	link_list.append(A(T('View reviewing tasks'), _href=URL('ranking', 'view_tasks', args=[c.id])))
	link_list.append(A(T('View comparisons'), _href=URL('ranking', 'view_comparisons_index', args=[c.id])))
    if can_view_ratings or access.can_view_submissions(c, props):
        link_list.append(A(T('View submissions'), _href=URL('ranking', 'view_venue', args=[c.id])))
    if access.can_view_rating_contributions(c, props):
        link_list.append(A(T('View reviewer contribution'), _href=URL('ranking', 'view_raters', args=[c.id])))
    if can_view_ratings:
        link_list.append(A(T('View final grades'), _href=URL('ranking', 'view_final_grades', args=[c.id])))
    return dict(form=venue_form, link_list=link_list, venue=c, has_rated=has_rated)
        

@auth.requires_login()
def subopen_index():
    props = db(db.user_properties.email == auth.user.email).select(db.user_properties.venues_can_submit).first()
    if props == None: 
        l = []
    else:
        l = util.get_list(props.venues_can_submit)
    t = datetime.utcnow()
    q_all = ((db.venue.close_date > t) &
             (db.venue.is_active == True) &
             (db.venue.is_approved == True) &
             (db.venue.submit_constraint == None)
             )
    c_all = db(q_all).select(db.venue.id, db.venue.open_date)
    # Filters by close date as well.
    c_all_open = []
    for c in c_all:
        if c.open_date < t:
            c_all_open.append(c.id)
    if len(l) > 0:
        q_user = ((db.venue.close_date > t) &
                  (db.venue.is_active == True) &
                  (db.venue.id.belongs(l))
                  )
        c_user = db(q_user).select(db.venue.id, db.venue.open_date)
        for c in c_user:
            if c.open_date < t and c.id not in c_all_open:
                c_all_open.append(c.id)
    if len(c_all_open) > 0:
	q = (db.venue.id.belongs(c_all_open))
    else:
	q = (db.venue.id == -1)
    grid = SQLFORM.grid(q,
        field_id=db.venue.id,
        fields=[db.venue.name, db.venue.close_date],
        csv=False, details=False, create=False, editable=False, deletable=False,
        links=[
	    dict(header=T('Submit'), 
		 body = lambda r: A(T('Submit'), _class='btn', _href=URL('submission', 'submit', args=[r.id]))),
	    ],
        )
    return dict(grid=grid)


@auth.requires_login()
def rateopen_index():
    #TODO(luca): see if I can put an inline form for accepting review tasks.
    props = db(db.user_properties.email == auth.user.email).select(db.user_properties.venues_can_rate).first()
    if props == None:
        l = []
    else:
        l = util.get_list(props.venues_can_rate)
    t = datetime.utcnow()
    q_all = ((db.venue.rate_close_date > datetime.utcnow()) &
             (db.venue.is_active == True) &
             (db.venue.is_approved == True) &
             (db.venue.rate_constraint == None)
             )
    c_all = db(q_all).select(db.venue.id, db.venue.open_date)
    c_all_open = []
    for c in c_all:
        if c.open_date < t:
            c_all_open.append(c.id)    
    if len(l) > 0:
        q_user = ((db.venue.rate_close_date > datetime.utcnow()) &
                  (db.venue.is_active == True) &
                  (db.venue.id.belongs(l))
                  )
        c_user = db(q_user).select(db.venue.id, db.venue.open_date)
        for c in c_user:
            if c.open_date < t and c.id not in c_all_open:
                c_all_open.append(c.id)
    if len(c_all_open) > 0:
	q = (db.venue.id.belongs(c_all_open))
    else:
	q = (db.venue.id == -1)
    db.venue.rate_close_date.label = T('Review deadline')
    grid = SQLFORM.grid(q,
        field_id=db.venue.id,
        fields=[db.venue.name, db.venue.rate_close_date],
        csv=False, details=False, create=False, editable=False, deletable=False,
        links=[
	    dict(header='Review', 
		 body = lambda r: A(T('Accept reviewing task'),
			       _class='btn',
			       _href=URL('rating', 'accept_review', args=[r.id])))],
        )
    return dict(grid=grid)

                
@auth.requires_login()
def submitted_index():
    props = db(db.user_properties.email == auth.user.email).select(db.user_properties.venues_has_submitted).first()
    if props == None: 
        l = []
    else:
        l = util.id_list(util.get_list(props.venues_has_submitted))
    if len(l) > 0:
	q = (db.venue.id.belongs(l))
    else:
	q = (db.venue.id == -1)
    db.venue.feedback_accessible_immediately.readable = False
    db.venue.rate_open_date.readable = False
    db.venue.rate_close_date.readable = False
    grid = SQLFORM.grid(q,
        field_id=db.venue.id,
        fields=[db.venue.name, db.venue.rate_open_date, db.venue.rate_close_date, db.venue.feedback_accessible_immediately],
        csv=False, details=False, create=False, editable=False, deletable=False,
        links=[
	    dict(header='Feedback', body = lambda r: link_feedback(r)),
            dict(header='My submissions', body = lambda r: 
                A(T('My submissions'),
		  _class='btn',
		  _href=URL('submission', 'my_submissions_index', args=[r.id]))),
            ],
        )
    return dict(grid=grid)

def link_feedback(venue):
    """Decides if it can show feedback for this venue."""
    if ((venue.rate_close_date < datetime.utcnow()) | venue.feedback_accessible_immediately):
        return A(T('View feedback'), _class='btn', _href=URL('feedback', 'index', args=[venue.id]))
    else:
        return T('Not yet available')


@auth.requires_login()
def observed_index():
    props = db(db.user_properties.email == auth.user.email).select(db.user_properties.venues_can_observe).first()
    if props == None: 
        l = []
    else:
        l = util.id_list(util.get_list(props.venues_can_observe))
    if len(l) > 0:
	q = (db.venue.id.belongs(l))
    else:
	q = (db.venue.id == -1)
    grid = SQLFORM.grid(q,
        field_id=db.venue.id,
        fields=[db.venue.name, db.venue.close_date, db.venue.rate_close_date],
        csv=False, details=False, create=False, editable=False, deletable=False,
        )
    return dict(grid=grid)


def public_index():
    q = ((db.venue.submissions_visible_to_all == True) &
	 ((db.venue.submissions_visible_immediately == True) | (
	     db.venue.close_date > datetime.utcnow())))
    db.venue.feedback_accessible_immediately.readable = False
    db.venue.rate_open_date.readable = False
    db.venue.rate_close_date.readable = False
    grid = SQLFORM.grid(q,
        field_id=db.venue.id,
        fields=[db.venue.name, db.venue.description, db.venue.close_date],
        csv=False, details=False, create=False, editable=False, deletable=False,
        links=[
	    dict(header=T('Submissions'),
		 body = lambda r: A(T('Submissions'), _href=URL('ranking', 'view_venue', args=[r.id])))
            ],
        )
    return dict(grid=grid)

                
@auth.requires_login()
def reviewing_duties():
    """This function lists venues where users have reviews to accept, so that users
    can be redirected to a page where to perform such reviews."""
    # Produces a list of venues that are open for rating.
    props = db(db.user_properties.email == auth.user.email).select(db.user_properties.venues_can_rate).first()
    if props == None:
        l = []
    else:
        l = util.get_list(props.venues_can_rate)
    t = datetime.utcnow()
    if len(l) == 0:
	q = (db.venue.id == -1)
    else:
	q = ((db.venue.rate_close_date > t) & (db.venue.is_active == True) & (db.venue.id.belongs(l)))
    db.venue.rate_close_date.label = T('Review deadline')
    db.venue.number_of_submissions_per_reviewer.label = T('Total n. of reviews')
    grid = SQLFORM.grid(q,
        field_id=db.venue.id,
        fields=[db.venue.name, db.venue.rate_open_date, db.venue.rate_close_date,
		db.venue.number_of_submissions_per_reviewer],
        csv=False, details=False, create=False, editable=False, deletable=False,
        links=[
	    dict(header=T('N. reviews to do'), body = lambda r: get_num_reviews_todo(r)),
	    dict(header='Accept',
		 body = lambda r: 
		 A(T('Accept to do a review'), _href=URL('rating', 'accept_review', args=[r.id]))),
	    ]
        )
    return dict(grid=grid)


def get_num_reviews_todo(venue):
    if venue.number_of_submissions_per_reviewer == 0 or venue.number_of_submissions_per_reviewer == None:
	return 0
    # See how many reviewing tasks the user has accepted.
    n_accepted_tasks = db((db.task.venue_id == venue.id) &
			  (db.task.user_id == auth.user_id)).count()
    return max(0, venue.number_of_submissions_per_reviewer - n_accepted_tasks)


def view_venue_link(venue_id):
    v = db.venue(venue_id)
    if v == None:
	return ''
    return A(v.name, _href=URL('venues', 'view_venue', args=[venue_id]))


def get_review_deadline(venue_id):
    v = db.venue(venue_id)
    if v == None:
	return ''
    return v.rate_close_date


@auth.requires_login()
def simple_index():
    q = (db.venue.id.belongs([1]))
    return dict(list=db(q).select())
        

@auth.requires_login()
def managed_index():
    props = db(db.user_properties.email == auth.user.email).select().first()
    if props == None:
        managed_venue_list = []
        managed_user_lists = []
    else:
        managed_venue_list = util.get_list(props.venues_can_manage)
        managed_user_lists = util.get_list(props.managed_user_lists)
    if len(managed_venue_list) > 0:
	q = (db.venue.id.belongs(managed_venue_list))
    else:
	q = (db.venue.id == -1)
    # Admins can see all venues.
    if is_user_admin():
	q = (db.venue.id > 0)
    # Deals with search parameter.
    if request.vars.cid and request.vars.cid != '':
        try:
            cid = int(request.vars.cid)
        except ValueError:
            cid = None
        if cid != None and cid in managed_venue_list:
            q = (db.venue.id == cid)
    # Constrains the user lists to those managed by the user.
    list_q = (db.user_list.id.belongs(managed_user_lists))
    db.venue.submit_constraint.requires = IS_EMPTY_OR(IS_IN_DB(
        db(list_q), 'user_list.id', '%(name)s', zero=T('-- Everybody --')))
    db.venue.rate_constraint.requires = IS_EMPTY_OR(IS_IN_DB(
        db(list_q), 'user_list.id', '%(name)s', zero=T('-- Everybody --')))
    # Keeps track of old managers and observers, if this is an update.
    if len(request.args) > 2 and request.args[-3] == 'edit':
        c = db.venue[request.args[-1]]
        old_managers = c.managers
	old_observers = c.observers
        old_submit_constraint = c.submit_constraint
        old_rate_constraint = c.rate_constraint
    else:
        old_managers = []
	old_observers = []
        old_submit_constraint = None
        old_rate_constraint = None
    if len(request.args) > 0 and (request.args[0] == 'edit' or request.args[0] == 'new'):
        # Adds some editing help
        add_help_for_venue('bogus')
	# Sets defaults for homeworks
	set_homework_defaults('bogus')
	db.venue.number_of_submissions_per_reviewer.writable = True
	db.venue.number_of_submissions_per_reviewer.readable = True
    if is_user_admin():
	db.venue.is_approved.writable = True
	db.venue.created_by.readable = True
	db.venue.creation_date.readable = True
	db.venue.is_approved.default = True
	fields = [db.venue.name, db.venue.created_by, db.venue.creation_date, db.venue.is_approved, db.venue.is_active]
    else:
	fields = [db.venue.name, db.venue.is_active]	
    grid = SQLFORM.grid(q,
        field_id=db.venue.id,
        fields=fields,
        csv=False, details=False,
	create=True,
        deletable=is_user_admin(), # Disabled for general users; cannot delete venues with submissions.
        onvalidation=validate_venue,
        oncreate=create_venue,
        onupdate=update_venue(old_managers, old_observers, old_submit_constraint, old_rate_constraint),
        links_in_grid=True,
        )
    db.commit()
    return dict(grid=grid)
    
def add_help_for_venue(bogus):
    # Let's add a bit of help for editing
    db.venue.is_approved.comment = 'A venue must be approved by site admins before others can access it.'
    db.venue.is_active.comment = 'Uncheck to prevent all access to this venue.'
    db.venue.managers.comment = 'Email addresses of venue managers.'
    db.venue.observers.comment = 'Email addresses of venue observers.'
    db.venue.name.comment = 'Name of the venue'
    db.venue.open_date.comment = 'In UTC.'
    db.venue.close_date.comment = 'In UTC.'
    db.venue.rate_open_date.comment = 'In UTC.'
    db.venue.rate_close_date.comment = 'In UTC.'
    db.venue.allow_multiple_submissions.comment = (
        'Allow users to submit multiple independent pieces of work to this venue.')
    db.venue.allow_link_submission.comment = (
	'Allow the submissions of links.  WARNING: CrowdRanker does not ensure '
	'that the content of the link is unchanged.')
    db.venue.feedback_accessible_immediately.comment = (
        'The feedback can be accessible immediately, or once '
        'the venue closes.')
    db.venue.rating_available_to_all.comment = (
        'The ratings will be publicly visible.')
    db.venue.feedback_available_to_all.comment = (
        'The feedback to submissions will be available to all.')
    db.venue.feedback_is_anonymous.comment = (
        'The identity of users providing feedback is not revealed.')
    db.venue.submissions_are_anonymized.comment = (
        'The identities of submission authors are not revealed to the raters.')
    db.venue.max_number_outstanding_reviews.comment = (
	'How many outstanding reviews for this venue can a user have at any given time. '
        'Enter a number between 1 and 100.  The lower, the more accurate the rankings are, '
	'since choosing later which submissions need additional reviews improves accuracy.')
    db.venue.can_rank_own_submissions.comment = (
	'Allow authors to rank their own submissions.  This is used mainly to facilitate '
	'demos and debugging.')
    db.venue.rater_contributions_visible_to_all.comment = (
	'Allow everybody to see how much the reviewers contributed to the ranking.')
    db.venue.submissions_visible_to_all.comment = (
	'Submissions are visible to all.')
    db.venue.submissions_visible_immediately.comment = (
	'Submissions are public immediately, even before the submission deadline.')


def set_homework_defaults(bogus):
    """Sets defaults appropriate for most homeworks."""
    db.venue.allow_multiple_submissions.default = False
    # db.venue.allow_multiple_submissions.readable = db.venue.allow_multiple_submissions.writable = False
    db.venue.submission_title_is_file_name.default = False
    db.venue.submission_title_is_file_name.readable = db.venue.submission_title_is_file_name.writable = False
    db.venue.can_rank_own_submissions.default = False
    # db.venue.can_rank_own_submissions.readable = db.venue.can_rank_own_submissions.writable = False
    db.venue.max_number_outstanding_reviews.default = 1
    db.venue.max_number_outstanding_reviews.readable = db.venue.max_number_outstanding_reviews.writable = False
    db.venue.feedback_is_anonymous.default = True
    db.venue.feedback_is_anonymous.readable = db.venue.feedback_is_anonymous.writable = False
    db.venue.submissions_visible_immediately.default = False
    db.venue.submissions_visible_immediately.readable = db.venue.submissions_visible_immediately.writable = False
    db.venue.feedback_available_to_all.default = False
    db.venue.feedback_available_to_all.readable = db.venue.feedback_available_to_all.writable = False
    db.venue.rating_available_to_all.default = False
    db.venue.rating_available_to_all.readable = db.venue.rating_available_to_all.writable = False
    db.venue.rater_contributions_visible_to_all.default = False
    db.venue.rater_contributions_visible_to_all.readable = db.venue.rater_contributions_visible_to_all.writable = False
    db.venue.latest_rank_update_date.readable = False
    db.venue.latest_reviewers_evaluation_date.readable = False
    db.venue.latest_final_grades_evaluation_date.readable = False
    db.venue.number_of_submissions_per_reviewer.readable = False

    
def validate_venue(form):
    """Validates the form venue, splitting managers listed on the same line."""
    form.vars.managers = util.normalize_email_list(form.vars.managers)
    form.vars.observers = util.normalize_email_list(form.vars.observers)
    if auth.user.email not in form.vars.managers:
        form.vars.managers = [auth.user.email] + form.vars.managers
    

def add_venue_to_user_managers(id, user_list):
    for m in user_list:
        u = db(db.user_properties.email == m).select(db.user_properties.venues_can_manage).first()
        if u == None:
            # We never heard of this user, but we still create the permission.
            db.user_properties.insert(email=m, venues_can_manage = [id])
        else:
            l = u.venues_can_manage
	    l = util.list_append_unique(l, id)
	    db(db.user_properties.email == m).update(venues_can_manage = l)
        
def add_venue_to_user_observers(id, user_list):
    for m in user_list:
        u = db(db.user_properties.email == m).select(db.user_properties.venues_can_observe).first()
        if u == None:
            # We never heard of this user, but we still create the permission.
            db.user_properties.insert(email=m, venues_can_observe = [id])
        else:
            l = u.venues_can_observe
	    l = util.list_append_unique(l, id)
	    db(db.user_properties.email == m).update(venues_can_observe = l)
        
def add_venue_to_user_submit(id, user_list):
    for m in user_list:
        u = db(db.user_properties.email == m).select(db.user_properties.venues_can_submit).first()
        if u == None:
            # We never heard of this user, but we still create the permission.
            db.user_properties.insert(email=m, venues_can_submit = [id])
        else:
            l = u.venues_can_submit
	    l = util.list_append_unique(l, id)
	    db(db.user_properties.email == m).update(venues_can_submit = l)
        
def add_venue_to_user_rate(id, user_list):
    for m in user_list:
        u = db(db.user_properties.email == m).select(db.user_properties.venues_can_rate).first()
        if u == None:
            # We never heard of this user, but we still create the permission.
            db.user_properties.insert(email=m, venues_can_rate = [id])
        else:
            l = u.venues_can_rate
	    l = util.list_append_unique(l, id)
	    db(db.user_properties.email == m).update(venues_can_rate = l)

def delete_venue_from_managers(id, user_list):
    for m in user_list:
        u = db(db.user_properties.email == m).select(db.user_properties.venues_can_manage).first()
        if u != None:
            l = util.list_remove(u.venues_can_manage, id)
            db(db.user_properties.email == m).update(venues_can_manage = l)
       
def delete_venue_from_observers(id, user_list):
    for m in user_list:
        u = db(db.user_properties.email == m).select(db.user_properties.venues_can_observe).first()
        if u != None:
            l = util.list_remove(u.venues_can_observe, id)
            db(db.user_properties.email == m).update(venues_can_observe = l)
       
def delete_venue_from_submitters(id, user_list):
    for m in user_list:
        u = db(db.user_properties.email == m).select(db.user_properties.venues_can_submit).first()
        if u != None:
            l = util.list_remove(u.venues_can_submit, id)
            db(db.user_properties.email == m).update(venues_can_submit = l)
       
def delete_venue_from_raters(id, user_list):
    for m in user_list:
        u = db(db.user_properties.email == m).select(db.user_properties.venues_can_rate).first()
        if u != None:
            l = util.list_remove(u.venues_can_rate, id)
            db(db.user_properties.email == m).update(venues_can_rate = l)
                        
def create_venue(form):
    """Processes the creation of a context, propagating the effects."""
    # First, we need to add the context for the new managers.
    add_venue_to_user_managers(form.vars.id, form.vars.managers)
    add_venue_to_user_observers(form.vars.id, form.vars.observers)
    # If there is a submit constraint, we need to allow all the users
    # in the list to submit.
    if not util.is_none(form.vars.submit_constraint):
        user_list = db.user_list[form.vars.submit_constraint].email_list
        # We need to add everybody in that list to submit.
        add_venue_to_user_submit(form.vars.id, user_list)
    # If there is a rating constraint, we need to allow all the users
    # in the list to rate.
    if not util.is_none(form.vars.rate_constraint):
        user_list = db.user_list[form.vars.rate_constraint].email_list
        add_venue_to_user_rate(form.vars.id, user_list)
                
def update_venue(old_managers, old_observers, old_submit_constraint, old_rate_constraint):
    """A venue is being updated.  We need to return a callback for the form,
    that will produce the proper update, taking into account the change in permissions."""
    def f(form):
        # Managers.
        add_venue_to_user_managers(form.vars.id, util.list_diff(form.vars.managers, old_managers))
        delete_venue_from_managers(form.vars.id, util.list_diff(old_managers, form.vars.managers))
	# Observers.
        add_venue_to_user_observers(form.vars.id, util.list_diff(form.vars.observers, old_observers))
        delete_venue_from_observers(form.vars.id, util.list_diff(old_observers, form.vars.observers))
        # Submitters.
        if str(old_submit_constraint) != str(form.vars.submit_constraint):
            # We need to update.
	    if old_submit_constraint != None:
                user_list = db.user_list[old_submit_constraint].email_list
                delete_venue_from_submitters(form.vars.id, user_list)
            if not util.is_none(form.vars.submit_constraint):
                user_list = db.user_list[form.vars.submit_constraint].email_list
                add_venue_to_user_submit(form.vars.id, user_list)
        # Raters.
        if str(old_rate_constraint) != str(form.vars.rate_constraint):
            # We need to update.
	    if old_rate_constraint != None:
                user_list = db.user_list[old_rate_constraint].email_list
                delete_venue_from_raters(form.vars.id, user_list)
            if not util.is_none(form.vars.rate_constraint):
                user_list = db.user_list[form.vars.rate_constraint].email_list
                add_venue_to_user_rate(form.vars.id, user_list)
    return f
                
def delete_venue(table, id):
    c = db.venue[id]
    delete_venue_from_managers(id, c.managers)
    delete_venue_from_observers(id, c.observers)
    if c.submit_constraint != None:
        user_list = db.user_list[c.submit_constraint]
        delete_venue_from_submitters(id, user_list)
    if c.rate_constraint != None:
        user_list = db.user_list[c.rate_constraint]
        delete_venue_from_raters(id, user_list)
