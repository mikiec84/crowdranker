# coding: utf8

from datetime import datetime
import datetime as dates # Ah, what a mess these python names

STRING_FIELD_LENGTH = 512 # Default length of string fields.

db.auth_user._format='%(email)s'

db.define_table('user_list',
    Field('name'),
    Field('creation_date', 'datetime', default=datetime.utcnow()),
    Field('managers', 'list:string'),
    Field('email_list', 'list:string'), 
    #TODO(luca): add a 'managed' field, and a table of users,
    # to allow managing very large sets of users via an API.
    format = '%(name)s',
    )

db.user_list.id.readable = db.user_list.id.writable = False
db.user_list.creation_date.writable = db.user_list.creation_date.readable = False 
db.user_list.name.required = True   
db.user_list.email_list.requires = [IS_LIST_OF(IS_EMAIL())]
db.user_list.managers.requires = [IS_LIST_OF(IS_EMAIL())]
db.user_list.email_list.label = 'Members'

db.define_table('user_properties',
    Field('email'), # Primary key
    Field('managed_user_lists', 'list:reference user_list'),
    Field('contests_can_manage', 'list:reference contest'),
    Field('contests_can_submit', 'list:reference user_list'),
    Field('contests_can_rate', 'list:reference user_list'),
    Field('contests_has_submitted', 'list:reference contest'),
    Field('contests_has_rated', 'list:reference contest'),
    )

db.user_properties.email.required = True


db.define_table('contest',
    Field('name'),
    Field('creation_date', 'datetime', default=datetime.utcnow()),
    Field('managers', 'list:string'),
    Field('submit_constraint', db.user_list),
    Field('rate_constraint', db.user_list),
    Field('open_date', 'datetime', required=True),
    Field('close_date', 'datetime', required=True),
    Field('rate_open_date', 'datetime', required=True),
    Field('rate_close_date', 'datetime', required=True),
    Field('allow_multiple_submissions', 'boolean', default=True),
    Field('submission_title_is_file_name', 'boolean', default=False),
    Field('is_active', 'boolean', required=True, default=True),
    Field('feedback_accessible_immediately', 'boolean', default=False),
    Field('rating_available_to_all', 'boolean', default=False),
    Field('feedback_available_to_all', 'boolean', default=False),
    Field('feedback_is_anonymous', 'boolean', default=True),
    Field('submissions_are_anonymized', 'boolean', default=True),
    )
    
db.contest.name.required = True
db.contest.creation_date.writable = db.contest.creation_date.readable = False
db.contest.id.readable = db.contest.id.writable = False
db.contest.is_active.label = 'Active'
db.contest.submit_constraint.label = 'Who can submit'
db.contest.rate_constraint.label = 'Who can rate'
db.contest.open_date.label = 'Submission opening date'
db.contest.open_date.default = datetime.utcnow()
db.contest.close_date.label = 'Submission deadline'
db.contest.close_date.default = datetime.utcnow()
db.contest.rate_open_date.label = 'Rating opening date'
db.contest.rate_open_date.default = datetime.utcnow()
db.contest.rate_close_date.label = 'Rating deadline'
db.contest.rate_close_date.default = datetime.utcnow()

def name_user_list(id, row):
    if id == None or id == '':
        return T('Anyone')
    else:
        return db.user_list(id).name
        
db.contest.submit_constraint.represent = name_user_list
db.contest.rate_constraint.represent = name_user_list
                                                
db.define_table('submission',
    Field('author', db.auth_user,  default=auth.user_id),
    Field('date', 'datetime', default=datetime.utcnow()),
    Field('contest_id', db.contest),
    Field('title'),
    Field('original_filename'),
    Field('identifier'), # Visible to all, unique.
    Field('content', 'upload'),
    )
    
db.submission.id.readable = db.submission.id.writable = False
db.submission.author.writable = False
db.submission.date.writable = False
db.submission.original_filename.readable = db.submission.original_filename.writable = False
db.submission.contest_id.readable = db.submission.contest_id.writable = False
db.submission.identifier.writable = False

db.define_table('comment',
    Field('author', db.auth_user,  default=auth.user_id),
    Field('date', 'datetime', default=datetime.utcnow()),
    Field('submission_id', db.submission),
    Field('content', 'text'),
    )

# For generating automatic display of comments.
db.comment.date.readable = False
db.comment.author.readable = False
db.comment.submission_id.readable = False
        
db.define_table('comparison', # An ordering of submissions, from worst to best.
    Field('author', db.auth_user,  default=auth.user_id),
    Field('date', 'datetime', default=datetime.utcnow()),
    Field('contest_id', db.contest),
    Field('ordering', 'list:reference submission'),
    )
    
db.define_table('task', # Tasks a user should complete for reviewing.
    Field('user_id', db.auth_user, default=auth.user_id),
    Field('submission_id', db.submission),
    Field('contest_id', db.contest),
    Field('submission_name'), # Name of the submission from the point of view of the user.
    Field('assigned_date', 'datetime', default=datetime.utcnow()),
    Field('completed_date', 'datetime', default=datetime(dates.MAXYEAR, 12, 1)),
    )

db.task.id.readable = db.task.id.writable = False
db.task.user_id.readable = db.task.user_id.writable = False
db.task.submission_id.readable = db.task.submission_id.writable = False
db.task.contest_id.readable = db.task.contest_id.writable = False
db.task.submission_name.writable = False

db.define_table('reviewing_duties', # Reviews a user should be doing.
    Field('user_email'),
    Field('contest_id', db.contest),
    Field('num_reviews', 'integer'),
    Field('date_assigned', 'datetime', default=datetime.utcnow()),
    Field('last_performed', 'datetime', update=datetime.utcnow()),
    )
    
db.reviewing_duties.user_email.readable = db.reviewing_duties.user_email.writable = False
db.reviewing_duties.contest_id.readable = db.reviewing_duties.contest_id.writable = False
db.reviewing_duties.num_reviews.writable = False
db.reviewing_duties.date_assigned.readable = db.reviewing_duties.date_assigned.writable = False
db.reviewing_duties.last_performed.readable = db.reviewing_duties.last_performed.writable = False

db.define_table('quality', # Quality of a submission in a context.
    Field('contest_id', db.contest),
    Field('submission_id', db.submission),
    Field('user_id', db.auth_user),
    Field('distribution', 'blob'),
    Field('average', 'double'),
    Field('stdev', 'double'),
    Field('percentile', 'double'),
    )
