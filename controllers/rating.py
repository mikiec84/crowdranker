# coding: utf8

import access
import util
import ranker
import gluon.contrib.simplejson as simplejson
from datetime import datetime
import datetime as dates


@auth.requires_login()
def assign_reviewers():
    c = db.venue(request.args(0)) or redirect('default', 'index')
    props = db(db.user_properties.email == auth.user.email).select().first()
    if props == None:
        session.flash = T('You cannot assign reviewers to this venue.')
        redirect(URL('default', 'index'))
    if not access.can_manage(c, props):
        session.flash = T('You cannot assign reviewers to this venue.')
        redirect(URL('default', 'index'))
    # These are the users that can be called upon reviewing the submissions.
    managed_user_lists = util.get_list(props.managed_user_lists)
    # Constrains the user lists to those managed by the user.
    list_q = (db.user_list.id.belongs(managed_user_lists))
    # The default is the list of users that can review the venue.
    if c.rate_constraint is None:
	form = SQLFORM.factory(
	    Field('users', requires = IS_IN_DB(db(list_q), 'user_list.id', '%(name)s')),
	    Field('number_of_reviews_per_user', 'integer'),
	    Field('incremental', 'boolean'),
	    )
    else:
	form = SQLFORM.factory(
	    Field('users', default = c.rate_constraint,
		  requires = IS_IN_DB(db(list_q), 'user_list.id', '%(name)s')),
	    Field('number_of_reviews_per_user', 'integer'),
	    Field('incremental', 'boolean'),
	    )	
    if form.process().accepted:
        if (util.is_none(form.vars.users) or form.vars.number_of_reviews_per_user == 0 
                or (form.vars.number_of_reviews_per_user < 0 and not form.vars.incremental)):
            session.flash = T('No reviewing duties added.')
            redirect(URL('venues', 'managed_index'))
	n = c.number_of_submissions_per_reviewer
	c.update_record(number_of_submissions_per_reviewer = n + form.vars.number_of_reviews_per_user)
        # TODO(luca): this should be implemented in terms of a job queue
        user_list = db.user_list(form.vars.users)
        for m in user_list.email_list:
            current_asgn = db((db.reviewing_duties.user_email == m) &
                (db.reviewing_duties.venue_id == c.id)).select().first()
            if current_asgn == None:
                # Creates a new one.
                db.reviewing_duties.insert(user_email = m, venue_id = c.id, 
                    num_reviews = form.vars.number_of_reviews_per_user)
            else:
                # Update an existing one
                if form.vars.incremental:
                    new_number = max(0, current_asgn.num_reviews + form.vars.number_of_reviews_per_user)
                else:
                    new_number = form.vars.number_of_reviews_per_user
                current_asgn.update_record(num_reviews = new_number)
        db.commit()
        session.flash = T('The reviewing duties have been assigned.')
        redirect(URL('venues', 'managed_index'))
    venue_form = SQLFORM(db.venue, record=c, readonly=True)
    return dict(venue=c, form=form, vform=venue_form)
                

