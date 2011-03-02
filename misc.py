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
from google.appengine.api import urlfetch
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
from v2ex.babel.ext.cookies import Cookies

from v2ex.babel.handlers import BaseHandler

template.register_template_library('v2ex.templatetags.filters')

class WorldClockHandler(webapp.RequestHandler):
    def get(self):
        site = GetSite()
        member = CheckAuth(self)
        template_values = {}
        template_values['site'] = site
        if member:
            template_values['member'] = member
        l10n = GetMessages(self, site, member)
        template_values['l10n'] = l10n
        template_values['page_title'] = site.title + u' › World Clock 世界时钟'
        template_values['now'] = datetime.datetime.now()
        path = os.path.join(os.path.dirname(__file__), 'tpl', 'desktop', 'time.html')
        output = template.render(path, template_values)
        self.response.out.write(output)

class MD5Handler(BaseHandler):
    def get(self, source):
        i = str(self.request.get('input').strip())
        if (i):
            self.values['md5'] = hashlib.md5(i).hexdigest()
            self.values['sha1'] = hashlib.sha1(i).hexdigest()
        self.set_title(u'MD5 / SHA1 计算器')
        self.finalize(template_name='md5')

class BFBCSPokeHandler(webapp.RequestHandler):
    def get(self, platform, soldier):
        ua = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2.13) Gecko/20101203 Firefox/3.6.13'
        referer = 'http://bfbcs.com/' + platform
        cache_tag = 'bfbcs::' + platform + '/' + soldier
        raw = memcache.get(cache_tag)
        url = 'http://bfbcs.com/stats_' + platform + '/' + soldier
        if raw is None:
            response = urlfetch.fetch(url, headers={'User-Agent' : ua, 'Referer' : referer })
            raw = response.content
            memcache.set(cache_tag, raw, 600)
        pcode = re.findall('([a-z0-9]{32})', raw)
        self.response.out.write('<strong>PCODE</strong> ' + str(pcode[0]) + '<br />')
        if len(pcode) == 1:
            pcode = pcode[0]
            payload = 'request=addplayerqueue&pcode=' + pcode
            self.response.out.write('<strong>PAYLOAD</strong> ' + payload + ' (' + str(len(payload))+ ' bytes)<br />')
            headers = {'User-Agent' : ua, 'Referer' : url, 'X-Requested-With' : 'XMLHttpRequest', 'Content-Type' : 'application/x-www-form-urlencoded; charset=UTF-8', 'Content-Length' : '61', 'Accept' : 'application/json, text/javascript, */*', 'Accept-Language' : 'en-us,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Keep-Alive' : 115, 'Host' : 'bfbcs.com', 'Pragma' : 'no-cache', 'Cache-Control' : 'no-cache', 'Cookie' : '__utma=7878317.1843709575.1297205447.1298572822.1298577848.12; __utmz=7878317.1297205447.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); sessid=enqd028n30d2tr4lv4ned04qi0; __utmb=7878317.21.10.1298577848; __utmc=7878317' }
            response = urlfetch.fetch(url, payload=payload, headers=headers, method='POST')
            if response.status_code == 500:
                response = urlfetch.fetch(url, payload=payload, headers=headers, method='POST')
                if response.status_code == 500:
                    self.response.out.write('<strong>FAILED</strong>')
                else:
                    self.response.out.write('<strong>RESULT</strong> OK ' + response.content)
            else:
                self.response.out.write('<strong>RESULT</strong> OK ' + response.content)
        
def main():
    application = webapp.WSGIApplication([
    ('/time/?', WorldClockHandler),
    ('/(md5|sha1)/?', MD5Handler),
    ('/bfbcs/poke/(ps3|360|pc)/(.*)', BFBCSPokeHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()