# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

#########################################################################
## Customize your APP title, subtitle and menus here
#########################################################################

response.title = None
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
    (T('CrowdLab Ranking System'), False, URL('default', 'index'), []),
    (T('Submit'), False, None, [
        (T('Venues open for submission'), False, URL('venues', 'subopen_index'), []),
        (T('Venues where I submitted'), False, URL('venues', 'submitted_index'), []),
	(T('My submissions'), False, URL('feedback', 'index', args=['all']), []),
	]),
    (T('Review'), False, None, [
        (T('Venues open for review'), False, URL('venues', 'rateopen_index'), []),
        (T('Reviewing duties to accept'), False, URL('venues', 'reviewing_duties'), []),
        (T('Reviews to submit'), False, URL('rating', 'task_index'), []),
        (T('Reviews completed'), False, URL('rating', 'my_reviews'), []),
	]),
    (T('Manage'), False, None, [
        (T('Active managed venues'), False, URL('venues', 'managed_index', args=['active']), []),
        (T('All managed venues'), False, URL('venues', 'managed_index', args=['all']), []),
        (T('Observable, active venues'), False, URL('venues', 'observed_index'), []),
	(T('User lists'), False, URL('user_lists', 'index'), []),
	]),
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
