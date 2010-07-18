#!/usr/bin/env python
# coding=utf-8

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext.webapp import util

from v2ex.babel import Avatar

from v2ex.babel.security import *
from v2ex.babel.da import *
        
class AvatarHandler(webapp.RequestHandler):
    def get(self, member_num, size):
        avatar = GetKindByName('Avatar', 'avatar_' + str(member_num) + '_' + str(size))
        if avatar is not None:
            self.response.headers['Content-Type'] = "image/png"
            self.response.headers['Cache-Control'] = "max-age=172800, public, must-revalidate"
            self.response.headers['Expires'] = "Sun, 25 Apr 2011 20:00:00 GMT"
            self.response.out.write(avatar.content)
        else:
            self.error(404)
            
def main():
    application = webapp.WSGIApplication([
    ('/avatar/([0-9]+)/(large|normal|mini)', AvatarHandler)
    ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
