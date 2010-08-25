#!/usr/bin/env python
# coding=utf-8

import os
import re
import time
import datetime
import hashlib
import string
import random
import logging

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
from v2ex.babel.ext.cookies import Cookies
from v2ex.babel.ext.sessions import Session

from twitter.oauthtwitter import OAuthApi
from twitter.oauth import OAuthToken

from config import twitter_consumer_key as CONSUMER_KEY
from config import twitter_consumer_secret as CONSUMER_SECRET

template.register_template_library('v2ex.templatetags.filters')

class TwitterLinkHandler(webapp.RequestHandler):
    def get(self):
        self.session = Session()
        member = CheckAuth(self)
        if member:
            twitter = OAuthApi(CONSUMER_KEY, CONSUMER_SECRET)
            request_token = twitter.getRequestToken()
            authorization_url = twitter.getAuthorizationURL(request_token)
            self.session['request_token'] = request_token
            self.redirect(authorization_url)
        else:
            self.redirect('/signin')

class TwitterUnlinkHandler(webapp.RequestHandler):
    def get(self):
        self.session = Session()
        member = CheckAuth(self)
        if member:
            memcache.delete('Member_' + str(member.num))
            member = GetKindByNum('Member', member.num)
            member.twitter_oauth = 0
            member.twitter_oauth_key = ''
            member.twitter_oauth_secret = ''
            member.twitter_sync = 0
            member.put()
            memcache.set('Member_' + str(member.num), member, 86400)
            self.redirect('/settings')
        else:
            self.redirect('/signin')

class TwitterCallbackHandler(webapp.RequestHandler):
    def get(self):
        self.session = Session()
        member = CheckAuth(self)
        host = self.request.headers['Host']
        if host == 'localhost:10000' or host == '127.0.0.1:10000':
            # Local debugging logic
            if member:
                request_token = self.session['request_token']
                twitter = OAuthApi(CONSUMER_KEY, CONSUMER_SECRET, request_token)
                access_token = twitter.getAccessToken()
                twitter = OAuthApi(CONSUMER_KEY, CONSUMER_SECRET, access_token)
                user = twitter.GetUserInfo()
                memcache.delete('Member_' + str(member.num))
                member = db.GqlQuery("SELECT * FROM Member WHERE num = :1", member.num)[0]
                member.twitter_oauth = 1
                member.twitter_oauth_key = access_token.key
                member.twitter_oauth_secret = access_token.secret
                member.twitter_oauth_string = access_token.to_string()
                member.twitter_sync = 0
                member.twitter_id = user.id
                member.twitter_name = user.name
                member.twitter_screen_name = user.screen_name
                member.twitter_location = user.location
                member.twitter_description = user.description
                member.twitter_profile_image_url = user.profile_image_url
                member.twitter_url = user.url
                member.twitter_statuses_count = user.statuses_count
                member.twitter_followers_count = user.followers_count
                member.twitter_friends_count = user.friends_count
                member.twitter_favourites_count = user.favourites_count
                member.put()
                memcache.set('Member_' + str(member.num), member, 86400)
                self.redirect('/settings')
            else:
                self.redirect('/signin')
        else:
            # Remote production logic
            if member and 'request_token' in self.session:
                request_token = self.session['request_token']
                twitter = OAuthApi(CONSUMER_KEY, CONSUMER_SECRET, request_token)
                access_token = twitter.getAccessToken()
                twitter = OAuthApi(CONSUMER_KEY, CONSUMER_SECRET, access_token)
                user = twitter.GetUserInfo()
                memcache.delete('Member_' + str(member.num))
                member = db.GqlQuery("SELECT * FROM Member WHERE num = :1", member.num)[0]
                member.twitter_oauth = 1
                member.twitter_oauth_key = access_token.key
                member.twitter_oauth_secret = access_token.secret
                member.twitter_oauth_string = access_token.to_string()
                member.twitter_sync = 0
                member.twitter_id = user.id
                member.twitter_name = user.name
                member.twitter_screen_name = user.screen_name
                member.twitter_location = user.location
                member.twitter_description = user.description
                member.twitter_profile_image_url = user.profile_image_url
                member.twitter_url = user.url
                member.twitter_statuses_count = user.statuses_count
                member.twitter_followers_count = user.followers_count
                member.twitter_friends_count = user.friends_count
                member.twitter_favourites_count = user.favourites_count
                member.put()
                memcache.set('Member_' + str(member.num), member, 86400)
                self.redirect('/settings')
            else:
                oauth_token = self.request.get('oauth_token')
                if host == 'v2ex.appspot.com':
                    self.redirect('http://www.v2ex.com/twitter/oauth?oauth_token=' + oauth_token)
                else:
                    self.redirect('http://v2ex.appspot.com/twitter/oauth?oauth_token=' + oauth_token)        

class TwitterHomeHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        member = CheckAuth(self)
        if member:
            if member.twitter_oauth == 1:
                template_values = {}
                template_values['site'] = site
                template_values['rnd'] = random.randrange(1, 100)
                template_values['member'] = member
                template_values['page_title'] = site.title + u' › Twitter › Home'
                access_token = OAuthToken.from_string(member.twitter_oauth_string)
                twitter = OAuthApi(CONSUMER_KEY, CONSUMER_SECRET, access_token)
                rate_limit = memcache.get(str(member.twitter_id) + '::rate_limit')
                if rate_limit is None:
                    try:
                        rate_limit = twitter.GetRateLimit()
                        memcache.set(str(member.twitter_id) + '::rate_limit', rate_limit, 60)
                    except:
                        logging.info('Failed to get rate limit for @' + member.twitter_screen_name)
                template_values['rate_limit'] = rate_limit
                cache_tag = 'member::' + str(member.num) + '::twitter::home'
                statuses = memcache.get(cache_tag)
                if statuses is None:
                    statuses = twitter.GetHomeTimeline(count = 50)
                    i = 0;
                    for status in statuses:
                        statuses[i].source = statuses[i].source.replace('<a', '<a class="dark"')
                        statuses[i].datetime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(status.created_at, '%a %b %d %H:%M:%S +0000 %Y')))
                        statuses[i].text = twitter.ConvertMentions(status.text)
                        #statuses[i].text = twitter.ExpandBitly(status.text)
                        i = i + 1
                    memcache.set(cache_tag, statuses, 120)
                template_values['statuses'] = statuses
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'twitter_home.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                self.redirect('/settings')
        else:
            self.redirect('/')

class TwitterMentionsHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        member = CheckAuth(self)
        if member:
            if member.twitter_oauth == 1:
                template_values = {}
                template_values['site'] = site
                template_values['rnd'] = random.randrange(1, 100)
                template_values['member'] = member
                template_values['page_title'] = site.title + u' › Twitter › Mentions'
                access_token = OAuthToken.from_string(member.twitter_oauth_string)
                twitter = OAuthApi(CONSUMER_KEY, CONSUMER_SECRET, access_token)
                rate_limit = memcache.get(str(member.twitter_id) + '::rate_limit')
                if rate_limit is None:
                    try:
                        rate_limit = twitter.GetRateLimit()
                        memcache.set(str(member.twitter_id) + '::rate_limit', rate_limit, 60)
                    except:
                        logging.info('Failed to get rate limit for @' + member.twitter_screen_name)
                template_values['rate_limit'] = rate_limit
                cache_tag = 'member::' + str(member.num) + '::twitter::mentions'
                statuses = memcache.get(cache_tag)
                if statuses is None:
                    statuses = twitter.GetReplies()
                    i = 0;
                    for status in statuses:
                        statuses[i].source = statuses[i].source.replace('<a', '<a class="dark"')
                        statuses[i].datetime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(status.created_at, '%a %b %d %H:%M:%S +0000 %Y')))
                        statuses[i].text = twitter.ConvertMentions(status.text)
                        #statuses[i].text = twitter.ExpandBitly(status.text)
                        i = i + 1
                    memcache.set(cache_tag, statuses, 120)
                template_values['statuses'] = statuses
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'twitter_mentions.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                self.redirect('/settings')
        else:
            self.redirect('/')

class TwitterDMInboxHandler(webapp.RequestHandler):
    def get(self):
        member = CheckAuth(self)
        site = GetSite()
        if member:
            if member.twitter_oauth == 1:
                template_values = {}
                template_values['site'] = site
                template_values['rnd'] = random.randrange(1, 100)
                template_values['member'] = member
                template_values['page_title'] = site.title + u' › Twitter › Direct Messages › Inbox'
                access_token = OAuthToken.from_string(member.twitter_oauth_string)
                twitter = OAuthApi(CONSUMER_KEY, CONSUMER_SECRET, access_token)
                rate_limit = memcache.get(str(member.twitter_id) + '::rate_limit')
                if rate_limit is None:
                    try:
                        rate_limit = twitter.GetRateLimit()
                        memcache.set(str(member.twitter_id) + '::rate_limit', rate_limit, 60)
                    except:
                        logging.info('Failed to get rate limit for @' + member.twitter_screen_name)
                template_values['rate_limit'] = rate_limit
                cache_tag = 'member::' + str(member.num) + '::twitter::dm::inbox'
                messages = memcache.get(cache_tag)
                if messages is None:
                    messages = twitter.GetDirectMessages()
                    i = 0;
                    for message in messages:
                        messages[i].datetime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(message.created_at, '%a %b %d %H:%M:%S +0000 %Y')))
                        messages[i].text = twitter.ConvertMentions(message.text)
                        #statuses[i].text = twitter.ExpandBitly(status.text)
                        i = i + 1
                    memcache.set(cache_tag, messages, 120)
                template_values['messages'] = messages
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'twitter_dm_inbox.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                self.redirect('/settings')
        else:
            self.redirect('/')

