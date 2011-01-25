#!/usr/bin/env python
# coding=utf-8

import os
import re
import time
import datetime
import hashlib
import string
import random
import urllib
import urllib2

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.api import urlfetch
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
from v2ex.babel.ext.sessions import Session

from django.utils import simplejson as json

template.register_template_library('v2ex.templatetags.filters')

class ImagesHomeHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        browser = detect(self.request)
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        self.session = Session()
        if member:
            source = 'http://daydream/stream/' + str(member.num)
            result = urlfetch.fetch(source)
            images = json.loads(result.content)
            template_values = {}
            template_values['images'] = images
            template_values['site'] = site
            template_values['member'] = member
            template_values['page_title'] = site.title + u' › 图片上传'
            template_values['l10n'] = l10n
            template_values['system_version'] = SYSTEM_VERSION
            if 'message' in self.session:
                template_values['message'] = self.session['message']
                del self.session['message']
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'images_home.html')
            output = template.render(path, template_values)
            self.response.out.write(output)
        else:
            self.redirect('/signin')

class ImagesUploadHandler(webapp.RequestHandler):
    def post(self):
        site = GetSite()
        browser = detect(self.request)
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        if member:    
            image = self.request.get('image')
            if image is not None:
                import urllib, urllib2
                parameters = urllib.urlencode(dict(member_id=member.num, image=image))
                try:
                    f = urllib2.urlopen('http://daydream/upload', parameters)
                    data = f.read()
                    f.close()
                except:
                    self.session = Session()
                    self.session['message'] = '图片不能超过 1M'
                self.redirect('/images')
        else:
            self.redirect('/signin')

class ImagesUploadRulesHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        browser = detect(self.request)
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)   
        template_values = {}
        template_values['site'] = site
        template_values['member'] = member
        template_values['page_title'] = site.title + u' › 图片上传规则'
        template_values['l10n'] = l10n
        template_values['system_version'] = SYSTEM_VERSION
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'images_rules.html')
        output = template.render(path, template_values)
        self.response.out.write(output)
        

def main():
    application = webapp.WSGIApplication([
    ('/images/upload', ImagesUploadHandler),
    ('/images/upload/rules', ImagesUploadRulesHandler),
    ('/images/?', ImagesHomeHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()