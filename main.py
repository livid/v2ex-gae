#!/usr/bin/env python
# coding=utf-8

import os
import re
import time
import datetime
import hashlib
import urllib
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

from v2ex.babel import SYSTEM_VERSION

from v2ex.babel.security import *
from v2ex.babel.ua import *
from v2ex.babel.da import *
from v2ex.babel.ext.cookies import Cookies

template.register_template_library('v2ex.templatetags.filters')

class HomeHandler(webapp.RequestHandler):
    def get(self):
        browser = detect(self.request)
        template_values = {}
        template_values['page_title'] = 'V2EX'
        template_values['system_version'] = SYSTEM_VERSION
        template_values['member'] = CheckAuth(self)
        new = ''
        nodes_new = []
        new = memcache.get('home_nodes_new_neue')
        nodes_new = memcache.get('home_nodes_new')
        try:
            if (new == None) or (nodes_new == None):
                nodes_new = []
                new = u'<div class="section">最近新增节点</div>'
                qnew = db.GqlQuery("SELECT * FROM Node ORDER BY created DESC LIMIT 10")
                if (qnew.count() > 0):
                    i = 0
                    for node in qnew:
                        nodes_new.append(node)
                        i = i + 1
                    n = ''
                    for node in nodes_new:
                        n = n + '<a href="/go/' + node.name + '">' + node.title + '</a>&nbsp; '
                    new = new + '<div class="cell">' + n + '</div>'
                memcache.set('home_nodes_new_neue', new, 300)
                memcache.set('home_nodes_new', nodes_new, 300)
        except:
            new = ''
        template_values['new'] = new
        template_values['nodes_new'] = nodes_new
        if browser['ios']:
            s = ''
            s = memcache.get('home_sections_neue')
            if (s == None):
                s = ''
                q = db.GqlQuery("SELECT * FROM Section ORDER BY created ASC")
                if (q.count() > 0):
                    for section in q:
                        q2 = db.GqlQuery("SELECT * FROM Node WHERE section_num = :1 ORDER BY created ASC", section.num)
                        n = ''
                        if (q2.count() > 0):
                            nodes = []
                            i = 0
                            for node in q2:
                                nodes.append(node)
                                i = i + 1
                            random.shuffle(nodes)
                            for node in nodes:
                                fs = random.randrange(12, 16)
                                n = n + '<a href="/go/' + node.name + '" style="font-size: ' + str(fs) + 'px;">' + node.title + '</a>&nbsp; '
                        s = s + '<div class="section">' + section.title + '</div><div class="cell">' + n + '</div>'
                memcache.set('home_sections_neue', s, 600)
            template_values['s'] = s
        latest = memcache.get('q_latest_12')
        if (latest):
            template_values['latest'] = latest
        else:
            q2 = db.GqlQuery("SELECT * FROM Topic ORDER BY last_touched DESC LIMIT 12")
            memcache.set('q_latest_12', q2, 120)
            template_values['latest'] = q2
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
        if (browser['ios']):
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'index.html')
        else:
            c = memcache.get('categories')
            if c is None:
                c = ''
                categories = [u'分享与探索', u'城市', u'V2EX', u'iOS', u'Apple', u'生活', u'Internet', u'Geek', u'电子游戏', u'品牌', u'最热节点']
                for category in categories:
                    if category == u'最热节点':
                        c = c + '<div class="inner"><table cellpadding="0" cellspacing="0" border="0"><tr><td align="right" width="80"><span class="snow"><strong>' + category + '</strong></span></td><td align="left">'
                        qx = db.GqlQuery("SELECT * FROM Node ORDER BY topics DESC LIMIT 8")
                    else:
                        c = c + '<div class="cell"><table cellpadding="0" cellspacing="0" border="0"><tr><td align="right" width="80"><span class="snow"><strong>' + category + '</strong></span></td><td align="left">'
                        qx = db.GqlQuery("SELECT * FROM Node WHERE category = :1 ORDER BY topics DESC", category)
                    for node in qx:
                        c = c + '&nbsp; <a href="/go/' + node.name + '">' + node.title + '</a>'
                    c = c + '</td></tr></table></div>'
                    memcache.set('categories', c, 120)
            template_values['c'] = c
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'index.html')
        output = template.render(path, template_values)
        self.response.out.write(output)
        
class RecentHandler(webapp.RequestHandler):
    def get(self):
        browser = detect(self.request)
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        template_values['page_title'] = u'V2EX › 最近的 50 个主题'
        template_values['member'] = CheckAuth(self)
        latest = memcache.get('q_recent_50')
        if (latest):
            template_values['latest'] = latest
        else:
            q2 = db.GqlQuery("SELECT * FROM Topic ORDER BY last_touched DESC LIMIT 12,50")
            memcache.set('q_recent_50', q2, 80)
            template_values['latest'] = q2
            template_values['latest_total'] = q2.count()
        if browser['ios']:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'recent.html')
        else:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'recent.html')
        output = template.render(path, template_values)
        self.response.out.write(output)

