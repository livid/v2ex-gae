#!/usr/bin/env python
# coding=utf-8

import base64
import os
import re
import time
import datetime
import hashlib
import logging
import string
import StringIO
import random
import math

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.api import images
from google.appengine.ext import db
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

from v2ex.babel import Avatar
from v2ex.babel import Member
from v2ex.babel import Counter
from v2ex.babel import Section
from v2ex.babel import Node
from v2ex.babel import Site
from v2ex.babel import Minisite
from v2ex.babel import Page

from v2ex.babel import SYSTEM_VERSION

from v2ex.babel.security import *
from v2ex.babel.ext.cookies import Cookies
from v2ex.babel.ua import *
from v2ex.babel.da import *
from v2ex.babel.l10n import *

from v2ex.babel.handlers import BaseHandler

template.register_template_library('v2ex.templatetags.filters')

import config

class BackstageHomeHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        browser = detect(self.request)
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values = {}
        template_values['l10n'] = l10n
        template_values['site'] = site
        template_values['rnd'] = random.randrange(1, 100)
        template_values['system_version'] = SYSTEM_VERSION
        template_values['member'] = member
        template_values['page_title'] = site.title + u' › ' + l10n.backstage.decode('utf-8')
        member_total = memcache.get('member_total')
        if member_total is None:
            q3 = db.GqlQuery("SELECT * FROM Counter WHERE name = 'member.total'")
            if (q3.count() > 0):
                member_total = q3[0].value
            else:
                member_total = 0
            memcache.set('member_total', member_total, 600)
        template_values['member_total'] = member_total
        topic_total = memcache.get('topic_total')
        if topic_total is None:
            q4 = db.GqlQuery("SELECT * FROM Counter WHERE name = 'topic.total'")
            if (q4.count() > 0):
                topic_total = q4[0].value
            else:
                topic_total = 0
            memcache.set('topic_total', topic_total, 600)
        template_values['topic_total'] = topic_total
        reply_total = memcache.get('reply_total')
        if reply_total is None:
            q5 = db.GqlQuery("SELECT * FROM Counter WHERE name = 'reply.total'")
            if (q5.count() > 0):
                reply_total = q5[0].value
            else:
                reply_total = 0
            memcache.set('reply_total', reply_total, 600)
        template_values['reply_total'] = reply_total
        if (member):
            if (member.level == 0):
                q = db.GqlQuery("SELECT * FROM Section ORDER BY nodes DESC")
                template_values['sections'] = q
                q2 = db.GqlQuery("SELECT * FROM Member ORDER BY created DESC LIMIT 5")
                template_values['latest_members'] = q2
                q3 = db.GqlQuery("SELECT * FROM Minisite ORDER BY created DESC")
                template_values['minisites'] = q3
                q4 = db.GqlQuery("SELECT * FROM Node ORDER BY last_modified DESC LIMIT 8")
                template_values['latest_nodes'] = q4
                if browser['ios']:
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'backstage_home.html')
                else:
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_home.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')
            
class BackstageNewMinisiteHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        template_values['page_title'] = site.title + u' › 添加新站点'
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        template_values['member'] = member
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            if (member.level == 0):    
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_new_minisite.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')
    
    def post(self):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        template_values['page_title'] = site.title + u' › 添加新站点'
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        template_values['member'] = member
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            if (member.level == 0):
                errors = 0
                # Verification: name
                minisite_name_error = 0
                minisite_name_error_messages = ['',
                    u'请输入站点名',
                    u'站点名长度不能超过 32 个字符',
                    u'站点名只能由 a-Z 0-9 及 - 和 _ 组成',
                    u'抱歉这个站点名已经存在了']
                minisite_name = self.request.get('name').strip().lower()
                if (len(minisite_name) == 0):
                    errors = errors + 1
                    minisite_name_error = 1
                else:
                    if (len(minisite_name) > 32):
                        errors = errors + 1
                        minisite_name_error = 2
                    else:
                        if (re.search('^[a-zA-Z0-9\-\_]+$', minisite_name)):
                            q = db.GqlQuery('SELECT __key__ FROM Minisite WHERE name = :1', minisite_name.lower())
                            if (q.count() > 0):
                                errors = errors + 1
                                minisite_name_error = 4
                        else:
                            errors = errors + 1
                            minisite_name_error = 3
                template_values['minisite_name'] = minisite_name
                template_values['minisite_name_error'] = minisite_name_error
                template_values['minisite_name_error_message'] = minisite_name_error_messages[minisite_name_error]
                # Verification: title
                minisite_title_error = 0
                minisite_title_error_messages = ['',
                    u'请输入站点标题',
                    u'站点标题长度不能超过 32 个字符'
                ]
                minisite_title = self.request.get('title').strip()
                if (len(minisite_title) == 0):
                    errors = errors + 1
                    minisite_title_error = 1
                else:
                    if (len(minisite_title) > 32):
                        errors = errors + 1
                        minisite_title_error = 2
                template_values['minisite_title'] = minisite_title
                template_values['minisite_title_error'] = minisite_title_error
                template_values['minisite_title_error_message'] = minisite_title_error_messages[minisite_title_error]
                # Verification: description
                minisite_description_error = 0
                minisite_description_error_messages = ['',
                    u'请输入站点描述',
                    u'站点描述长度不能超过 2000 个字符'
                ]
                minisite_description = self.request.get('description').strip()
                if (len(minisite_description) == 0):
                    errors = errors + 1
                    minisite_description_error = 1
                else:
                    if (len(minisite_description) > 2000):
                        errors = errors + 1
                        minisite_description_error = 2
                template_values['minisite_description'] = minisite_description
                template_values['minisite_description_error'] = minisite_description_error
                template_values['minisite_description_error_message'] = minisite_description_error_messages[minisite_description_error]
                template_values['errors'] = errors
                if (errors == 0):
                    minisite = Minisite()
                    q = db.GqlQuery('SELECT * FROM Counter WHERE name = :1', 'minisite.max')
                    if (q.count() == 1):
                        counter = q[0]
                        counter.value = counter.value + 1
                    else:
                        counter = Counter()
                        counter.name = 'minisite.max'
                        counter.value = 1
                    minisite.num = counter.value
                    minisite.name = minisite_name
                    minisite.title = minisite_title
                    minisite.description = minisite_description
                    minisite.put()
                    counter.put()
                    self.redirect('/backstage')
                else:    
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_new_minisite.html')
                    output = template.render(path, template_values)
                    self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')
            
class BackstageMinisiteHandler(webapp.RequestHandler):
    def get(self, minisite_name):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        template_values['page_title'] = site.title + u' › Minisite'
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        template_values['member'] = member
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            if (member.level == 0):
                minisite = GetKindByName('Minisite', minisite_name)
                if minisite is not False:
                    template_values['minisite'] = minisite
                    template_values['page_title'] = site.title + u' › ' + minisite.title
                    q = db.GqlQuery("SELECT * FROM Page WHERE minisite = :1 ORDER BY weight ASC", minisite)
                    template_values['pages'] = q
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_minisite.html')
                    output = template.render(path, template_values)
                    self.response.out.write(output)
                else:
                    self.redirect('/backstage')
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')

