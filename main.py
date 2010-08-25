#!/usr/bin/env python
# coding=utf-8

import base64
import os
import re
import time
import datetime
import hashlib
import urllib
import string
import random
import pickle

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import mail
from google.appengine.ext import db
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

from v2ex.babel import Member
from v2ex.babel import Counter
from v2ex.babel import Section
from v2ex.babel import Node
from v2ex.babel import Topic
from v2ex.babel import Reply
from v2ex.babel import PasswordResetToken

from v2ex.babel import SYSTEM_VERSION

from v2ex.babel.security import *
from v2ex.babel.ua import *
from v2ex.babel.da import *
from v2ex.babel.ext.cookies import Cookies
from v2ex.babel.ext.sessions import Session

from v2ex.babel.handler import GenericHandler

from django.utils import simplejson as json

from v2ex.babel.ext import captcha

template.register_template_library('v2ex.templatetags.filters')

import config

class HomeHandler(webapp.RequestHandler):
    def head(self):
        pass
        
    def get(self):
        host = self.request.headers['Host']
        if host == 'beta.v2ex.com':
            self.redirect('http://v2ex.appspot.com/')
            return
        site = GetSite()
        browser = detect(self.request)
        self.session = Session()
        template_values = {}
        template_values['site'] = GetSite()
        template_values['rnd'] = random.randrange(1, 100)
        template_values['page_title'] = site.title
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        if member:
            self.response.headers['Set-Cookie'] = 'auth=' + member.auth + '; expires=' + (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/'
            template_values['member'] = member
            try:
                blocked = pickle.loads(member.blocked.encode('utf-8'))
            except:
                blocked = []
            if (len(blocked) > 0):
                template_values['blocked'] = ','.join(map(str, blocked))
        if member:
            recent_nodes = memcache.get('member::' + str(member.num) + '::recent_nodes')
            if recent_nodes:
                template_values['recent_nodes'] = recent_nodes
        nodes_new = []
        nodes_new = memcache.get('home_nodes_new')
        if nodes_new is None:
            nodes_new = []
            qnew = db.GqlQuery("SELECT * FROM Node ORDER BY created DESC LIMIT 10")
            if (qnew.count() > 0):
                i = 0
                for node in qnew:
                    nodes_new.append(node)
                    i = i + 1
            memcache.set('home_nodes_new', nodes_new, 3600)
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
        latest = memcache.get('q_latest_16')
        if (latest):
            template_values['latest'] = latest
        else:
            q2 = db.GqlQuery("SELECT * FROM Topic ORDER BY last_touched DESC LIMIT 16")
            memcache.set('q_latest_16', q2, 120)
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
            hottest = memcache.get('index_hottest_sidebar')
            if hottest is None:
                qhot = db.GqlQuery("SELECT * FROM Node ORDER BY topics DESC LIMIT 25")
                hottest = u'<div class="box"><div class="cell"><span class="fade">最热节点</span></div><div class="inner" style="line-height: 200%;">'
                for node in qhot:
                    hottest = hottest + '<a href="/go/' + node.name + '" class="item_node">' + node.title + '</a>'
                hottest = hottest + '</div></div>'
                memcache.set('index_hottest_sidebar', hottest, 5000)
            template_values['index_hottest_sidebar'] = hottest
            c = memcache.get('index_categories')
            if c is None:
                c = ''
                i = 0
                categories = [u'分享与探索', u'城市', u'V2EX', u'iOS', u'Apple', u'生活', u'Internet', u'Geek', u'电子游戏', u'品牌']
                for category in categories:
                    i = i + 1
                    if i == len(categories):
                        css_class = 'inner'
                    else:
                        css_class = 'cell'
                    c = c + '<div class="' + css_class + '"><table cellpadding="0" cellspacing="0" border="0"><tr><td align="right" width="80"><span class="snow"><strong>' + category + '</strong></span></td><td style="line-height: 200%; padding-left: 15px;">'
                    qx = db.GqlQuery("SELECT * FROM Node WHERE category = :1 ORDER BY topics DESC", category)
                    for node in qx:
                        c = c + '<a href="/go/' + node.name + '" style="font-size: 14px;">' + node.title + '</a>&nbsp; &nbsp; '
                    c = c + '</td></tr></table></div>'
                    memcache.set('index_categories', c, 3600)
            template_values['c'] = c
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'index.html')
        output = template.render(path, template_values)
        self.response.out.write(output)
        
class RecentHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        browser = detect(self.request)
        template_values = {}
        template_values['site'] = site
        template_values['rnd'] = random.randrange(1, 100)
        template_values['system_version'] = SYSTEM_VERSION
        template_values['page_title'] = site.title + u' › 最近的 50 个主题'
        member = CheckAuth(self)
        if member:
            template_values['member'] = member
            try:
                blocked = pickle.loads(member.blocked.encode('utf-8'))
            except:
                blocked = []
            if (len(blocked) > 0):
                template_values['blocked'] = ','.join(map(str, blocked))
        latest = memcache.get('q_recent_50')
        if (latest):
            template_values['latest'] = latest
        else:
            q2 = db.GqlQuery("SELECT * FROM Topic ORDER BY last_touched DESC LIMIT 16,50")
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
        site = GetSite()
        browser = detect(self.request)
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        template_values['member'] = CheckAuth(self)
        template_values['ua'] = os.environ['HTTP_USER_AGENT']
        template_values['page_title'] = site.title + u' › 用户代理字符串'
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'ua.html')
        output = template.render(path, template_values)
        self.response.out.write(output)

        
class SigninHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        browser = detect(self.request)
        template_values = {}
        template_values['site'] = site
        template_values['page_title'] = site.title + u' › 登入'
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
        site = GetSite()
        browser = detect(self.request)
        template_values = {}
        template_values['site'] = site
        template_values['page_title'] = site.title + u' › 登入'
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
                self.response.headers['Set-Cookie'] = 'auth=' + member.auth + '; expires=' + (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/'
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
        site = GetSite()
        chtml = captcha.displayhtml(
            public_key = config.recaptcha_public_key,
            use_ssl = False,
            error = None)
        browser = detect(self.request)
        template_values = {}
        template_values['site'] = site
        template_values['page_title'] = site.title + u' › 注册'
        template_values['system_version'] = SYSTEM_VERSION
        template_values['errors'] = 0
        template_values['captchahtml'] = chtml
        if browser['ios']:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'signup.html')
        else:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'signup.html')
        output = template.render(path, template_values)
        self.response.out.write(output)
        
    def post(self):
        site = GetSite()
        browser = detect(self.request)
        template_values = {}
        template_values['site'] = site
        template_values['page_title'] = site.title + u' › 注册'
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
        # Verification: reCAPTCHA
        challenge = self.request.get('recaptcha_challenge_field')
        response  = self.request.get('recaptcha_response_field')
        remoteip  = os.environ['REMOTE_ADDR']
        
        cResponse = captcha.submit(
                         challenge,
                         response,
                         config.recaptcha_private_key,
                         remoteip)

        if cResponse.is_valid:
            logging.info('reCAPTCHA verification passed')
            template_values['recaptcha_error'] = 0
        else:
            errors = errors + 1
            error = cResponse.error_code
            chtml = captcha.displayhtml(
                public_key = config.recaptcha_public_key,
                use_ssl = False,
                error = cResponse.error_code)
            template_values['captchahtml'] = chtml
            template_values['recaptcha_error'] = 1
            template_values['recaptcha_error_message'] = '请重新输入 reCAPTCHA 验证码'
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
            self.response.headers['Set-Cookie'] = 'auth=' + member.auth + '; expires=' + (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/'
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
        site = GetSite()
        browser = detect(self.request)
        template_values = {}
        template_values['site'] = site
        template_values['page_title'] = site.title + u' › 登出'
        template_values['system_version'] = SYSTEM_VERSION
        cookies = Cookies(self, max_age = 86400, path = '/')
        del cookies['auth']
        if browser['ios']:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'signout.html')
        else:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'signout.html')
        output = template.render(path, template_values)
        self.response.out.write(output)

class ForgotHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        browser = detect(self.request)
        template_values = {}
        template_values['rnd'] = random.randrange(1, 100)
        template_values['site'] = site
        member = CheckAuth(self)
        if member:
            template_values['member'] = member
        template_values['page_title'] = site.title + u' › 重新设置密码'
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'forgot.html')
        output = template.render(path, template_values)
        self.response.out.write(output)
    
    def post(self):
        site = GetSite()
        browser = detect(self.request)
        template_values = {}
        template_values['rnd'] = random.randrange(1, 100)
        template_values['site'] = site
        member = CheckAuth(self)
        if member:
            template_values['member'] = member
        template_values['page_title'] = site.title + u' › 重新设置密码'
        # Verification: username & email
        username = self.request.get('username').strip().lower()
        email = self.request.get('email').strip().lower()
        q = db.GqlQuery("SELECT * FROM Member WHERE username_lower = :1 AND email = :2", username, email)
        if q.count() == 1:
            one = q[0]
            q2 = db.GqlQuery("SELECT * FROM PasswordResetToken WHERE timestamp > :1", (int(time.time()) - 86400))
            if q2.count() > 2:
                error_message = '你不能在 24 小时内进行超过 2 次的密码重设操作。'
                template_values['errors'] = 1
                template_values['error_message'] = error_message
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'forgot.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                token = ''.join([str(random.randint(0, 9)) for i in range(32)])
                prt = PasswordResetToken()
                prt.token = token
                prt.member = one
                prt.email = one.email
                prt.timestamp = int(time.time())
                prt.put()
                mail_template_values = {}
                mail_template_values['site'] = site
                mail_template_values['one'] = one
                mail_template_values['host'] = self.request.headers['Host']
                mail_template_values['token'] = token
                mail_template_values['ua'] = self.request.headers['User-Agent']
                mail_template_values['ip'] = self.request.remote_addr
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'mail', 'reset_password.txt')
                output = template.render(path, mail_template_values)
                result = mail.send_mail(sender="V2EX <v2ex.livid@gmail.com>",
                              to= one.email,
                              subject="=?UTF-8?B?" + base64.b64encode((u"[" + site.title + u"] 重新设置密码").encode('utf-8')) + "?=",
                              body=output)
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'forgot_sent.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
        else:
            error_message = '无法找到匹配的用户名和邮箱记录'
            template_values['errors'] = 1
            template_values['error_message'] = error_message
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'forgot.html')
            output = template.render(path, template_values)
            self.response.out.write(output)

class PasswordResetHandler(GenericHandler):
    def get(self, token):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        token = str(token.strip().lower())
        q = db.GqlQuery("SELECT * FROM PasswordResetToken WHERE token = :1 AND valid = 1", token)
        if q.count() == 1:
            prt = q[0]
            template_values['page_title'] = site.title + u' › 重新设置密码'
            template_values['token'] = prt
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'reset_password.html')
            output = template.render(path, template_values)
            self.response.out.write(output)
        else:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'token_not_found.html')
            output = template.render(path, template_values)
            self.response.out.write(output)
    
    def post(self, token):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        token = str(token.strip().lower())
        q = db.GqlQuery("SELECT * FROM PasswordResetToken WHERE token = :1 AND valid = 1", token)
        if q.count() == 1:
            prt = q[0]
            template_values['page_title'] = site.title + u' › 重新设置密码'
            template_values['token'] = prt
            # Verification
            errors = 0
            new_password = str(self.request.get('new_password').strip())
            new_password_again = str(self.request.get('new_password_again').strip())
            if new_password is '' or new_password_again is '':
                errors = errors + 1
                error_message = '请输入两次新密码'
            if errors == 0:
                if new_password != new_password_again:
                    errors = errors + 1
                    error_message = '两次输入的新密码不一致'
            if errors == 0:
                if len(new_password) > 32:
                    errors = errors + 1
                    error_message = '新密码长度不能超过 32 个字符'
            if errors == 0:
                q2 = db.GqlQuery("SELECT * FROM Member WHERE num = :1", prt.member.num)
                one = q2[0]
                one.password = hashlib.sha1(new_password).hexdigest()
                one.auth = hashlib.sha1(str(one.num) + ':' + one.password).hexdigest()
                one.put()
                prt.valid = 0
                prt.put()
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'reset_password_ok.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                template_values['errors'] = errors
                template_values['error_message'] = error_message
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'reset_password.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
        else:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'token_not_found.html')
            output = template.render(path, template_values)
            self.response.out.write(output)

