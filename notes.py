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
from v2ex.babel import Site

from v2ex.babel import SYSTEM_VERSION

from v2ex.babel.security import *
from v2ex.babel.ua import *
from v2ex.babel.da import *
from v2ex.babel.l10n import *
from v2ex.babel.ext.cookies import Cookies

template.register_template_library('v2ex.templatetags.filters')

class NotesHomeHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        browser = detect(self.request)
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        template_values['page_title'] = site.title + u' › 记事本'
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if member:
            template_values['member'] = member
            q = db.GqlQuery("SELECT * FROM Note WHERE member = :1 ORDER BY last_modified DESC", member)
            try:
                notes_count = q.count()
            except:
                q = db.GqlQuery("SELECT * FROM Note WHERE member = :1 ORDER BY created DESC", member)
                notes_count = q.count()
            if (notes_count > 0):
                template_values['notes'] = q
            if browser['ios']:
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'notes_home.html')
            else:
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'notes_home.html')
            output = template.render(path, template_values)
            self.response.out.write(output)
        else:
            self.redirect('/signin')
            
class NotesNewHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        template_values['page_title'] = site.title + u' › 新建记事'
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if member:
            template_values['member'] = member
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'notes_new.html')
            output = template.render(path, template_values)
            self.response.out.write(output)
        else:
            self.redirect('/signin')
    
    def post(self):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        template_values['page_title'] = site.title + u' › 新建记事'
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if member:
            template_values['member'] = member
            # Verification: content
            note_content = self.request.get('content').strip()
            note_content_length = len(note_content)
            if note_content_length > 0:
                note = Note()
                q = db.GqlQuery('SELECT * FROM Counter WHERE name = :1', 'note.max')
                if (q.count() == 1):
                    counter = q[0]
                    counter.value = counter.value + 1
                else:
                    counter = Counter()
                    counter.name = 'note.max'
                    counter.value = 1
                q2 = db.GqlQuery('SELECT * FROM Counter WHERE name = :1', 'note.total')
                if (q2.count() == 1):
                    counter2 = q2[0]
                    counter2.value = counter2.value + 1
                else:
                    counter2 = Counter()
                    counter2.name = 'note.total'
                    counter2.value = 1
                note.num = counter.value
                note.title = note_content.split("\n")[0][0:60].strip()
                note.content = note_content
                note.body = "\n".join(note_content.split("\n")[1:]).strip()
                note.length = len(note_content)
                note.member_num = member.num
                note.member = member
                note.put()
                counter.put()
                counter2.put()
                self.redirect('/notes/' + str(note.num))
            else:
                template_values['note_content'] = note_content
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'notes_new.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
        else:
            self.redirect('/signin')

class NotesItemHandler(webapp.RequestHandler):
    def get(self, num):
        site = GetSite()
        browser = detect(self.request)
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if member:
            q = db.GqlQuery("SELECT * FROM Note WHERE num = :1", int(num))
            if q.count() > 0:
                note = q[0]
                if note.member.num == member.num:
                    template_values['member'] = member
                    template_values['note'] = note
                    template_values['page_title'] = site.title + u' › 记事本 › ' + note.title
                    if browser['ios']:
                        path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'notes_item.html')
                    else:
                        path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'notes_item.html')
                    output = template.render(path, template_values)
                    self.response.out.write(output)
                else:
                    self.redirect('/')
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')

class NotesItemEraseHandler(webapp.RequestHandler):
    def get(self, num):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        template_values['page_title'] = site.title + u' › 记事本'
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if member:
            q = db.GqlQuery("SELECT * FROM Note WHERE num = :1", int(num))
            if q.count() > 0:
                note = q[0]
                if note.member.num == member.num:
                    note.delete()
                    self.redirect('/notes')
                else:
                    self.redirect('/notes')
            else:
                self.redirect('/notes')
        else:
            self.redirect('/signin')

class NotesItemEditHandler(webapp.RequestHandler):
    def get(self, num):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        template_values['page_title'] = site.title + u' › 记事本 › 编辑'
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if member:
            q = db.GqlQuery("SELECT * FROM Note WHERE num = :1", int(num))
            if q.count() > 0:
                note = q[0]
                if note.member.num == member.num:
                    template_values['member'] = member
                    template_values['note'] = note
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'notes_edit.html')
                    output = template.render(path, template_values)
                    self.response.out.write(output)
                else:
                    self.redirect('/notes')
            else:
                self.redirect('/notes')
        else:
            self.redirect('/signin')

    def post(self, num):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        template_values['page_title'] = site.title + u' › 记事本'
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if member:
            template_values['member'] = member
            # Verification: content
            note_content = self.request.get('content').strip()
            note_content_length = len(note_content)
            if note_content_length > 0:
                q = db.GqlQuery("SELECT * FROM Note WHERE num = :1", int(num))
                if q.count() > 0:
                    note = q[0]
                    template_values['page_title'] = site.title + u' › 记事本 › 编辑' 
                    if note.member.num == member.num:
                        note.title = note_content.split("\n")[0][0:60].strip()
                        note.content = note_content
                        note.body = "\n".join(note_content.split("\n")[1:]).strip()
                        note.length = len(note_content)
                        note.edits = note.edits + 1
                        note.put()
                        memcache.set('Note_' + str(note.num), note, 86400)
                        self.redirect('/notes/' + str(note.num))
                    else:
                        self.redirect('/notes')
                else:
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
    ('/notes/new', NotesNewHandler),
    ('/notes/([0-9]+)', NotesItemHandler),
    ('/notes/([0-9]+)/erase', NotesItemEraseHandler),
    ('/notes/([0-9]+)/edit', NotesItemEditHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()