class BackstageNewPageHandler(webapp.RequestHandler):
    def get(self, minisite_name):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        template_values['member'] = member
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            if (member.level == 0):
                minisite = GetKindByName('Minisite', minisite_name)
                if minisite is not False:
                    template_values['minisite'] = minisite
                    template_values['page_title'] = site.title + u' › ' + minisite.title + u' › 添加新页面'
                    template_values['page_content_type'] = 'text/html;charset=utf-8'
                    template_values['page_weight'] = 0
                    template_values['page_mode'] = 0
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_new_page.html')
                    output = template.render(path, template_values)
                    self.response.out.write(output)
                else:
                    self.redirect('/backstage')
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')

    def post(self, minisite_name):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        template_values['member'] = member
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            if (member.level == 0):
                minisite = GetKindByName('Minisite', minisite_name)
                if minisite is False:
                    self.redirect('/backstage')
                else:
                    template_values['minisite'] = minisite
                    template_values['page_title'] = site.title + u' › ' + minisite.title + u' › 添加新页面'
                    errors = 0
                    # Verification: name
                    page_name_error = 0
                    page_name_error_messages = ['',
                        u'请输入页面名',
                        u'页面名长度不能超过 64 个字符',
                        u'页面名只能由 a-Z 0-9 及 . - _ 组成',
                        u'抱歉这个页面名已经存在了']
                    page_name = self.request.get('name').strip().lower()
                    if (len(page_name) == 0):
                        errors = errors + 1
                        page_name_error = 1
                    else:
                        if (len(page_name) > 64):
                            errors = errors + 1
                            page_name_error = 2
                        else:
                            if (re.search('^[a-zA-Z0-9\-\_\.]+$', page_name)):
                                q = db.GqlQuery('SELECT * FROM Page WHERE name = :1', page_name.lower())
                                if (q.count() > 0):
                                    if q[0].minisite.name == minisite.name:
                                        errors = errors + 1
                                        page_name_error = 4
                            else:
                                errors = errors + 1
                                page_name_error = 3
                    template_values['page_name'] = page_name
                    template_values['page_name_error'] = page_name_error
                    template_values['page_name_error_message'] = page_name_error_messages[page_name_error]
                    # Verification: title
                    page_t_error = 0
                    page_t_error_messages = ['',
                        u'请输入页面标题',
                        u'页面标题长度不能超过 100 个字符'
                    ]
                    page_t = self.request.get('t').strip()
                    if (len(page_t) == 0):
                        errors = errors + 1
                        page_t_error = 1
                    else:
                        if (len(page_t) > 100):
                            errors = errors + 1
                            page_t_error = 2
                    template_values['page_t'] = page_t
                    template_values['page_t_error'] = page_t_error
                    template_values['page_t_error_message'] = page_t_error_messages[page_t_error]
                    # Verification: content
                    page_content_error = 0
                    page_content_error_messages = ['',
                        u'请输入页面内容',
                        u'页面内容长度不能超过 200000 个字符'
                    ]
                    page_content = self.request.get('content').strip()
                    if (len(page_content) == 0):
                        errors = errors + 1
                        page_content_error = 1
                    else:
                        if (len(page_content) > 200000):
                            errors = errors + 1
                            page_content_error = 2
                    template_values['page_content'] = page_content
                    template_values['page_content_error'] = page_content_error
                    template_values['page_content_error_message'] = page_content_error_messages[page_content_error]
                    # Verification: mode
                    page_mode = 0
                    page_mode = self.request.get('mode').strip()
                    if page_mode == '1':
                        page_mode = 1
                    else:
                        page_mode = 0
                    # Verification: content_type
                    page_content_type = self.request.get('content_type').strip()
                    if (len(page_content_type) == 0):
                        page_content_type = 'text/html;charset=utf-8'
                    else:
                        if (len(page_content_type) > 40):
                            page_content_type = 'text/html;charset=utf-8'
                    template_values['page_content_type'] = page_content_type
                    # Verification: weight
                    page_weight = self.request.get('weight').strip()
                    if (len(page_content_type) == 0):
                        page_content_type = 0
                    else:
                        if (len(page_weight) > 9):
                            page_weight = 0
                        else:
                            try:
                                page_weight = int(page_weight)
                            except:
                                page_weight = 0
                    template_values['page_weight'] = page_weight
                    template_values['errors'] = errors
                    if (errors == 0):
                        page = Page(parent=minisite)
                        q = db.GqlQuery('SELECT * FROM Counter WHERE name = :1', 'page.max')
                        if (q.count() == 1):
                            counter = q[0]
                            counter.value = counter.value + 1
                        else:
                            counter = Counter()
                            counter.name = 'page.max'
                            counter.value = 1
                        q2 = db.GqlQuery('SELECT * FROM Counter WHERE name = :1', 'page.total')
                        if (q2.count() == 1):
                            counter2 = q[0]
                            counter2.value = counter.value + 1
                        else:
                            counter2 = Counter()
                            counter2.name = 'page.total'
                            counter2.value = 1
                        page.num = counter.value
                        page.name = page_name
                        page.title = page_t
                        page.content = page_content
                        if page_mode == 1:
                            from django.template import Context, Template
                            t = Template(page_content)
                            c = Context({"site" : site, "minisite" : page.minisite, "page" : page})
                            output = t.render(c)
                            page.content_rendered = output
                        else:
                            page.content_rendered = page_content
                        page.content_type = page_content_type
                        page.weight = page_weight
                        page.mode = page_mode
                        page.minisite = minisite
                        page.put()
                        counter.put()
                        counter2.put()
                        minisite.pages = minisite.pages + 1
                        minisite.put()
                        memcache.delete('Minisite_' + str(minisite.num))
                        memcache.delete('Minisite::' + str(minisite.name))
                        self.redirect('/backstage/minisite/' + minisite.name)
                    else:    
                        path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_new_page.html')
                        output = template.render(path, template_values)
                        self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')

class BackstageRemoveMinisiteHandler(webapp.RequestHandler):
    def get(self, minisite_key):
        member = CheckAuth(self)
        if member:
            if member.level == 0:
                minisite = db.get(db.Key(minisite_key))
                if minisite:
                    # Delete all contents
                    pages = db.GqlQuery("SELECT * FROM Page WHERE minisite = :1", minisite)
                    for page in pages:
                        memcache.delete('Page_' + str(page.num))
                        memcache.delete('Page::' + str(page.name))
                        memcache.delete(minisite.name + '/' + page.name)
                        page.delete()
                    minisite.pages = 0
                    minisite.put()
                    # Delete the minisite
                    memcache.delete('Minisite_' + str(minisite.num))
                    memcache.delete('Minisite::' + str(minisite.name))
                    minisite.delete()
                    self.redirect('/backstage')
                else:
                    self.redirect('/backstage')
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')

class BackstagePageHandler(webapp.RequestHandler):
    def get(self, page_key):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        template_values['member'] = member
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            if (member.level == 0):
                page = db.get(db.Key(page_key))
                if page:
                    minisite = page.minisite
                    template_values['page'] = page
                    template_values['minisite'] = minisite
                    template_values['page_title'] = site.title + u' › ' + minisite.title + u' › ' + page.title + u' › 编辑'
                    template_values['page_name'] = page.name
                    template_values['page_t'] = page.title
                    template_values['page_content'] = page.content
                    template_values['page_content_type'] = page.content_type
                    template_values['page_mode'] = page.mode
                    template_values['page_weight'] = page.weight
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_page.html')
                    output = template.render(path, template_values)
                    self.response.out.write(output)
                else:
                    self.redirect('/backstage')
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')

    def post(self, page_key):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        template_values['member'] = member
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            if (member.level == 0):
                page = db.get(db.Key(page_key))
                if page:
                    minisite = page.minisite
                    template_values['minisite'] = minisite
                    template_values['page_title'] = site.title + u' › ' + minisite.title + u' › 添加新页面'
                    errors = 0
                    # Verification: name
                    page_name_error = 0
                    page_name_error_messages = ['',
                        u'请输入页面名',
                        u'页面名长度不能超过 64 个字符',
                        u'页面名只能由 a-Z 0-9 及 . - _ 组成',
                        u'抱歉这个页面名已经存在了']
                    page_name = self.request.get('name').strip().lower()
                    if (len(page_name) == 0):
                        errors = errors + 1
                        page_name_error = 1
                    else:
                        if (len(page_name) > 64):
                            errors = errors + 1
                            page_name_error = 2
                        else:
                            if (re.search('^[a-zA-Z0-9\-\_\.]+$', page_name)):
                                q = db.GqlQuery('SELECT * FROM Page WHERE name = :1 AND minisite = :2', page_name.lower(), page.minisite)
                                if (q.count() > 0):
                                    if q[0].num != page.num:
                                        errors = errors + 1
                                        page_name_error = 4
                            else:
                                errors = errors + 1
                                page_name_error = 3
                    template_values['page_name'] = page_name
                    template_values['page_name_error'] = page_name_error
                    template_values['page_name_error_message'] = page_name_error_messages[page_name_error]
                    # Verification: title
                    page_t_error = 0
                    page_t_error_messages = ['',
                        u'请输入页面标题',
                        u'页面标题长度不能超过 100 个字符'
                    ]
                    page_t = self.request.get('t').strip()
                    if (len(page_t) == 0):
                        errors = errors + 1
                        page_t_error = 1
                    else:
                        if (len(page_t) > 100):
                            errors = errors + 1
                            page_t_error = 2
                    template_values['page_t'] = page_t
                    template_values['page_t_error'] = page_t_error
                    template_values['page_t_error_message'] = page_t_error_messages[page_t_error]
                    # Verification: content
                    page_content_error = 0
                    page_content_error_messages = ['',
                        u'请输入页面内容',
                        u'页面内容长度不能超过 200000 个字符'
                    ]
                    page_content = self.request.get('content').strip()
                    if (len(page_content) == 0):
                        errors = errors + 1
                        page_content_error = 1
                    else:
                        if (len(page_content) > 200000):
                            errors = errors + 1
                            page_content_error = 2
                    template_values['page_content'] = page_content
                    template_values['page_content_error'] = page_content_error
                    template_values['page_content_error_message'] = page_content_error_messages[page_content_error]
                    # Verification: mode
                    page_mode = 0
                    page_mode = self.request.get('mode').strip()
                    if page_mode == '1':
                        page_mode = 1
                    else:
                        page_mode = 0
                    # Verification: content_type
                    page_content_type = self.request.get('content_type').strip()
                    if (len(page_content_type) == 0):
                        page_content_type = 'text/html;charset=utf-8'
                    else:
                        if (len(page_content_type) > 40):
                            page_content_type = 'text/html;charset=utf-8'
                    template_values['page_content_type'] = page_content_type
                    # Verification: weight
                    page_weight = self.request.get('weight').strip()
                    if (len(page_content_type) == 0):
                        page_content_type = 0
                    else:
                        if (len(page_weight) > 9):
                            page_weight = 0
                        else:
                            try:
                                page_weight = int(page_weight)
                            except:
                                page_weight = 0
                    template_values['page_weight'] = page_weight
                    template_values['errors'] = errors
                    if (errors == 0):
                        page.name = page_name
                        page.title = page_t
                        page.content = page_content
                        if page.mode == 1:
                            from django.template import Context, Template
                            t = Template(page_content)
                            c = Context({"site" : site, "minisite" : page.minisite, "page" : page})
                            output = t.render(c)
                            page.content_rendered = output
                        else:
                            page.content_rendered = page_content
                        page.content_type = page_content_type
                        page.mode = page_mode
                        page.weight = page_weight
                        page.put()
                        memcache.delete('Page_' + str(page.num))
                        memcache.delete('Page::' + str(page.name))
                        memcache.delete(minisite.name + '/' + page.name)
                        self.redirect('/backstage/minisite/' + minisite.name)
                    else:    
                        path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_page.html')
                        output = template.render(path, template_values)
                        self.response.out.write(output)
                else:
                    self.redirect('/backstage')
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')
    
