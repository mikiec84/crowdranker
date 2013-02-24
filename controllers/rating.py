# coding: utf8

import access
import util
import ranker
import gluon.contrib.simplejson as simplejson
from datetime import datetime
import datetime as dates



@auth.requires_login()
def accept_review():
    """Asks a user whether the user is willing to accept a rating task for a venue,
    and if so, picks a task and adds it to the set of tasks for the user."""
    # Checks the permissions.
    c = db.venue(request.args(0)) or redirect('default', 'index')
    props = db(db.user_properties.user == auth.user.email).select(db.user_properties.venues_can_rate).first()
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
    num_open_tasks = db((db.task.user == auth.user.email) &
			(db.task.venue_id == c.id) &
			(db.task.rejected == False) &
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
        # Reads the most recent ratings given by the user.
        # TODO(luca): we should really poll the rating system for this; that's what
        # should keep track of these things.
        previous_ratings = db((db.comparison.user == auth.user.email) 
            & (db.comparison.venue_id == c.id)).select(orderby=~db.comparison.date).first()
        # To get list of old items we need to check previous ratings
        # and current open tasks.
        if previous_ratings == None:
            old_items = []
        else:
            old_items = util.get_list(previous_ratings.ordering)
        # Now checking open tasks for the user.
        active_items_rows = db((db.task.venue_id == c.id) &
                               (db.task.user == auth.user.email) &
                               (db.task.completed_date == datetime(dates.MAXYEAR, 12, 1))
                               ).select(db.task.submission_id)
        active_items = [x.submission_id for x in active_items_rows]
        old_items.extend(active_items)
        new_item = ranker.get_item(db, c.id, auth.user.email, old_items,
				   can_rank_own_submissions=c.can_rank_own_submissions)
        if new_item == None:
            session.flash = T('There are no items to review so far.')
            redirect(URL('venues', 'rateopen_index'))
        # Creates a reviewing task.
        # To name it, counts how many tasks the user has already for this venue.
        num_tasks = db((db.task.venue_id == c.id) & (db.task.user == auth.user.email)).count()
        task_name = (c.name + ' ' + T('Submission') + ' ' + str(num_tasks + 1))[:STRING_FIELD_LENGTH]
        task_id = db.task.insert(submission_id = new_item, venue_id = c.id, submission_name = task_name)
	# Increments the number of reviews for the item.
	subm = db.submission(new_item)
	if subm is not None:
	    if subm.n_assigned_reviews is None:
		subm.n_assigned_reviews = 1
	    else:
		subm.n_assigned_reviews = subm.n_assigned_reviews + 1
	    subm.update_record()
        db.commit()
        session.flash = T('A review has been added to your review assignments.')
        redirect(URL('task_index', args=[task_id]))
    return dict(venue_form=venue_form, confirmation_form=confirmation_form)

            
@auth.requires_login()
def task_index():
    if len(request.args) == 0:
        q = ((db.task.user == auth.user.email) &
	     (db.task.completed_date > datetime.utcnow()) &
	     (db.task.rejected == False))
	db.task.completed_date.readable = False
	title = T('Reviews to submit')
        links=[
	    dict(header='Deadline',
		 body = lambda r: db.venue(r.venue_id).rate_close_date),
            dict(header='Venue', 
                body = lambda r: A(db.venue(r.venue_id).name, _href=URL('venues', 'view_venue', args=[r.venue_id]))),
            dict(header='Submission', 
                body = lambda r: A(r.submission_name, _href=URL('submission', 'view_submission', args=[r.id]))),
            dict(header='Review', body = review_link),
	    dict(header='Decline', body = decline_link),
	    ]
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
            dict(header='Review', body = review_link),
	    dict(header='Decline', body = decline_link),
	    ]
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


def decline_link(r):
    if r.completed_date > datetime.utcnow():
        return A(T('Decline review'), _class='btn', _href=URL('decline', args=[r.id]))
    else:
        return ''

    
@auth.requires_login()
def decline():
    # Here is where the comparisons are entered.
    t = db.task(request.args(0)) or redirect(URL('default', 'index'))
    if t.user != auth.user.email:
	session.flash = T('Invalid request.')
        redirect(URL('default', 'index'))
    if t.completed_date < datetime.utcnow():
	session.flash = T('This task has alredy been completed.')
	redirect(URL('default', 'index'))
    db.task.rejected.default = True
    db.task.completed_date.readable = False
    db.task.comments.readable = db.task.comments.writable = False
    form = SQLFORM(db.task, t)
    form.vars.rejected = True
    form.add_button(T('Cancel'), URL('rating', 'task_index'))
    if form.process().accepted:
	# Increases the number of rejected reviews for the submission.
	subm = db.submission(t.submission_id)
	n = subm.n_rejected_reviews
        n = 0 if n is None else n
	subm.n_rejected_reviews = n + 1
	subm.update_record()
	db.commit()
	session.flash = T('Review status updated')
	redirect(URL('rating', 'task_index'))
    return dict(form=form)