class NodeHandler(webapp.RequestHandler):
    def get(self, node_name):
        site = GetSite()
        browser = detect(self.request)
        self.session = Session()
        template_values = {}
        template_values['site'] = site
        template_values['rnd'] = random.randrange(1, 100)
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        if member:
            template_values['member'] = member
        node = GetKindByName('Node', node_name)
        template_values['node'] = node
        pagination = False
        pages = 1
        page = 1
        page_size = 15
        start = 0
        has_more = False
        more = 1
        has_previous = False
        previous = 1
        if node:
            if member:
                recent_nodes = memcache.get('member::' + str(member.num) + '::recent_nodes')
                recent_nodes_ids = memcache.get('member::' + str(member.num) + '::recent_nodes_ids')
                if recent_nodes and recent_nodes_ids:
                    if (node.num in recent_nodes_ids) is not True:
                        recent_nodes.insert(0, node)
                        recent_nodes_ids.insert(0, node.num)
                        memcache.set('member::' + str(member.num) + '::recent_nodes', recent_nodes, 7200)
                        memcache.set('member::' + str(member.num) + '::recent_nodes_ids', recent_nodes_ids, 7200)
                else:
                    recent_nodes = []
                    recent_nodes.append(node)
                    recent_nodes_ids = []
                    recent_nodes_ids.append(node.num)
                    memcache.set('member::' + str(member.num) + '::recent_nodes', recent_nodes, 7200)
                    memcache.set('member::' + str(member.num) + '::recent_nodes_ids', recent_nodes_ids, 7200)
                template_values['recent_nodes'] = recent_nodes
            template_values['page_title'] = site.title + u' › ' + node.title
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
        else:
            template_values['page_title'] = site.title + u' › 节点未找到'
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

class NodeApiHandler(webapp.RequestHandler):
    def get(self, node_name):
        site = GetSite()
        node = GetKindByName('Node', node_name)
        if node:
            template_values = {}
            template_values['site'] = site
            template_values['node'] = node
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'node.json')
            self.response.headers['Content-type'] = 'application/json;charset=UTF-8'
            output = template.render(path, template_values)
            self.response.out.write(output)
        else:
            self.error(404)

class SearchHandler(webapp.RequestHandler):
    def get(self, q):
        site = GetSite()
        q = urllib.unquote(q)
        template_values = {}
        template_values['site'] = site
        member = CheckAuth(self)
        if member:
            template_values['member'] = member
        template_values['page_title'] = site.title + ' › 搜索 ' + q
        template_values['q'] = q
        if config.fts_enabled is not True:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'search_unavailable.html')
            output = template.render(path, template_values)
            self.response.out.write(output)
        else:
            if re.findall('^([a-zA-Z0-9\_]+)$', q):
                node = GetKindByName('Node', q.lower())
                if node is not None:
                    template_values['node'] = node
            # Fetch result
            q_lowered = q.lower()
            q_md5 = hashlib.md5(q_lowered).hexdigest()
            topics = memcache.get('q::' + q_md5)
            if topics is None:
                if os.environ['SERVER_SOFTWARE'] == 'Development/1.0':
                    fts = u'http://127.0.0.1:20000/search?q=' + str(urllib.quote(q_lowered))
                else:
                    fts = u'http://' + config.fts_server + '/search?q=' + str(urllib.quote(q_lowered))
                response = urlfetch.fetch(fts, headers = {"Authorization" : "Basic %s" % base64.b64encode(config.fts_username + ':' + config.fts_password)})
                if response.status_code == 200:
                    results = json.loads(response.content)
                    topics = []
                    for num in results:
                        topics.append(GetKindByNum('Topic', num))
                    template_values['topics'] = topics
                    memcache.set('q::' + q_md5, topics, 86400)
            else:
                template_values['topics'] = topics
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'search.html')
            output = template.render(path, template_values)
            self.response.out.write(output)

class DispatcherHandler(webapp.RequestHandler):
    def post(self):
        referer = self.request.headers['Referer']
        q = self.request.get('q').strip()
        if len(q) > 0:
            self.redirect('/q/' + q)
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
    ('/forgot', ForgotHandler),
    ('/reset/([0-9]+)', PasswordResetHandler),
    ('/go/(.*)', NodeHandler),
    ('/n/([a-zA-Z0-9]+).json', NodeApiHandler),
    ('/q/(.*)', SearchHandler),
    ('/_dispatcher', DispatcherHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
