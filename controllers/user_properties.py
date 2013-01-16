# coding: utf8

import util

@auth.requires_login()
def index():
    if not is_user_admin():
	session.flash = T('Not authorized')
	redirect(URL('default', 'index'))
    q = (db.user_properties.id > 0)
    grid = SQLFORM.grid(q, 
        field_id = db.user_properties.id,
        csv=False, details=True,
        deletable=True,
        )
    return dict(grid=grid)
    
