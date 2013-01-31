# coding: utf8

import util
import ranker
import re
from contenttype import contenttype

@auth.requires_login()
def my_submissions_index():
    """Index of submissions to a context."""
    # Gets information on this specific venue.
    c = db.venue(request.args(0)) or redirect(URL('default', 'index'))
    # Gets the list of all submissions to the given venue.
    q = ((db.submission.author == auth.user_id) 
            & (db.submission.venue_id == c.id))
    db.submission.venue_id.readable = False
    db.submission.title.readable = False
    grid = SQLFORM.grid(q,
        args=request.args[:1],
        field_id = db.submission.id,
        fields = [db.submission.id, db.submission.title, db.submission.venue_id],
        create = False,
        user_signature = False,
        details = False,
        csv = False,
        editable = False,
        deletable = False,
        links = [
            dict(header = T('Submission'), body = lambda r:
                A(T(r.title), _href=URL('view_own_submission', args=[r.id]))),
            dict(header = T('Feedback'), body = lambda r:
                A(T('View Feedback'), _class='btn', _href=URL('feedback', 'view_feedback', args=[r.id]))),
            ]
        )
    # TODO(luca): check can_add to see if we can include a link to submit, below.
    return dict(grid=grid, venue=c)


@auth.requires_login()
def submit():
    # Gets the information on the venue.
    c = db.venue(request.args[0]) or redirect(URL('default', 'index'))
    # Gets information on the user.
    props = db(db.user_properties.email == auth.user.email).select().first()
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
    sub = db((db.submission.author == auth.user_id) & (db.submission.venue_id == c.id)).select().first()
    if sub != None and not c.allow_multiple_submissions:
        session.flash = T('You have already submitted to this venue.')
        redirect(URL('my_submissions_index', args=[c.id]))
    # The author can access the title.
    db.submission.title.readable = db.submission.title.writable = True
    # Check whether link submission is allowed.
    db.submission.link.readable = db.submission.link.writable = c.allow_link_submission
    # Produces an identifier for the submission.
    db.submission.identifier.default = util.get_random_id()
    db.submission.email.default = auth.user.email
    # Assigns default quality to the submission.
    avg, stdev = ranker.get_init_average_stdev()
    db.submission.quality.default = avg
    db.submission.stdev.default = stdev
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
            db(db.user_properties.email == auth.user.email).update(venues_has_submitted = submitted_ids)
        else:
            props.update_record(venues_has_submitted = submitted_ids)
        # Assigns the initial distribution to the submission.
	# TODO(michael): remove this line (but leave the db.commit). 
        db.quality.insert(venue_id=c.id, submission_id=form.vars.id, user_id=auth.user_id, average=avg, stdev=stdev)
        db.commit()
        session.flash = T('Your submission has been accepted.')
        redirect(URL('feedback', 'index', args=['all']))
    return dict(form=form, venue=c)

         
@auth.requires_login()
def manager_submit():
    """This function is used by venue managers to do submissions on behalf of others.  It can be used
    even when the submission deadline is past."""
    # Gets the information on the venue.
    c = db.venue(request.args[0]) or redirect(URL('default', 'index'))
    # Checks that the user is a manager for the venue.
    manager_props = db(db.user_properties.email == auth.user.email).select().first()
    can_manage = c.id in util.get_list(manager_props.venues_can_manage)
    if not can_manage:
	session.flash = T('Not authorized!')
	redirect(URL('default', 'index'))
    # Prepares the submission.
    db.submission.email.writable = db.submission.email.readable = True
    db.submission.author.readable = db.submission.author.writable = False
    db.submission.email.label = T('Author')
    # Produces an identifier for the submission.
    db.submission.identifier.default = util.get_random_id()
    form = SQLFORM(db.submission, upload=URL('download_manager', args=[None]))
    form.vars.venue_id = c.id
    if request.vars.content != None and request.vars.content != '':
        form.vars.original_filename = request.vars.content.filename
    if form.process(onvalidation=manager_submit_validation).accepted:
        # Adds the venue to the list of venues where the user submitted.
        # TODO(luca): Enable users to delete submissions.  But this is complicated; we need to 
        # delete also their quality information etc.  For the moment, no deletion.
	props = db(db.user_properties.email == form.vars.email).select().first()
	if props == None: 
	    venues_has_submitted = []
	else:
	    venues_has_submitted = util.get_list(props.venues_has_submitted)
        submitted_ids = util.id_list(venues_has_submitted)
        submitted_ids = util.list_append_unique(submitted_ids, c.id)
        if props == None:
            db(db.user_properties.email == form.vars.email).update(venues_has_submitted = submitted_ids)
        else:
            props.update_record(venues_has_submitted = submitted_ids)
        # Assigns the initial distribution to the submission.
        avg, stdev = ranker.get_init_average_stdev()
        db.quality.insert(venue_id=c.id, submission_id=form.vars.id, user_id=form.vars.author,
			  average=avg, stdev=stdev)
        db.commit()
        session.flash = T('The submission has been accepted.')
        redirect(URL('ranking', 'view_venue', args=[c.id]))
    return dict(form=form, venue=c)
         