@auth.requires_login()
def accept_review():
    """Asks a user whether the user is willing to accept a rating task for a venue,
    and if so, picks a task and adds it to the set of tasks for the user."""
    # Checks the permissions.
    c = db.venue(request.args(0)) or redirect('default', 'index')
    props = db(db.user_properties.email == auth.user.email).select(db.user_properties.venues_can_rate).first()
    if props == None:
	c_can_rate = []
    else:
	c_can_rate = util.get_list(props.venues_can_rate)
    if not (c.rate_constraint == None or c.id in c_can_rate):
	session.flash = T('You cannot rate this venue.')
        redirect(URL('venues', 'rateopen_index'))
    t = datetime.utcnow()
    if not (c.is_active and c.is_approved and c.rate_open_date <= t and c.rate_close_date >= t):
        session.flash = T('This venue is not open for rating.')
        redirect(URL('venues', 'rateopen_index'))
    # The user can rate the venue.
    # Does the user have any pending reviewing tasks for the venue?
    num_open_tasks = db((db.task.user_id == auth.user_id) &
			(db.task.venue_id == c.id) &
			(db.task.completed_date > datetime.utcnow())).count()
    if num_open_tasks > c.max_number_outstanding_reviews:
	session.flash = T('You have too many reviews outstanding for this venue. '
			  'Complete some of them before accepting additional reviewing tasks.')
	redirect(URL('rating', 'task_index'))
    # This venue_form is used to display the venue.
    venue_form = SQLFORM(db.venue, record=c, readonly=True)
    confirmation_form = FORM.confirm(T('Accept'),
        {T('Decline'): URL('default', 'index')})
    if confirmation_form.accepted:
        # Decreases the reviewing duties.
        duties = db((db.reviewing_duties.user_email == auth.user.email) &
            (db.reviewing_duties.venue_id == c.id)).select().first()
        if duties != None and duties.num_reviews > 0:
            duties.update_record(num_reviews = duties.num_reviews - 1)
        # Reads the most recent ratings given by the user.
        # TODO(luca): we should really poll the rating system for this; that's what
        # should keep track of these things.
        previous_ratings = db((db.comparison.author == auth.user_id) 
            & (db.comparison.venue_id == c.id)).select(orderby=~db.comparison.date).first()
        # To get list of old items we need to check previous ratings
        # and current open tasks.
        if previous_ratings == None:
            old_items = []
        else:
            old_items = util.get_list(previous_ratings.ordering)
        # Now checking open tasks for the user.
        active_items_rows = db((db.task.venue_id == c.id) &
                               (db.task.user_id == auth.user_id) &
                               (db.task.completed_date == datetime(dates.MAXYEAR, 12, 1))
                               ).select(db.task.submission_id)
        active_items = [x.submission_id for x in active_items_rows]
        old_items.extend(active_items)
        new_item = ranker.get_item(db, c.id, auth.user_id, old_items,
				   can_rank_own_submissions=c.can_rank_own_submissions)
        if new_item == None:
            session.flash = T('There are no items to review so far.')
            redirect(URL('venues', 'rateopen_index'))
        # Creates a reviewing task.
        # To name it, counts how many tasks the user has already for this venue.
        num_tasks = db((db.task.venue_id == c.id) & (db.task.user_id == auth.user_id)).count()
        task_name = (c.name + ' ' + T('Submission') + ' ' + str(num_tasks + 1))[:STRING_FIELD_LENGTH]
        task_id = db.task.insert(submission_id = new_item, venue_id = c.id, submission_name = task_name)
        db.commit()
        session.flash = T('A review has been added to your review assignments.')
        redirect(URL('task_index', args=[task_id]))
    return dict(venue_form=venue_form, confirmation_form=confirmation_form)

            
@auth.requires_login()
def task_index():
    if len(request.args) == 0:
        q = ((db.task.user_id == auth.user_id) & (db.task.completed_date > datetime.utcnow()))
	db.task.completed_date.readable = False
	title = T('Reviews to submit')
        links=[
	    dict(header='Deadline',
		 body = lambda r: db.venue(r.venue_id).rate_close_date),
            dict(header='Venue', 
                body = lambda r: A(db.venue(r.venue_id).name, _href=URL('venues', 'view_venue', args=[r.venue_id]))),
            dict(header='Submission', 
                body = lambda r: A(r.submission_name, _href=URL('submission', 'view_submission', args=[r.id]))),
            dict(header='Review', body = review_link),]
    else:
	t = db.task(request.args(0)) or redirect(URL('default', 'index'))
        # The mode if a specific item.
        title = T('')
        q = (db.task.id == t.id)
        links=[
	    dict(header='Deadline',
		 body = lambda r: db.venue(r.venue_id).rate_close_date),
            dict(header='Venue', 
                body = lambda r: A(db.venue(r.venue_id).name, _href=URL('venues', 'view_venue', args=[r.venue_id]))),
            dict(header='Submission', 
                body = lambda r: A(r.submission_name, _href=URL('submission', 'view_submission', args=[r.id]))),
            dict(header='Review', body = review_link),]
    db.task.submission_name.readable = False
    grid = SQLFORM.grid(q,
        args=request.args[:1],
        field_id=db.task.id,
	user_signature=False,
        create=False, editable=False, deletable=False, csv=False, details=False,
	links=links
        )
    return dict(title=title, grid=grid)

       
