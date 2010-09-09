#!/usr/bin/env python
# coding=utf-8

import os
import re
import time
import datetime
import hashlib
import string
import random
import base64

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

template.register_template_library('v2ex.templatetags.filters')


# Site
# /api/site/stats.json
class SiteStatsHandler(webapp.RequestHandler):
    def get(self):
        template_values = {}
        template_values['topic_max'] = GetKindByName('Counter', 'topic.max')
        template_values['member_max'] = GetKindByName('Counter', 'member.max')
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'site_stats.json')
        output = template.render(path, template_values)
        self.response.headers['Content-type'] = 'application/json'
        self.response.out.write(output)

# /api/site/info.json
class SiteInfoHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'site_info.json')
        output = template.render(path, template_values)
        self.response.headers['Content-type'] = 'application/json'
        self.response.out.write(output)

# Nodes
# /api/nodes/all.json
class NodesAllHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        nodes = memcache.get('api_nodes_all')
        if nodes is None:
            nodes = db.GqlQuery("SELECT * FROM Node")
            memcache.set('api_nodes_all', nodes, 3600)
        template_values['nodes'] = nodes
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'nodes_all.json')
        output = template.render(path, template_values)
        self.response.headers['Content-type'] = 'application/json'
        self.response.out.write(output)

# /api/nodes/show.json
class NodesShowHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        method_determined = False
        parameter_id = self.request.get('id')
        if parameter_id:
            method_determined = True
        if method_determined is not True:
            parameter_name = self.request.get('name')
            if parameter_name:
                method_determined = True
        if method_determined is True:
            if parameter_id:
                node = GetKindByNum('Node', int(parameter_id))
            else:
                node = GetKindByName('Node', str(parameter_name))
            if node is not False:
                template_values['node'] = node
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'nodes_show.json')
                output = template.render(path, template_values)
                self.response.headers['Content-type'] = 'application/json'
                self.response.out.write(output)
            else:
                template_values['message'] = 'Node not found'
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'error.json')
                output = template.render(path, template_values)
                self.response.headers['Content-type'] = 'application/json'
                self.response.out.write(output)
        else:
            template_values['message'] = "Required parameter id or name is missing"
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'error.json')
            output = template.render(path, template_values)
            self.response.headers['Content-type'] = 'application/json'
            self.response.out.write(output)

# Topics
# /api/topics/latest.json
class TopicsLatestHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        topics = memcache.get('api_topics_latest')
        if topics is None:
            topics = db.GqlQuery("SELECT * FROM Topic ORDER BY created DESC LIMIT 20")
            memcache.set('api_topics_latest', topics, 120)
        template_values['topics'] = topics
        template_values['topics_count'] = topics.count()
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'topics_latest.json')
        output = template.render(path, template_values)
        self.response.headers['Content-type'] = 'application/json'
        self.response.out.write(output)

