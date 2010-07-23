import os
import time
import datetime
import random
import Cookie
import logging
from google.appengine.api import memcache
from django.utils import simplejson as json

# Note - please do not use this for production applications
# see: http://code.google.com/p/appengine-utitlies/

COOKIE_NAME = 'appengine-simple-session-sid'
DEFAULT_COOKIE_PATH = '/'
SESSION_EXPIRE_TIME = 7200 # sessions are valid for 7200 seconds (2 hours)

class Session(object):

    def __init__(self):
        self.sid = None
        self.key = None
        self.session = None
        string_cookie = os.environ.get('HTTP_COOKIE', '')
        self.cookie = Cookie.SimpleCookie()
        self.cookie.load(string_cookie)

        # check for existing cookie
        if self.cookie.get(COOKIE_NAME):
            self.sid = self.cookie[COOKIE_NAME].value
            self.key = "session-" + self.sid
	    self.session = memcache.get(self.key)
            if self.session is None:
               logging.info("Invalidating session "+self.sid)
               self.sid = None
               self.key = None

        if self.session is None:
            self.sid = str(random.random())[5:]+str(random.random())[5:]
            self.key = "session-" + self.sid
            logging.info("Creating session "+self.key);
            self.session = dict()
	    memcache.add(self.key, self.session, 3600)

            self.cookie[COOKIE_NAME] = self.sid
            self.cookie[COOKIE_NAME]['path'] = DEFAULT_COOKIE_PATH
            # Send the Cookie header to the browser
            print self.cookie

    # Private method to update the cache on modification 
    def _update_cache(self):
        memcache.replace(self.key, self.session, 3600)

    # Convenient delete with no error method
    def delete_item(self, keyname):
        if keyname in self.session:
            del self.session[keyname]
            self._update_cache()

    # Support the dictionary get() method
    def get(self, keyname, default=None):
        if keyname in self.session:
            return self.session[keyname]
        return default

    # session[keyname] = value
    def __setitem__(self, keyname, value):
        self.session[keyname] = value
        self._update_cache()

    # x = session[keyname]
    def __getitem__(self, keyname):
        if keyname in self.session:
            return self.session[keyname]
        raise KeyError(str(keyname))

    # del session[keyname]
    def __delitem__(self, keyname):
        if keyname in self.session:
	    del self.session[keyname]
            logging.info(self.session)
            self._update_cache()
            return
        raise KeyError(str(keyname))

    # if keyname in session :
    def __contains__(self, keyname):
        try:
            r = self.__getitem__(keyname)
        except KeyError:
            return False
        return True

    # x = len(session)
    def __len__(self):
        return len(self.session)