class TwitterUserTimelineHandler(webapp.RequestHandler):
    def get(self, screen_name):
        site = GetSite()
        member = CheckAuth(self)
        if member:
            if member.twitter_oauth == 1:
                template_values = {}
                template_values['site'] = site
                template_values['rnd'] = random.randrange(1, 100)
                template_values['member'] = member
                template_values['page_title'] = site.title + u' › Twitter › ' + screen_name
                template_values['screen_name'] = screen_name
                access_token = OAuthToken.from_string(member.twitter_oauth_string)
                twitter = OAuthApi(CONSUMER_KEY, CONSUMER_SECRET, access_token)
                rate_limit = memcache.get(str(member.twitter_id) + '::rate_limit')
                if rate_limit is None:
                    try:
                        rate_limit = twitter.GetRateLimit()
                        memcache.set(str(member.twitter_id) + '::rate_limit', rate_limit, 60)
                    except:
                        logging.info('Failed to get rate limit for @' + member.twitter_screen_name)
                template_values['rate_limit'] = rate_limit
                cache_tag = 'twitter::' + screen_name + '::home'
                statuses = memcache.get(cache_tag)
                if statuses is None:
                    statuses = twitter.GetUserTimeline(user=screen_name, count = 50)
                    i = 0;
                    for status in statuses:
                        statuses[i].source = statuses[i].source.replace('<a', '<a class="dark"')
                        statuses[i].datetime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(status.created_at, '%a %b %d %H:%M:%S +0000 %Y')))
                        statuses[i].text = twitter.ConvertMentions(status.text)
                        #statuses[i].text = twitter.ExpandBitly(status.text)
                        i = i + 1
                    memcache.set(cache_tag, statuses, 120)
                template_values['statuses'] = statuses
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'twitter_user.html')
                output = template.render(path, template_values)
                self.response.out.write(output)
            else:
                self.redirect('/settings')
        else:
            self.redirect('/')
                        
class TwitterTweetHandler(webapp.RequestHandler):
    def post(self):
        if 'Referer' in self.request.headers:
            go = self.request.headers['Referer']
        else:
            go = '/'
        member = CheckAuth(self)
        if member:
            if member.twitter_oauth == 1:
                status = self.request.get('status')
                if len(status) > 140:
                    status = status[0:140]
                access_token = OAuthToken.from_string(member.twitter_oauth_string)
                twitter = OAuthApi(CONSUMER_KEY, CONSUMER_SECRET, access_token)
                try:
                    twitter.PostUpdate(status.encode('utf-8'))
                    memcache.delete('member::' + str(member.num) + '::twitter::home')
                except:
                    logging.error('Failed to tweet: ' + status)
                self.redirect(go)
            else:
                self.redirect('/twitter/link')
        else:
            self.redirect('/')
        
class TwitterApiCheatSheetHandler(webapp.RequestHandler):
    def head(self):
        template_values = {}
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'twitter_api_cheat_sheet.html')
        output = template.render(path, template_values)
        self.response.out.write(output)
        
    def get(self):
        template_values = {}
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'twitter_api_cheat_sheet.html')
        output = template.render(path, template_values)
        self.response.out.write(output)
        
def main():
    application = webapp.WSGIApplication([
    ('/twitter/?', TwitterHomeHandler),
    ('/twitter/mentions/?', TwitterMentionsHandler),
    ('/twitter/inbox/?', TwitterDMInboxHandler),
    ('/twitter/user/([a-zA-Z0-9\_]+)', TwitterUserTimelineHandler),
    ('/twitter/link', TwitterLinkHandler),
    ('/twitter/unlink', TwitterUnlinkHandler),
    ('/twitter/oauth', TwitterCallbackHandler),
    ('/twitter/tweet', TwitterTweetHandler),
    ('/twitter/api/?', TwitterApiCheatSheetHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()