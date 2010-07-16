# coding=utf-8

import hashlib

from google.appengine.ext import db
from google.appengine.api import memcache

from v2ex.babel.ext.cookies import Cookies

def CheckAuth(request):
  cookies = Cookies(request, max_age = 86400, path = '/')
  if 'auth' in cookies:
      auth = cookies['auth']
      member_num = memcache.get(auth)
      if (member_num > 0):
          q = db.GqlQuery("SELECT * FROM Member WHERE num = :1", member_num)
          return q[0]
      else:
          q = db.GqlQuery("SELECT * FROM Member WHERE auth = :1", auth)
          if (q.count() == 1):
              member_num = q[0].num
              memcache.set(auth, member_num, 86400)
              return q[0]
          else:
              return False
  else:
      return False

def DoAuth(request, destination, message = None):
    if message != None:
        request.session['message'] = message
    else:
        request.session['message'] = u'请首先登入或注册'
    return request.redirect('/signin?destination=' + destination)