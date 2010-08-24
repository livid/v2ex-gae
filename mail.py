#!/usr/bin/env python
# coding=utf-8

import logging
import re

from v2ex.babel import Member

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.ext.webapp.util import run_wsgi_app

from twitter.oauthtwitter import OAuthApi
from twitter.oauth import OAuthToken

from config import twitter_consumer_key as CONSUMER_KEY
from config import twitter_consumer_secret as CONSUMER_SECRET

def extract_address(raw):
    if raw.find('<') == -1:
        return raw
    else:
        return re.findall('<(.+)>', raw)[0]

class MailHandler(InboundMailHandler):
    def receive(self, message):
        bodies = message.bodies(content_type = 'text/plain')
        for body in bodies:
            to = extract_address(message.to)
            sender = extract_address(message.sender.lower())
            if to[0:5].lower() == 'tweet':
                q = db.GqlQuery("SELECT * FROM Member WHERE email = :1", sender)
                if q.count() == 1:
                    member = q[0]
                    if member.twitter_oauth == 1:
                        access_token = OAuthToken.from_string(member.twitter_oauth_string)
                        twitter = OAuthApi(CONSUMER_KEY, CONSUMER_SECRET, access_token)
                        status = body[1].decode()
                        if len(status) > 140:
                            status = status[0:140]
                        try:
                            logging.info("About to send tweet: " + status)
                            twitter.PostUpdate(status.encode('utf-8'))
                            logging.info("Successfully tweet: " + status)
                        except:
                            logging.error("Failed to tweet for " + member.username)
                else:
                    logging.error("User " + sender + " doesn't have Twitter link.")

application = webapp.WSGIApplication([
    MailHandler.mapping()
], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()