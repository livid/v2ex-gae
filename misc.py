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

from v2ex.babel import Member
from v2ex.babel import Counter
from v2ex.babel import Section
from v2ex.babel import Node
from v2ex.babel import Topic
from v2ex.babel import Reply
from v2ex.babel import Note

from v2ex.babel import SYSTEM_VERSION

from v2ex.babel.security import *
from v2ex.babel.ua import *
from v2ex.babel.da import *
from v2ex.babel.l10n import *
from v2ex.babel.ext.cookies import Cookies

template.register_template_library('v2ex.templatetags.filters')

class WorldClockHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        member = CheckAuth(self)
        template_values = {}
        template_values['site'] = site
        if member:
            template_values['member'] = member
        l10n = GetMessages(self, site, member)
        template_values['l10n'] = l10n
        template_values['page_title'] = site.title + u' › World Clock 世界时钟'
        template_values['now'] = datetime.datetime.now()
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'time.html')
        output = template.render(path, template_values)
        self.response.out.write(output)

class WeblukerHandler(webapp.RequestHandler):
    def head(self):
        self.response.out.write('webluker-site-verification:webluker-8d00e4a6a4a4fc50.html')

    def get(self):
        self.response.out.write('webluker-site-verification:webluker-8d00e4a6a4a4fc50.html')

def main():
    application = webapp.WSGIApplication([
    ('/time/?', WorldClockHandler),
    ('/webluker-verif.html', WeblukerHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()