class BackstageRemovePageHandler(webapp.RequestHandler):
    def get(self, page_key):
        member = CheckAuth(self)
        if member:
            if member.level == 0:
                page = db.get(db.Key(page_key))
                if page:
                    memcache.delete('Page_' + str(page.num))
                    memcache.delete('Page::' + str(page.name))
                    memcache.delete(page.minisite.name + '/' + page.name)
                    minisite = page.minisite
                    page.delete()
                    minisite.pages = minisite.pages - 1
                    minisite.put()
                    self.redirect('/backstage/minisite/' + minisite.name)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')

class BackstageNewSectionHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        template_values['member'] = member
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            if (member.level == 0):    
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'backstage_new_section.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')
    
    def post(self):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        template_values['member'] = member
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            if (member.level == 0):
                errors = 0
                # Verification: name
                section_name_error = 0
                section_name_error_messages = ['',
                    u'请输入区域名',
                    u'区域名长度不能超过 32 个字符',
                    u'区域名只能由 a-Z 0-9 及 - 和 _ 组成',
                    u'抱歉这个区域名已经存在了']
                section_name = self.request.get('name').strip().lower()
                if (len(section_name) == 0):
                    errors = errors + 1
                    section_name_error = 1
                else:
                    if (len(section_name) > 32):
                        errors = errors + 1
                        section_name_error = 2
                    else:
                        if (re.search('^[a-zA-Z0-9\-\_]+$', section_name)):
                            q = db.GqlQuery('SELECT __key__ FROM Section WHERE name = :1', section_name.lower())
                            if (q.count() > 0):
                                errors = errors + 1
                                section_name_error = 4
                        else:
                            errors = errors + 1
                            section_name_error = 3
                template_values['section_name'] = section_name
                template_values['section_name_error'] = section_name_error
                template_values['section_name_error_message'] = section_name_error_messages[section_name_error]
                # Verification: title
                section_title_error = 0
                section_title_error_messages = ['',
                    u'请输入区域标题',
                    u'区域标题长度不能超过 32 个字符'
                ]
                section_title = self.request.get('title').strip()
                if (len(section_title) == 0):
                    errors = errors + 1
                    section_title_error = 1
                else:
                    if (len(section_title) > 32):
                        errors = errors + 1
                        section_title_error = 2
                template_values['section_title'] = section_title
                template_values['section_title_error'] = section_title_error
                template_values['section_title_error_message'] = section_title_error_messages[section_title_error]
                # Verification: title
                section_title_alternative_error = 0
                section_title_alternative_error_messages = ['',
                    u'请输入区域副标题',
                    u'区域标题长度不能超过 32 个字符'
                ]
                section_title_alternative = self.request.get('title_alternative').strip()
                if (len(section_title_alternative) == 0):
                    errors = errors + 1
                    section_title_alternative_error = 1
                else:
                    if (len(section_title_alternative) > 32):
                        errors = errors + 1
                        section_title_alternative_error = 2
                template_values['section_title_alternative'] = section_title_alternative
                template_values['section_title_alternative_error'] = section_title_alternative_error
                template_values['section_title_alternative_error_message'] = section_title_alternative_error_messages[section_title_alternative_error]
                template_values['errors'] = errors
                if (errors == 0):
                    section = Section()
                    q = db.GqlQuery('SELECT * FROM Counter WHERE name = :1', 'section.max')
                    if (q.count() == 1):
                        counter = q[0]
                        counter.value = counter.value + 1
                    else:
                        counter = Counter()
                        counter.name = 'section.max'
                        counter.value = 1
                    section.num = counter.value
                    section.name = section_name
                    section.title = section_title
                    section.title_alternative = section_title_alternative
                    section.put()
                    counter.put()
                    self.redirect('/backstage')
                else:    
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'backstage_new_section.html')
                    output = template.render(path, template_values)
                    self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')

class BackstageSectionHandler(webapp.RequestHandler):
    def get(self, section_name):
        site = GetSite()
        browser = detect(self.request)
        template_values = {}
        template_values['rnd'] = random.randrange(1, 100)
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            if (member.level == 0):
                template_values['member'] = member
                q = db.GqlQuery("SELECT * FROM Section WHERE name = :1", section_name)
                section = False
                if (q.count() == 1):
                    section = q[0]
                    template_values['section'] = section
                    template_values['page_title'] = site.title + u' › 后台 › ' + section.title
                    template_values['section_name'] = section.name
                    template_values['section_title'] = section.title
                    template_values['section_title_alternative'] = section.title_alternative
                    if section.header:
                        template_values['section_header'] = section.header
                    else:
                        template_values['section_header'] = ''
                    if section.footer:
                        template_values['section_footer'] = section.footer
                    else:
                        template_values['section_footer'] = ''
                else:
                    template_values['section'] = section
                if (section):
                    template_values['section'] = section
                    q2 = db.GqlQuery("SELECT * FROM Node WHERE section_num = :1 ORDER BY last_modified DESC LIMIT 10", section.num)
                    template_values['recent_modified'] = q2
                else:
                    template_values['nodes'] = False
                if browser['ios']:
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'backstage_section.html')
                else:
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_section.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')
    
    def post(self, section_name):
        site = GetSite()
        browser = detect(self.request)
        template_values = {}
        template_values['rnd'] = random.randrange(1, 100)
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if member:
            if member.level == 0:
                template_values['member'] = member
                section = GetKindByName('Section', section_name)
                if section is not False:
                    template_values['section'] = section
                    errors = 0
                    # Verification: name
                    section_name_error = 0
                    section_name_error_messages = ['',
                        u'请输入区域名',
                        u'区域名长度不能超过 32 个字符',
                        u'区域名只能由 a-Z 0-9 及 - 和 _ 组成',
                        u'抱歉这个区域名已经存在了']
                    section_name = self.request.get('name').strip().lower()
                    if (len(section_name) == 0):
                        errors = errors + 1
                        section_name_error = 1
                    else:
                        if (len(section_name) > 32):
                            errors = errors + 1
                            section_name_error = 2
                        else:
                            if (re.search('^[a-zA-Z0-9\-\_]+$', section_name)):
                                q = db.GqlQuery('SELECT * FROM Section WHERE name = :1', section_name.lower())
                                if (q.count() > 0):
                                    for possible_conflict in q:
                                        if possible_conflict.num != section.num:
                                            errors = errors + 1
                                            section_name_error = 4
                            else:
                                errors = errors + 1
                                section_name_error = 3
                    template_values['section_name'] = section_name
                    template_values['section_name_error'] = section_name_error
                    template_values['section_name_error_message'] = section_name_error_messages[section_name_error]
                    # Verification: title
                    section_title_error = 0
                    section_title_error_messages = ['',
                        u'请输入区域标题',
                        u'区域标题长度不能超过 32 个字符'
                    ]
                    section_title = self.request.get('title').strip()
                    if (len(section_title) == 0):
                        errors = errors + 1
                        section_title_error = 1
                    else:
                        if (len(section_title) > 32):
                            errors = errors + 1
                            section_title_error = 2
                    template_values['section_title'] = section_title
                    template_values['section_title_error'] = section_title_error
                    template_values['section_title_error_message'] = section_title_error_messages[section_title_error]
                    # Verification: title_alternative
                    section_title_alternative_error = 0
                    section_title_alternative_error_messages = ['',
                        u'请输入区域副标题',
                        u'区域标题长度不能超过 32 个字符'
                    ]
                    section_title_alternative = self.request.get('title_alternative').strip()
                    if (len(section_title_alternative) == 0):
                        errors = errors + 1
                        section_title_alternative_error = 1
                    else:
                        if (len(section_title_alternative) > 32):
                            errors = errors + 1
                            section_title_alternative_error = 2
                    template_values['section_title_alternative'] = section_title_alternative
                    template_values['section_title_alternative_error'] = section_title_alternative_error
                    template_values['section_title_alternative_error_message'] = section_title_alternative_error_messages[section_title_alternative_error]
                    # Verification: header
                    section_header_error = 0
                    section_header_error_messages = ['',
                        u'区域头部信息不能超过 1000 个字符'
                    ]
                    section_header = self.request.get('header').strip()
                    if len(section_header) > 1000:
                        errors = errors + 1
                        section_header_error = 1
                    template_values['section_header'] = section_header
                    template_values['section_header_error'] = section_header_error
                    template_values['section_header_error_message'] = section_header_error_messages[section_header_error]
                    # Verification: footer
                    section_footer_error = 0
                    section_footer_error_messages = ['',
                        u'区域尾部信息不能超过 1000 个字符'
                    ]
                    section_footer = self.request.get('footer').strip()
                    if len(section_footer) > 1000:
                        errors = errors + 1
                        section_footer_error = 1
                    template_values['section_footer'] = section_footer
                    template_values['section_footer_error'] = section_footer_error
                    template_values['section_footer_error_message'] = section_footer_error_messages[section_footer_error]
                    template_values['errors'] = errors
                    if (errors == 0):
                        memcache.delete('Section::' + section.name)
                        section.name = section_name
                        section.title = section_title
                        section.title_alternative = section_title_alternative
                        section.header = section_header
                        section.footer = section_footer
                        section.put()
                        memcache.delete('Section_' + str(section.num))
                        memcache.delete('Section::' + section_name)
                        self.redirect('/backstage')
                    else:
                        path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_section.html')
                        output = template.render(path, template_values)
                        self.response.out.write(output)
                else:
                    self.redirect('/backstage')
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')

