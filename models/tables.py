# coding: utf8

from datetime import datetime

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
    Field('featured_submissions', 'boolean', required=True, default=False),
    Field('is_active', 'boolean', required=True, default=True),
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
    Field('content', 'upload'),
    Field('notes', 'text'),
    Field('comments', 'list:reference comment'),
    Field('is_featured', 'boolean', default=False),
    )
    
db.submission.id.readable = db.submission.id.writable = False
db.submission.author.writable = False
db.submission.date.writable = False
db.submission.is_featured.readable = db.submission.is_featured.writable = False
db.submission.comments.readable = db.submission.comments.writable = False
db.submission.is_featured.readable = db.submission.is_featured.writable = False
db.submission.contest_id.readable = db.submission.contest_id.writable = False
    
db.define_table('comment',
    Field('author', db.auth_user,  default=auth.user_id),
    Field('date', 'datetime', default=datetime.utcnow()),
    Field('submission', db.submission),
    Field('content', 'text'),
    Field('useful', 'integer'),
    )
    
db.define_table('comparison', # An ordering of submissions, from worst to best.
    Field('author', db.auth_user,  default=auth.user_id),
    Field('date', 'datetime', default=datetime.utcnow()),
    Field('contest', db.contest),
    Field('ratings', 'list:reference submission'),
    )

db.define_table('quality', # Quality of a submission in a context.
    Field('contest', db.contest),
    Field('submission', db.submission),
    Field('distribution', 'blob'),
    Field('average', 'double'),
    Field('stdev', 'double'),
    )
