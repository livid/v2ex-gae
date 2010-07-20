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
from v2ex.babel.ext.cookies import Cookies

template.register_template_library('v2ex.templatetags.filters')

class StatsHandler(webapp.RequestHandler):
    def get(self):
        template_values = {}
        template_values['topic_max'] = GetKindByName('Counter', 'topic.max')
        template_values['member_max'] = GetKindByName('Counter', 'member.max')
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'stats.json')
        output = template.render(path, template_values)
        self.response.headers['Content-type'] = 'application/json'
        self.response.out.write(output)

def main():
    application = webapp.WSGIApplication([
    ('/api/stats', StatsHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()