class BackstageNewNodeHandler(webapp.RequestHandler):
    def get(self, section_name):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            if (member.level == 0):
                template_values['member'] = CheckAuth(self)
                q = db.GqlQuery("SELECT * FROM Section WHERE name = :1", section_name)
                if (q.count() == 1):
                    template_values['section'] = q[0]
                else:
                    template_values['section'] = False
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'backstage_new_node.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')

    def post(self, section_name):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            if (member.level == 0):        
                template_values['member'] = member
                section = False
                q = db.GqlQuery("SELECT * FROM Section WHERE name = :1", section_name)
                if (q.count() == 1):
                    section = q[0]
                    template_values['section'] = section
                else:
                    template_values['section'] = False
                errors = 0
                # Verification: name
                node_name_error = 0
                node_name_error_messages = ['',
                    u'请输入节点名',
                    u'节点名长度不能超过 32 个字符',
                    u'节点名只能由 a-Z 0-9 及 - 和 _ 组成',
                    u'抱歉这个节点名已经存在了']
                node_name = self.request.get('name').strip().lower()
                if (len(node_name) == 0):
                    errors = errors + 1
                    node_name_error = 1
                else:
                    if (len(node_name) > 32):
                        errors = errors + 1
                        node_name_error = 2
                    else:
                        if (re.search('^[a-zA-Z0-9\-\_]+$', node_name)):
                            q = db.GqlQuery('SELECT __key__ FROM Node WHERE name = :1', node_name.lower())
                            if (q.count() > 0):
                                errors = errors + 1
                                node_name_error = 4
                        else:
                            errors = errors + 1
                            node_name_error = 3
                template_values['node_name'] = node_name
                template_values['node_name_error'] = node_name_error
                template_values['node_name_error_message'] = node_name_error_messages[node_name_error]
                # Verification: title
                node_title_error = 0
                node_title_error_messages = ['',
                    u'请输入节点标题',
                    u'节点标题长度不能超过 32 个字符'
                ]
                node_title = self.request.get('title').strip()
                if (len(node_title) == 0):
                    errors = errors + 1
                    node_title_error = 1
                else:
                    if (len(node_title) > 32):
                        errors = errors + 1
                        node_title_error = 2
                template_values['node_title'] = node_title
                template_values['node_title_error'] = node_title_error
                template_values['node_title_error_message'] = node_title_error_messages[node_title_error]
                # Verification: title
                node_title_alternative_error = 0
                node_title_alternative_error_messages = ['',
                    u'请输入节点副标题',
                    u'节点标题长度不能超过 32 个字符'
                ]
                node_title_alternative = self.request.get('title_alternative').strip()
                if (len(node_title_alternative) == 0):
                    errors = errors + 1
                    node_title_alternative_error = 1
                else:
                    if (len(node_title_alternative) > 32):
                        errors = errors + 1
                        node_title_alternative_error = 2
                template_values['node_title_alternative'] = node_title_alternative
                template_values['node_title_alternative_error'] = node_title_alternative_error
                template_values['node_title_alternative_error_message'] = node_title_alternative_error_messages[node_title_alternative_error]
                template_values['errors'] = errors
                if (errors == 0):
                    node = Node()
                    q = db.GqlQuery('SELECT * FROM Counter WHERE name = :1', 'node.max')
                    if (q.count() == 1):
                        counter = q[0]
                        counter.value = counter.value + 1
                    else:
                        counter = Counter()
                        counter.name = 'node.max'
                        counter.value = 1
                    node.num = counter.value
                    node.section_num = section.num
                    node.name = node_name
                    node.title = node_title
                    node.title_alternative = node_title_alternative
                    node.put()
                    counter.put()
                    memcache.delete('index_categories')
                    memcache.delete('home_nodes_new')
                    self.redirect('/backstage/node/' + node.name)
                else:    
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'backstage_new_node.html')
                    output = template.render(path, template_values)
                    self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')


class BackstageNodeHandler(webapp.RequestHandler):
    def get(self, node_name):
        site = GetSite()
        browser = detect(self.request)
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            if (member.level == 0):
                template_values['member'] = member
                q = db.GqlQuery("SELECT * FROM Node WHERE name = :1", node_name)
                if (q.count() == 1):
                    node = q[0]
                    if node.parent_node_name is None:
                        siblings = []
                    else:
                        siblings = db.GqlQuery("SELECT * FROM Node WHERE parent_node_name = :1 AND name != :2", node.parent_node_name, node.name)
                    template_values['siblings'] = siblings
                    template_values['node'] = node
                    template_values['node_name'] = node.name
                    template_values['node_title'] = node.title
                    template_values['node_title_alternative'] = q[0].title_alternative
                    if q[0].category is None:
                        template_values['node_category'] = ''
                    else:
                        template_values['node_category'] = q[0].category
                    if q[0].parent_node_name is None:
                        template_values['node_parent_node_name'] = ''
                    else:
                        template_values['node_parent_node_name'] = q[0].parent_node_name
                    if q[0].header is None:
                        template_values['node_header'] = ''
                    else:
                        template_values['node_header'] = q[0].header
                    if q[0].footer is None:
                        template_values['node_footer'] = ''
                    else:
                        template_values['node_footer'] = q[0].footer
                    if q[0].sidebar is None:
                        template_values['node_sidebar'] = ''
                    else:
                        template_values['node_sidebar'] = q[0].sidebar
                    if q[0].sidebar_ads is None:
                        template_values['node_sidebar_ads'] = ''
                    else:
                        template_values['node_sidebar_ads'] = q[0].sidebar_ads
                    template_values['node_topics'] = q[0].topics
                else:
                    template_values['node'] = False
                section = GetKindByNum('Section', node.section_num)
                template_values['section'] = section
                if section is not False:
                    template_values['page_title'] = site.title + u' › ' + l10n.backstage.decode('utf-8') + u' › ' + section.title + u' › ' + node.title
                if browser['ios']:
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'backstage_node.html')
                else:
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_node.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')
    
    def post(self, node_name):
        site = GetSite()
        browser = detect(self.request)
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            if (member.level == 0):        
                template_values['member'] = member
                node = False
                q = db.GqlQuery("SELECT * FROM Node WHERE name = :1", node_name)
                if (q.count() == 1):
                    node = q[0]
                    template_values['node'] = q[0]
                    template_values['node_name'] = q[0].name
                    template_values['node_title'] = q[0].title
                    template_values['node_title_alternative'] = q[0].title_alternative
                    if q[0].category is None:
                        template_values['node_category'] = ''
                    else:
                        template_values['node_category'] = q[0].category
                    if q[0].parent_node_name is None:
                        template_values['node_parent_node_name'] = ''
                    else:
                        template_values['node_parent_node_name'] = q[0].parent_node_name
                    if q[0].header is None:
                        template_values['node_header'] = ''
                    else:
                        template_values['node_header'] = q[0].header
                    if q[0].footer is None:
                        template_values['node_footer'] = ''
                    else:
                        template_values['node_footer'] = q[0].footer
                    if q[0].sidebar is None:
                        template_values['node_sidebar'] = ''
                    else:
                        template_values['node_sidebar'] = q[0].sidebar
                    if q[0].sidebar_ads is None:
                        template_values['node_sidebar_ads'] = ''
                    else:
                        template_values['node_sidebar_ads'] = q[0].sidebar_ads
                    template_values['node_topics'] = q[0].topics
                else:
                    template_values['node'] = False
                section = False
                q2 = db.GqlQuery("SELECT * FROM Section WHERE num = :1", q[0].section_num)
                if (q2.count() == 1):
                    section = q2[0]
                    template_values['section'] = q2[0]
                else:
                    template_values['section'] = False
                if section is not False:
                    template_values['page_title'] = site.title + u' › ' + l10n.backstage.decode('utf-8') + u' › ' + section.title + u' › ' + node.title
                errors = 0
                # Verification: name
                node_name_error = 0
                node_name_error_messages = ['',
                    u'请输入节点名',
                    u'节点名长度不能超过 32 个字符',
                    u'节点名只能由 a-Z 0-9 及 - 和 _ 组成',
                    u'抱歉这个节点名已经存在了']
                node_name = self.request.get('name').strip().lower()
                if (len(node_name) == 0):
                    errors = errors + 1
                    node_name_error = 1
                else:
                    if (len(node_name) > 32):
                        errors = errors + 1
                        node_name_error = 2
                    else:
                        if (re.search('^[a-zA-Z0-9\-\_]+$', node_name)):
                            q = db.GqlQuery('SELECT * FROM Node WHERE name = :1 AND num != :2', node_name.lower(), node.num)
                            if (q.count() > 0):
                                errors = errors + 1
                                node_name_error = 4
                        else:
                            errors = errors + 1
                            node_name_error = 3
                template_values['node_name'] = node_name
                template_values['node_name_error'] = node_name_error
                template_values['node_name_error_message'] = node_name_error_messages[node_name_error]
                # Verification: title
                node_title_error = 0
                node_title_error_messages = ['',
                    u'请输入节点标题',
                    u'节点标题长度不能超过 32 个字符'
                ]
                node_title = self.request.get('title').strip()
                if (len(node_title) == 0):
                    errors = errors + 1
                    node_title_error = 1
                else:
                    if (len(node_title) > 32):
                        errors = errors + 1
                        node_title_error = 2
                template_values['node_title'] = node_title
                template_values['node_title_error'] = node_title_error
                template_values['node_title_error_message'] = node_title_error_messages[node_title_error]
                # Verification: title_alternative
                node_title_alternative_error = 0
                node_title_alternative_error_messages = ['',
                    u'请输入节点副标题',
                    u'节点标题长度不能超过 32 个字符'
                ]
                node_title_alternative = self.request.get('title_alternative').strip()
                if (len(node_title_alternative) == 0):
                    errors = errors + 1
                    node_title_alternative_error = 1
                else:
                    if (len(node_title_alternative) > 32):
                        errors = errors + 1
                        node_title_alternative_error = 2
                template_values['node_title_alternative'] = node_title_alternative
                template_values['node_title_alternative_error'] = node_title_alternative_error
                template_values['node_title_alternative_error_message'] = node_title_alternative_error_messages[node_title_alternative_error]
                # Verification: node_category
                node_category = self.request.get('category').strip()
                template_values['node_category'] = node_category
                # Verification: node_parent_node_name
                node_parent_node_name = self.request.get('parent_node_name').strip()
                template_values['node_parent_node_name'] = node_parent_node_name
                # Verification: node_header
                node_header = self.request.get('header').strip()
                template_values['node_header'] = node_header
                # Verification: node_footer
                node_footer = self.request.get('footer').strip()
                template_values['node_footer'] = node_footer
                # Verification: node_sidebar
                node_sidebar = self.request.get('sidebar').strip()
                template_values['node_sidebar'] = node_sidebar
                # Verification: node_sidebar_ads
                node_sidebar_ads = self.request.get('sidebar_ads').strip()
                template_values['node_sidebar_ads'] = node_sidebar_ads
                template_values['errors'] = errors
                if (errors == 0):
                    node.name = node_name
                    node.title = node_title
                    node.title_alternative = node_title_alternative
                    node.category = node_category
                    node.parent_node_name = node_parent_node_name
                    node.header = node_header
                    node.footer = node_footer
                    node.sidebar = node_sidebar
                    node.sidebar_ads = node_sidebar_ads
                    node.put()
                    memcache.delete('Node_' + str(node.num))
                    memcache.delete('Node::' + node.name)
                    memcache.delete('index_categories')
                    memcache.delete('home_nodes_new')
                    self.redirect('/backstage/section/' + section.name)
                else:    
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'backstage_node.html')
                    output = template.render(path, template_values)
                    self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')