@auth.requires_login()        
def review():
    """Enters the review, and comparisons, for a particular task.
    This function is only used to enter NEW reviews."""

    # Here is where the comparisons are entered.
    t = db.task(request.args(0)) or redirect(URL('default', 'index'))
    if t.user != auth.user.email:
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
    last_comparison = db((db.comparison.user == auth.user.email)
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
	str_grades = {}
    else:
	try:
	    str_grades = simplejson.loads(last_comparison.grades)
	except Exception, e:
	    str_grades = {}
	    logger.warning("Grades cannot be read: " + str(last_comparison.grades))
    # Now converts the keys to ints.
    grades = {}
    for k, v in str_grades.iteritems():
	try:
	    grades[long(k)] = float(v)
	except Exception, e:
	    logger.warning("Grades cannot be converted: " + str(k) + ":" + str(v))

    # Now we need to find the names of the submissions (for the user) that were 
    # used in this last ordering.
    # We create a submission_id to line mapping, that will be passed in json to the view.
    submissions = {}
    for i in last_ordering:
	# Finds the task.
	st = db((db.task.submission_id == i) &
		(db.task.user == auth.user.email)).select().first()
	if st != None:
	    v = access.validate_task(db, st.id, auth.user.email)
	    if v != None:
		(_, subm, cont) = v
		line = SPAN(A(st.submission_name, _href=URL('submission', 'view_submission', args=[i])),
			    " (Comments: ", util.shorten(st.comments), ") ",
			    A(T('Download'), _class='btn',
			      _href=URL('submission', 'download_reviewer', args=[st.id, subm.content])))
		submissions[i] = line 
    # Adds also the last submission.
    v = access.validate_task(db, t.id, auth.user.email)
    if v == None:
	# Should not happen.
	session.flash('You cannot view this submission.')
	redirect(URL('default', 'index'))
    (_, subm, cont) = v
    line = SPAN(A(t.submission_name, _href=(URL('submission', 'view_submission', args=[t.id]))),
		" ",
		A(T('Download'), _class='btn', _href=URL('submission', 'download_reviewer', args=[t.id, subm.content])))
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
	# Increments the number of reviews this submission has received.
	subm = db.submission(t.submission_id)
	if subm != None and subm.n_completed_reviews != None:
	    n = subm.n_completed_reviews
	    subm.n_completed_reviews = n + 1
	    subm.update_record()
	
	# Marks that the user has reviewed for this venue.
	props = db(db.user_properties.user == auth.user.email).select(db.user_properties.id, db.user_properties.venues_has_rated).first()
        if props == None:
	    db.user_properties.insert(user = auth.user.email,
				      venues_has_rated = [venue.id])
        else:
	    has_rated = util.get_list(props.venues_has_rated)
	    has_rated = util.list_append_unique(has_rated, venue.id)
            props.update_record(venues_has_rated = has_rated)

        # TODO(luca): put it in a queue of things that need processing.
        # All updates done.
        # Calling ranker.py directly.
        ranker.process_comparison(db, t.venue_id, auth.user.email,
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
	logger.debug("request.vars.grades: " + request.vars.grades)
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
			    (db.task.user == auth.user.email)).select().first()
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
	    decoded_grades = simplejson.loads(request.vars.grades)
	    grade_subm = [(float(g), long(s)) for (s, g) in decoded_grades.iteritems()]
	    # Check that all grades are between 0 and 10.
	    for (g, s) in grade_subm:
		if g < 0.0 or g > 10.0:
		    form.errors.comments = T('Grades should be in the interval [0..10]')
		    session.flash = T('Errors in the received grades')
		    return
	    # Sorts the grades in decreasing order.
	    grade_subm.sort()
	    grade_subm.reverse()
	    # Checks that there are no duplicate grades.
	    if len(grade_subm) == 0:
		form.errors.comments = T('No grades specified')
		session.flash = T('Errors in the received grades')
		return
	    (prev, _) = grade_subm[0]
	    for (g, s) in grade_subm[:1]:
		if g == prev:
		    form.errors.comments = T('There is a repeated grade: grades need to be unique.')
		    session.flash = T('Errors in the received grades')
		    return
	    # Checks that the order of the grades matches the one of the submissions.
	    subm_order = [s for (g, s) in grade_subm]
	    if subm_order != form.vars.order:
		form.errors.comments = T('The ranking of the submissions does not reflect the grades.')
		session.flash = T('Errors in the received grades.')
		return
	    # Copies the grades in the form variable.
	    form.vars.grades = request.vars.grades
	except Exception, e:
	    form.errors.comments = T('Error in the received grades')
	    session.flash = T('Error in the received grades')
	    return
	logger.debug("form.vars.order: " + str(form.vars.order))
	logger.debug("form.vars.grades: " + str(form.vars.grades))
    return decode_order


@auth.requires_login()
def my_reviews():
    props = db(db.user_properties.user == auth.user.email).select(db.user_properties.venues_has_rated).first()
    venue_list = util.get_list(props.venues_has_rated)
    q = (db.venue.id.belongs(venue_list))
    db.venue.name.readable = False
    grid = SQLFORM.grid(q,
	field_id = db.venue.id,
	fields = [db.venue.name],
	create=False, details=False,
	csv=False, editable=False, deletable=False,
    # TODO(michael): link to View/edit reviews is disabled for now.
	links=[
	    dict(header=T('Venue'),
		 body = lambda r: A(r.name, _href=URL('venue', 'view_venue', args=[r.id]))),
	    dict(header=T('My reviews'),
		 #body = lambda r: A(T('View/edit reviews'), _href=URL('rating', 'edit_reviews', args=[r.id]))),
		 body = lambda r: T('View/edit reviews')),
	    ],
	)
    return dict(grid=grid)


@auth.requires_login()
def edit_reviews():
    # Gets the information on the venue.
    c = db.venue(request.args[0]) or redirect(URL('default', 'index'))
    # Building ordering.
    last_comparison_r = db((db.comparison.venue_id == c.id) &
                           (db.comparison.user == auth.user) &
                           (db.comparison.is_valid == True)
                          ).select(orderby=~db.comparison.date).first()
    if last_comparison_r is None:
        current_ordering = []
        compar_id = None
        current_grades = {}
    else:
        current_ordering = last_comparison_r.ordering
        compar_id = last_comparison_r.id
        # Dictionary submission id: grade.
        str_grades = simplejson.loads(last_comparison_r.grades)
        current_grades = {long(key):float(value) for (key, value) in str_grades.iteritems()}
    submissions = {}
    for sub_id in current_ordering:
        # Finds the task.
        st = db((db.task.submission_id == sub_id) &
                (db.task.user == auth.user.email)).select().first()
        subm = db.submission(sub_id)
        line = SPAN(A(st.submission_name, _href=URL('submission', 'view_submission', args=[sub_id])),
            " (Comments: ", util.shorten(st.comments), ") ",
            A(T('Download'), _class='btn',
            _href=URL('submission', 'download_reviewer', args=[st.id, subm.content])))
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
         (db.task.user == auth.user.email))
    db.task.assigned_date.writable = False
    db.task.completed_date.writable = False
    db.task.rejection_comment.writable = False
    grid = SQLFORM.grid(q, details=True, csv=False, create=False,
                        editable=(not expired), searchable=False,
                        deletable=False, args=request.args[:1],
                        )
    return dict(grid=grid, title=c.name,
                current_ordering=current_ordering,
                submissions=submissions,
                current_grades=current_grades,
                ordering_edit_link=ordering_edit_link)


