# coding: utf8

import util
import ranker
import gluon.contrib.simplejson as simplejson


@auth.requires_login()
def assign_reviewers():
    c = db.contest(request.args(0)) or redirect('default', 'index')
    props = db(db.user_properties.email == auth.user.email).select().first()
    if props == None:
        session.flash = T('You cannot assign reviewers to this contest.')
        redirect(URL('default', 'index'))
    managed_contests_list = util.get_list(props.contests_can_manage)
    managed_user_lists = util.get_list(props.managed_user_lists)
    if c.id not in managed_contests_list:
        session.flash = T('You cannot assign reviewers to this contest.')
        redirect(URL('default', 'index'))
    # Constrains the user lists to those managed by the user.
    list_q = (db.user_list.id.belongs(managed_user_lists))
    form = SQLFORM.factory(Field('users', requires = IS_EMPTY_OR(IS_IN_DB(
        db(list_q), 'user_list.id', '%(name)s', zero=T('-- Everybody --')))),
        Field('number_of_reviews_per_user', 'integer'),
        Field('incremental', 'boolean'),
        )
    if form.process().accepted:
        if (util.is_none(form.vars.users) or form.vars.number_of_reviews_per_user == 0 
                or (form.vars.number_of_reviews_per_user < 0 and not form.vars.incremental)):
            session.flash = T('No reviewing duties added.')
            redirect(URL('contests', 'managed_index'))
        # TODO(luca): this should be implemented in terms of an appengine queue
        user_list = db.user_list(form.vars.users)
        for m in user_list.email_list:
            current_asgn = db((db.reviewing_duties.user_email == m) &
                (db.reviewing_duties.contest_id == c.id)).select().first()
            if current_asgn == None:
                # Creates a new one.
                db.reviewing_duties.insert(user_email = m, contest_id = c.id, 
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
        redirect(URL('contests', 'managed_index'))
                

@auth.requires_login()
def accept_review():
    """Asks a user whether the user is willing to accept a rating task for a contest,
    and if so, picks a task and adds it to the set of tasks for the user."""
    # Checks the permissions.
    c = db.contest(request.args(0)) or redirect('default', 'index')
    props = db(db.user_properties.email == auth.user.email).select(db.user_properties.contests_can_rate).first()
    if props == None:
	c_can_rate = []
    else:
	c_can_rate = util.get_list(props.contests_can_rate)
    if not (c.rate_constraint == None or c.id in c_can_rate):
	session.flash = T('You cannot rate this contest.')
        redirect(URL('contests', 'rateopen_index'))
    t = datetime.utcnow()
    if not (c.is_active and c.rate_open_date <= t and c.rate_close_date >= t):
        session.flash = T('This contest is not open for rating.')
        redirect(URL('contests', 'rateopen_index'))
    # The user can rate the contest.
    # Does the user have any pending reviewing tasks for the contest?
    num_open_tasks = db((db.task.user_id == auth.user_id) &
			(db.task.contest_id == c.id) &
			(db.task.completed_date > datetime.utcnow())).count()
    if num_open_tasks > c.max_number_outstanding_reviews:
	session.flash = T('You have too many reviews outstanding for this contest. '
			  'Complete some of them before accepting additional reviewing tasks.')
	redirect(URL('rating', 'task_index', args=['open']))
	# This contest_form is used to display the contest.
    contest_form = SQLFORM(db.contest, record=c, readonly=True)
    # Gets any previous ratings for the contest.
    confirmation_form = FORM.confirm(T('Accept'),
        {T('Decline'): URL('default', 'index')})
    if confirmation_form.accepted:
        # Decreases the reviewing duties.
        duties = db((db.reviewing_duties.user_email == auth.user.email) &
            (db.reviewing_duties.contest_id == c.id)).select().first()
        if duties != None and duties.num_reviews > 0:
            db.duties.update_record(num_reviews = num_reviews - 1)
        # Reads the most recent ratings given by the user.
        # TODO(luca): we should really poll the rating system for this; that's what
        # should keep track of these things.
        previous_ratings = db((db.comparison.author == auth.user_id) 
            & (db.comparison.contest_id == c.id)).select(orderby=~db.comparison.date).first()
        if previous_ratings == None:
            old_items = []
        else:
            old_items = util.get_list(previous_ratings.ordering)
        new_item = ranker.get_item(db, c.id, auth.user_id, old_items)
        if new_item == None:
            session.flash = T('There are no items to review so far.')
            redirect(URL('contests', 'rateopen_index'))
        # Creates a reviewing task.
        # To name it, counts how many tasks the user has already for this contest.
        num_tasks = db((db.task.contest_id == c.id) & (db.task.user_id == auth.user_id)).count()
        task_name = (c.name + ' ' + T('Submission') + ' ' + str(num_tasks + 1))[:STRING_FIELD_LENGTH]
        db.task.insert(submission_id = new_item, contest_id = c.id, submission_name = task_name)
        db.commit()
        session.flash = T('A review has been added to your review assignments.')
        redirect(URL('task_index', args=[new_item]))
    return dict(contest_form=contest_form, confirmation_form=confirmation_form)

            
@auth.requires_login()
def task_index():
    if not request.args(0):
        redirect(URL('default', 'index'))
    mode = request.args(0)
    if mode == 'completed':
        q = ((db.task.user_id == auth.user_id) & (db.task.completed_date < datetime.utcnow()))
	title = T('Reviews completed')
    elif mode == 'all':
        q = (db.task.user_id == auth.user_id)
	title = T('All reviews')
    elif mode == 'open':
        q = ((db.task.user_id == auth.user_id) & (db.task.completed_date > datetime.utcnow()))
	title = T('Reviews to submit')
    else:
        # The mode if a specific item.
        title = T('')
        q = (db.task.id == mode)
    db.task.submission_name.readable = False
    grid = SQLFORM.grid(q,
        args=request.args[1:],
        field_id=db.task.id,
	user_signature=False,
        create=False, editable=False, deletable=False, csv=False,
        links=[
            dict(header='Contest', 
                body = lambda r: A(db.contest(r.contest_id).name, _href=URL('contests', 'view_contest', args=[r.contest_id]))),
            dict(header='Submission', 
                body = lambda r: A(r.submission_name, _href=URL('submission', 'view_submission', args=[r.id]))),
            dict(header='Review', body = review_link),],
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
    """Enters the review, and comparisons, for a particular task."""

    def decode_order_json(form):
	try:
	    decoded_order = simplejson.loads(request.vars.order)
	    form.vars.order = decoded_order
	    # Validates the fact that submissions correspond only tasks that are completed in the past,
	    # or the current one.
	    for i in decoded_order:
		if i != t.submission_id:
		    # This must correspond to a previously done task.
		    mt = db((db.task.submission_id == i) &
			  (db.task.user_id == auth.user_id)).select().first()
		    if mt == None or mt.completed_date < datetime.utcnow():
			form.errors.order = T('Corruputed data received')
			session.flash = T('Corrupted data received')
			break
	except ValueError:
	    form.errors.order = T('Error in the received ranking')
	    session.flash = T('Error in the received ranking')
	    form.vars.order = []

    # Here is where the comparisons are entered.
    t = db.task(request.args(0)) or redirect(URL('default', 'index'))
    if t.user_id != auth.user_id:
	session.flash = T('Invalid request.')
        redirect(URL('default', 'index'))

    # Check that the contest rating deadline is currently open.
    contest = db.contest(t.contest_id)
    if datetime.utcnow() < contest.rate_open_date or datetime.utcnow() > contest.rate_close_date:
	session.flash = T('The review deadline for this contest is closed.')
        redirect(URL('contests', 'view_contest', args=[contest.id]))

    # Ok, the task belongs to the user. 
    # Gets the last reviewing task done for the same contest.
    last_comparison = db((db.comparison.author == auth.user_id)
        & (db.comparison.contest_id == t.contest_id)).select(orderby=~db.comparison.date).first()
    if last_comparison == None:
        last_ordering = []
    else:
        last_ordering = util.get_list(last_comparison.ordering)
    current_list = last_ordering
    if t.submission_id not in last_ordering:
	current_list.append(t.submission_id)

    # Now we need to find the names of the submissions (for the user) that were 
    # used in this last ordering.
    # We create a submission_id to name mapping, that will be passed in json to the view.
    submissions = {}
    for i in last_ordering:
	# Finds the task.
	st = db((db.task.submission_id == i) &
		(db.task.user_id == auth.user_id)).select().first()
	if st != None:
	    # It should always be non-None, as we never delete tasks.
	    submissions[i] = st.submission_name
    # Adds also the last submission.
    submissions[t.submission_id] = t.submission_name
	    
    # Used to check each draggable item and determine which one we should
    # highlight (because its the current/new record).
    new_comparison_item = t.submission_id

    # Reads any comments previously given by the user on this submission.
    previous_comments = db((db.comment.author == auth.user_id) 
        & (db.comment.submission_id == t.submission_id)).select(orderby=~db.comment.date).first()
    if previous_comments == None:
        previous_comment_text = ''
    else:
        previous_comment_text = previous_comments.content

    form = SQLFORM.factory(
        Field('comments', 'text', default=previous_comment_text),
        hidden=dict(order=simplejson.dumps(current_list))
        )

    if form.process(onvalidation=decode_order_json).accepted:
        # Creates a new comparison in the db.
        comparison_id = db.comparison.insert(
            contest_id = t.contest_id,
            ordering = simplejson.loads(request.vars.order)) 

        # Marks the task as done.
        t.update_record(completed_date=datetime.utcnow())

        # Adds the comment to the comments for the submission, over-writing any previous
        # comments.
        if previous_comments == None:
            db.comment.insert(submission_id = t.submission_id,
                content = form.vars.comments)
        else:
            previous_comments.update_record(content = form.vars.comments)

        # TODO(luca): put it in a queue of things that need processing.
        # All updates done.
        # Calling ranker.py directly.
        comparison = db(db.comparison.id == comparison_id).select().first()
        ordering = util.get_list(comparison.ordering)
        ranker.process_comparison(db, t.contest_id, auth.user_id,
                                  ordering[::-1], t.submission_id)
        db.commit()
	session.flash = T('The review has been submitted.')
	redirect(URL('rating', 'task_index', args=['open']))

    return dict(form=form, task=t, 
        submissions = submissions, 
        current_list = current_list,
        new_comparison_item = new_comparison_item,
        )
        
        