class BackstageNodeAvatarHandler(BaseHandler):
    def get(self, node_name):
        self.redirect('/backstage/node/' + node_name)
    
    def post(self, node_name):
        if self.member:
            if self.member.level == 0:
                node = GetKindByName('Node', node_name)
                if node is None:
                    return self.redirect('/backstage')
                dest = '/backstage/node/' + node.name
                timestamp = str(int(time.time()))
                try:
                    avatar = self.request.get('avatar')
                except:
                    return self.redirect(dest)
                if avatar is None:
                    return self.redirect(dest)
                avatar_len = len(avatar)
                if avatar_len == 0:
                    return self.redirect(dest)
                avatar_73 = images.resize(avatar, 73, 73)
                avatar_48 = images.resize(avatar, 48, 48)
                avatar_24 = images.resize(avatar, 24, 24)
                # Large 73x73
                q1 = db.GqlQuery("SELECT * FROM Avatar WHERE name = :1", 'node_' + str(node.num) + '_large')
                if (q1.count() == 1):
                    avatar_large = q1[0]
                    avatar_large.content = db.Blob(avatar_73)
                    avatar_large.put()
                else:
                    qc1 = db.GqlQuery("SELECT * FROM Counter WHERE name = :1", 'avatar.max')
                    if (qc1.count() == 1):
                        counter1 = qc1[0]
                        counter1.value = counter1.value + 1
                    else:
                        counter1 = Counter()
                        counter1.name = 'avatar.max'
                        counter1.value = 1
                    counter1.put()
                    avatar_large = Avatar()
                    avatar_large.name = 'node_' + str(node.num) + '_large'
                    avatar_large.content = db.Blob(avatar_73)
                    avatar_large.num = counter1.value
                    avatar_large.put()
                node.avatar_large_url = '/navatar/' + str(node.num) + '/large?r=' + timestamp
                node.put()
                # Normal 48x48
                q2 = db.GqlQuery("SELECT * FROM Avatar WHERE name = :1", 'node_' + str(node.num) + '_normal')
                if (q2.count() == 1):
                    avatar_normal = q2[0]
                    avatar_normal.content = db.Blob(avatar_48)
                    avatar_normal.put()
                else:
                    qc2 = db.GqlQuery("SELECT * FROM Counter WHERE name = :1", 'avatar.max')
                    if (qc2.count() == 1):
                        counter2 = qc2[0]
                        counter2.value = counter2.value + 1
                    else:
                        counter2 = Counter()
                        counter2.name = 'avatar.max'
                        counter2.value = 1
                    counter2.put()
                    avatar_normal = Avatar()
                    avatar_normal.name = 'node_' + str(node.num) + '_normal'
                    avatar_normal.content = db.Blob(avatar_48)
                    avatar_normal.num = counter2.value
                    avatar_normal.put()
                node.avatar_normal_url = '/navatar/' + str(node.num) + '/normal?r=' + timestamp
                node.put() 
                # Mini 24x24
                q3 = db.GqlQuery("SELECT * FROM Avatar WHERE name = :1", 'node_' + str(node.num) + '_mini')
                if (q3.count() == 1):
                    avatar_mini = q3[0]
                    avatar_mini.content = db.Blob(avatar_24)
                    avatar_mini.put()
                else:
                    qc3 = db.GqlQuery("SELECT * FROM Counter WHERE name = :1", 'avatar.max')
                    if (qc3.count() == 1):
                        counter3 = qc3[0]
                        counter3.value = counter3.value + 1
                    else:
                        counter3 = Counter()
                        counter3.name = 'avatar.max'
                        counter3.value = 1
                    counter3.put()
                    avatar_mini = Avatar()
                    avatar_mini.name = 'node_' + str(node.num) + '_mini'
                    avatar_mini.content = db.Blob(avatar_24)
                    avatar_mini.num = counter3.value
                    avatar_mini.put()
                node.avatar_mini_url = '/navatar/' + str(node.num) + '/mini?r=' + timestamp
                node.put()
                # Upload to MobileMe
                use_this = False
                if config.mobileme_enabled and use_this:
                    headers = {'Authorization' : 'Basic ' + base64.b64encode(config.mobileme_username + ':' + config.mobileme_password)}
                    host = 'idisk.me.com'
                    # Sharding
                    timestamp = str(int(time.time()))
                    shard = node.num % 31
                    root = '/' + config.mobileme_username + '/Web/Sites/v2ex/navatars/' + str(shard)
                    root_mini = root + '/mini'
                    root_normal = root + '/normal'
                    root_large = root + '/large'
                    h = httplib.HTTPConnection(host)
                    # Mini
                    h.request('PUT', root_mini + '/' + str(node.num) + '.png', str(avatar_24), headers)
                    response = h.getresponse()
                    if response.status == 201 or response.status == 204:
                        node.avatar_mini_url = 'http://web.me.com/' + config.mobileme_username + '/v2ex/navatars/' + str(shard) + '/mini/' + str(node.num) + '.png?r=' + timestamp
                    # Normal
                    h.request('PUT', root_normal + '/' + str(node.num) + '.png', str(avatar_48), headers)
                    response = h.getresponse()
                    if response.status == 201 or response.status == 204:
                        node.avatar_normal_url = 'http://web.me.com/' + config.mobileme_username + '/v2ex/navatars/' + str(shard) + '/normal/' + str(node.num) + '.png?r=' + timestamp
                    # Large
                    h.request('PUT', root_large + '/' + str(node.num) + '.png', str(avatar_73), headers)
                    response = h.getresponse()
                    if response.status == 201 or response.status == 204:
                        node.avatar_large_url = 'http://web.me.com/' + config.mobileme_username + '/v2ex/navatars/' + str(shard) + '/large/' + str(node.num) + '.png?r=' + timestamp
                    node.put()
                memcache.set('Node_' + str(node.num), node, 86400 * 14)
                memcache.set('Node::' + node.name, node, 86400 * 14)
                memcache.delete('Avatar::node_' + str(node.num) + '_large')
                memcache.delete('Avatar::node_' + str(node.num) + '_normal')
                memcache.delete('Avatar::node_' + str(node.num) + '_mini')
                #self.session['message'] = '新节点头像设置成功'
                self.redirect(dest)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')
        

class BackstageRemoveReplyHandler(webapp.RequestHandler):
    def get(self, reply_key):
        member = CheckAuth(self)
        t = self.request.get('t')
        if (member):
            if (member.level == 0) and (str(member.created_ts) == str(t)):
                reply = db.get(db.Key(reply_key))
                if reply:
                    topic = reply.topic
                    reply.delete()
                    q = db.GqlQuery("SELECT __key__ FROM Reply WHERE topic = :1", topic)
                    topic.replies = q.count()
                    if (topic.replies == 0):
                        topic.last_reply_by = None
                    topic.put()
                    pages = 1
                    memcache.delete('Topic_' + str(topic.num))
                    memcache.delete('topic_' + str(topic.num) + '_replies_desc_compressed')
                    memcache.delete('topic_' + str(topic.num) + '_replies_asc_compressed')
                    memcache.delete('topic_' + str(topic.num) + '_replies_filtered_compressed')
                    memcache.delete('topic_' + str(topic.num) + '_replies_desc_rendered_desktop_' + str(pages))
                    memcache.delete('topic_' + str(topic.num) + '_replies_asc_rendered_desktop_' + str(pages))
                    memcache.delete('topic_' + str(topic.num) + '_replies_filtered_rendered_desktop_' + str(pages))
                    memcache.delete('topic_' + str(topic.num) + '_replies_desc_rendered_ios_' + str(pages))
                    memcache.delete('topic_' + str(topic.num) + '_replies_asc_rendered_ios_' + str(pages))
                    memcache.delete('topic_' + str(topic.num) + '_replies_filtered_rendered_ios_' + str(pages))
                    self.redirect('/t/' + str(topic.num))
                else:
                    self.redirect('/')
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')