@auth.requires_login()
def edit_ordering():
    """ Edit last ordering."""
    # Gets the information on the venue and comparison.
    venue = db.venue(request.args[0]) or redirect(URL('default', 'index'))
    last_comparison = db.comparison(request.args[1]) or redirect(URL('default', 'index'))
    if last_comparison.user != auth.user.email:
        session.flash = T('Invalid request.')
        redirect(URL('default', 'index'))

    # Check that the venue rating deadline is currently open, or that the ranker
    # is a manager or observer.
    if ((auth.user.email not in util.get_list(venue.managers)) and
	(auth.user.email not in util.get_list(venue.observers)) and 
	(datetime.utcnow() < venue.rate_open_date or datetime.utcnow() > venue.rate_close_date)):
	session.flash = T('The review deadline for this venue is closed.')
        redirect(URL('venues', 'view_venue', args=[venue.id]))

    # Ok, the task belongs to the user.
    # Gets the last reviewing task done for the same venue.
    if last_comparison == None:
        last_ordering = []
    else:
        last_ordering = util.get_list(last_comparison.ordering)

    # Finds the grades that were given for the submissions previously reviewed.
    if last_comparison == None or last_comparison.grades == None:
	str_grades = {}
    else:
	try:
	    str_grades = simplejson.loads(last_comparison.grades)
	except Exception, e:
	    str_grades = {}
	    logger.warning("Grades cannot be read: " + str(last_comparison.grades))
    # Now converts the keys to ints.
    grades = {}
    for k, v in str_grades.iteritems():
	try:
	    grades[long(k)] = float(v)
	except Exception, e:
	    logger.warning("Grades cannot be converted: " + str(k) + ":" + str(v))

    # Now we need to find the names of the submissions (for the user) that were 
    # used in this last ordering.
    # We create a submission_id to line mapping, that will be passed in json to the view.
    submissions = {}
    for i in last_ordering:
	# Finds the task.
	st = db((db.task.submission_id == i) &
		(db.task.user == auth.user.email)).select().first()
	if st != None:
	    v = access.validate_task(db, st.id, auth.user.email)
	    if v != None:
		(_, subm, cont) = v
		line = SPAN(A(st.submission_name, _href=URL('submission', 'view_submission', args=[i])),
			    " (Comments: ", util.shorten(st.comments), ") ",
			    A(T('Download'), _class='btn',
			      _href=URL('submission', 'download_reviewer', args=[st.id, subm.content])))
		submissions[i] = line 

    # Creating form.
    form = SQLFORM.factory(hidden=dict(order='', grades=''))

    if form.process(onvalidation=verify_rating_form(-1)).accepted:
        # Creates a new comparison in the db and marks old ona as not valid.
        new_ordering = form.vars.order
        new_grades = form.vars.grades
        decoded_grades = simplejson.loads(new_grades)
        grades_subm = {long(key):float(value) for (key, value) in decoded_grades.iteritems()}
        # Check whether new ordering is different from old one.
        coinside_ordering = (len(new_ordering) == len(last_ordering) and
                         all(x==y for x, y in zip(new_ordering, last_ordering)))
        # Check whether new grades are different from old ones.
        coinside_grades = False
        if coinside_ordering:
            coinside_grades = True
            for subm_id in new_ordering:
                if abs(grades_subm[subm_id] - grades[subm_id]) > 0.00001:
                    coinside_grades = False
        if coinside_ordering and coinside_grades:
            session.flash = T('The review has not been changed.')
            redirect(URL('rating', 'edit_reviews', args=[venue.id]))
        # Okay, we have new review.
        # Mark current review as not valid and create new comparison.
        last_comparison.update_record(is_valid=False)
        new_comparison_id = db.comparison.insert(
            venue_id=venue.id, ordering=new_ordering, grades=new_grades,
            new_item=last_comparison.new_item)
        # Mark that user has revised the comparison.
        props = db(db.user_properties.user == auth.user.email).select(db.user_properties.id, db.user_properties.venues_has_re_reviewed).first()
        if props == None:
            # Should not happen.
            session.flash('You cannot view this review.')
            redirect(URL('default', 'index'))
        has_re_reviewed = util.get_list(props.venues_has_re_reviewed)
        has_re_reviewed.append(venue.id)
        props.update_record(venues_has_re_reviewed = has_re_reviewed)

        # TODO(luca): put it in a queue of things that need processing.
        # All updates done.
        # Calling ranker.py directly.
        ranker.process_comparison(db, venue.id, auth.user.email,
                                  new_ordering[::-1], last_comparison.new_item)
        db.commit()
        session.flash = T('The review has been submitted.')
        redirect(URL('rating', 'edit_reviews', args=[venue.id]))

    return dict(form=form,
        submissions = submissions,
        grades = grades,
        venue = venue,
        current_list = last_ordering,
        )


def check_manager_eligibility(venue_id, user, reject_msg):
    props = db(db.user_properties.user == user).select().first()
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


@auth.requires_login()
def run_rep_system():
    # Gets the information on the venue.
    c = db.venue(request.args[0]) or redirect(URL('default', 'index'))
    check_manager_eligibility(c.id, auth.user.email, 'You cannot evaluate contributors for this venue')
    # This venue_form is used to display the venue.
    venue_form = SQLFORM(db.venue, record=c, readonly=True)
    confirmation_form = FORM.confirm(T('Run'),
        {T('Cancel'): URL('venues', 'view_venue', args=[c.id])})
    if confirmation_form.accepted:
        num_of_iterations = 4
        ranker.run_reputation_system(db, c.id,
                                     num_of_iterations=num_of_iterations)
        db.commit()
        session.flash = T('The computation of reviewer contribution, submission quality, and final grade is complete.')
        redirect(URL('venues', 'view_venue', args=[c.id]))
    return dict(venue_form=venue_form, confirmation_form=confirmation_form)
