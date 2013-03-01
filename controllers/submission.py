# coding: utf8

import access
import util
import ranker
import re
from contenttype import contenttype


@auth.requires_login()
def submit():
    # Gets the information on the venue.
    c = db.venue(request.args(0)) or redirect(URL('default', 'index'))
    # Gets information on the user.
    props = db(db.user_properties.user == auth.user.email).select().first()
    if props == None: 
        venue_ids = []
        venues_has_submitted = []
    else:
        venue_ids = util.get_list(props.venues_can_submit)
        venues_has_submitted = util.get_list(props.venues_has_submitted)
    # Is the venue open for submission?
    if not (c.submit_constraint == None or c.id in venue_ids):
	session.flash = T('You cannot submit to this venue.')
        redirect(URL('venues', 'view_venue', args=[c.id]))
    t = datetime.utcnow()
    if not (c.is_active and c.is_approved and c.open_date <= t and c.close_date >= t):
	session.flash = T('The submission deadline has passed; submissions are closed.')
        redirect(URL('venues', 'view_venue', args=[c.id]))
    # Ok, the user can submit.  Looks for previous submissions.
    sub = db((db.submission.user == auth.user.email) & (db.submission.venue_id == c.id)).select().first()
    if sub != None and not c.allow_multiple_submissions:
        session.flash = T('You have already submitted to this venue.')
        redirect(URL('venues', 'view_venue', args=[c.id]))
    # The author can access the title.
    db.submission.title.readable = db.submission.title.writable = True
    # Check whether link submission is allowed.
    db.submission.link.readable = db.submission.link.writable = c.allow_link_submission
    db.submission.n_completed_reviews.readable = False
    db.submission.n_rejected_reviews.readable = False
    db.submission.feedback.readable = db.submission.feedback.writable = False
    db.submission.date_updated.readable = False
    # Produces an identifier for the submission.
    db.submission.identifier.default = util.get_random_id()
    db.submission.user.default = auth.user.email
    # Assigns default quality to the submission.
    avg, stdev = ranker.get_init_average_stdev()
    db.submission.quality.default = avg
    db.submission.error.default = stdev
    # No percentile readable.
    db.submission.percentile.readable = False
    # TODO(luca): check that it is fine to do the download link without parameters.
    form = SQLFORM(db.submission, upload=URL('download_auhor', args=[None]))
    form.vars.venue_id = c.id
    if request.vars.content != None and request.vars.content != '':
        form.vars.original_filename = request.vars.content.filename
    if form.process().accepted:
        # Adds the venue to the list of venues where the user submitted.
        # TODO(luca): Enable users to delete submissions.  But this is complicated; we need to 
        # delete also their quality information etc.  For the moment, no deletion.
        submitted_ids = util.id_list(venues_has_submitted)
        submitted_ids = util.list_append_unique(submitted_ids, c.id)
        if props == None:
	    db.user_properties.insert(user = auth.user.email,
				      venues_has_submitted = submitted_ids)
        else:
            props.update_record(venues_has_submitted = submitted_ids)
        db.commit()
        session.flash = T('Your submission has been accepted.')
        redirect(URL('feedback', 'index', args=['all']))
    return dict(form=form, venue=c)


