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
from v2ex.babel.ext.cookies import Cookies

template.register_template_library('v2ex.templatetags.filters')

class NotesHomeHandler(webapp.RequestHandler):
    def get(self):
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        template_values['page_title'] = 'V2EX › 记事本'
        member = CheckAuth(self)
        if member:
            template_values['member'] = member
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'notes_home.html')
            output = template.render(path, template_values)
            self.response.out.write(output)
        else:
            self.redirect('/signin')
            
class NotesNewHandler(webapp.RequestHandler):
    def get(self):
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        template_values['page_title'] = 'V2EX › 新建记事'
        member = CheckAuth(self)
        if member:
            template_values['member'] = member
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'notes_new.html')
            output = template.render(path, template_values)
            self.response.out.write(output)
        else:
            self.redirect('/signin')
    
    def post(self):
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        template_values['page_title'] = 'V2EX › 新建记事'
        member = CheckAuth(self)
        if member:
            template_values['member'] = member
            # Verification: content
            note_content = self.request.get('content').strip()
            note_content_length = len(note_content)
            if note_content_length > 0:
                note = Note()
                note.content = note_content
                note.put()
                self.redirect('/notes')
            else:
                template_values['note_content'] = note_content
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'notes_new.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
        else:
            self.redirect('/signin')

def main():
    application = webapp.WSGIApplication([
    ('/notes', NotesHomeHandler),
    ('/notes/new', NotesNewHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()