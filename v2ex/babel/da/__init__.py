# coding=utf-8
# "da" means Data Access, this file contains various quick (or dirty) methods for accessing data.

import hashlib
import logging
import zlib
import pickle

from google.appengine.ext import db
from google.appengine.api import memcache

from v2ex.babel import Member
from v2ex.babel import Counter
from v2ex.babel import Section
from v2ex.babel import Node
from v2ex.babel import Topic
from v2ex.babel import Reply
from v2ex.babel import Place
from v2ex.babel import Site

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

def ip2long(ip):
    ip_array = ip.split('.')
    ip_long = int(ip_array[0]) * 16777216 + int(ip_array[1]) * 65536 + int(ip_array[2]) * 256 + int(ip_array[3])
    return ip_long

def GetPlaceByIP(ip):
    cache = 'Place_' + ip
    place = memcache.get(cache)
    if place:
        return place
    else:
        q = db.GqlQuery("SELECT * FROM Place WHERE ip = :1", ip)
        if q.count() == 1:
            place = q[0]
            memcache.set(cache, place, 86400)
            return place
        else:
            return False

def CreatePlaceByIP(ip):
    place = Place()
    q = db.GqlQuery('SELECT * FROM Counter WHERE name = :1', 'place.max')
    if (q.count() == 1):
        counter = q[0]
        counter.value = counter.value + 1
    else:
        counter = Counter()
        counter.name = 'place.max'
        counter.value = 1
    q2 = db.GqlQuery('SELECT * FROM Counter WHERE name = :1', 'place.total')
    if (q2.count() == 1):
        counter2 = q2[0]
        counter2.value = counter2.value + 1
    else:
        counter2 = Counter()
        counter2.name = 'place.total'
        counter2.value = 1
    place.num = ip2long(ip)
    place.ip = ip
    place.put()
    counter.put()
    counter2.put()
    return place

def GetSite():
    site = memcache.get('site')
    if site is not None:
        return site
    else:
        q = db.GqlQuery("SELECT * FROM Site WHERE num = 1")
        if q.count() == 1:
            site = q[0]
            if site.l10n is None:
                site.l10n = 'en'
            memcache.set('site', site, 86400)
            return site
        else:
            site = Site()
            site.num = 1
            site.title = 'V2EX'
            site.domain = 'v2ex.appspot.com'
            site.slogan = 'way to explore'
            site.l10n = 'en'
            site.description = ''
            site.put()
            memcache.set('site', site, 86400)
            return site

# input is a compressed string
# output is an object
def GetUnpacked(data):
    decompressed = zlib.decompress(data)
    return pickle.loads(decompressed)

# input is an object
# output is an compressed string
def GetPacked(data):
    s = pickle.dumps(data)
    return zlib.compress(s)