#!/usr/bin/env python
# coding=utf-8

import logging
import re
import hashlib
import urllib

from v2ex.babel import Member

from v2ex.babel.da import *

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import xmpp
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import xmpp_handlers
from google.appengine.ext.webapp.util import run_wsgi_app

from twitter.twitter import Api
from twitter.oauthtwitter import OAuthApi
from twitter.oauth import OAuthToken

from config import twitter_consumer_key as CONSUMER_KEY
from config import twitter_consumer_secret as CONSUMER_SECRET

from django.utils import simplejson as json

def extract_address(raw):
    if raw.find('/') == -1:
        return raw
    else:
        return raw.split('/')[0]

class XMPPHandler(webapp.RequestHandler):
    def post(self):
        message = xmpp.Message(self.request.POST)
        to = extract_address(message.to.lower())
        sender = extract_address(message.sender.lower())
        member = GetMemberByEmail(sender)
        if member:
            if member.twitter_oauth == 1:
                access_token = OAuthToken.from_string(member.twitter_oauth_string)
                twitter = OAuthApi(CONSUMER_KEY, CONSUMER_SECRET, access_token)
                status = message.body
                result = None
                if len(status) > 140:
                    status = status[0:140]
                try:
                    if message.command is not None:
                        command = message.command.lower()
                        if command == 'mentions' or command == 'm' or command == 'r':
                            logging.info('About to get mentions for @' + member.twitter_screen_name)
                            statuses = twitter.GetReplies()
                            msg = ''
                            i = 0
                            for s in statuses:
                                msg = msg + '@' + s.user.screen_name + ': ' + s.text + "\n\n"
                                i = i + 1
                                if i > 5:
                                    break
                            xmpp.send_message(message.sender, msg)
                        if command == 'search' or command == 'q' or command == 's':
                            q = re.findall('/' + command + ' (.+)', message.body)[0]
                            url = 'http://twitter.com/search.json?q=' + urllib.quote(q)
                            response = urlfetch.fetch(url)
                            logging.info(response.status_code)
                            data = json.loads(response.content)
                            msg = ''
                            i = 0
                            for s in data['results']:
                                msg = msg + '@' + s['from_user'] + ': ' + s['text'] + "\n\n"
                                i = i + 1
                                if i > 5:
                                    break
                            xmpp.send_message(message.sender, msg)
                    else:
                        if status.lower() == 'ls':
                            logging.info('About to get home timeline for @' + member.twitter_screen_name)
                            statuses = twitter.GetHomeTimeline(count = 5)
                            msg = ''
                            i = 0
                            for s in statuses:
                                msg = msg + '@' + s.user.screen_name + ': ' + s.text + "\n\n"
                            xmpp.send_message(message.sender, msg)
                        else:
                            logging.info("About to send tweet: " + status)
                            result = twitter.PostUpdate(status.encode('utf-8'))
                            logging.info("Successfully tweet: " + status)
                except:
                    logging.error("Failed to tweet for " + member.username)
                if result is not None:
                    msg = 'OK: http://twitter.com/' + result.user.screen_name + '/status/' + str(result.id)
                    xmpp.send_message(message.sender, msg)
            else:
                logging.error("User " + sender + " doesn't have Twitter link.")
        else:
            logging.error("Cannot find a corresponding member for " + message.sender) 

application = webapp.WSGIApplication([
    ('/_ah/xmpp/message/chat/', XMPPHandler)
], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()