def review_link(r):
    if r.completed_date > datetime.utcnow():
        return A(T('Enter review'), _class='btn', _href=URL('review', args=[r.id]))
    else:
        # TODO(luca): Allow resubmitting a review.
        return T('Completed on ') + str(r.completed_date)


@auth.requires_login()        
def review():
    """Enters the review, and comparisons, for a particular task.
    This function is only used to enter NEW reviews."""

    # Here is where the comparisons are entered.
    t = db.task(request.args(0)) or redirect(URL('default', 'index'))
    if t.user_id != auth.user_id:
	session.flash = T('Invalid request.')
        redirect(URL('default', 'index'))

    # Check that the venue rating deadline is currently open, or that the ranker
    # is a manager or observer.
    venue = db.venue(t.venue_id)
    if ((auth.user.email not in util.get_list(venue.managers)) and
	(auth.user.email not in util.get_list(venue.observers)) and 
	(datetime.utcnow() < venue.rate_open_date or datetime.utcnow() > venue.rate_close_date)):
	session.flash = T('The review deadline for this venue is closed.')
        redirect(URL('venues', 'view_venue', args=[venue.id]))

    # Ok, the task belongs to the user. 
    # Gets the last reviewing task done for the same venue.
    last_comparison = db((db.comparison.author == auth.user_id)
        & (db.comparison.venue_id == t.venue_id)).select(orderby=~db.comparison.date).first()
    if last_comparison == None:
        last_ordering = []
    else:
        last_ordering = util.get_list(last_comparison.ordering)
    current_list = last_ordering
    if t.submission_id not in last_ordering:
	current_list.append(t.submission_id)

    # Finds the grades that were given for the submissions previously reviewed.
    if last_comparison == None or last_comparison.grades == None:
	grades = {}
    else:
	try:
	    grades = simplejson.loads(last_comparison.grades)
	except Exception, e:
	    grades = {}
 
    # Now we need to find the names of the submissions (for the user) that were 
    # used in this last ordering.
    # We create a submission_id to line mapping, that will be passed in json to the view.
    submissions = {}
    for i in last_ordering:
	# Finds the task.
	st = db((db.task.submission_id == i) &
		(db.task.user_id == auth.user_id)).select().first()
	if st != None:
	    v = access.validate_task(db, st.id, auth.user_id)
	    if v != None:
		(_, subm, cont) = v
		line = SPAN(A(st.submission_name, _href=URL('submission', 'view_submission', args=[i])),
			    " (Comments: ", util.shorten(st.comments), ") ",
			    A(T('Download'), _class='btn',
			      _href=URL('download_reviewer', args=[st.id, subm.content])))
		submissions[i] = line 
    # Adds also the last submission.
    v = access.validate_task(db, t.id, auth.user_id)
    if v == None:
	# Should not happen.
	session.flash('You cannot view this submission.')
	redirect(URL('default', 'index'))
    (_, subm, cont) = v
    line = SPAN(A(t.submission_name, _href=(URL('submission', 'view_submission', args=[t.id]))),
		" ",
		A(T('Download'), _class='btn', _href=URL('download_reviewer', args=[t.id, subm.content])))
    submissions[t.submission_id] = line
	    
    # Used to check each draggable item and determine which one we should
    # highlight (because its the current/new record).
    new_comparison_item = t.submission_id

    form = SQLFORM.factory(
        Field('comments', 'text'),
        hidden=dict(order='', grades='')
        )

    if form.process(onvalidation=verify_rating_form(t.submission_id)).accepted:
        # Creates a new comparison in the db.
	ordering = form.vars.order
	grades = form.vars.grades
        comparison_id = db.comparison.insert(
	    venue_id=t.venue_id, ordering=ordering, grades=grades, new_item=new_comparison_item) 
        # Marks the task as done.
        t.update_record(completed_date=datetime.utcnow(), comments=form.vars.comments)
	
	# Marks that the user has reviewed for this venue.
	props = db(db.user_properties.email == auth.user.email).select(db.user_properties.id, db.user_properties.venues_has_rated).first()
        if props == None:
	    db.user_properties.insert(email = auth.user.email,
				      venues_has_rated = [venue.id])
        else:
	    has_rated = util.get_list(props.venues_has_rated)
	    has_rated = util.list_append_unique(has_rated, venue.id)
            props.update_record(venues_has_rated = has_rated)

        # TODO(luca): put it in a queue of things that need processing.
        # All updates done.
        # Calling ranker.py directly.
        ranker.process_comparison(db, t.venue_id, auth.user_id,
                                  ordering[::-1], t.submission_id)
        db.commit()
	session.flash = T('The review has been submitted.')
	redirect(URL('rating', 'task_index'))

    return dict(form=form, task=t, 
        submissions = submissions,
	grades = grades,
	sub_title = t.submission_name,
	venue = venue,
        current_list = current_list,
        new_comparison_item = new_comparison_item,
        )

        