class BackstageTidyReplyHandler(webapp.RequestHandler):
    def get(self, reply_num):
        member = CheckAuth(self)
        if (member):
            if (member.level == 0):
                q = db.GqlQuery("SELECT * FROM Reply WHERE num = :1", int(reply_num))
                if (q.count() == 1):
                    reply = q[0]
                    topic_num = reply.topic_num
                    q2 = db.GqlQuery("SELECT * FROM Member WHERE username_lower = :1", reply.created_by.lower())
                    member = q2[0]
                    reply.member = member
                    reply.member_num = member.num
                    q3 = db.GqlQuery("SELECT * FROM Topic WHERE num = :1", topic_num)
                    topic = q3[0]
                    # Begin to do real stuff
                    reply2 = Reply(parent=topic)
                    reply2.num = reply.num
                    reply2.content = reply.content
                    reply2.topic = topic
                    reply2.topic_num = topic.num
                    reply2.member = reply.member
                    reply2.member_num = reply.member_num
                    reply2.created_by = reply.created_by
                    reply2.source = reply.source
                    reply2.created = reply.created
                    reply2.last_modified = reply.last_modified
                    reply2.put()
                    reply.delete()
                    self.redirect('/t/' + str(topic_num))
                else:
                    self.redirect('/')
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')
            
class BackstageTidyTopicHandler(webapp.RequestHandler):
    def get(self, topic_num):
        member = CheckAuth(self)
        if (member):
            if (member.level == 0):
                q = db.GqlQuery("SELECT * FROM Topic WHERE num = :1", int(topic_num))
                if (q.count() == 1):
                    topic = q[0]
                    q2 = db.GqlQuery("SELECT * FROM Member WHERE num = :1", topic.member_num)
                    member = q2[0]
                    topic.member = member
                    q3 = db.GqlQuery("SELECT * FROM Node WHERE num = :1", topic.node_num)
                    node = q3[0]
                    topic.node = node
                    topic.put()
                    memcache.delete('Topic_' + str(topic.num))
                    self.redirect('/t/' + str(topic.num))
                else:
                    self.redirect('/')
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')

class BackstageDeactivateUserHandler(webapp.RequestHandler):
    def get(self, key):
        member = CheckAuth(self)
        t = self.request.get('t')
        if member:
            if (member.level == 0) and (str(member.created_ts) == str(t)):
                one = db.get(db.Key(key))
                if one:
                    if one.num != 1:
                        memcache.delete(one.auth)
                        one.deactivated = int(time.time())
                        one.password = hashlib.sha1(str(time.time())).hexdigest()
                        one.auth = hashlib.sha1(str(one.num) + ':' + one.password).hexdigest()
                        one.newbie = 1
                        one.noob = 1
                        one.put()
                        memcache.delete('Member_' + str(one.num))
                        return self.redirect('/member/' + one.username)
        return self.redirect('/')               

class BackstageMoveTopicHandler(webapp.RequestHandler):
    def get(self, key):
        template_values = {}
        site = GetSite()
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        topic = db.get(db.Key(key))
        can_move = False
        ttl = 0
        if member:
            if member.level == 0:
                can_move = True
            if topic:
                if topic.member_num == member.num:
                    now = datetime.datetime.now()
                    ttl = 300 - int((now - topic.created).seconds)
                    if ttl > 0:
                        can_move = True
                        template_values['ttl'] = ttl
        template_values['can_move'] = can_move
        if member:
            template_values['member'] = member
            if can_move:
                template_values['page_title'] = site.title + u' › 移动主题'
                template_values['site'] = site
                if topic is not None:
                    node = topic.node
                    template_values['topic'] = topic
                    template_values['node'] = node
                    template_values['system_version'] = SYSTEM_VERSION
                    themes = os.listdir(os.path.join(os.path.dirname(__file__), 'tpl', 'themes'))
                    template_values['themes'] = themes
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_move_topic.html')
                    output = template.render(path, template_values)
                    self.response.out.write(output)
                else:
                    self.redirect('/')
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')
    
    def post(self, key):
        template_values = {}
        site = GetSite()
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        topic = db.get(db.Key(key))
        can_move = False
        ttl = 0
        if member:
            if member.level == 0:
                can_move = True
            if topic:
                if topic.member_num == member.num:
                    now = datetime.datetime.now()
                    ttl = 300 - int((now - topic.created).seconds)
                    if ttl > 0:
                        can_move = True
                        template_values['ttl'] = ttl
        template_values['can_move'] = can_move
        if member:
            template_values['member'] = member
            if can_move:
                template_values['page_title'] = site.title + u' › 移动主题'
                template_values['site'] = site
                if topic is not None:
                    errors = 0
                    node = topic.node
                    template_values['topic'] = topic
                    template_values['node'] = node
                    template_values['system_version'] = SYSTEM_VERSION
                    destination = self.request.get('destination')
                    if destination is not None:
                        node_new = GetKindByName('Node', destination)
                        if node_new is not False:
                            node_new = db.get(node_new.key())
                            node_old = topic.node
                            node_old.topics = node_old.topics - 1
                            node_old.put()
                            node_new.topics = node_new.topics + 1
                            node_new.put()
                            topic.node = node_new
                            topic.node_num = node_new.num
                            topic.node_name = node_new.name
                            topic.node_title = node_new.title
                            topic.put()
                            memcache.delete('Topic_' + str(topic.num))
                            memcache.delete('Node_' + str(node_old.num))
                            memcache.delete('Node_' + str(node_new.num))
                            memcache.delete('Node::' + str(node_old.name))
                            memcache.delete('Node::' + str(node_new.name))
                            memcache.delete('q_latest_16')
                            memcache.delete('home_rendered')
                            memcache.delete('home_rendered_mobile')
                            self.redirect('/t/' + str(topic.num))
                        else:
                            errors = errors + 1
                    else:
                        errors = errors + 1
                    if errors > 0:
                        themes = os.listdir(os.path.join(os.path.dirname(__file__), 'tpl', 'themes'))
                        template_values['themes'] = themes
                        path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_move_topic.html')
                        output = template.render(path, template_values)
                        self.response.out.write(output)
                else:
                    self.redirect('/')
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')
        
