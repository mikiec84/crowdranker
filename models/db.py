# -*- coding: utf-8 -*-

from gluon.custom_import import track_changes; track_changes(True) # for reloading modules

#########################################################################
## This scaffolding model makes your app work on Google App Engine too
## File is released under public domain and you can use without limitations
#########################################################################

## if SSL/HTTPS is properly configured and you want all HTTP requests to
## be redirected to HTTPS, uncomment the line below:
# request.requires_https()

if not request.env.web2py_runtime_gae:
    ## if NOT running on Google App Engine use SQLite or other DB
    db = DAL('sqlite://storage.sqlite')
else:
    ## connect to Google BigTable (optional 'google:datastore://namespace')
    db = DAL('google:datastore')
    ## store sessions and tickets there
    session.connect(request, response, db=db)
    ## or store session in Memcache, Redis, etc.
    ## from gluon.contrib.memdb import MEMDB
    ## from google.appengine.api.memcache import Client
    ## session.connect(request, response, db = MEMDB(Client()))

## by default give a view/generic.extension to all actions from localhost
## none otherwise. a pattern can be 'controller/function.extension'

# Luca says: do NOT make generic json possible, as there is information that should
# not leak out in most forms.
response.generic_patterns = ['*'] if request.is_local else []

## (optional) optimize handling of static files
# response.optimize_css = 'concat,minify,inline'
# response.optimize_js = 'concat,minify,inline'

#########################################################################
## Here is sample code if you need for
## - email capabilities
## - authentication (registration, login, logout, ... )
## - authorization (role based authorization)
## - services (xml, csv, json, xmlrpc, jsonrpc, amf, rss)
## - old style crud actions
## (more options discussed in gluon/tools.py)
#########################################################################

from gluon.tools import Auth, Crud, Service, PluginManager, prettydate
auth = Auth(db)
crud, service, plugins = Crud(db), Service(), PluginManager()

## create all tables needed by auth if not custom tables
auth.define_tables(username=False)

## configure email
mail = auth.settings.mailer
mail.settings.server = 'logging' or 'smtp.gmail.com:587'
mail.settings.sender = 'you@gmail.com'
mail.settings.login = 'username:password'

## configure auth policy
auth.settings.registration_requires_verification = False
auth.settings.registration_requires_approval = False
auth.settings.reset_password_requires_verification = True

##### This tells web2py to use GAE logins.
if request.env.web2py_runtime_gae:
    from gluon.contrib.login_methods.gae_google_account import GaeGoogleAccount
    auth.settings.login_form = GaeGoogleAccount()


## if you need to use OpenID, Facebook, MySpace, Twitter, Linkedin, etc.
## register with janrain.com, write your domain:api_key in private/janrain.key
from gluon.contrib.login_methods.rpx_account import use_janrain
use_janrain(auth, filename='private/janrain.key')

#########################################################################
## Define your tables below (or better in another model file) for example
##
## >>> db.define_table('mytable',Field('myfield','string'))
##
## Fields can be 'string','text','password','integer','double','boolean'
##       'date','time','datetime','blob','upload', 'reference TABLENAME'
## There is an implicit 'id integer autoincrement' field
## Consult manual for more options, validators, etc.
##
## More API examples for controllers:
##
## >>> db.mytable.insert(myfield='value')
## >>> rows=db(db.mytable.myfield=='value').select(db.mytable.ALL)
## >>> for row in rows: print row.id, row.myfield
#########################################################################

## after defining tables, uncomment below to enable auditing
# auth.enable_record_versioning(db)

#####################
# Admin settings
admin_emails = ['luca@ucsc.edu', 'luca.de.alfaro@gmail.com', 'luca@dealfaro.com', 'luca@dealfaro.org',
		'mshavlov@ucsc.edu', 'mshavlovsky@gmail.com']
# These are the people that can create submission venues.
creator_emails = admin_emails

def is_user_admin():
    return auth.user and auth.user.email in admin_emails

######################
# Logging
import logging, logging.handlers

class GAEHandler(logging.Handler):
    """
    Logging handler for GAE DataStore
    """
    def emit(self, record):

        from google.appengine.ext import db

        class Log(db.Model):
            name = db.StringProperty()
            level = db.StringProperty()
            module = db.StringProperty()
            func_name = db.StringProperty()
            line_no = db.IntegerProperty()
            thread = db.IntegerProperty()
            thread_name = db.StringProperty()
            process = db.IntegerProperty()
            message = db.StringProperty(multiline=True)
            args = db.StringProperty(multiline=True)
            date = db.DateTimeProperty(auto_now_add=True)

        log = Log()
        log.name = record.name
        log.level = record.levelname
        log.module = record.module
        log.func_name = record.funcName
        log.line_no = record.lineno
        log.thread = record.thread
        log.thread_name = record.threadName
        log.process = record.process
        log.message = record.msg
        log.args = str(record.args)
        log.put()

def get_configured_logger(name):
    logger = logging.getLogger(name)
    if (len(logger.handlers) == 0):
        # This logger has no handlers, so we can assume it hasn't yet been configured
        # (Configure logger)

        # Create default handler
        if request.env.web2py_runtime_gae:
            # Create GAEHandler
            handler = GAEHandler()
	    handler.setLevel(logging.WARNING)
	    logger.addHandler(handler)
	    logger.setLevel(logging.WARNING)
        else:
            # Create RotatingFileHandler
            import os
            formatter="%(asctime)s %(levelname)s %(process)s %(thread)s %(funcName)s():%(lineno)d %(message)s"
            handler = logging.handlers.RotatingFileHandler(os.path.join(request.folder,'private/app.log'),maxBytes=1024,backupCount=2)
            handler.setFormatter(logging.Formatter(formatter))
	    handler.setLevel(logging.DEBUG)
	    logger.addHandler(handler)
	    logger.setLevel(logging.DEBUG)

        # Test entry:
        # logger.debug(name + ' logger created')
    else:
	pass
        # Test entry:
        # logger.debug(name + ' already exists')

    return logger

# Assign application logger to a global var  
logger = get_configured_logger(request.application)