def verify_rating_form(subm_id):
    """Verifies a ranking received from the browser, together with the grades."""
    def decode_order(form):
	logger.debug("request.vars.order: " + request.vars.order)
	if request.vars.order == None or request.vars.grades == None:
	    form.errors.comments = T('Error in the received ranking')
	    session.flash = T('Error in the received ranking')
	    return
	# Verifies the order.
	try:
	    decoded_order = [int(x) for x in request.vars.order.split()]
	    for i in decoded_order:
		if i != subm_id:
		    # This must correspond to a previously done task.
		    mt = db((db.task.submission_id == i) &
			    (db.task.user_id == auth.user_id)).select().first()
		    if mt == None or mt.completed_date > datetime.utcnow():
			form.errors.comments = T('Corruputed data received')
			session.flash = T('Corrupted data received')
			break
	    form.vars.order = decoded_order
	except ValueError:
	    form.errors.comments = T('Error in the received ranking')
	    session.flash = T('Error in the received ranking')
	    return
	# Verifies the grades.
	try:
	    decoded_grades = simplejson.loads(form.vars.grades)
	    # Sorts the grades in decreasing order.
	    grade_subm = [(float(g), int(s)) for (s, g) in decoded_grades.iteritems()]
	    grade_subm.sort()
	    grade_subm.reverse()
	    # Checks that there are no duplicate grades.
	    if len(grade_subm) == 0:
		form.errors.comment = T('No grades specified')
		session.flash = T('Errors in the received grades')
		return
	    (prev, _) = grade_subm[0]
	    for (g, s) in grade_subm[1:]:
		if g == prev:
		    form.errors.comment = T('There is a repeated grade: grades need to be unique.')
		    session.flash = T('Errors in the received grades')
		    return
	    # Checks that the order of the grades matches the one of the submissions.
	    subm_order = [s for (g, s) in grade_subm]
	    if subm_order != form.vars.order:
		form.errors.comment = T('The ranking of the submissions does not reflect the grades.')
		session.flash = T('Errors in the received grades.')
		return
	except Exception, e:
	    form.errors.comments = T('Error in the received grades')
	    session.flash = T('Error in the received grades')
	    return
    return decode_order


