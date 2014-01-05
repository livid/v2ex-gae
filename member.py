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

from StringIO import StringIO

from django.utils import simplejson as json

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.api import urlfetch
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
from v2ex.babel.ext.upyun import UpYun, md5, md5file

from v2ex.babel import SYSTEM_VERSION

from v2ex.babel.handlers import BaseHandler

import config

template.register_template_library('v2ex.templatetags.filters')

class MemberHandler(webapp.RequestHandler):
    def get(self, member_username):
        site = GetSite()
        browser = detect(self.request)
        self.session = Session()
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        template_values['member'] = member
        template_values['show_extra_options'] = False
        if member:
            if member.num == 1:
                template_values['show_extra_options'] = True
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        one = False
        one = GetMemberByUsername(member_username)
        if one is not False:
            if one.followers_count is None:
                one.followers_count = 0
            template_values['one'] = one
            template_values['page_title'] = site.title + u' › ' + one.username
            template_values['canonical'] = 'http://' + site.domain + '/member/' + one.username
            if one.github:
                github = memcache.get('Member::' + one.username_lower + '::github')
                if github is None:
                    response = urlfetch.fetch("https://api.github.com/users/" + one.github + "/repos")
                    if response.status_code == 200:
                        github = response.content
                        memcache.set('Member::' + one.username_lower + '::github', github, 86400)
                if github is not None:
                    template_values['github_repos'] = sorted(json.loads(github), key=lambda x:x['stargazers_count'], reverse=True)
        if one is not False:
            member_blog = memcache.get('member::' + str(one.num) + '::blog')
            if member_blog == None:
                blog = db.GqlQuery("SELECT * FROM Topic WHERE node_name = :1 AND member_num = :2 ORDER BY created DESC LIMIT 1", 'blog', one.num)
                if blog.count() > 0:
                    template_values['blog'] = blog[0]
                    memcache.set('member::' + str(one.num) + '::blog', blog[0], 7200)
            else:
                template_values['blog'] = member_blog
            member_topics = memcache.get('member::' + str(one.num) + '::topics')
            if member_topics != None:
                template_values['topics'] = member_topics
            else:
                q2 = db.GqlQuery("SELECT * FROM Topic WHERE member_num = :1 ORDER BY created DESC LIMIT 10", one.num)
                template_values['topics'] = q2
                memcache.set('member::' + str(one.num) + '::topics', q2, 7200)
            replies = memcache.get('member::' + str(one.num) + '::participated')
            
            if replies is None:
                q3 = db.GqlQuery("SELECT * FROM Reply WHERE member_num = :1 ORDER BY created DESC LIMIT 10", one.num)
                ids = []
                replies = []
                i = 0
                for reply in q3:
                    if reply.topic.num not in ids:
                        i = i + 1
                        if i > 10:
                            break
                        replies.append(reply)
                        ids.append(reply.topic.num)
                if len(replies) > 0:
                    memcache.set('member::' + str(one.num) + '::participated', replies, 7200)
            if len(replies) > 0:
                template_values['replies'] = replies
        template_values['show_block'] = False
        template_values['show_follow'] = False
        template_values['favorited'] = False
        if one and member:
            if one.num != member.num:
                template_values['show_follow'] = True
                template_values['show_block'] = True
                try:
                    blocked = pickle.loads(member.blocked.encode('utf-8'))
                except:
                    blocked = []
                if one.num in blocked:
                    template_values['one_is_blocked'] = True
                else:
                    template_values['one_is_blocked'] = False
                if member.hasFavorited(one):
                    template_values['favorited'] = True
                else:
                    template_values['favorited'] = False
        if 'message' in self.session:
            template_values['message'] = self.session['message']
            del self.session['message']
        if one is not False: 
            if browser['ios']:
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'member_home.html')
            else:
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'member_home.html')
        else:
            if browser['ios']:
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'member_not_found.html')
            else:
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'member_not_found.html')
        output = template.render(path, template_values)
        self.response.out.write(output)
        