@auth.requires_login()
def manager_submit():
    """This function is used by venue managers to do submissions on behalf of others.  It can be used
    even when the submission deadline is past."""
    # Gets the information on the venue.
    c = db.venue(request.args(0)) or redirect(URL('default', 'index'))
    # Checks that the user is a manager for the venue.
    manager_props = db(db.user_properties.user == auth.user.email).select().first()
    can_manage = c.id in util.get_list(manager_props.venues_can_manage)
    if not can_manage:
	session.flash = T('Not authorized!')
	redirect(URL('default', 'index'))
    # Prepares the submission.
    db.submission.user.readable = db.submission.user.writable = True
    db.submission.user.default = ''
    db.submission.feedback.readable = db.submission.feedback.writable = False
    # Assigns default quality to the submission.
    avg, stdev = ranker.get_init_average_stdev()
    db.submission.quality.default = avg
    db.submission.error.default = stdev
    # Produces an identifier for the submission.
    db.submission.identifier.default = util.get_random_id()

    # Prepares the submission form.
    form = SQLFORM(db.submission, upload=URL('download_manager', args=[None]))
    form.vars.venue_id = c.id
    if request.vars.content != None and request.vars.content != '':
        form.vars.original_filename = request.vars.content.filename
    if form.process().accepted:
        # Adds the venue to the list of venues where the user submitted.
	props = db(db.user_properties.user == form.vars.email).select().first()
	if props == None: 
	    venues_has_submitted = []
	else:
	    venues_has_submitted = util.get_list(props.venues_has_submitted)
        submitted_ids = util.id_list(venues_has_submitted)
        submitted_ids = util.list_append_unique(submitted_ids, c.id)
        if props == None:
            db(db.user_properties.user == form.vars.user).update(venues_has_submitted = submitted_ids)
        else:
            props.update_record(venues_has_submitted = submitted_ids)

	# If there is a prior submission of the same author to this venue, replaces the content.
	is_there_another = False
	other_subms = db(db.submission.user == form.vars.user).select()
	for other_subm in other_subms:
	    if other_subm.id != form.vars.id:
		is_there_another = True
		other_subm.update_record(
		    date_updated = datetime.utcnow(),
		    title = form.vars.title,
		    original_filename = form.vars.original_filename,
		    content = new_content,
		    link = form.vars.link,
		    comment = form.vars.comment,
		    )
	# And deletes this submission.
	if is_there_another:
	    db(db.submission.id == form.vars.id).delete()
	    session.flash = T('The previous submission by the same author has been updated.')
	else:
	    session.flash = T('The submission has been added.')
        db.commit()
	redirect(URL('ranking', 'view_venue', args=[c.id]))
    return dict(form=form, venue=c)
         

@auth.requires_login()
def view_submission():
    """Allows viewing a submission by someone who has the task to review it.
    This function is accessed by task id, not submission id, to check access
    and anonymize the submission."""
    ok, v = access.validate_task(db, request.args(0), auth.user.email)
    if not ok:
        session.flash = T(v)
        redirect(URL('default', 'index'))
    (t, subm, cont) = v
    download_link = A(T('Download'),
		      _class='btn',
	              _href=URL('download_reviewer', args=[t.id]))
    venue_link = A(cont.name, _href=URL('venues', 'view_venue', args=[cont.id]))
    subm_link = None
    if cont.allow_link_submission:
	subm_link = A(subm.link, _href=subm.link)
    return dict(title=t.submission_name, download_link=download_link,
		venue_link=venue_link, subm_link=subm_link)

   
@auth.requires_login()
def view_own_submission():
    """Allows viewing a submission by the submission owner.
    The argument is the submission id."""
    subm = db.submission(request.args(0)) or redirect(URL('default', 'index'))
    if subm.user != auth.user.email:
        session.flash = T('You cannot view this submission.')
        redirect(URL('default', 'index'))
    c = db.venue(subm.venue_id) or redirect(URL('default', 'index'))
    t = datetime.utcnow()
    download_link = None
    subm_link = None
    if c.allow_link_submission:
	subm_link = A(subm.link, _href=subm.link)
    db.submission.user.readable = db.submission.user.writable = False
    db.submission.feedback.readable = db.submission.feedback.writable = False
    db.submission.percentile.readable = db.submission.percentile.writable = False
    db.submission.n_completed_reviews.readable = False
    db.submission.n_rejected_reviews.readable = False
    # Prepares the form, according to whether the author can edit the submission or not.
    is_editable = (c.is_active and c.is_approved and c.open_date <= t and c.close_date >= t)
    if is_editable:
	# The venue is still open for submissions, and we allow editing of the submission.
        form = SQLFORM(db.submission, subm, upload=URL('download_author', args=[subm.id]),
		       deletable=False)
        if request.vars.content != None and request.vars.content != '':
            form.vars.original_filename = request.vars.content.filename
	if form.process().accepted:
            session.flash = T('Your submission has been updated.')
	    redirect(URL('feedback', 'index', args=['all']))
    else:
	# The venue is no longer open for submission.
        db.submission.content.readable = False
        form = SQLFORM(db.submission, subm, readonly=True,
		       upload=URL('download_author', args=[subm.id]), buttons=[])
    return dict(form=form, subm=subm)