@auth.requires_login()
def my_reviews():
    props = db(db.user_properties.email == auth.user.email).select(db.user_properties.venues_has_rated).first()
    venue_list = util.get_list(props.venues_has_rated)
    q = (db.venue.id.belongs(venue_list))
    db.venue.name.readable = False
    grid = SQLFORM.grid(q,
	field_id = db.venue.id,
	fields = [db.venue.name],
	create=False, details=False,
	csv=False, editable=False, deletable=False,
	links=[
	    dict(header=T('Venue'),
		 body = lambda r: A(r.name, _href=URL('venue', 'view_venue', args=[r.id]))),
	    dict(header=T('My reviews'),
		 body = lambda r: A(T('View/edit reviews'), _href=URL('rating', 'edit_reviews', args=[r.id]))),
	    ],
	)
    return dict(grid=grid)

@auth.requires_login()
def edit_reviews():
    # Gets the information on the venue.
    c = db.venue(request.args[0]) or redirect(URL('default', 'index'))
    # Building ordering.
    last_comparison_r = db((db.comparison.venue_id == c.id) &
                           (db.comparison.author == auth.user_id) &
                           (db.comparison.valid == True)
                          ).select(orderby=~db.comparison.date).first()
    if last_comparison_r is None:
        current_ordering = []
        compar_id = None
    else:
        current_ordering = last_comparison_r.ordering
        compar_id = last_comparison_r.id
    submissions = {}
    for sub_id in current_ordering:
        # Finds the task.
        st = db((db.task.submission_id == sub_id) &
                (db.task.user_id == auth.user_id)).select().first()
        subm = db.submission(sub_id)
        line = SPAN(A(st.submission_name, _href=URL('submission', 'view_submission', args=[sub_id])),
            " (Comments: ", util.shorten(st.comments), ") ",
            A(T('Download'), _class='btn',
            _href=URL('download_reviewer', args=[st.id, subm.content])))
        submissions[sub_id] = line
    expired =  (datetime.utcnow() < c.rate_open_date or
                datetime.utcnow() > c.rate_close_date)
    # Link for editing ordering.
    if (compar_id is None) or expired:
        ordering_edit_link = None
    else:
        ordering_edit_link = A(T("Edit ordering"),
                               _href=URL('rating', 'edit_ordering',
                               args=[c.id, compar_id]))
    # View/Editing comments.
    q = ((db.task.venue_id == c.id) &
         (db.task.user_id == auth.user_id))
    db.task.assigned_date.writable = False
    db.task.completed_date.writable = False
    grid = SQLFORM.grid(q, details=True, csv=False, create=False,
                        editable=(not expired), searchable=False,
                        deletable=False, args=request.args[:1],
                        )
    return dict(grid=grid, title=c.name,
                current_ordering=current_ordering,
                submissions=submissions,
                ordering_edit_link=ordering_edit_link)

@auth.requires_login()
def edit_ordering():
    return dict()

# TODO(michael): delete this function.
def get_list_of_users(venue_id, constraint, users_are_reviewers=True):
    """ Arguments
        - users_are_reviewers
            if True, then method returns a list of users who rated the venue
            if False, then method returns a list of users who submitted to the venue.
        - constraint is either rate_constraints or submit_constraints
    """
    # Obtaining list of users who can rate the venue.
    list_of_users_r = db(db.user_list.id == constraint).select(db.user_list.email_list).first()
    if not list_of_users_r is None:
        return util.get_list(list_of_users_r.email_list)
    # We don't have list of users, so create one base on reviews or submissions.
    # Next code uses db access a lot but it should not be a problem because we use
    # list of users stored in the db.
    if users_are_reviewers:
        rows = db(db.comparison.venue_id == venue_id).select(db.comparison.author)
        list_of_users = []
        for row in rows:
            usr_id_r = db(db.auth_user.id == row.author).select().first()
            if usr_id_r is None:
                continue
            list_of_users.append(usr_id_r.email)
    else:
        rows = db(db.submission.venue_id == venue_id).select(db.submission.email)
        list_of_users = list(set([x.email for x in rows]))
    return list_of_users