# /api/topics/show.json
class TopicsShowHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        method_determined = False
        parameter_id = self.request.get('id')
        parameter_username = False
        parameter_node_id = False
        parameter_node_name = False
        if parameter_id:
            method_determined = True
        if method_determined is False:
            parameter_username = self.request.get('username')
            if parameter_username:
                method_determined = True
        if method_determined is False:
            parameter_node_id = self.request.get('node_id')
            if parameter_node_id:
                method_determined = True
        if method_determined is False:
            parameter_node_name = self.request.get('node_name')
            if parameter_node_name:
                method_determined = True
        if method_determined is False:
            template_values['message'] = "Required parameter id, username, node_id or node_name is missing"
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'error.json')
            output = template.render(path, template_values)
            self.response.set_status(400, 'Bad Request')
            self.response.headers['Content-type'] = 'application/json'
            self.response.out.write(output)
        else:
            topics = False
            topic = False
            if parameter_id:
                try:
                    topic = GetKindByNum('Topic', int(parameter_id))
                    if topic is not False:
                        topics = []
                        topics.append(topic)
                        template_values['topic'] = topic
                except:
                    topics = False
            if topics is False:
                if parameter_username:
                    one = GetMemberByUsername(parameter_username)
                    if one is not False:
                        topics = db.GqlQuery("SELECT * FROM Topic WHERE member_num = :1 ORDER BY created DESC LIMIT 20", one.num)
                        template_values['topics'] = topics
            if topics is False:
                try:
                    if parameter_node_id:
                        node = GetKindByNum('Node', int(parameter_node_id))
                        if node is not False:
                            topics = db.GqlQuery("SELECT * FROM Topic WHERE node_num = :1 ORDER BY last_touched DESC LIMIT 20", node.num)
                            template_values['topics'] = topics
                except:
                    topics = False
            if topics is False:
                if parameter_node_name:
                    node = GetKindByName('Node', str(parameter_node_name))
                    if node is not False:
                        topics = db.GqlQuery("SELECT * FROM Topic WHERE node_num = :1 ORDER BY last_touched DESC LIMIT 20", node.num)
                        template_values['topics'] = topics
            if topic or topics:
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'topics_show.json')
                output = template.render(path, template_values)
                self.response.headers['Content-type'] = 'application/json'
                self.response.out.write(output)
            else:
                template_values['message'] = "Failed to get topics"
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'error.json')
                output = template.render(path, template_values)
                self.response.set_status(400, 'Bad Request')
                self.response.headers['Content-type'] = 'application/json'
                self.response.out.write(output)

# /api/topics/create.json
class TopicsCreateHandler(webapp.RequestHandler):
    def post(self):
        authenticated = False
        if 'Authorization' in self.request.headers:
            auth = self.request.headers['Authorization']
            decoded = base64.b64decode(auth[6:])
            authenticated = True
        if authenticated:
            self.response.out.write('OK')
        else:    
            site = GetSite()
            template_values = {}
            template_values['site'] = site
            template_values['message'] = "Authentication required"
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'error.json')
            output = template.render(path, template_values)
            self.response.set_status(401, 'Unauthorized')
            self.response.headers['Content-type'] = 'application/json'
            self.response.headers['WWW-Authenticate'] = 'Basic realm="' + site.domain + '"'
            self.response.out.write(output)

# Users
# /api/members/show.json
class MembersShowHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        template_values = {}
        template_values['site'] = site
        username = self.request.get('username')
        if username:
            one = GetMemberByUsername(username)
            if one is not False:
                if one.avatar_mini_url:
                    if (one.avatar_mini_url[0:1] == '/'):
                        one.avatar_mini_url = 'http://' + site.domain + one.avatar_mini_url
                        one.avatar_normal_url = 'http://' +  site.domain + one.avatar_normal_url
                        one.avatar_large_url = 'http://' + site.domain + one.avatar_large_url
                template_values['member'] = one
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'members_show.json')
                output = template.render(path, template_values)
                self.response.headers['Content-type'] = 'application/json'
                self.response.out.write(output)
            else:
                template_values['message'] = "Member not found"
                path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'error.json')
                output = template.render(path, template_values)
                self.response.set_status(400, 'Bad Request')
                self.response.headers['Content-type'] = 'application/json'
                self.response.out.write(output)
        else:
            template_values['message'] = "Required parameter username is missing"
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'api', 'error.json')
            output = template.render(path, template_values)
            self.response.set_status(400, 'Bad Request')
            self.response.headers['Content-type'] = 'application/json'
            self.response.out.write(output)
                

def main():
    application = webapp.WSGIApplication([
    ('/api/site/stats.json', SiteStatsHandler),
    ('/api/site/info.json', SiteInfoHandler),
    ('/api/nodes/all.json', NodesAllHandler),
    ('/api/nodes/show.json', NodesShowHandler),
    ('/api/topics/latest.json', TopicsLatestHandler),
    ('/api/topics/show.json', TopicsShowHandler),
    ('/api/topics/create.json', TopicsCreateHandler),
    ('/api/members/show.json', MembersShowHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()