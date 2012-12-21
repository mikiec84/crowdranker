# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

#########################################################################
## Customize your APP title, subtitle and menus here
#########################################################################

response.title = T('CrowdLab Ranking System')
response.subtitle = T('')

## read more at http://dev.w3.org/html5/markup/meta.name.html
response.meta.author = 'Luca de Alfaro <luca@ucsc.edu>'
response.meta.description = 'CrowdLab Submission Ranking System'
response.meta.keywords = 'web2py, python, framework'
response.meta.generator = 'Web2py Web Framework'

## your http://google.com/analytics id
response.google_analytics_id = None

#########################################################################
## this is the main application menu add/remove items as required
#########################################################################

response.menu = [
    (T('Home'), False, URL('default', 'index'), []),
    (T('Contests'), False, None, [
        (T('Contests I manage'), False, URL('contests', 'managed_index'), []),
        (T('Contests open for submission'), False, URL('contests', 'subopen_index'), []),
        (T('Contests open for rating'), False, URL('contests', 'rateopen_index'), []),
        (T('Contests where I submitted'), False, URL('contests', 'submitted_index'), []),
        ]),
    (T('User lists'), False, URL('user_lists', 'index'), []),
    (T('Reviews'), False, None, [
        (T('To do'), False, URL('rating', 'task_index', args=['open']), []),
        (T('Done'), False, URL('rating', 'task_index', args=['completed']), []),
        (T('All'),  False, URL('rating', 'task_index', args=['all']), []),
        ]),
    (T('My submissions'), False, URL('feedback', 'index', args=['all']), []),
]

#########################################################################
## provide shortcuts for development. remove in production
#########################################################################


def _():
    # shortcuts
    app = request.application
    ctr = request.controller
    # useful links to internal and external resources

_()