class MemberApiHandler(webapp.RequestHandler):
    def get(self, member_username):
        site = GetSite()
        one = GetMemberByUsername(member_username)
        if one:
            if one.avatar_mini_url:
                if (one.avatar_mini_url[0:1] == '/'):
                    one.avatar_mini_url = 'http://' + site.domain + one.avatar_mini_url
                    one.avatar_normal_url = 'http://' +  site.domain + one.avatar_normal_url
                    one.avatar_large_url = 'http://' + site.domain + one.avatar_large_url
            template_values = {}
            template_values['site'] = site
            template_values['one'] = one
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'member.json')
            self.response.headers['Content-type'] = 'application/json;charset=UTF-8'
            output = template.render(path, template_values)
            self.response.out.write(output)
        else:
            self.error(404)

class SettingsHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        browser = detect(self.request)
        self.session = Session()
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        template_values['page_title'] = site.title + u' › ' + l10n.settings.decode('utf-8')
        if (member):
            template_values['member'] = member
            template_values['member_username'] = member.username
            template_values['member_email'] = member.email
            if (member.website == None):
                member.website = ''
            template_values['member_website'] = member.website
            if (member.twitter == None):
                member.twitter = ''
            template_values['member_twitter'] = member.twitter
            if (member.location == None):
                member.location = ''
            if member.psn is None:
                member.psn = ''
            template_values['member_psn'] = member.psn
            if (member.my_home == None):
                member.my_home = ''
            template_values['member_my_home'] = member.my_home
            template_values['member_btc'] = member.btc
            if member.github:
                template_values['member_github'] = member.github
            else:
                template_values['member_github'] = u''
            template_values['member_location'] = member.location
            if (member.tagline == None):
                member.tagline = ''
            template_values['member_tagline'] = member.tagline
            if (member.bio == None):
                member.bio = ''
            template_values['member_bio'] = member.bio
            template_values['member_show_home_top'] = member.show_home_top
            template_values['member_show_quick_post'] = member.show_quick_post
            if member.l10n is None:
                member.l10n = 'en'
            template_values['member_l10n'] = member.l10n
            s = GetLanguageSelect(member.l10n)
            template_values['s'] = s
            if member.twitter_sync == 1:
                template_values['member_twitter_sync'] = 1
            if member.use_my_css == 1:
                template_values['member_use_my_css'] = 1
            if (member.my_css == None):
                member.my_css = ''
            template_values['member_my_css'] = member.my_css
            if 'message' in self.session:
                message = self.session['message']
                del self.session['message']
            else:
                message = None
            template_values['message'] = message
            try:
                blocked = pickle.loads(member.blocked.encode('utf-8'))
            except:
                blocked = []
            template_values['member_stats_blocks'] = len(blocked)
            if browser['ios']:
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'member_settings.html')
            else:
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'member_settings.html')
            output = template.render(path, template_values)
            self.response.out.write(output)
        else:
            self.redirect('/signin')
        
    def post(self):
        self.session = Session()
        site = GetSite()
        browser = detect(self.request)
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        errors = 0
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        template_values['page_title'] = site.title + u' › ' + l10n.settings.decode('utf-8')
        if (member):
            template_values['member'] = member
            template_values['member_username'] = member.username
            template_values['member_email'] = member.email
            template_values['member_website'] = member.website
            template_values['member_twitter'] = member.twitter
            # Verification: password
            password_error = 0
            password_update = False
            password_error_messages = ['',
                '新密码长度不能超过 32 个字符',
                '请输入当前密码',
                '当前密码不正确'
            ]
            password_new = self.request.get('password_new').strip()
            if (len(password_new) > 0):
                password_update = True
                if (len(password_new) > 32):
                    password_error = 1
                else:
                    password_current = self.request.get('password_current').strip()
                    if (len(password_current) == 0):
                        password = 2
                    else:
                        password_current_sha1 = hashlib.sha1(password_current).hexdigest()
                        if (password_current_sha1 != member.password):
                            password_error = 3
            template_values['password_error'] = password_error
            template_values['password_error_message'] = password_error_messages[password_error]
            if ((password_error == 0) and (password_update == True)):
                member.password = hashlib.sha1(password_new).hexdigest()
                member.auth = hashlib.sha1(str(member.num) + ':' + member.password).hexdigest()
                member.put()
                self.response.headers['Set-Cookie'] = 'auth=' + member.auth + '; expires=' + (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/'
                self.redirect('/settings')
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
                    p = re.compile(r"(?:^|\s)[-a-z0-9_.+]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)", re.IGNORECASE)
                    if (p.search(member_email)):
                        q = db.GqlQuery('SELECT * FROM Member WHERE email = :1 AND num != :2', member_email.lower(), member.num)
                        if (q.count() > 0):
                            errors = errors + 1
                            member_email_error = 4
                    else:
                        errors = errors + 1
                        member_email_error = 3
            template_values['member_email'] = member_email
            template_values['member_email_error'] = member_email_error
            template_values['member_email_error_message'] = member_email_error_messages[member_email_error]
            # Verification: website
            member_website_error = 0
            member_website_error_messages = ['',
                u'个人网站地址长度不能超过 200 个字符',
                u'这个网站地址不符合规则'
            ]
            member_website = self.request.get('website').strip()
            if (len(member_website) == 0):
                member_website = ''    
            else:
                if (len(member_website) > 200):
                    errors = errors + 1
                    member_website_error = 1
                else:
                    p = re.compile('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
                    if (p.search(member_website)):
                        errors = errors
                    else:
                        errors = errors + 1
                        member_website_error = 2
            template_values['member_website'] = member_website
            template_values['member_website_error'] = member_website_error
            template_values['member_website_error_message'] = member_website_error_messages[member_website_error]
            # Verification: Twitter
            member_twitter_error = 0
            member_twitter_error_messages = ['',
                u'Twitter 用户名长度不能超过 20 个字符',
                u'Twitter 用户名不符合规则'
            ]
            member_twitter = self.request.get('twitter').strip()
            if (len(member_twitter) == 0):
                member_twitter = ''
            else:
                if (len(member_twitter) > 20):
                    errors = errors + 1
                    member_twitter_error = 1
                else:
                    p = re.compile('[a-zA-Z0-9\_]+')
                    if (p.search(member_twitter)):
                        errors = errors
                    else:
                        errors = errors + 1
                        member_twitter_error = 2
            template_values['member_twitter'] = member_twitter
            template_values['member_twitter_error'] = member_twitter_error
            template_values['member_twitter_error_message'] = member_twitter_error_messages[member_twitter_error]
            # Verification: psn
            member_psn_error = 0
            member_psn_error_messages = ['',
                u'PSN ID 长度不能超过 20 个字符',
                u'PSN ID 不符合规则'
            ]
            member_psn = self.request.get('psn').strip()
            if (len(member_psn) == 0):
                member_psn = ''
            else:
                if (len(member_psn) > 20):
                    errors = errors + 1
                    member_psn_error = 1
                else:
                    p = re.compile('^[a-zA-Z0-9\-\_]+$')
                    if (p.search(member_psn)):
                        errors = errors
                    else:
                        errors = errors + 1
                        member_psn_error = 2
            template_values['member_psn'] = member_psn
            template_values['member_psn_error'] = member_psn_error
            template_values['member_psn_error_message'] = member_psn_error_messages[member_psn_error]
            # Verification: my_home
            member_my_home_error = 0
            member_my_home_error_messages = ['',
                u'不是一个合法的自定义首页跳转位置',
                u'自定义首页跳转位置长度不能超过 32 个字符',
                u'自定义首页跳转位置必须以 / 开头'
            ]
            member_my_home = self.request.get('my_home').strip()
            if len(member_my_home) > 0:
                if member_my_home == '/' or member_my_home.startswith('/signout'):
                    member_my_home_error = 1
                    errors = errors + 1
                else:
                    if len(member_my_home) > 32:
                        member_my_home_error = 2
                        errors = errors + 1
                    else:
                        if member_my_home.startswith('/') is not True:
                            member_my_home_error = 3
                            errors = errors + 1
            template_values['member_my_home'] = member_my_home
            template_values['member_my_home_error'] = member_my_home_error
            template_values['member_my_home_error_message'] = member_my_home_error_messages[member_my_home_error]
            # Verification: btc
            member_btc_error = 0
            member_btc_error_messages = ['',
                u'BTC 收款地址长度不能超过 40 个字符',
                u'BTC 收款地址不符合规则'
            ]
            member_btc = self.request.get('btc').strip()
            if (len(member_btc) == 0):
                member_btc = ''
            else:
                if (len(member_btc) > 40):
                    errors = errors + 1
                    member_btc_error = 1
                else:
                    p = re.compile('^[a-zA-Z0-9]+$')
                    if (p.search(member_btc)):
                        errors = errors
                    else:
                        errors = errors + 1
                        member_btc_error = 2
            template_values['member_btc'] = member_btc
            template_values['member_btc_error'] = member_btc_error
            template_values['member_btc_error_message'] = member_btc_error_messages[member_btc_error]
            # Verification: github
            member_github_error = 0
            member_github_error_messages = ['',
                u'GitHub 用户名长度不能超过 40 个字符',
                u'GitHub 用户名不符合规则'
            ]
            member_github = self.request.get('github').strip()
            if (len(member_github) == 0):
                member_github = ''
            else:
                if (len(member_github) > 40):
                    errors = errors + 1
                    member_github_error = 1
                else:
                    p = re.compile('^[a-zA-Z0-9\_]+$')
                    if (p.search(member_github)):
                        errors = errors
                    else:
                        errors = errors + 1
                        member_github_error = 2
            template_values['member_github'] = member_github
            template_values['member_github_error'] = member_github_error
            template_values['member_github_error_message'] = member_github_error_messages[member_github_error]
            # Verification: location
            member_location_error = 0
            member_location_error_messages = ['',
                u'所在地长度不能超过 40 个字符'
            ]
            member_location = self.request.get('location').strip()
            if (len(member_location) == 0):
                member_location = ''    
            else:
                if (len(member_location) > 40):
                    errors = errors + 1
                    member_location_error = 1
            template_values['member_location'] = member_location
            template_values['member_location_error'] = member_location_error
            template_values['member_location_error_message'] = member_location_error_messages[member_location_error]
            # Verification: tagline
            member_tagline_error = 0
            member_tagline_error_messages = ['',
                u'个人签名长度不能超过 70 个字符'
            ]
            member_tagline = self.request.get('tagline').strip()
            if (len(member_tagline) == 0):
                member_tagline = ''    
            else:
                if (len(member_tagline) > 70):
                    errors = errors + 1
                    member_tagline_error = 1
            template_values['member_tagline'] = member_tagline
            template_values['member_tagline_error'] = member_tagline_error
            template_values['member_tagline_error_message'] = member_tagline_error_messages[member_tagline_error]
            # Verification: bio
            member_bio_error = 0
            member_bio_error_messages = ['',
                u'个人简介长度不能超过 2000 个字符'
            ]
            member_bio = self.request.get('bio').strip()
            if (len(member_bio) == 0):
                member_bio = ''    
            else:
                if (len(member_bio) > 2000):
                    errors = errors + 1
                    member_bio_error = 1
            template_values['member_bio'] = member_bio
            template_values['member_bio_error'] = member_bio_error
            template_values['member_bio_error_message'] = member_bio_error_messages[member_bio_error]
            # Verification: show_home_top and show_quick_post
            try:
                member_show_home_top = int(self.request.get('show_home_top'))
            except:
                member_show_home_top = 1
            try:
                member_show_quick_post = int(self.request.get('show_quick_post'))
            except:
                member_show_quick_post = 0
            if member_show_home_top not in [0, 1]:
                member_show_home_top = 1
            if member_show_quick_post not in [0, 1]:
                member_show_quick_post = 0
            # Verification: l10n
            member_l10n = self.request.get('l10n').strip()
            supported = GetSupportedLanguages()
            if member_l10n == '':
                member_l10n = site.l10n
            else:
                if member_l10n not in supported:
                    member_l10n = site.l10n
            s = GetLanguageSelect(member_l10n)
            template_values['s'] = s
            template_values['member_l10n'] = member_l10n
            # Verification: twitter_sync
            if member.twitter_oauth == 1:
                member_twitter_sync = self.request.get('twitter_sync')
                if member_twitter_sync == 'on':
                    member_twitter_sync = 1
                else:
                    member_twitter_sync = 0
                template_values['member_twitter_sync'] = member_twitter_sync
            # Verification: use_my_css
            member_use_my_css = self.request.get('use_my_css')
            if member_use_my_css == 'on':
                member_use_my_css = 1
            else:
                member_use_my_css = 0
            template_values['member_use_my_css'] = member_use_my_css
            # Verification: my_css
            member_my_css_error = 0
            member_my_css_error_messages = ['',
                u'CSS Hack cannot be longer than 2000 characters'
            ]
            member_my_css = self.request.get('my_css').strip()
            if (len(member_my_css) == 0):
                member_my_css = ''    
            else:
                if (len(member_my_css) > 2000):
                    errors = errors + 1
                    member_my_css_error = 1
            template_values['member_my_css'] = member_my_css
            template_values['member_my_css_error'] = member_my_css_error
            template_values['member_my_css_error_message'] = member_my_css_error_messages[member_my_css_error]
            template_values['errors'] = errors
            if (errors == 0):
                member.email = member_email.lower()
                member.website = member_website
                member.twitter = member_twitter
                member.psn = member_psn
                member.btc = member_btc
                member.github = member_github
                member.location = member_location
                member.tagline = member_tagline
                if member.twitter_oauth == 1:
                    member.twitter_sync = member_twitter_sync
                member.use_my_css = member_use_my_css
                member.my_css = member_my_css
                if member_my_home_error == 0 and len(member_my_home) > 0:
                    member.my_home = member_my_home
                else:
                    if member_my_home_error == 0:
                        member.my_home = None
                member.bio = member_bio
                member.show_home_top = member_show_home_top
                member.show_quick_post = member_show_quick_post
                member.l10n = member_l10n
                member.put()
                memcache.delete('Member::' + str(member.username))
                memcache.delete('Member::' + str(member.username_lower))
                memcache.set('Member_' + str(member.num), member, 86400)
                self.session['message'] = '个人设置成功更新'
                self.redirect('/settings')
            else:
                if browser['ios']:
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'member_settings.html')
                else:
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'member_settings.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
        else:
            self.redirect('/signin')


class SettingsPasswordHandler(webapp.RequestHandler):
    def post(self):
        site = GetSite()
        browser = detect(self.request)
        self.session = Session()
        template_values = {}
        template_values['site'] = site
        template_values['page_title'] = site.title + u' › 密码设置'
        template_values['system_version'] = SYSTEM_VERSION
        errors = 0
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            template_values['member'] = member
            template_values['member_username'] = member.username
            template_values['member_email'] = member.email
            # Verification: password
            password_error = 0
            password_update = False
            password_error_messages = ['',
                '新密码长度不能超过 32 个字符',
                '请输入当前密码',
                '当前密码不正确'
            ]
            password_new = self.request.get('password_new').strip()
            if (len(password_new) > 0):
                password_update = True
                if (len(password_new) > 32):
                    password_error = 1
                else:
                    password_current = self.request.get('password_current').strip()
                    if (len(password_current) == 0):
                        password_error = 2
                    else:
                        password_current_sha1 = hashlib.sha1(password_current).hexdigest()
                        if (password_current_sha1 != member.password):
                            password_error = 3
            template_values['password_error'] = password_error
            template_values['password_error_message'] = password_error_messages[password_error]
            if ((password_error == 0) and (password_update == True)):
                old_auth = member.auth
                memcache.delete(old_auth)
                member.password = hashlib.sha1(password_new).hexdigest()
                member.auth = hashlib.sha1(str(member.num) + ':' + member.password).hexdigest()
                member.put()
                memcache.set(member.auth, member.num, 86400 * 14)
                memcache.set('Member_' + str(member.num), member, 86400 * 14)
                self.session['message'] = '密码已成功更新，下次请用新密码登录'
                self.response.headers['Set-Cookie'] = 'auth=' + member.auth + '; expires=' + (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/'
                self.redirect('/settings')
            else:
                if browser['ios']:
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'member_settings_password.html')
                else:
                    path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'member_settings_password.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
        else:
            self.redirect('/signin')

class SettingsAvatarHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        self.session = Session()
        browser = detect(self.request)
        template_values = {}
        template_values['site'] = site
        template_values['page_title'] = site.title + u' › 头像'
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            if 'message' in self.session:
                template_values['message'] = self.session['message']
                del self.session['message']
            template_values['member'] = member
            if browser['ios']:
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'mobile', 'member_settings_avatar.html')
            else:
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'member_settings_avatar.html')
            output = template.render(path, template_values)
            self.response.out.write(output)
        else:
            self.redirect('/signin')
        
    def post(self):
        site = GetSite()
        self.session = Session()
        browser = detect(self.request)
        template_values = {}
        template_values['site'] = site
        template_values['system_version'] = SYSTEM_VERSION
        member = CheckAuth(self)
        l10n = GetMessages(self, member, site)
        template_values['l10n'] = l10n
        if (member):
            dest = '/settings/avatar'
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
            q1 = db.GqlQuery("SELECT * FROM Avatar WHERE name = :1", 'avatar_' + str(member.num) + '_large')
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
                avatar_large.name = 'avatar_' + str(member.num) + '_large'
                avatar_large.content = db.Blob(avatar_73)
                avatar_large.num = counter1.value
                avatar_large.put()
            member.avatar_large_url = '/avatar/' + str(member.num) + '/large?r=' + timestamp
            member.put()
            # Normal 48x48
            q2 = db.GqlQuery("SELECT * FROM Avatar WHERE name = :1", 'avatar_' + str(member.num) + '_normal')
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
                avatar_normal.name = 'avatar_' + str(member.num) + '_normal'
                avatar_normal.content = db.Blob(avatar_48)
                avatar_normal.num = counter2.value
                avatar_normal.put()
            member.avatar_normal_url = '/avatar/' + str(member.num) + '/normal?r=' + timestamp
            member.put() 
            # Mini 24x24
            q3 = db.GqlQuery("SELECT * FROM Avatar WHERE name = :1", 'avatar_' + str(member.num) + '_mini')
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
                avatar_mini.name = 'avatar_' + str(member.num) + '_mini'
                avatar_mini.content = db.Blob(avatar_24)
                avatar_mini.num = counter3.value
                avatar_mini.put()
            member.avatar_mini_url = '/avatar/' + str(member.num) + '/mini?r=' + timestamp
            member.put()
            # Upload to MobileMe
            if config.mobileme_enabled:
                headers = {'Authorization' : 'Basic ' + base64.b64encode(config.mobileme_username + ':' + config.mobileme_password)}
                host = 'idisk.me.com'
                # Sharding
                timestamp = str(int(time.time()))
                shard = member.num % 31
                root = '/' + config.mobileme_username + '/Web/Sites/v2ex/avatars/' + str(shard)
                root_mini = root + '/mini'
                root_normal = root + '/normal'
                root_large = root + '/large'
                h = httplib.HTTPConnection(host)
                # Mini
                h.request('PUT', root_mini + '/' + str(member.num) + '.png', str(avatar_24), headers)
                response = h.getresponse()
                if response.status == 201 or response.status == 204:
                    member.avatar_mini_url = 'http://web.me.com/' + config.mobileme_username + '/v2ex/avatars/' + str(shard) + '/mini/' + str(member.num) + '.png?r=' + timestamp
                # Normal
                h.request('PUT', root_normal + '/' + str(member.num) + '.png', str(avatar_48), headers)
                response = h.getresponse()
                if response.status == 201 or response.status == 204:
                    member.avatar_normal_url = 'http://web.me.com/' + config.mobileme_username + '/v2ex/avatars/' + str(shard) + '/normal/' + str(member.num) + '.png?r=' + timestamp
                # Large
                h.request('PUT', root_large + '/' + str(member.num) + '.png', str(avatar_73), headers)
                response = h.getresponse()
                if response.status == 201 or response.status == 204:
                    member.avatar_large_url = 'http://web.me.com/' + config.mobileme_username + '/v2ex/avatars/' + str(shard) + '/large/' + str(member.num) + '.png?r=' + timestamp
                member.put()
            # Upload to UpYun
            if config.upyun_enabled:
                u = UpYun(config.upyun_bucket, config.upyun_username, config.upyun_password)
                # Mini
                mini = avatar_24
                u.setContentMD5(md5(mini))
                mini_suffix = '/avatars/mini/' + str(member.num) + '.png'
                r = u.writeFile(mini_suffix, mini, True)
                if r == True:
                    member.avatar_mini_url = 'http://' + config.upyun_bucket + '.b0.upaiyun.com' + mini_suffix + '?r=' + timestamp
                # Normal
                normal = avatar_48
                u.setContentMD5(md5(normal))
                normal_suffix = '/avatars/normal/' + str(member.num) + '.png'
                r = u.writeFile(normal_suffix, normal, True)
                if r == True:
                    member.avatar_normal_url = 'http://' + config.upyun_bucket + '.b0.upaiyun.com' + normal_suffix + '?r=' + timestamp
                # Large
                large = avatar_73
                u.setContentMD5(md5(large))
                large_suffix = '/avatars/large/' + str(member.num) + '.png'
                r = u.writeFile(large_suffix, large, True)
                if r == True:
                    member.avatar_large_url = 'http://' + config.upyun_bucket + '.b0.upaiyun.com' + large_suffix + '?r=' + timestamp
                member.put()
            memcache.set('Member_' + str(member.num), member, 86400 * 14)
            memcache.set('Member::' + member.username_lower, member, 86400 * 14)
            memcache.delete('Avatar::avatar_' + str(member.num) + '_large')
            memcache.delete('Avatar::avatar_' + str(member.num) + '_normal')
            memcache.delete('Avatar::avatar_' + str(member.num) + '_mini')
            self.session['message'] = '新头像设置成功'
            self.redirect('/settings/avatar')
        else:
            self.redirect('/signin')


