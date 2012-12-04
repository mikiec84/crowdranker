#!/usr/bin/env python
# coding: utf8
from gluon import *
import util

from gluon.custom_import import track_changes; track_changes(True)

def split_emails(form):
    form.vars.email_list = util.split_emails(form.vars.user_emails)
    form.vars.managers = util.split_emails(form.vars.manager_emails)
