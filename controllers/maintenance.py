# coding: utf8

from datetime import datetime
import gluon.contrib.simplejson as simplejson
import util

@auth.requires_login()
def port_comments():
    if auth.user.email != 'luca@ucsc.edu':
        session.flash = T('Not authorized')
        redirect(URL('default', 'index'))
    comments = db().select(db.comment.ALL)
    for c in comments:
        db((db.task.submission_id == c.submission_id) & (db.task.user_id == c.author)).update(comments = c.content)
    db.commit()
    session.flash = T('Ported comments.')
    redirect(URL('default', 'index'))
    
@auth.requires_login()
def compute_n_reviews():
    if auth.user.email != 'luca@ucsc.edu':
        session.flash = T('Not authorized')
        redirect(URL('default', 'index'))
    submissions = db().select(db.submission.ALL)
    for s in submissions:
        s.n_assigned_reviews = db((db.task.submission_id == s.id) & (db.task.venue_id == s.venue_id)).count()
        s.n_completed_reviews = db((db.task.submission_id == s.id) & (db.task.venue_id == s.venue_id)
            & (db.task.completed_date < datetime.utcnow())).count()
        s.n_rejected_reviews = db((db.task.submission_id == s.id) & (db.task.venue_id == s.venue_id)
            & (db.task.rejected == False)).count()
        s.update_record()
    db.commit()
    session.flash = T('Fixed numbers of completed reviews')
    redirect(URL('default', 'index'))

@auth.requires_login()
def mark_completed_tasks():
    if auth.user.email != 'luca@ucsc.edu':
        session.flash = T('Not authorized')
        redirect(URL('default', 'index'))
    tasks = db().select(db.task.ALL)
    for t in tasks:
	if t.completed_date < datetime.utcnow():
	    t.update_record(is_completed = True)
	else:
	    t.update_record(is_completed = False)
    db.commit()
    session.flash = T('done')
    
@auth.requires_login()
def create_comparison_nicks():
    if auth.user.email != 'luca@ucsc.edu':
        session.flash = T('Not authorized')
        redirect(URL('default', 'index'))
    comps = db().select(db.comparison.ALL)
    for comp in comps:
	nicks = {}
	for subm_id in comp.ordering:
	    s = db.submission(subm_id)
	    if s is not None:
		nicks[subm_id] = util.produce_submission_nickname(s)
	comp.update_record(submission_nicknames = simplejson.dumps(nicks))
    db.commit()
    session.flash = T('done')
    