def manager_submit_validation(form):
    """Validates a manager-entered submission.  The main validation is
    that the user account must already exist for that user.
    TODO(luca): we could lift this restriction, but at the price of
    having to move to email as the general user identifier.
    Shall we do this?"""
    user_info = db(db.auth_user.email == form.vars.email).select().first()
    if user_info is None:
	form.errors.email = T('User does not exist.')
    else:
	form.vars.author = user_info.id


@auth.requires_login()
def view_submission():
    """Allows viewing a submission by someone who has the task to review it.
    This function is accessed by task id, not submission id, to check access
    and anonymize the submission."""
    v = validate_task(request.args(0), auth.user_id)
    if v == None:
        session.flash(T('Not authorized.'))
        redirect(URL('default', 'index'))
    (t, subm, cont) = v
    download_link = A(T('Download'),
		      _class='btn',
	              _href=URL('download_reviewer', args=[t.id, subm.content]))
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
    if subm.author != auth.user_id:
        session.flash = T('You cannot view this submission.')
        redirect(URL('default', 'index'))
    # If the venue is still open for submissions, then we allow editing of the submission.
    c = db.venue(subm.venue_id) or redirect(URL('default', 'index'))
    t = datetime.utcnow()
    download_link = None
    subm_link = None
    if c.allow_link_submission:
	subm_link = A(subm.link, _href=subm.link)
    if (c.is_active and c.is_approved and c.open_date <= t and c.close_date >= t):
        form = SQLFORM(db.submission, subm, upload=URL('download_author', args=[subm.id]))
        if request.vars.content != None and request.vars.content != '':
            form.vars.original_filename = request.vars.content.filename
        if form.process().accepted:
            session.flash = T('Your submission has been updated.')
            redirect(URL('feedback', 'index', args=['all']))
    else:
        db.submission.content.readable = False
        form = SQLFORM(db.submission, subm, readonly=True,
		       upload=URL('download_author', args=[subm.id]), buttons=[])
	download_link = A(T('download'), _class='btn',
			  _href=URL('download_author', args=[subm.id, subm.content]))
    return dict(form=form, subm=subm, download_link=download_link, subm_link=subm_link)


@auth.requires_login()
def view_submission_by_manager():
    """Allows viewing a submission by a contest manager.
    The argument is the submission id."""
    subm = db.submission(request.args(0)) or redirect(URL('default', 'index'))
    if subm.author != auth.user_id:
        session.flash = T('You cannot view this submission.')
        redirect(URL('default', 'index'))
    c = db.venue(subm.venue_id) or redirect(URL('default', 'index'))
    managers = util.get_list(c.managers)
    if auth.user.email not in managers:
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


def validate_task(t_id, user_id):
    """Validates that user_id can do the reviewing task t."""
    t = db.task(request.args(0))
    if t == None:
        return None
    if t.user_id != user_id:
        return None
    s = db.submission(t.submission_id)
    if s == None:
        return None
    c = db.venue(s.venue_id)
    if c == None:
        return None
    d = datetime.utcnow()
    if c.rate_open_date > d or c.rate_close_date < d:
        return None
    return (t, s, c)

	
@auth.requires_login()
def download_author():
    # The user must be the owner of the submission.
    subm = db.submission(request.args(0))
    if (subm  == None):
        redirect(URL('default', 'index' ) )
    if subm.author != auth.user_id:
        session.flash = T('Not authorized.')
        redirect(URL('default', 'index'))
    return my_download(request, db, subm.original_filename)
	

@auth.requires_login()
def download_manager():
    # The user must be the manager of the venue where the submission occurred.
    subm = db.submission(request.args(0))
    if (subm  == None):
        redirect(URL('default', 'index' ))
    # Gets the venue.
    c = db.venue(subm.venue_id)
    if c is None:
        session.flash = T('Not authorized.')
        redirect(URL('default', 'index'))
    managers = util.get_list(c.managers)
    if auth.user.email not in managers:
        session.flash = T('Not authorized.')
        redirect(URL('default', 'index'))	
    return my_download(request, db, subm.original_filename)
	

@auth.requires_login()
def download_viewer():
    """This method allows the download of a submission by someone who has access to
    all the submissions of the venue.  We need to do all access control here."""
    subm = db.submission(request.args(0)) or redirect(URL('default', 'index'))
    c = db.venue(subm.venue_id) or redirect(URL('default', 'index'))
    # Does the user have access to the venue submissions?
    # TODO(luca): factor this in a permission module.
    props = db(db.user_properties.email == auth.user.email).select().first()
    can_manage = c.id in util.get_list(props.venues_can_manage)
    can_observe = c.id in util.get_list(props.venues_can_observe)
    can_view_ratings = can_manage or c.rating_available_to_all or can_observe
    if not can_view_ratings:
	session.flash(T('Not authorized.'))
	redirect(URL('default', 'index'))
    # Creates an appropriate file name for the submission.
    original_ext = subm.original_filename.split('.')[-1]
    filename = subm.email or 'anonymous'
    if subm.title != None and len(subm.title) > 0:
	filename += '_' + subm.title
    else:
	filename += '_' + subm.identifier
    filename += '.' + original_ext
    # Allows the download.
    # TODO(luca): The next line should be useless.
    request.args = request.args[1:]
    return my_download(request, db, filename)


@auth.requires_login()
def download_reviewer():
    # Checks that the reviewer has access.
    v = validate_task(request.args(0), auth.user_id)
    if v == None:
        session.flash = T('Not authorized.')
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