class UAHandler(webapp.RequestHandler):
    def get(self):
        browser = detect(self.request)
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        template_values['member'] = CheckAuth(self)
        template_values['ua'] = os.environ['HTTP_USER_AGENT']
        template_values['page_title'] = 'V2EX › 用户代理字符串'
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'ua.html')
        output = template.render(path, template_values)
        self.response.out.write(output)

        
class SigninHandler(webapp.RequestHandler):
    def get(self):
        browser = detect(self.request)
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        errors = 0
        template_values['errors'] = errors
        if browser['ios']:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'signin.html')
        else:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'signin.html')
        output = template.render(path, template_values)
        self.response.out.write(output)
 
    def post(self):
        browser = detect(self.request)
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        u = self.request.get('u').strip()
        p = self.request.get('p').strip()
        errors = 0
        error_messages = ['', '请输入用户名和密码', '你输入的用户名或密码不正确']
        if (len(u) > 0 and len(p) > 0):
            p_sha1 = hashlib.sha1(p).hexdigest()
            q = db.GqlQuery("SELECT * FROM Member WHERE username_lower = :1 AND password = :2", u.lower(), p_sha1)
            if (q.count() == 1):
                member = q[0]
                cookies = Cookies(self, max_age = 86400 * 365, path = '/')
                cookies['auth'] = member.auth
                self.redirect('/')
            else:
                errors = 2
        else:
            errors = 1
        template_values['u'] = u
        template_values['p'] = p
        template_values['errors'] = errors
        template_values['error_message'] = error_messages[errors]
        if browser['ios']:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'signin.html')
        else:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'signin.html')
        output = template.render(path, template_values)
        self.response.out.write(output)
        
class SignupHandler(webapp.RequestHandler):
    def get(self):
        browser = detect(self.request)
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        template_values['errors'] = 0
        if browser['ios']:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'signup.html')
        else:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'signup.html')
        output = template.render(path, template_values)
        self.response.out.write(output)
        
    def post(self):
        browser = detect(self.request)
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        errors = 0
        # Verification: username
        member_username_error = 0
        member_username_error_messages = ['',
            u'请输入你的用户名',
            u'用户名长度不能超过 32 个字符',
            u'用户名只能由 a-Z 0-9 及 - 和 _ 组成',
            u'抱歉这个用户名已经有人使用了']
        member_username = self.request.get('username').strip()
        if (len(member_username) == 0):
            errors = errors + 1
            member_username_error = 1
        else:
            if (len(member_username) > 32):
                errors = errors + 1
                member_username_error = 2
            else:
                if (re.search('^[a-zA-Z0-9\-\_]+$', member_username)):
                    q = db.GqlQuery('SELECT __key__ FROM Member WHERE username_lower = :1', member_username.lower())
                    if (q.count() > 0):
                        errors = errors + 1
                        member_username_error = 4
                else:
                    errors = errors + 1
                    member_username_error = 3
        template_values['member_username'] = member_username
        template_values['member_username_error'] = member_username_error
        template_values['member_username_error_message'] = member_username_error_messages[member_username_error]
        # Verification: password
        member_password_error = 0
        member_password_error_messages = ['',
            u'请输入你的密码',
            u'密码长度不能超过 32 个字符'
        ]
        member_password = self.request.get('password').strip()
        if (len(member_password) == 0):
            errors = errors + 1
            member_password_error = 1
        else:
            if (len(member_password) > 32):
                errors = errors + 1
                member_password_error = 2
        template_values['member_password'] = member_password
        template_values['member_password_error'] = member_password_error
        template_values['member_password_error_message'] = member_password_error_messages[member_password_error]
        # Verification: email
        member_email_error = 0
        member_email_error_messages = ['',
            u'请输入你的电子邮件地址',
            u'电子邮件地址长度不能超过 32 个字符',
            u'你输入的电子邮件地址不符合规则',
            u'抱歉这个电子邮件地址已经有人注册过了']
        member_email = self.request.get('email').strip()
        if (len(member_email) == 0):
            errors = errors + 1
            member_email_error = 1
        else:
            if (len(member_email) > 32):
                errors = errors + 1
                member_email_error = 2
            else:
                p = re.compile(r"(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)", re.IGNORECASE)
                if (p.search(member_email)):
                    q = db.GqlQuery('SELECT __key__ FROM Member WHERE email = :1', member_email.lower())
                    if (q.count() > 0):
                        errors = errors + 1
                        member_email_error = 4
                else:
                    errors = errors + 1
                    member_email_error = 3
        template_values['member_email'] = member_email
        template_values['member_email_error'] = member_email_error
        template_values['member_email_error_message'] = member_email_error_messages[member_email_error]
        template_values['errors'] = errors
        if (errors == 0):
            member = Member()
            q = db.GqlQuery('SELECT * FROM Counter WHERE name = :1', 'member.max')
            if (q.count() == 1):
                counter = q[0]
                counter.value = counter.value + 1
            else:
                counter = Counter()
                counter.name = 'member.max'
                counter.value = 1
            q2 = db.GqlQuery('SELECT * FROM Counter WHERE name = :1', 'member.total')
            if (q2.count() == 1):
                counter2 = q2[0]
                counter2.value = counter2.value + 1
            else:
                counter2 = Counter()
                counter2.name = 'member.total'
                counter2.value = 1
            member.num = counter.value
            member.username = member_username
            member.username_lower = member_username.lower()
            member.password = hashlib.sha1(member_password).hexdigest()
            member.email = member_email.lower()
            member.auth = hashlib.sha1(str(member.num) + ':' + member.password).hexdigest()
            member.put()
            counter.put()
            counter2.put()
            cookies = Cookies(self, max_age = 86400, path = '/')
            cookies['auth'] = member.auth
            self.redirect('/')
        else:
            if browser['ios']:
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'signup.html')
            else:
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'signup.html')
            output = template.render(path, template_values)
            self.response.out.write(output)

