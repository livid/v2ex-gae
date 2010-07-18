# coding=utf-8

import hashlib

from google.appengine.ext import db
from google.appengine.api import memcache

from v2ex.babel.ext.cookies import Cookies

def CheckAuth(request):
  cookies = Cookies(request, max_age = 86400 * 365, path = '/')
  if 'auth' in cookies:
      auth = cookies['auth']
      member_num = memcache.get(auth)
      if (member_num > 0):
          member = memcache.get('member_' + str(member_num))
          if member is None:
              q = db.GqlQuery("SELECT * FROM Member WHERE num = :1", member_num)
              if q.count() == 1:
                  member = q[0]
                  memcache.set('member_' + str(member_num), member, 86400 * 365)
              else:
                  member = False
          return member
      else:
          q = db.GqlQuery("SELECT * FROM Member WHERE auth = :1", auth)
          if (q.count() == 1):
              member_num = q[0].num
              member = q[0]
              memcache.set(auth, member_num, 86400 * 365)
              memcache.set('member_' + str(member_num), member, 86400 * 365)
              return member
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