def check_manager_eligibility(venue_id, user_id, reject_msg):
    props = db(db.user_properties.email == user_id).select().first()
    if props == None:
        session.flash = T(reject_msg)
        redirect(URL('default', 'index'))
    managed_venues_list = util.get_list(props.venues_can_manage)
    if venue_id not in managed_venues_list:
        session.flash = T(regect_msg)
        redirect(URL('default', 'index'))


@auth.requires_login()
def recompute_ranks():
    """Recomputes the submission rank.  This can be useful if we change or improve
    the algorithm for computing ranks."""
    # Gets the information on the venue.
    c = db.venue(request.args[0]) or redirect(URL('default', 'index'))
    check_manager_eligibility(c.id, auth.user.email, 'Not authorized.')
    # This venue_form is used to display the venue.
    venue_form = SQLFORM(db.venue, record=c, readonly=True)
    confirmation_form = FORM.confirm(T('Recompute'),
        {T('Cancel'): URL('venues', 'view_venue', args=[c.id])})
    if confirmation_form.accepted:
        # Rerun ranking algorithm.
        # TODO(michael): essentially we need to fork a separate process
	# TODO(luca,michael): ask whether to rerun twice.
        ranker.rerun_processing_comparisons(db, c.id, alpha_annealing=0.5, run_twice=True)
        db.commit()
        session.flash = T('The submission ranking has been recomputed.')
        redirect(URL('venues', 'view_venue', args=[c.id]))
    return dict(venue_form=venue_form, confirmation_form=confirmation_form)


@auth.requires_login()
def evaluate_reviewers():
    # Gets the information on the venue.
    c = db.venue(request.args[0]) or redirect(URL('default', 'index'))
    check_manager_eligibility(c.id, auth.user.email, 'You cannot evaluate contributors for this venue')
    # This venue_form is used to display the venue.
    venue_form = SQLFORM(db.venue, record=c, readonly=True)
    confirmation_form = FORM.confirm(T('Evaluate'),
        {T('Cancel'): URL('venues', 'view_venue', args=[c.id])})
    if confirmation_form.accepted:
        ranker.evaluate_contributors(db, c.id)
        db.commit()
        session.flash = T('The evaluation of reviewers has been performed.')
        redirect(URL('venues', 'view_venue', args=[c.id]))
    return dict(venue_form=venue_form, confirmation_form=confirmation_form)


@auth.requires_login()
def compute_final_grades():
    # Gets the information on the venue.
    c = db.venue(request.args[0]) or redirect(URL('default', 'index'))
    check_manager_eligibility(c.id, auth.user.email, 'You cannot compute final grades for this venue')
    # This venue_form is used to display the venue.
    venue_form = SQLFORM(db.venue, record=c, readonly=True)
    # Checking that reviewers and ranking were computed.
    venue_row = db(db.venue.id == c.id).select().first()
    reviewers_eval_date = venue_row.latest_reviewers_evaluation_date
    rank_update_date = venue_row.latest_rank_update_date
    if rank_update_date is None:
        session.flash = T('Final grades cannot be computed. Please compute ranking first')
        redirect(URL('venues', 'view_venue', args=[c.id]))
    if reviewers_eval_date is None or reviewers_eval_date < rank_update_date:
        session.flash = T('Final grades cannot be computed. Please evaluate reviewers first')
        redirect(URL('venues', 'view_venue', args=[c.id]))
    # Okay, we can compute final grades.
    confirmation_form = FORM.confirm(T('Compute grades'),
        {T('Cancel'): URL('venues', 'view_venue', args=[c.id])})
    if confirmation_form.accepted:
        ranker.compute_final_grades(db, c.id)
        db.commit()
        session.flash = T('The final grades have been computed.')
        redirect(URL('venues', 'view_venue', args=[c.id]))
    return dict(venue_form=venue_form, confirmation_form=confirmation_form)

