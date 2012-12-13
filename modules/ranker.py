#!/usr/bin/env python
# coding: utf8
from gluon import *

# This is a mock for the real rating function.

def get_item(db, contest_id, user_id, old_items):
    # As a mock, just returns the first submission.
    s = db(db.submission.contest_id == contest_id).select(db.submission.id).first()
    return s.id
