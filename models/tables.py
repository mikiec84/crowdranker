# coding: utf8

from datetime import datetime

db.define_table('user_list',
    Field('name'),
    Field('creation_date', 'datetime', default=datetime.utcnow()),
    Field('email_list', 'list:string'),
    Field('managers', 'list:string'),
    )

db.user_list.id.readable = db.user_list.id.writable = False
db.user_list.creation_date.writable = False    
db.user_list.email_list.requires = [IS_LIST_OF(IS_EMAIL())]
db.user_list.managers.requires = [IS_LIST_OF(IS_EMAIL())]

db.define_table('user_properties',
    Field('email'), # Primary key
    Field('user_lists', 'list:reference user_list'), # Managed by user
    Field('contests_can_submit', 'list:reference contest'),
    Field('contests_can_rate', 'list:reference contest'),
    Field('contests_has_rated', 'list:reference contest'),
    Field('contests_has_submitted', 'list:reference contest'),
    Field('contests_can_manage', 'list:reference contest'),
    )



db.define_table('contest',
    Field('name'),
    Field('creation_date', 'datetime', default=datetime.utcnow()),
    Field('managers', 'list:string'),
    Field('submit_constraint', db.user_list),
    Field('rate_constraint', db.user_list),
    Field('open_date', 'datetime', default=datetime.utcnow()),
    Field('close_date', 'datetime'),
    Field('rate_open_date', 'datetime'),
    Field('rate_close_date', 'datetime'),
    )
    
db.define_table('submission',
    Field('author', db.auth_user,  default=auth.user_id),
    Field('date', 'datetime', default=datetime.utcnow()),
    Field('contest', db.contest),
    Field('content', 'upload'),
    Field('comments', 'list:reference comment'),
    )
    
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
