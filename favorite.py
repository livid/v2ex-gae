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
from google.appengine.api.labs import taskqueue

from v2ex.babel import Member
from v2ex.babel import Counter
from v2ex.babel import Section
from v2ex.babel import Node
from v2ex.babel import Topic
from v2ex.babel import Reply
from v2ex.babel import Note
from v2ex.babel import NodeBookmark
from v2ex.babel import TopicBookmark

from v2ex.babel import SYSTEM_VERSION

from v2ex.babel.security import *
from v2ex.babel.ua import *
from v2ex.babel.da import *

class FavoriteNodeHandler(webapp.RequestHandler):
    def get(self, node_name):
        if 'Referer' in self.request.headers:
            go = self.request.headers['Referer']
        else:
            go = '/'
        member = CheckAuth(self)
        if member:
            node = GetKindByName('Node', node_name)
            if node is not False:
                q = db.GqlQuery("SELECT * FROM NodeBookmark WHERE node = :1 AND member = :2", node, member)
                if q.count() == 0:
                    bookmark = NodeBookmark(parent=member)
                    bookmark.node = node
                    bookmark.member = member
                    bookmark.put()
                    member.favorited_nodes = member.favorited_nodes + 1
                    member.put()
                    n = 'r/n' + str(node.num) + '/m' + str(member.num)
                    memcache.set(n, True, 86400 * 14)
        self.redirect(go)
    
class UnfavoriteNodeHandler(webapp.RequestHandler):
    def get(self, node_name):
        if 'Referer' in self.request.headers:
            go = self.request.headers['Referer']
        else:
            go = '/'
        member = CheckAuth(self)
        if member:
            node = GetKindByName('Node', node_name)
            if node is not False:
                q = db.GqlQuery("SELECT * FROM NodeBookmark WHERE node = :1 AND member = :2", node, member)
                if q.count() > 0:
                    bookmark = q[0]
                    bookmark.delete()
                    member.favorited_nodes = member.favorited_nodes - 1
                    member.put()
                    n = 'r/n' + str(node.num) + '/m' + str(member.num)
                    memcache.delete(n)
        self.redirect(go)

class FavoriteTopicHandler(webapp.RequestHandler):
    def get(self, topic_num):
        if 'Referer' in self.request.headers:
            go = self.request.headers['Referer']
        else:
            go = '/'
        member = CheckAuth(self)
        if member:
            topic = GetKindByNum('Topic', int(topic_num))
            if topic is not False:
                q = db.GqlQuery("SELECT * FROM TopicBookmark WHERE topic = :1 AND member = :2", topic, member)
                if q.count() == 0:
                    bookmark = TopicBookmark(parent=member)
                    bookmark.topic = topic
                    bookmark.member = member
                    bookmark.put()
                    member.favorited_topics = member.favorited_topics + 1
                    member.put()
                    n = 'r/t' + str(topic.num) + '/m' + str(member.num)
                    memcache.set(n, True, 86400 * 14)
                    taskqueue.add(url='/add/star/topic/' + str(topic.key()))
        self.redirect(go)

class UnfavoriteTopicHandler(webapp.RequestHandler):
    def get(self, topic_num):
        if 'Referer' in self.request.headers:
            go = self.request.headers['Referer']
        else:
            go = '/'
        member = CheckAuth(self)
        if member:
            topic = GetKindByNum('Topic', int(topic_num))
            if topic is not False:
                q = db.GqlQuery("SELECT * FROM TopicBookmark WHERE topic = :1 AND member = :2", topic, member)
                if q.count() > 0:
                    bookmark = q[0]
                    bookmark.delete()
                    member.favorited_topics = member.favorited_topics - 1
                    member.put()
                    n = 'r/t' + str(topic.num) + '/m' + str(member.num)
                    memcache.delete(n)
                    taskqueue.add(url='/minus/star/topic/' + str(topic.key()))
        self.redirect(go)

def main():
    application = webapp.WSGIApplication([
    ('/favorite/node/([a-zA-Z0-9]+)', FavoriteNodeHandler),
    ('/unfavorite/node/([a-zA-Z0-9]+)', UnfavoriteNodeHandler),
    ('/favorite/topic/([0-9]+)', FavoriteTopicHandler),
    ('/unfavorite/topic/([0-9]+)', UnfavoriteTopicHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()