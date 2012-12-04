#!/usr/bin/env python
# coding: utf8
from gluon import *
import util

def separate_emails(form):
    form.vars.email_list = util.separate_emails(form.vars.user_emails)
    form.vars.managers = util.separate_emails(form.vars.manager_emails)
