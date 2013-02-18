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
    Field('venues_can_manage', 'list:reference venue'),
    Field('venues_can_observe', 'list:reference venue'),
    Field('venues_can_submit', 'list:reference venue'),
    Field('venues_can_rate', 'list:reference venue'),
    Field('venues_has_submitted', 'list:reference venue'),
    Field('venues_has_rated', 'list:reference venue'),
    )

db.user_properties.email.required = True


db.define_table('venue',
    Field('name'),
    Field('description', 'text'),
    Field('creation_date', 'datetime', default=datetime.utcnow()),
    Field('created_by', db.auth_user,  default=auth.user_id),
    Field('managers', 'list:string'),
    Field('observers', 'list:string'),
    Field('submit_constraint', db.user_list),
    Field('rate_constraint', db.user_list),
    Field('open_date', 'datetime', required=True),
    Field('close_date', 'datetime', required=True),
    Field('rate_open_date', 'datetime', required=True),
    Field('rate_close_date', 'datetime', required=True),
    Field('allow_multiple_submissions', 'boolean', default=True),
    Field('submission_title_is_file_name', 'boolean', default=False),
    Field('allow_link_submission', 'boolean', default=False),
    Field('is_active', 'boolean', required=True, default=True),
    Field('is_approved', 'boolean', required=True, default=False),
    Field('submissions_are_anonymized', 'boolean', default=True),
    Field('can_rank_own_submissions', 'boolean', default=False),
    Field('max_number_outstanding_reviews', 'integer', default=1),
    Field('feedback_is_anonymous', 'boolean', default=True),
    Field('submissions_visible_to_all', 'boolean', default=False),
    Field('submissions_visible_immediately', 'boolean', default=False),
    Field('feedback_accessible_immediately', 'boolean', default=False),
    Field('feedback_available_to_all', 'boolean', default=False),
    Field('rating_available_to_all', 'boolean', default=False),
    Field('rater_contributions_visible_to_all', default=False),
    Field('number_of_submissions_per_reviewer', 'integer', default=0),
    Field('latest_rank_update_date', 'datetime'),
    Field('latest_reviewers_evaluation_date', 'datetime'),
    Field('latest_final_grades_evaluation_date', 'datetime'),
    format = '%(name)s',
    )

db.venue.created_by.readable = db.venue.created_by.writable = False
db.venue.name.required = True
db.venue.name.requires = IS_LENGTH(minsize=8)
db.venue.is_approved.writable = False
db.venue.creation_date.writable = db.venue.creation_date.readable = False
db.venue.id.readable = db.venue.id.writable = False
db.venue.is_active.label = 'Active'
db.venue.submit_constraint.label = 'Who can submit'
db.venue.rate_constraint.label = 'Who can rate'
db.venue.open_date.label = 'Submission opening date'
db.venue.open_date.default = datetime.utcnow()
db.venue.close_date.label = 'Submission deadline'
db.venue.close_date.default = datetime.utcnow()
db.venue.rate_open_date.label = 'Reviewing start date'
db.venue.rate_open_date.default = datetime.utcnow()
db.venue.rate_close_date.label = 'Reviewing deadline'
db.venue.rate_close_date.default = datetime.utcnow()
db.venue.max_number_outstanding_reviews.requires = IS_INT_IN_RANGE(1, 100,
    error_message=T('Enter a number between 0 and 100.'))
db.venue.latest_rank_update_date.writable = False
db.venue.latest_reviewers_evaluation_date.writable = False
db.venue.latest_final_grades_evaluation_date.writable = False
db.venue.number_of_submissions_per_reviewer.writable = False

def name_user_list(id, row):
    if id == None or id == '':
        return T('Anyone')
    else:
        return db.user_list(id).name
        
db.venue.submit_constraint.represent = name_user_list
db.venue.rate_constraint.represent = name_user_list
                                                