class BackstageSiteHandler(webapp.RequestHandler):
    def get(self):
        template_values = {}
        site = GetSite()
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if member:
            if member.level == 0:
                template_values['page_title'] = site.title + u' › 站点设置'
                template_values['site'] = site
                template_values['site_title'] = site.title
                template_values['site_slogan'] = site.slogan
                template_values['site_domain'] = site.domain
                template_values['site_description'] = site.description
                if site.home_categories is not None:
                    template_values['site_home_categories'] = site.home_categories
                else:
                    template_values['site_home_categories'] = ''
                if site.analytics is not None:
                    template_values['site_analytics'] = site.analytics
                else:
                    template_values['site_analytics'] = ''
                if site.topic_view_level is not None:
                    template_values['site_topic_view_level'] = site.topic_view_level
                else:
                    template_values['site_topic_view_level'] = -1
                if site.topic_create_level is not None:
                    template_values['site_topic_create_level'] = site.topic_create_level
                else:
                    template_values['site_topic_create_level'] = 1000
                if site.topic_reply_level is not None:
                    template_values['site_topic_reply_level'] = site.topic_reply_level
                else:
                    template_values['site_topic_reply_level'] = 1000
                if site.meta is not None:
                    template_values['site_meta'] = site.meta
                else:
                    template_values['site_meta'] = ''
                if site.home_top is not None:
                    template_values['site_home_top'] = site.home_top
                else:
                    template_values['site_home_top'] = ''
                if site.theme is not None:
                    template_values['site_theme'] = site.theme
                else:
                    template_values['site_theme'] = 'default'
                if site.data_migration_mode is not None:
                    template_values['site_data_migration_mode'] = site.data_migration_mode
                else:
                    template_values['site_data_migration_mode'] = 0
                s = GetLanguageSelect(site.l10n)
                template_values['s'] = s
                template_values['member'] = member
                template_values['system_version'] = SYSTEM_VERSION
                themes = os.listdir(os.path.join(os.path.dirname(__file__), 'tpl', 'themes'))
                template_values['themes'] = themes
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_site.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
        else:
            self.redirect('/')
    
    def post(self):
        template_values = {}
        site = GetSite()
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if member:
            if member.level == 0:
                template_values['page_title'] = site.title + u' › 站点设置'
                template_values['site'] = site
                template_values['member'] = member
                template_values['system_version'] = SYSTEM_VERSION
                errors = 0
                # Verification: title (required)
                site_title_error = 0
                site_title_error_messages = ['',
                    u'请输入站点名',
                    u'站点名长度不能超过 40 个字符'
                ]
                site_title = self.request.get('title').strip()
                if (len(site_title) == 0):
                    errors = errors + 1
                    site_title_error = 1    
                else:
                    if (len(site_title) > 40):
                        errors = errors + 1
                        site_title_error = 1
                template_values['site_title'] = site_title
                template_values['site_title_error'] = site_title_error
                template_values['site_title_error_message'] = site_title_error_messages[site_title_error]
                # Verification: slogan (required)
                site_slogan_error = 0
                site_slogan_error_messages = ['',
                    u'请输入站点标语',
                    u'站点标语长度不能超过 140 个字符'
                ]
                site_slogan = self.request.get('slogan').strip()
                if (len(site_slogan) == 0):
                    errors = errors + 1
                    site_slogan_error = 1    
                else:
                    if (len(site_slogan) > 140):
                        errors = errors + 1
                        site_slogan_error = 1
                template_values['site_slogan'] = site_slogan
                template_values['site_slogan_error'] = site_slogan_error
                template_values['site_slogan_error_message'] = site_slogan_error_messages[site_slogan_error]
                # Verification: domain (required)
                site_domain_error = 0
                site_domain_error_messages = ['',
                    u'请输入主要域名',
                    u'主要域名长度不能超过 40 个字符'
                ]
                site_domain = self.request.get('domain').strip()
                if (len(site_domain) == 0):
                    errors = errors + 1
                    site_domain_error = 1    
                else:
                    if (len(site_domain) > 40):
                        errors = errors + 1
                        site_domain_error = 1
                template_values['site_domain'] = site_domain
                template_values['site_domain_error'] = site_domain_error
                template_values['site_domain_error_message'] = site_domain_error_messages[site_domain_error]
                # Verification: description (required)
                site_description_error = 0
                site_description_error_messages = ['',
                    u'请输入站点简介',
                    u'站点简介长度不能超过 200 个字符'
                ]
                site_description = self.request.get('description').strip()
                if (len(site_description) == 0):
                    errors = errors + 1
                    site_description_error = 1    
                else:
                    if (len(site_description) > 200):
                        errors = errors + 1
                        site_description_error = 1
                template_values['site_description'] = site_description
                template_values['site_description_error'] = site_description_error
                template_values['site_description_error_message'] = site_description_error_messages[site_description_error]
                # Verification: analytics (optional)
                site_analytics_error = 0
                site_analytics_error_messages = ['',
                    u'Analytics ID 格式不正确'
                ]
                site_analytics = self.request.get('analytics').strip()
                if len(site_analytics) > 0:
                    if re.findall('^UA\-[0-9]+\-[0-9]+$', site_analytics):
                        site_analytics_error = 0
                    else:
                        errors = errors + 1
                        site_analytics_error = 1
                else:
                    site_analytics = ''
                template_values['site_analytics'] = site_analytics
                template_values['site_analytics_error'] = site_analytics_error
                template_values['site_analytics_error_message'] = site_analytics_error_messages[site_analytics_error]
                # Verification: l10n (required)
                site_l10n = self.request.get('l10n').strip()
                supported = GetSupportedLanguages()
                if site_l10n == '':
                    site_l10n = site.l10n
                else:
                    if site_l10n not in supported:
                        site_l10n = site.l10n
                s = GetLanguageSelect(site_l10n)
                template_values['s'] = s
                template_values['site_l10n'] = site_l10n
                # Verification: home_categories (optional)
                site_home_categories_error = 0
                site_home_categories_error_messages = ['',
                    u'首页分类信息不要超过 2000 个字符'
                ]
                site_home_categories = self.request.get('home_categories').strip()
                site_home_categories_length = len(site_home_categories)
                if len(site_home_categories) > 0:
                    if site_home_categories_length > 2000:
                        errors = errors + 1
                        site_home_categories_error = 1
                else:
                    site_home_categories = ''
                template_values['site_home_categories'] = site_home_categories
                template_values['site_home_categories_error'] = site_home_categories_error
                template_values['site_home_categories_error_message'] = site_home_categories_error_messages[site_home_categories_error]
                # Verification: topic_view_level (default=-1)
                site_topic_view_level = self.request.get('topic_view_level')
                try:
                    site_topic_view_level = int(site_topic_view_level)
                    if site_topic_view_level < -1:
                        site_topic_view_level = -1
                except:
                    site_topic_view_level = -1
                template_values['site_topic_view_level'] = site_topic_view_level
                # Verification: topic_create_level (default=1000)
                site_topic_create_level = self.request.get('topic_create_level')
                try:
                    site_topic_create_level = int(site_topic_create_level)
                    if site_topic_create_level < -1:
                        site_topic_create_level = 1000
                except:
                    site_topic_create_level = 1000
                template_values['site_topic_create_level'] = site_topic_create_level
                # Verification: topic_reply_level (default=1000)
                site_topic_reply_level = self.request.get('topic_reply_level')
                try:
                    site_topic_reply_level = int(site_topic_reply_level)
                    if site_topic_reply_level < -1:
                        site_topic_reply_level = 1000
                except:
                    site_topic_reply_level = 1000
                template_values['site_topic_reply_level'] = site_topic_reply_level
                # Verification: meta
                site_meta = self.request.get('meta')
                template_values['site_meta'] = site_meta
                # Verification: home_top
                site_home_top = self.request.get('home_top')
                template_values['site_home_top'] = site_home_top
                # Verification: theme
                site_theme = self.request.get('theme')
                themes = os.listdir(os.path.join(os.path.dirname(__file__), 'tpl', 'themes'))
                template_values['themes'] = themes
                if site_theme in themes:
                    template_values['site_theme'] = site_theme
                else:
                    site_theme = 'default'
                    template_values['site_theme'] = site_theme
                # Verification: data_migration_mode
                site_data_migration_mode = self.request.get('data_migration_mode')
                if site_data_migration_mode == 'on':
                    template_values['site_data_migration_mode'] = 1
                else:
                    template_values['site_data_migration_mode'] = 0
                
                template_values['errors'] = errors
                
                if errors == 0:
                    site.title = site_title
                    site.slogan = site_slogan
                    site.domain = site_domain
                    site.description = site_description
                    if site_home_categories != '':
                        site.home_categories = site_home_categories
                    if site_analytics != '':
                        site.analytics = site_analytics
                    site.l10n = site_l10n
                    site.topic_view_level = site_topic_view_level
                    site.topic_create_level = site_topic_create_level
                    site.topic_reply_level = site_topic_reply_level
                    site.meta = site_meta
                    site.home_top = site_home_top
                    site.theme = site_theme
                    site.data_migration_mode = template_values['site_data_migration_mode']
                    site.put()
                    memcache.delete('index_categories')
                    template_values['message'] = l10n.site_settings_updated;
                    template_values['site'] = site
                    memcache.delete('site')
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_site.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
        else:
            self.redirect('/')

class BackstageTopicHandler(webapp.RequestHandler):
    def get(self):
        template_values = {}
        site = GetSite()
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if member:
            if member.level == 0:
                template_values['page_title'] = site.title + u' › ' + l10n.backstage.decode('utf-8') + u' › ' + l10n.topic_settings.decode('utf-8')
                template_values['site'] = site
                template_values['site_use_topic_types'] = site.use_topic_types
                if site.topic_types is None:
                    template_values['site_topic_types'] = ''
                else:
                    template_values['site_topic_types'] = site.topic_types
                if site.use_topic_types is not True:
                    s = '<select name="use_topic_types"><option value="1">Enabled</option><option value="0" selected="selected">Disabled</option></select>'
                else:
                    s = '<select name="use_topic_types"><option value="1" selected="selected">Enabled</option><option value="0">Disabled</option></select>'
                template_values['s'] = s
                template_values['member'] = member
                template_values['system_version'] = SYSTEM_VERSION
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_topic.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
        else:
            self.redirect('/')

    def post(self):
        template_values = {}
        site = GetSite()
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if member:
            if member.level == 0:
                template_values['page_title'] = site.title + u' › ' + l10n.backstage.decode('utf-8') + u' › ' + l10n.topic_settings.decode('utf-8')
                template_values['site'] = site
                template_values['site_use_topic_types'] = site.use_topic_types
                if site.topic_types is None:
                    template_values['site_topic_types'] = ''
                else:
                    template_values['site_topic_types'] = site.topic_types
                if site.use_topic_types is not True:
                    s = '<select name="use_topic_types"><option value="1">Enabled</option><option value="0" selected="selected">Disabled</option></select>'
                else:
                    s = '<select name="use_topic_types"><option value="1" selected="selected">Enabled</option><option value="0">Disabled</option></select>'
                template_values['s'] = s
                template_values['member'] = member
                template_values['system_version'] = SYSTEM_VERSION
                errors = 0
                # Verification: use_topic_types
                site_use_topic_types = self.request.get('use_topic_types').strip()
                if site_use_topic_types is None:
                    s = '<select name="use_topic_types"><option value="1">Enabled</option><option value="0" selected="selected">Disabled</option></select>'
                else:
                    if site_use_topic_types == '1':
                        s = '<select name="use_topic_types"><option value="1" selected="selected">Enabled</option><option value="0">Disabled</option></select>'
                    else:
                        s = '<select name="use_topic_types"><option value="1">Enabled</option><option value="0" selected="selected">Disabled</option></select>'
                template_values['s'] = s
                # Verification: topic_types
                site_topic_types = self.request.get('topic_types').strip()
                if errors == 0:
                    if site_use_topic_types == '1':
                        site.use_topic_types = True
                    else:
                        site.use_topic_types = False
                    site.topic_types = site_topic_types
                    site.put()
                    memcache.delete('site')
                    self.redirect('/backstage')
                else:
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_topic.html')
                    output = template.render(path, template_values)
                    self.response.out.write(output)
        else:
            self.redirect('/')


class BackstageRemoveMemcacheHandler(webapp.RequestHandler):
    def post(self):
        member = CheckAuth(self)
        if member:
            if member.level == 0:
                mc = self.request.get('mc')
                if mc is not None:
                    memcache.delete(mc)
        self.redirect('/backstage')


