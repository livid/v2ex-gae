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

from v2ex.babel.handlers import BaseHandler

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

class MD5Handler(BaseHandler):
    def get(self, source):
        i = str(self.request.get('input').strip())
        if (i):
            self.values['md5'] = hashlib.md5(i).hexdigest()
            self.values['sha1'] = hashlib.sha1(i).hexdigest()
        self.set_title(u'MD5 / SHA1 计算器')
        self.finalize(template_name='md5')
        
def main():
    application = webapp.WSGIApplication([
    ('/time/?', WorldClockHandler),
    ('/(md5|sha1)/?', MD5Handler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()