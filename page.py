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

class AboutHandler(webapp.RequestHandler):
    def get(self):
        template_values = {}
        template_values['page_title'] = 'About'
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'about.html')
        output = template.render(path, template_values)
        self.response.out.write(output)
        
class FAQHandler(webapp.RequestHandler):
    def get(self):
        template_values = {}
        template_values['page_title'] = 'About'
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'faq.html')
        output = template.render(path, template_values)
        self.response.out.write(output)

def main():
    application = webapp.WSGIApplication([
    ('/about', AboutHandler),
    ('/faq', FAQHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()