class AvatarStringIO(StringIO):
    def __len__(self):
        content = self.read()
        return len(content)

class MemberBlockHandler(webapp.RequestHandler):
    def get(self, key):
        go = '/'
        member = CheckAuth(self)
        if member:
            member = db.get(member.key())
            one = db.get(db.Key(key))
            if one:
                if one.num != member.num:
                    try:
                        blocked = pickle.loads(member.blocked.encode('utf-8'))
                    except:
                        blocked = []
                    if len(blocked) == 0:
                        blocked = []
                    if one.num not in blocked:
                        blocked.append(one.num)
                    member.blocked = pickle.dumps(blocked)
                    member.put()
                    memcache.set('Member_' + str(member.num), member, 86400)
        self.redirect(go)

class MemberUnblockHandler(webapp.RequestHandler):
    def get(self, key):
        go = '/'
        member = CheckAuth(self)
        if member:
            member = db.get(member.key())
            one = db.get(db.Key(key))
            if one:
                if one.num != member.num:
                    try:
                        blocked = pickle.loads(member.blocked.encode('utf-8'))
                    except:
                        blocked = []
                    if len(blocked) == 0:
                        blocked = []
                    if one.num  in blocked:
                        blocked.remove(one.num)
                    member.blocked = pickle.dumps(blocked)
                    member.put()
                    memcache.set('Member_' + str(member.num), member, 86400)
        self.redirect(go)

def main():
    application = webapp.WSGIApplication([
    ('/member/([a-z0-9A-Z\_\-]+)', MemberHandler),
    ('/member/([a-z0-9A-Z\_\-]+).json', MemberApiHandler),
    ('/settings', SettingsHandler),
    ('/settings/password', SettingsPasswordHandler),
    ('/settings/avatar', SettingsAvatarHandler),
    ('/block/(.*)', MemberBlockHandler),
    ('/unblock/(.*)', MemberUnblockHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
