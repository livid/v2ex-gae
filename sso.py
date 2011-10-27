#!/usr/bin/env python
# coding=utf-8

import os
import re
import time
import datetime
import hashlib
import string
import random

import config

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

class SSOV0Handler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        self.response.headers['Content-type'] = 'application/json'
        u = self.request.get('u').strip().lower()
        p = self.request.get('p').strip()
        failed = '{"ok" : 0}'
        if (len(u) > 0) and (len(p) > 0):
            q = db.GqlQuery("SELECT * FROM Member WHERE username_lower = :1 AND password = :2", u, p)
            if q.count() > 0:
                member = q[0]
                if member.avatar_mini_url:
                    if (member.avatar_mini_url[0:1] == '/'):
                        member.avatar_mini_url = 'http://' + site.domain + member.avatar_mini_url
                        member.avatar_normal_url = 'http://' +  site.domain + member.avatar_normal_url
                        member.avatar_large_url = 'http://' + site.domain + member.avatar_large_url
                else:
                    member.avatar_mini_url = 'http://' + site.domain + '/static/img/avatar_mini.png'
                    member.avatar_normal_url = 'http://' + site.domain + '/static/img/avatar_normal.png'
                    member.avatar_large_url = 'http://' + site.domain + '/static/img/avatar_large.png'
                self.response.out.write('{"ok" : 1, "num" : ' + str(member.num) + ', "username" : "' + member.username + '", "username_lower" : "' + member.username_lower + '", "email" : "' + member.email + '", "avatar_mini_url" : "' + member.avatar_mini_url + '", "avatar_normal_url" : "' + member.avatar_normal_url + '", "avatar_large_url" : "' + member.avatar_large_url + '", "created" : ' + str(time.mktime(member.created.timetuple())) + ', "last_modified" : ' + str(time.mktime(member.last_modified.timetuple())) + '}')
            else:
                self.response.out.write(failed)
        else:
            self.response.out.write(failed)

class SSOX0Handler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        self.response.headers['Content-type'] = 'application/json'
        x = self.request.get('x').strip()
        n = self.request.get('n').strip().lower()
        failed = '{"ok" : 0}'
        if x == config.ssox:
            q = db.GqlQuery("SELECT * FROM Member WHERE username_lower = :1", n)
            if q.count() > 0:
                member = q[0]
                if member.avatar_mini_url:
                    if (member.avatar_mini_url[0:1] == '/'):
                        member.avatar_mini_url = 'http://' + site.domain + member.avatar_mini_url
                        member.avatar_normal_url = 'http://' +  site.domain + member.avatar_normal_url
                        member.avatar_large_url = 'http://' + site.domain + member.avatar_large_url
                else:
                    member.avatar_mini_url = 'http://' + site.domain + '/static/img/avatar_mini.png'
                    member.avatar_normal_url = 'http://' + site.domain + '/static/img/avatar_normal.png'
                    member.avatar_large_url = 'http://' + site.domain + '/static/img/avatar_large.png'
                self.response.out.write('{"ok" : 1, "num" : ' + str(member.num) + ', "username" : "' + member.username + '", "username_lower" : "' + member.username_lower + '", "email" : "' + member.email + '", "password" : "' + member.password + '", "avatar_mini_url" : "' + member.avatar_mini_url + '", "avatar_normal_url" : "' + member.avatar_normal_url + '", "avatar_large_url" : "' + member.avatar_large_url + '", "created" : ' + str(time.mktime(member.created.timetuple())) + ', "last_modified" : ' + str(time.mktime(member.last_modified.timetuple())) + '}')
            else:
                self.response.out.write(failed)
        else:
            self.response.out.write(failed)
            

def main():
    application = webapp.WSGIApplication([
    ('/sso/v0', SSOV0Handler),
    ('/sso/x0', SSOX0Handler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()