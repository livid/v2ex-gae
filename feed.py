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

template.register_template_library('v2ex.templatetags.filters')

class FeedHomeHandler(webapp.RequestHandler):
    def get(self):
        template_values = {}
        template_values['site_domain'] = 'www.v2ex.com'
        template_values['site_name'] = 'V2EX'
        template_values['site_slogan'] = 'way to explore'
        template_values['feed_url'] = 'http://' + template_values['site_domain'] + '/index.xml'
        template_values['site_updated'] = datetime.datetime.now()
        q = db.GqlQuery("SELECT * FROM Topic ORDER BY created DESC LIMIT 10")
        template_values['topics'] = q
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'feed', 'index.xml')
        output = template.render(path, template_values)
        self.response.out.write(output)

def main():
    application = webapp.WSGIApplication([
    ('/index.xml', FeedHomeHandler),
    ('/feed/v2ex.rss', FeedHomeHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()