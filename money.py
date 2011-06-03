#!/usr/bin/env python
# coding=utf-8

import os
import re
import time
import datetime
import hashlib
import string
import random

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api.labs import taskqueue

from v2ex.babel import Member
from v2ex.babel import Counter
from v2ex.babel import Section
from v2ex.babel import Node
from v2ex.babel import Topic
from v2ex.babel import Reply
from v2ex.babel import Note
from v2ex.babel import Notification

from v2ex.babel import SYSTEM_VERSION

from v2ex.babel.security import *
from v2ex.babel.ua import *
from v2ex.babel.da import *
from v2ex.babel.l10n import *
from v2ex.babel.ext.cookies import Cookies

from v2ex.babel.handlers import BaseHandler

import config

template.register_template_library('v2ex.templatetags.filters')

class MoneyDashboardHandler(BaseHandler):
    def get(self):
        if self.member:
            self.set_title(u'账户查询')
            self.finalize(template_name='money_dashboard')
        else:
            self.redirect('/signin')

def main():
    application = webapp.WSGIApplication([
    ('/money/dashboard/?', MoneyDashboardHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()