db.define_table('submission',
    Field('author', db.auth_user,  default=auth.user_id),
    Field('email'),
    Field('date', 'datetime'),
    Field('venue_id', db.venue),
    Field('title'),
    Field('original_filename'),
    Field('identifier'), # Visible to all, unique.
    Field('content', 'upload'),
    Field('link'),
    Field('comment', 'text'), # Of the person doing the submission.
    Field('feedback', 'text'), # Of a TA, grader, etc.
    Field('quality', 'double'),
    Field('error', 'double'),
    Field('true_quality', 'double'),
    Field('percentile', 'double'),
    Field('n_assigned_reviews', 'integer'),
    Field('n_completed_reviews', 'integer', default=0),
    Field('n_rejected_reviews', 'integer', default=0),
    )
    
db.submission.id.readable = db.submission.id.writable = False
db.submission.author.writable = False
db.submission.email.writable = False
db.submission.date.default = datetime.utcnow()
db.submission.date.update = datetime.utcnow()
db.submission.date.writable = False
db.submission.original_filename.readable = db.submission.original_filename.writable = False
db.submission.venue_id.readable = db.submission.venue_id.writable = False
db.submission.identifier.writable = False
db.submission.quality.readable = db.submission.quality.writable = False
db.submission.error.readable = db.submission.error.writable = False
db.submission.link.readable = db.submission.link.writable = False
db.submission.link.requires = IS_URL()
db.submission.title.requires = IS_LENGTH(minsize=2)
db.submission.true_quality.readable = db.submission.true_quality.writable = False
db.submission.percentile.writable = False
db.submission.n_assigned_reviews.writable = db.submission.n_assigned_reviews.readable = False
db.submission.n_completed_reviews.writable = False
db.submission.n_completed_reviews.label = T('N. reviews')
db.submission.n_rejected_reviews.writable = False
db.submission.n_rejected_reviews.label = T('N. rejected reviews')
db.submission.true_quality.label = T('TA Grade')
db.submission.feedback.label = T('TA Feedback')

db.define_table('user_accuracy',
    Field('user_id', db.auth_user),
    Field('venue_id', db.venue),
    Field('accuracy', 'double'),
    Field('n_ratings', 'integer'),
    )

db.define_table('comparison', # An ordering of submissions, from Best to Worst.
    Field('author', db.auth_user,  default=auth.user_id),
    Field('date', 'datetime', default=datetime.utcnow()),
    Field('venue_id', db.venue),
    Field('ordering', 'list:reference submission'),
    Field('grades'), # This is a json dictionary of submission_id: grade
    Field('new_item', 'reference submission'),
    Field('is_valid', 'boolean', default=True),
    )
    
db.define_table('task', # Tasks a user should complete for reviewing.
    Field('user_id', db.auth_user, default=auth.user_id),
    Field('submission_id', db.submission),
    Field('venue_id', db.venue),
    Field('submission_name'), # Name of the submission from the point of view of the user.
    Field('assigned_date', 'datetime', default=datetime.utcnow()),
    Field('completed_date', 'datetime', default=datetime(dates.MAXYEAR, 12, 1)),
    Field('rejected', 'boolean', default=False),
    Field('rejection_comment', 'text'),
    Field('comments', 'text'),
    )

db.task.id.readable = db.task.id.writable = False
db.task.user_id.readable = db.task.user_id.writable = False
db.task.submission_id.readable = db.task.submission_id.writable = False
db.task.venue_id.readable = db.task.venue_id.writable = False
db.task.assigned_date.writable = False
db.task.completed_date.writable = False
db.task.submission_name.writable = False
db.task.rejected.readable = db.task.rejected.writable = False
db.task.rejection_comment.label = T('Reason declined')
db.task.rejected.label = T('Review declined')

db.define_table('grades',
    Field('venue_id', db.venue, required=True),
    Field('author', db.auth_user),
    Field('grade', 'double'),
    )

db.grades.author.writable = False

# Deprecated.
db.define_table('comment',
    Field('author', db.auth_user,  default=auth.user_id),
    Field('date', 'datetime', default=datetime.utcnow()),
    Field('submission_id', db.submission),
    Field('content', 'text'),
    )
