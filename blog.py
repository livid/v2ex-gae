#!/usr/bin/env python
# coding=utf-8

import os
import base64
import re
import time
import datetime
import hashlib
import httplib
import string
import pickle

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.api import images
from google.appengine.ext import db
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

from v2ex.babel import Member
from v2ex.babel import Avatar
from v2ex.babel import Counter
from v2ex.babel.security import *
from v2ex.babel.ua import *
from v2ex.babel.da import *
from v2ex.babel.l10n import *
from v2ex.babel.ext.cookies import Cookies
from v2ex.babel.ext.sessions import Session

from v2ex.babel import SYSTEM_VERSION

from v2ex.babel.handlers import BaseHandler

import config

template.register_template_library('v2ex.templatetags.filters')

class BlogHandler(BaseHandler):
    def get(self, member_username):
        one = GetMemberByUsername(member_username)
        if one:
            self.values['one'] = one
            topics = db.GqlQuery("SELECT * FROM Topic WHERE node_name = 'blog' AND member_num = :1 ORDER BY created DESC", one.num)
            self.values['topics'] = topics
            friends = db.GqlQuery("SELECT * FROM MemberBookmark WHERE member_num = :1", one.num)
            self.values['friends'] = friends
            self.set_title(u'Blog')
            self.finalize(template_name='blog')
        else:
            self.set_title(u'Member Not Found')
            self.finalize(template_name='member_not_found')

class BlogEntryHandler(BaseHandler):
    def get(self, topic_num):
        topic = GetKindByNum('Topic', int(topic_num))
        if topic:
            if topic.node_name == 'blog':
                self.values['one'] = topic.member
                self.values['topic'] = topic
                if topic.replies > 0:
                    self.values['replies'] = db.GqlQuery("SELECT * FROM Reply WHERE topic_num = :1", topic.num)
                self.values['page_title'] = topic.title
                self.finalize(template_name='blog_entry')
            else:
                self.redirect('/t/' + str(topic.num) + '#reply' + str(topic.replies))
        else:
            self.set_title(u'Topic Not Found')
            self.finalize(template_name='topic_not_found')

def main():
    application = webapp.WSGIApplication([
    ('/blog/([a-z0-9A-Z\_\-]+)', BlogHandler),
    ('/entry/([0-9]+)', BlogEntryHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()