@auth.requires_login()
def view_submission_by_manager():
    """Allows viewing a submission by a contest manager.
    The argument is the submission id."""
    subm = db.submission(request.args(0)) or redirect(URL('default', 'index'))
    c = db.venue(subm.venue_id) or redirect(URL('default', 'index'))
    props = db(db.user_properties.user == auth.user.email).select().first()
    if not access.can_observe(c, props):
        session.flash = T('Not authorized.')
        redirect(URL('default', 'index'))	    
    download_link = None
    subm_link = None
    if c.allow_link_submission:
	subm_link = A(subm.link, _href=subm.link)
    db.submission.content.readable = False
    form = SQLFORM(db.submission, subm, readonly=True,
		   upload=URL('download_manager', args=[subm.id]), buttons=[])
    download_link = A(T('download'), _class='btn',
		      _href=URL('download_author', args=[subm.id, subm.content]))
    return dict(form=form, subm=subm, download_link=download_link, subm_link=subm_link)


@auth.requires_login()
def download_author():
    # The user must be the owner of the submission.
    subm = db.submission(request.args(0))
    if (subm  == None):
        redirect(URL('default', 'index' ) )
    if subm.user != auth.user.email:
        session.flash = T('Not authorized.')
        redirect(URL('default', 'index'))
    return my_download(request, db, subm.original_filename)


@auth.requires_login()
def download_manager():
    # The user must be the manager of the venue where the submission occurred.
    subm = db.submission(request.args(0)) or redirect(URL('default', 'index' ))
    # Gets the venue.
    c = db.venue(subm.venue_id)
    if c is None:
        session.flash = T('Not authorized.')
        redirect(URL('default', 'index'))
    managers = util.get_list(c.managers)
    if auth.user.email not in managers:
        session.flash = T('Not authorized.')
        redirect(URL('default', 'index'))	
    return my_download(subm)
	

@auth.requires_login()
def download_viewer():
    """This method allows the download of a submission by someone who has access to
    all the submissions of the venue.  We need to do all access control here."""
    subm = db.submission(request.args(0)) or redirect(URL('default', 'index'))
    c = db.venue(subm.venue_id) or redirect(URL('default', 'index'))
    props = db(db.user_properties.user == auth.user.email).select().first()
    # Does the user have access to the venue submissions?
    if not can_view_submissions(c, props): 
	session.flash(T('Not authorized.'))
	redirect(URL('default', 'index'))
    # Creates an appropriate file name for the submission.
    original_ext = subm.original_filename.split('.')[-1]
    filename = subm.user
    if subm.title != None and len(subm.title) > 0:
	filename += '_' + subm.title
    else:
	filename += '_' + subm.identifier
    filename += '.' + original_ext
    # Allows the download.
    return my_download(subm, filename=filename)


@auth.requires_login()
def download_reviewer():
    # Checks that the reviewer has access.
    ok, v = access.validate_task(db, request.args(0), auth.user.email)
    if not ok:
        session.flash = T(v)
        redirect(URL('default', 'index'))
    (t, s, c) = v
    # Builds the download name for the file.
    if c.submissions_are_anonymized:
	# Get the extension of the original file
	original_ext = s.original_filename.split('.')[-1]
        file_alias = ( t.submission_name if t != None else 'submission' )  + '.' + original_ext
    else:
        # If title_is_file_name is set, then we use that as the alias,
        # otherwise we use the original filename.
        if c.submission_title_is_file_name:
            file_alias = s.title + '.' + original_ext
        else:
            file_alias = s.original_filename
    # TODO(luca): The next line should be useless.
    request.args = request.args[1:]
    return my_download(request, db, file_alias)


DEFAULT_CHUNK_SIZE = 64 * 1024

def my_download(request, db, download_filename):
    """This implements my download procedure that can rename files."""
    if not request.args:
	raise HTTP(404)
    name = request.args[-1]
    items = re.compile('(?P<table>.*?)\.(?P<field>.*?)\..*')\
	.match(name)
    if not items:
	raise HTTP(404)
    (t, f) = (items.group('table'), items.group('field'))
    try:
	field = db[t][f]
    except AttributeError:
	raise HTTP(404)
    try:
	(filename, stream) = field.retrieve(name)
    except IOError:
	raise HTTP(404)
    headers = response.headers
    headers['Content-Type'] = contenttype(name)
    headers['Content-Disposition'] = \
	'attachment; filename="%s"' % download_filename.replace('"','\"')
    return response.stream(stream, chunk_size=DEFAULT_CHUNK_SIZE)
