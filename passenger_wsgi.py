'''
This module stats the application in production mode. It load app.py and creates
the application.
'''
import imp
import os
import sys

# this file is used by hosting server (now i'm in shared hosting namecheap.com)
# used in production with passenger server.
# requires app.py

sys.path.insert(0, os.path.dirname(__file__))
wsgi = imp.load_source('wsgi', 'app.py')
application = wsgi.app
