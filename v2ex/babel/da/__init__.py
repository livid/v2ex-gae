# coding=utf-8

import hashlib

from google.appengine.ext import db
from google.appengine.api import memcache

from v2ex.babel import Member
from v2ex.babel import Counter
from v2ex.babel import Section
from v2ex.babel import Node
from v2ex.babel import Topic
from v2ex.babel import Reply

def GetKindByNum(kind, num):
    K = str(kind.capitalize())
    one = memcache.get(K + '_' + str(num))
    if one:
        return one
    else:
        q = db.GqlQuery("SELECT * FROM " + K + " WHERE num = :1", int(num))
        if q.count() == 1:
            one = q[0]
            memcache.set(K + '_' + str(num), one, 86400)
            return one
        else:
            return False
            
def GetKindByName(kind, name):
    K = str(kind.capitalize())
    one = memcache.get(K + '::' + str(name))
    if one:
        return one
    else:
        q = db.GqlQuery("SELECT * FROM " + K + " WHERE name = :1", str(name))
        if q.count() == 1:
            one = q[0]
            memcache.set(K + '::' + str(name), one, 86400)
            return one
        else:
            return False

def GetMemberByUsername(name):
    one = memcache.get('Member::' + str(name).lower())
    if one:
        return one
    else:
        q = db.GqlQuery("SELECT * FROM Member WHERE username_lower = :1", str(name).lower())
        if q.count() == 1:
            one = q[0]
            memcache.set('Member::' + str(name).lower(), one, 86400)
            return one
        else:
            return False

def GetMemberByEmail(email):
    cache = 'Member::email::' + hashlib.md5(email.lower()).hexdigest()
    one = memcache.get(cache)
    if one:
        return one
    else:
        q = db.GqlQuery("SELECT * FROM Member WHERE email = :1", str(email).lower())
        if q.count() == 1:
            one = q[0]
            memcache.set(cache, one, 86400)
            return one
        else:
            return False