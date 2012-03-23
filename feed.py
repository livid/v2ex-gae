#!/usr/bin/env python
# coding=utf-8

import os
import datetime

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

from v2ex.babel.da import *

from v2ex.babel.handlers import BaseHandler

template.register_template_library('v2ex.templatetags.filters')

class FeedHomeHandler(BaseHandler):
    def head(self):
        self.response.out.write('')
        
    def get(self):
        output = memcache.get('feed_index')
        if output is None:
            self.values['site_domain'] = self.site.domain
            self.values['site_name'] = self.site.title
            self.values['site_slogan'] = self.site.slogan
            self.values['feed_url'] = 'http://' + self.values['site_domain'] + '/index.xml'
            self.values['site_updated'] = datetime.datetime.now()
            topics = memcache.get('feed_home')
            if topics is None:
                q = db.GqlQuery("SELECT * FROM Topic ORDER BY created DESC LIMIT 10")
                topics = []
                IGNORED = ['newbie', 'in', 'flamewar', 'pointless', 'tuan', '528491', 'chamber', 'autistic', 'blog', 'love', 'flood', 'fanfou', 'closed']
                for topic in q:
                    if topic.node.name not in IGNORED:
                        topics.append(topic)
                memcache.set('feed_home', topics, 3600)
            self.values['topics'] = topics
            self.values['feed_title'] = self.site.title
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'feed', 'index.xml')
            output = template.render(path, self.values)
            memcache.set('feed_index', output, 3600)
        self.response.headers['Content-type'] = 'application/xml;charset=UTF-8'
        self.response.out.write(output)

        
class FeedReadHandler(BaseHandler):
    def head(self):
        self.response.out.write('')
        
    def get(self):
        output = memcache.get('feed_read_output')
        if output is None:
            self.values['site_domain'] = self.site.domain
            self.values['site_name'] = self.site.title
            self.values['site_slogan'] = self.site.slogan
            self.values['feed_url'] = 'http://' + self.values['site_domain'] + '/read.xml'
            self.values['site_updated'] = datetime.datetime.now()
            topics = memcache.get('feed_home')
            if topics is None:
                q = db.GqlQuery("SELECT * FROM Topic ORDER BY created DESC LIMIT 10")
                topics = []
                IGNORED = ['newbie', 'in', 'flamewar', 'pointless', 'tuan', '528491', 'chamber', 'autistic', 'blog', 'love', 'flood']
                for topic in q:
                    if topic.node.name not in IGNORED:
                        topics.append(topic)
                memcache.set('feed_home', topics, 3600)
            self.values['topics'] = topics
            self.values['feed_title'] = self.site.title
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'feed', 'read.xml')
            output = template.render(path, self.values)
            memcache.set('feed_read_output', output, 3600)
        self.response.headers['Content-type'] = 'application/xml;charset=UTF-8'
        self.response.out.write(output)


class FeedNodeHandler(webapp.RequestHandler):
    def head(self):
        self.response.out.write('')
    
    def get(self, node_name):
        node_name = node_name.lower()
        site = GetSite()
        node = GetKindByName('Node', node_name)
        if node is False:
            return self.response.out.write('node not found')
        output = memcache.get('feed_node_' + node_name)
        if output is None:
            template_values = {}
            template_values['site'] = site
            template_values['site_domain'] = site.domain
            template_values['site_name'] = site.title
            template_values['site_slogan'] = site.slogan
            template_values['feed_url'] = 'http://' + template_values['site_domain'] + '/index.xml'
            template_values['site_updated'] = datetime.datetime.now()
            q = db.GqlQuery("SELECT * FROM Topic WHERE node = :1 ORDER BY created DESC LIMIT 10", node)
            topics = []
            for topic in q:
                topics.append(topic)
            template_values['topics'] = topics
            template_values['feed_title'] = site.title + u' › ' + node.title
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'feed', 'index.xml')
            output = template.render(path, template_values)
            memcache.set('feed_node_' + node.name, output, 7200)
        self.response.headers['Content-type'] = 'application/xml;charset=UTF-8'
        self.response.out.write(output)

def main():
    application = webapp.WSGIApplication([
    ('/index.xml', FeedHomeHandler),
    ('/read.xml', FeedReadHandler),
    ('/feed/v2ex.rss', FeedHomeHandler),
    ('/feed/([0-9a-zA-Z\-\_]+).xml', FeedNodeHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()