class SignoutHandler(webapp.RequestHandler):
    def get(self):
        browser = detect(self.request)
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        cookies = Cookies(self, max_age = 86400, path = '/')
        del cookies['auth']
        if browser['ios']:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'signout.html')
        else:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'signout.html')
        output = template.render(path, template_values)
        self.response.out.write(output)
        
class NodeHandler(webapp.RequestHandler):
    def get(self, node_name):
        browser = detect(self.request)
        template_values = {}
        template_values['system_version'] = SYSTEM_VERSION
        template_values['member'] = CheckAuth(self)
        node = GetKindByName('Node', node_name)
        template_values['node'] = node
        pagination = False
        pages = 1
        page = 1
        page_size = 12
        start = 0
        has_more = False
        more = 1
        has_previous = False
        previous = 1
        if node:
            template_values['page_title'] = u'V2EX › ' + node.title
            # Pagination
            if node.topics > page_size:
                pagination = True
            else:
                pagination = False
            if pagination:
                if node.topics % page_size == 0:
                    pages = int(node.topics / page_size)
                else:
                    pages = int(node.topics / page_size) + 1
                page = self.request.get('p')
                if (page == '') or (page is None):
                    page = 1
                else:
                    page = int(page)
                    if page > pages:
                        page = pages
                    else:
                        if page < 1:
                            page = 1
                if page < pages:
                    has_more = True
                    more = page + 1
                if page > 1:
                    has_previous = True
                    previous = page - 1    
                start = (page - 1) * page_size
        template_values['pagination'] = pagination
        template_values['pages'] = pages
        template_values['page'] = page
        template_values['page_size'] = page_size
        template_values['has_more'] = has_more
        template_values['more'] = more
        template_values['has_previous'] = has_previous
        template_values['previous'] = previous
        section = False
        if node:
            section = GetKindByNum('Section', node.section_num)
        template_values['section'] = section
        topics = False
        if node:
            q3 = db.GqlQuery("SELECT * FROM Topic WHERE node_num = :1 ORDER BY last_touched DESC LIMIT " + str(start) + ", " + str(page_size), node.num)
            topics = q3
        template_values['topics'] = topics
        if browser['ios']:
            if (node):
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'node.html')
            else:
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'node_not_found.html')
        else:
            if (node):
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'node.html')
            else:
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'node_not_found.html')
        output = template.render(path, template_values)
        self.response.out.write(output)

class SearchHandler(webapp.RequestHandler):
    def get(self, q):
        q = urllib.unquote(q)
        template_values = {}
        template_values['page_title'] = u'V2EX › 搜索 ' + str(q)
        template_values['q'] = q
        # Fetch result
        q_lowered = q.lower()
        self.response.out.write(self.request.headers)
        if self.request.headers['Host'] == 'localhost:10000':
            fts = 'http://localhost:20000/search?q=yeah'
        else:
            fts = 'http://fts.v2ex.com/search?q=yeah'
        response = urlfetch.fetch(fts)
        self.response.out.write(response)
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'search.html')
        output = template.render(path, template_values)
        self.response.out.write(output)

class DispatcherHandler(webapp.RequestHandler):
    def post(self):
        referer = self.request.headers['Referer']
        q = self.request.get('q').strip()
        if len(q) > 0:
            self.redirect('/q/' + str(q))
        else:
            self.redirect(referer)

def main():
    application = webapp.WSGIApplication([
    ('/', HomeHandler),
    ('/recent', RecentHandler),
    ('/ua', UAHandler),
    ('/signin', SigninHandler),
    ('/signup', SignupHandler),
    ('/signout', SignoutHandler),
    ('/go/(.*)', NodeHandler),
    ('/q/(.*)', SearchHandler),
    ('/_dispatcher', DispatcherHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
