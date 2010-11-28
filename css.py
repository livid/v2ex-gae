#!/usr/bin/env python
# coding=utf-8

import os
import datetime

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

from v2ex.babel import SYSTEM_VERSION

template.register_template_library('v2ex.templatetags.filters')

class CSSHandler(webapp.RequestHandler):
    def get(self, theme):
        template_values = {}
        themes = os.listdir(os.path.join(os.path.dirname(__file__), 'tpl', 'themes'))
        if theme in themes:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'themes', theme, 'style.css')
        else:
            path = os.path.join(os.path.dirname(__file__), 'tpl', 'themes', 'default', 'style.css')
        output = template.render(path, template_values)
        expires_date = datetime.datetime.utcnow() + datetime.timedelta(days=7)
        expires_str = expires_date.strftime("%d %b %Y %H:%M:%S GMT")
        self.response.headers.add_header("Expires", expires_str)
        self.response.headers['Cache-Control'] = 'max-age=120, must-revalidate'
        self.response.headers['Content-type'] = 'text/css;charset=UTF-8'
        self.response.out.write(output)

def main():
    application = webapp.WSGIApplication([
    ('/css/([a-zA-Z0-9]+).css', CSSHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()