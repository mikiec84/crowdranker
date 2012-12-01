# coding: utf8


from datetime import datetime

db.define_table('user_list',
    Field('name'),
    Field('creation_date', 'datetime', default=datetime.utcnow()),
    Field('email_list', 'list:string'),
    Field('managers', 'list:string', default=[auth.user.email]),
    )
    
db.user_list.email_list.requires = [IS_LIST_OF(IS_EMAIL())]
db.user_list.managers.requires = [IS_LIST_OF(IS_EMAIL())]

db.define_table('user_properties',
    Field('user', db.auth_user),
    Field('user_lists', 'list:reference user_list'),
    Field('contests', 'list:reference contest'),
    )

db.define_table('contest',
    Field('name'),
    Field('creation_date', 'datetime', default=datetime.utcnow()),
    Field('managers', 'list:string', default=[auth.user.email]),
    Field('submit_constraint', db.user_list),
    Field('rate_constraint', db.user_list),
    Field('open_date', 'datetime', default=datetime.utcnow()),
    Field('close_date', 'datetime'),
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
    )
    
db.define_table('rating',
    Field('author', db.auth_user,  default=auth.user_id),
    Field('date', 'datetime', default=datetime.utcnow()),
    Field('contest', db.contest),
    Field('ratings', 'list:reference submission'),
    )

db.define_table('ranking',
    Field('contest', db.contest),
    Field('submission', db.summission),
    Field('quality', 'blob'),
    )