class BackstageMemberHandler(webapp.RequestHandler):
    def get(self, member_username):
        template_values = {}
        site = GetSite()
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if member:
            if member.level == 0:
                member_username_lower = member_username.lower()
                q = db.GqlQuery("SELECT * FROM Member WHERE username_lower = :1", member_username_lower)
                if (q.count() == 1):
                    one = q[0]
                    template_values['one'] = one
                    errors = 0
                    template_values['one_username'] = one.username
                    template_values['one_email'] = one.email
                    if one.avatar_large_url is None:
                        template_values['one_avatar_large_url'] = ''
                    else:
                        template_values['one_avatar_large_url'] = one.avatar_large_url
                    if one.avatar_normal_url is None:
                        template_values['one_avatar_normal_url'] = ''
                    else:
                        template_values['one_avatar_normal_url'] = one.avatar_normal_url
                    if one.avatar_mini_url is None:
                        template_values['one_avatar_mini_url'] = ''
                    else:
                        template_values['one_avatar_mini_url'] = one.avatar_mini_url
                    if one.bio is None:
                        template_values['one_bio'] = ''
                    else:
                        template_values['one_bio'] = one.bio
                    template_values['one_level'] = one.level
                    template_values['page_title'] = site.title + u' › ' + l10n.backstage.decode('utf-8') + u' › ' + one.username
                    template_values['site'] = site
                    template_values['member'] = member
                    template_values['system_version'] = SYSTEM_VERSION
                    template_values['latest_members'] = db.GqlQuery("SELECT * FROM Member ORDER BY created DESC LIMIT 5")
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_member.html')
                    output = template.render(path, template_values)
                    self.response.out.write(output)
                else:
                    self.redirect('/backstage')
                
        else:
            self.redirect('/')
            

    def post(self, member_username):
        template_values = {}
        site = GetSite()
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if member:
            if member.level == 0:
                member_username_lower = member_username.lower()
                q = db.GqlQuery("SELECT * FROM Member WHERE username_lower = :1", member_username_lower)
                if (q.count() == 1):
                    one = q[0]
                    template_values['one'] = one
                    errors = 0
                    # Verification: username
                    one_username_error = 0
                    one_username_error_messages = ['',
                        l10n.username_empty,
                        l10n.username_too_long,
                        l10n.username_too_short,
                        l10n.username_invalid,
                        l10n.username_taken]
                    one_username = self.request.get('username').strip()
                    if (len(one_username) == 0):
                        errors = errors + 1
                        one_username_error = 1
                    else:
                        if (len(one_username) > 32):
                            errors = errors + 1
                            one_username_error = 2
                        else:
                            if (len(one_username) < 3):
                                errors = errors + 1
                                one_username_error = 3
                            else:
                                if (re.search('^[a-zA-Z0-9\_]+$', one_username)):
                                    q = db.GqlQuery('SELECT * FROM Member WHERE username_lower = :1 AND num != :2', one_username.lower(), one.num)
                                    if (q.count() > 0):
                                        errors = errors + 1
                                        one_username_error = 5
                                else:
                                    errors = errors + 1
                                    one_username_error = 4
                    template_values['one_username'] = one_username
                    template_values['one_username_error'] = one_username_error
                    template_values['one_username_error_message'] = one_username_error_messages[one_username_error]
                    # Verification: email
                    one_email_error = 0
                    one_email_error_messages = ['',
                        u'请输入电子邮件地址',
                        u'电子邮件地址长度不能超过 32 个字符',
                        u'输入的电子邮件地址不符合规则',
                        u'这个电子邮件地址已经有人注册过了']
                    one_email = self.request.get('email').strip()
                    if (len(one_email) == 0):
                        errors = errors + 1
                        one_email_error = 1
                    else:
                        if (len(one_email) > 32):
                            errors = errors + 1
                            one_email_error = 2
                        else:
                            p = re.compile(r"(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)", re.IGNORECASE)
                            if (p.search(one_email)):
                                q = db.GqlQuery('SELECT * FROM Member WHERE email = :1 AND num != :2', one_email.lower(), one.num)
                                if (q.count() > 0):
                                    errors = errors + 1
                                    one_email_error = 4
                            else:
                                errors = errors + 1
                                one_email_error = 3
                    template_values['one_email'] = one_email.lower()
                    template_values['one_email_error'] = one_email_error
                    template_values['one_email_error_message'] = one_email_error_messages[one_email_error]
                    # Verification: avatar
                    one_avatar_large_url = self.request.get('avatar_large_url')
                    template_values['one_avatar_large_url'] = one_avatar_large_url
                    one_avatar_normal_url = self.request.get('avatar_normal_url')
                    template_values['one_avatar_normal_url'] = one_avatar_normal_url
                    one_avatar_mini_url = self.request.get('avatar_mini_url')
                    template_values['one_avatar_mini_url'] = one_avatar_mini_url
                    # Verification: bio
                    one_bio = self.request.get('bio')
                    template_values['one_bio'] = one_bio
                    # Verification: level
                    one_level = self.request.get('level')
                    try:
                        one_level = int(one_level)
                    except:
                        if one.num == 1:
                            one_level = 0
                        else:
                            one_level = 1000
                    template_values['one_level'] = one_level
                    if errors == 0:
                        one.username = one_username
                        one.username_lower = one_username.lower()
                        one.email = one_email
                        one.avatar_large_url = one_avatar_large_url
                        one.avatar_normal_url = one_avatar_normal_url
                        one.avatar_mini_url = one_avatar_mini_url
                        one.bio = one_bio
                        one.level = one_level
                        one.put()
                        memcache.delete('Member_' + str(one.num))
                        memcache.delete('Member::' + one_username.lower())
                        self.redirect('/backstage')
                    else:
                        template_values['page_title'] = site.title + u' › ' + l10n.backstage.decode('utf-8') + u' › ' + one.username
                        template_values['site'] = site
                        template_values['member'] = member
                        template_values['system_version'] = SYSTEM_VERSION
                        template_values['latest_members'] = db.GqlQuery("SELECT * FROM Member ORDER BY created DESC LIMIT 5")
                        path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_member.html')
                        output = template.render(path, template_values)
                        self.response.out.write(output)
                else:
                    self.redirect('/backstage')

        else:
            self.redirect('/')

class BackstageMembersHandler(webapp.RequestHandler):
    def get(self):
        template_values = {}
        site = GetSite()
        template_values['site'] = site
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if member:
            if member.level == 0:
                template_values['member'] = member
                template_values['page_title'] = site.title + u' › ' + l10n.backstage.decode('utf-8') + u' › 浏览所有会员'
                member_total = memcache.get('member_total')
                if member_total is None:
                    q3 = db.GqlQuery("SELECT * FROM Counter WHERE name = 'member.total'")
                    if (q3.count() > 0):
                        member_total = q3[0].value
                    else:
                        member_total = 0
                    memcache.set('member_total', member_total, 600)
                template_values['member_total'] = member_total
                page_size = 60
                pages = 1
                if member_total > page_size:
                    if (member_total % page_size) > 0:
                        pages = int(math.floor(member_total / page_size)) + 1
                    else:
                        pages = int(math.floor(member_total / page_size))
                try:
                    page_current = int(self.request.get('p'))
                    if page_current < 1:
                        page_current = 1
                    if page_current > pages:
                        page_current = pages
                except:
                    page_current = 1
                page_start = (page_current - 1) * page_size
                template_values['pages'] = pages
                template_values['page_current'] = page_current
                i = 1
                ps = []
                while i <= pages:
                    ps.append(i)
                    i = i + 1
                template_values['ps'] = ps
                q = db.GqlQuery("SELECT * FROM Member ORDER BY created DESC LIMIT " + str(page_start )+ "," + str(page_size))
                template_values['members'] = q
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'backstage_members.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')

class BackstageRemoveNotificationHandler(BaseHandler):
    def get(self, key):
        o = db.get(db.Key(key))
        if o and self.member:
            if type(o).__name__ == 'Notification':
                if o.for_member_num == self.member.num:
                    o.delete()
                    memcache.delete('nn::' + self.member.username_lower)
        self.redirect('/notifications')

def main():
    application = webapp.WSGIApplication([
    ('/backstage', BackstageHomeHandler),
    ('/backstage/new/minisite', BackstageNewMinisiteHandler),
    ('/backstage/minisite/(.*)', BackstageMinisiteHandler),
    ('/backstage/remove/minisite/(.*)', BackstageRemoveMinisiteHandler),
    ('/backstage/new/page/(.*)', BackstageNewPageHandler),
    ('/backstage/page/(.*)', BackstagePageHandler),
    ('/backstage/remove/page/(.*)', BackstageRemovePageHandler),
    ('/backstage/new/section', BackstageNewSectionHandler),
    ('/backstage/section/(.*)', BackstageSectionHandler),
    ('/backstage/new/node/(.*)', BackstageNewNodeHandler),
    ('/backstage/node/([a-z0-9A-Z]+)', BackstageNodeHandler),
    ('/backstage/node/([a-z0-9A-Z]+)/avatar', BackstageNodeAvatarHandler),
    ('/backstage/remove/reply/(.*)', BackstageRemoveReplyHandler),
    ('/backstage/tidy/reply/([0-9]+)', BackstageTidyReplyHandler),
    ('/backstage/tidy/topic/([0-9]+)', BackstageTidyTopicHandler),
    ('/backstage/deactivate/user/(.*)', BackstageDeactivateUserHandler),
    ('/backstage/move/topic/(.*)', BackstageMoveTopicHandler),
    ('/backstage/site', BackstageSiteHandler),
    ('/backstage/topic', BackstageTopicHandler),
    ('/backstage/remove/mc', BackstageRemoveMemcacheHandler),
    ('/backstage/member/(.*)', BackstageMemberHandler),
    ('/backstage/members', BackstageMembersHandler),
    ('/backstage/remove/notification/(.*)', BackstageRemoveNotificationHandler),
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()