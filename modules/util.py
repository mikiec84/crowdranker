#!/usr/bin/env python
# coding: utf8
from gluon import *
import re
import string
import random

email_split_pattern = re.compile('[,\s]+')
whitespace = re.compile('\s+$')
all_whitespace = re.compile('\s*$')
vowels = 'aeiouy'
consonants = 'bcdfgmnpqrstvwz'

def union_id_list(l1, l2):
    """Computes the union of the 'id' elements of two lists of dictionaries."""
    id1l = [el['id'] for el in l1]
    id2l = [el['id'] for el in l2]
    for id in id2l:
        if not (id in id1l):
            id1l.append(id)
    return id1l

def union_list(l1, l2):
    l = l1.copy()
    for el in l2:
        if el not in l:
            l.append(el)
    return l
            
def get_list(f):
    """Unfortunately, empty list fields are often returned as None rather than the empty list."""
    if f == None:
        return []
    else:
        return f

def id_list(l):
    return [el['id'] for el in l]
    
def get_id_list(f):
    return id_list(get_list(f))
    
def list_append_unique(l, el):
    """Appends an element to a list, if not present."""
    if l == None:
        return [el]
    if el in l:
        return l
    else:
        return l + [el]
                
def list_remove(l, el):
    """Removes element el from list l, if found."""
    if l == None:
        return []
    if el not in l:
        return l
    else:
        l.remove(el)
        return l
        
def list_diff(l1, l2):
    if l1 == None:
        l1 = []
    if l2 == None:
        l2 = []
    r = []
    for el in l1:
        if el not in l2:
            r += [el]
    return r
        
def split_emails(s):
    """Splits the emails that occur in a string s, returning the list of emails."""
    l = email_split_pattern.split(s)
    if l == None:
        return []
    else:
        r = []
        for el in l:
            if len(el) > 0 and not whitespace.match(el):
                r += [el]
        return r

def normalize_email_list(l):
    if isinstance(l, basestring):
        l = [l]
    r = []
    for el in l:
        ll = split_emails(el)
        r += ll
    return r

def is_none(s):
    """Checks whether something is empty or None"""
    if s == None:
        return True
    elif isinstance(s, basestring):
        return all_whitespace.match(str(s))
    else:
	return False
    
def get_random_id(n_sections=6, section_length=6):
    """Produces a memorable random string."""
    sections = []
    for i in range(n_sections):
        s = ''
        for j in range(section_length / 2):
            s += random.choice(consonants) + random.choice(vowels)
        sections.append(s)
    return '_'.join(sections)

def shorten(s, max_length=32, dotdot=True):
    max_length = max(2, max_length)
    if s is None:
	return ""
    if len(s) <= max_length:
	return s
    else:
	if dotdot:
	    return s[:max_length - 3] + "..."
	else:
	    return s[:max_length]

def produce_submission_nickname(subm):
    if subm != None:
	return shorten(subm.user, max_length=3, dotdot=False)
    else:
	return '???'
