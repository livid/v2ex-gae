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
from v2ex.babel.da import *
from v2ex.babel.l10n import *

class AddStarTopicHandler(webapp.RequestHandler):
    def post(self, topic_key):
        topic = db.get(db.Key(topic_key))
        if topic:
            topic.stars = topic.stars + 1
            topic.put()
            memcache.set('Topic_' + str(topic.num), topic, 86400)

class MinusStarTopicHandler(webapp.RequestHandler):
    def post(self, topic_key):
        topic = db.get(db.Key(topic_key))
        if topic:
            topic.stars = topic.stars - 1
            topic.put()
            memcache.set('Topic_' + str(topic.num), topic, 86400)


def main():
    application = webapp.WSGIApplication([
    ('/add/star/topic/(.*)', AddStarTopicHandler),
    ('/minus/star/topic/(.*)', MinusStarTopicHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()