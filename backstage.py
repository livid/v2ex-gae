#!/usr/bin/env python
# coding=utf-8

import os
import re
import time
import datetime
import hashlib
import string

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

from v2ex.babel import Member
from v2ex.babel import Counter
from v2ex.babel import Section
from v2ex.babel import Node

from v2ex.babel import SYSTEM_VERSION

from v2ex.babel.security import *
from v2ex.babel.ext.cookies import Cookies

class BackstageHomeHandler(webapp.RequestHandler):
    def get(self):
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        template_values['member'] = member
        if (member):
            if (member.num == 1):
                q = db.GqlQuery("SELECT * FROM Section ORDER BY nodes DESC")
                template_values['sections'] = q
                q2 = db.GqlQuery("SELECT * FROM Counter WHERE name = :1", 'member.max')
                counter = q2[0]
                template_values['member_max'] = counter.value
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'backstage_home.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')
        
class BackstageNewSectionHandler(webapp.RequestHandler):
    def get(self):
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        template_values['member'] = member
        if (member):
            if (member.num == 1):    
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'backstage_new_section.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')
    
    def post(self):
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        template_values['member'] = member
        if (member):
            if (member.num == 1):
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
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        if (member):
            if (member.num == 1):
                template_values['member'] = member
                q = db.GqlQuery("SELECT * FROM Section WHERE name = :1", section_name)
                section = False
                if (q.count() == 1):
                    section = q[0]
                    template_values['section'] = section
                else:
                    template_values['section'] = section
                if (section):
                    q = db.GqlQuery("SELECT * FROM Node WHERE section_num = :1 ORDER BY topics DESC", section.num)
                    template_values['nodes'] = q
                else:
                    template_values['nodes'] = False
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'backstage_section.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')

class BackstageNewNodeHandler(webapp.RequestHandler):
    def get(self, section_name):
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        if (member):
            if (member.num == 1):
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
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        if (member):
            if (member.num == 1):        
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
                    self.redirect('/backstage/section/' + section.name)
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
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        if (member):
            if (member.num == 1):
                template_values['member'] = member
                q = db.GqlQuery("SELECT * FROM Node WHERE name = :1", node_name)
                if (q.count() == 1):
                    template_values['node'] = q[0]
                    template_values['node_name'] = q[0].name
                    template_values['node_title'] = q[0].title
                    template_values['node_title_alternative'] = q[0].title_alternative
                    if q[0].category is None:
                        template_values['node_category'] = ''
                    else:
                        template_values['node_category'] = q[0].category
                    if q[0].header is None:
                        template_values['node_header'] = ''
                    else:
                        template_values['node_header'] = q[0].header
                    if q[0].footer is None:
                        template_values['node_footer'] = ''
                    else:
                        template_values['node_footer'] = q[0].footer
                    template_values['node_topics'] = q[0].topics
                else:
                    template_values['node'] = False
                q2 = db.GqlQuery("SELECT * FROM Section WHERE num = :1", q[0].section_num)
                if (q2.count() == 1):
                    template_values['section'] = q2[0]
                else:
                    template_values['section'] = False
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'backstage_node.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')
    
    def post(self, node_name):
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        if (member):
            if (member.num == 1):        
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
                    if q[0].header is None:
                        template_values['node_header'] = ''
                    else:
                        template_values['node_header'] = q[0].header
                    if q[0].footer is None:
                        template_values['node_footer'] = ''
                    else:
                        template_values['node_footer'] = q[0].footer
                    template_values['node_topics'] = q[0].topics
                else:
                    template_values['node'] = False
                section = False
                q2 = db.GqlQuery("SELECT * FROM Section WHERE num = :1", q[0].section_num)
                if (q2.count() == 1):
                    template_values['section'] = q2[0]
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
                # Verification: node_header
                node_header = self.request.get('header').strip()
                # Verification: node_footer
                node_footer = self.request.get('footer').strip()
                template_values['errors'] = errors
                if (errors == 0):
                    node.name = node_name
                    node.title = node_title
                    node.title_alternative = node_title_alternative
                    node.category = node_category
                    node.header = node_header
                    node.footer = node_footer
                    node.put()
                    self.redirect('/backstage/node/' + node.name)
                else:    
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'backstage_node.html')
                    output = template.render(path, template_values)
                    self.response.out.write(output)
            else:
                self.redirect('/')
        else:
            self.redirect('/signin')


class BackstageRemoveReplyHandler(webapp.RequestHandler):
    def get(self, reply_key):
        member = CheckAuth(self)
        if (member):
            if (member.num == 1):
                reply = db.get(db.Key(reply_key))
                if reply:
                    topic = reply.topic
                    reply.delete()
                    q = db.GqlQuery("SELECT __key__ FROM Reply WHERE topic = :1", topic)
                    topic.replies = q.count()
                    if (topic.replies == 0):
                        topic.last_reply_by = None
                    topic.put()
                    memcache.delete('Topic_' + str(topic.num))
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
            if (member.num == 1):
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
                    reply.topic = topic
                    reply.topic_num = topic.num
                    reply.put()
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
            if (member.num == 1):
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
        if member:
            if member.num == 1:
                one = db.get(db.Key(key))
                if one:
                    if one.num != 1:
                        memcache.delete(one.auth)
                        one.deactivated = int(time.time())
                        one.password = hashlib.sha1(str(time.time())).hexdigest()
                        one.auth = hashlib.sha1(str(one.num) + ':' + one.password).hexdigest()
                        one.put()
                        memcache.delete('Member_' + str(one.num))
                        return self.redirect('/member/' + one.username)
        return self.redirect('/')               

class BackstageMoveTopicHandler(webapp.RequestHandler):
    def get(self, key):
        member = CheckAuth(self)

def main():
    application = webapp.WSGIApplication([
    ('/backstage', BackstageHomeHandler),
    ('/backstage/new/section', BackstageNewSectionHandler),
    ('/backstage/section/(.*)', BackstageSectionHandler),
    ('/backstage/new/node/(.*)', BackstageNewNodeHandler),
    ('/backstage/node/(.*)', BackstageNodeHandler),
    ('/backstage/remove/reply/(.*)', BackstageRemoveReplyHandler),
    ('/backstage/tidy/reply/([0-9]+)', BackstageTidyReplyHandler),
    ('/backstage/tidy/topic/([0-9]+)', BackstageTidyTopicHandler),
    ('/backstage/deactivate/user/(.*)', BackstageDeactivateUserHandler),
    ('/backstage/move/topic/(.*)', BackstageMoveTopicHandler),
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()