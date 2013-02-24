# coding: utf8

from datetime import datetime
import util

def can_manage(venue, props):
    can_manage = venue.id in util.get_list(props.venues_can_manage)
    return can_manage

def can_observe(venue, props):
    can_manage = venue.id in util.get_list(props.venues_can_manage)
    can_observe = venue.id in util.get_list(props.venues_can_observe)
    return can_manage or can_observe


def can_view_ratings(venue, props):
    can_manage = venue.id in util.get_list(props.venues_can_manage)
    can_observe = venue.id in util.get_list(props.venues_can_observe)
    if can_manage or can_observe:
	return True
    if venue.rating_available_to_all:
	if venue.feedback_accessible_immediately:
	    return True
	else:
	    return venue.rate_close_date > datetime.utcnow()
    else:
	return False


def can_view_rating_contributions(venue, props):
    can_manage = venue.id in util.get_list(props.venues_can_manage)
    can_observe = venue.id in util.get_list(props.venues_can_observe)
    if can_manage or can_observe:
	return True
    if venue.rater_contributions_visible_to_all:
	if venue.feedback_accessible_immediately:
	    return True
	else:
	    return venue.rate_close_date > datetime.utcnow()
    else:
	return False
    

def can_enter_true_quality(venue, props):
    can_manage = venue.id in util.get_list(props.venues_can_manage)
    can_observe = venue.id in util.get_list(props.venues_can_observe)
    return (can_manage or can_observe)
    

def can_view_feedback(venue, props):
    can_manage = venue.id in util.get_list(props.venues_can_manage)
    can_observe = venue.id in util.get_list(props.venues_can_observe)
    if can_manage or can_observe:
	return True
    if venue.feedback_available_to_all:
	if venue.feedback_accessible_immediately:
	    return True
	else:
	    return venue.rate_close_date > datetime.utcnow()
    else:
	return False

    
def can_view_submissions(venue, props):
    can_manage = venue.id in util.get_list(props.venues_can_manage)
    can_observe = venue.id in util.get_list(props.venues_can_observe)
    if can_manage or can_observe:
	return True
    if venue.submissions_visible_to_all:
	if venue.submissions_visible_immediately:
	    return True
	else:
	    return venue.close_date > datetime.utcnow()
    else:
	return False

    
def validate_task(db, t_id, user_email):
    """Validates that user_email can do the reviewing task t."""
    t = db.task(t_id)
    if t == None:
        return None
    if t.user != user_email:
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

	
