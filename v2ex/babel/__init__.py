SYSTEM_VERSION = '2.3.13'

import datetime
import hashlib

from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import users

class Member(db.Model):
    num = db.IntegerProperty(indexed=True)
    auth = db.StringProperty(required=False, indexed=True)
    deactivated = db.IntegerProperty(required=True, default=0)
    username = db.StringProperty(required=False, indexed=True)
    username_lower = db.StringProperty(required=False, indexed=True)
    password = db.StringProperty(required=False, indexed=True)
    email = db.StringProperty(required=False, indexed=True)
    email_verified = db.IntegerProperty(required=False, indexed=True, default=0)
    website = db.StringProperty(required=False, default='')
    twitter = db.StringProperty(required=False, default='')
    twitter_oauth = db.IntegerProperty(required=False, default=0)
    twitter_oauth_key = db.StringProperty(required=False)
    twitter_oauth_secret = db.StringProperty(required=False)
    twitter_oauth_string = db.StringProperty(required=False)
    twitter_sync = db.IntegerProperty(required=False, default=0)
    twitter_id = db.IntegerProperty(required=False)
    twitter_name = db.StringProperty(required=False)
    twitter_screen_name = db.StringProperty(required=False)
    twitter_location = db.StringProperty(required=False)
    twitter_description = db.TextProperty(required=False)
    twitter_profile_image_url = db.StringProperty(required=False)
    twitter_url = db.StringProperty(required=False)
    twitter_statuses_count = db.IntegerProperty(required=False)
    twitter_followers_count = db.IntegerProperty(required=False)
    twitter_friends_count = db.IntegerProperty(required=False)
    twitter_favourites_count = db.IntegerProperty(required=False)
    location = db.StringProperty(required=False, default='')
    tagline = db.TextProperty(required=False, default='')
    bio = db.TextProperty(required=False, default='')
    avatar_large_url = db.StringProperty(required=False, indexed=False)
    avatar_normal_url = db.StringProperty(required=False, indexed=False)
    avatar_mini_url = db.StringProperty(required=False, indexed=False)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)
    last_signin = db.DateTimeProperty()
    blocked = db.TextProperty(required=False, default='')
    
class Counter(db.Model):
    name = db.StringProperty(required=False, indexed=True)
    value = db.IntegerProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    last_increased = db.DateTimeProperty(auto_now=True)
    
class Section(db.Model):
    num = db.IntegerProperty(indexed=True)
    name = db.StringProperty(required=False, indexed=True)
    title = db.StringProperty(required=False, indexed=True)
    title_alternative = db.StringProperty(required=False, indexed=True)
    header = db.TextProperty(required=False)
    footer = db.TextProperty(required=False)
    nodes = db.IntegerProperty(default=0)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)
    
class Node(db.Model):
    num = db.IntegerProperty(indexed=True)
    section_num = db.IntegerProperty(indexed=True)
    name = db.StringProperty(required=False, indexed=True)
    title = db.StringProperty(required=False, indexed=True)
    title_alternative = db.StringProperty(required=False, indexed=True)
    header = db.TextProperty(required=False)
    footer = db.TextProperty(required=False)
    category = db.StringProperty(required=False, indexed=True)
    topics = db.IntegerProperty(default=0)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)
    
class Topic(db.Model):
    num = db.IntegerProperty(indexed=True)
    node = db.ReferenceProperty(Node)
    node_num = db.IntegerProperty(indexed=True)
    node_name = db.StringProperty(required=False, indexed=True)
    node_title = db.StringProperty(required=False, indexed=False)
    member = db.ReferenceProperty(Member)
    member_num = db.IntegerProperty(indexed=True)
    title = db.StringProperty(required=False, indexed=True)
    content = db.TextProperty(required=False)
    content_rendered = db.TextProperty(required=False)
    content_length = db.IntegerProperty(default=0)
    hits = db.IntegerProperty(default=0)
    replies = db.IntegerProperty(default=0)
    created_by = db.StringProperty(required=False, indexed=True)
    last_reply_by = db.StringProperty(required=False, indexed=True)
    source = db.StringProperty(required=False, indexed=True)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)
    last_touched = db.DateTimeProperty()
    
class Reply(db.Model):
    num = db.IntegerProperty(indexed=True)
    topic = db.ReferenceProperty(Topic)
    topic_num = db.IntegerProperty(indexed=True)
    member = db.ReferenceProperty(Member)
    member_num = db.IntegerProperty(indexed=True)
    content = db.TextProperty(required=False)
    source = db.StringProperty(required=False, indexed=True)
    created_by = db.StringProperty(required=False, indexed=True)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)
    
class Avatar(db.Model):
    num = db.IntegerProperty(indexed=True)
    name = db.StringProperty(required=False, indexed=True)
    content = db.BlobProperty()
    
class Note(db.Model):
    num = db.IntegerProperty(indexed=True)
    member = db.ReferenceProperty(Member)
    member_num = db.IntegerProperty(indexed=True)
    title = db.StringProperty(required=False, indexed=True)
    content = db.TextProperty(required=False)
    body = db.TextProperty(required=False)
    length = db.IntegerProperty(indexed=False, default=0)
    edits = db.IntegerProperty(indexed=False, default=1)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)

class PasswordResetToken(db.Model):
    token = db.StringProperty(required=False, indexed=True)
    email = db.StringProperty(required=False, indexed=True)
    member = db.ReferenceProperty(Member)
    valid = db.IntegerProperty(required=False, indexed=True, default=1)
    timestamp = db.IntegerProperty(required=False, indexed=True, default=0)

class Place(db.Model):
    num = db.IntegerProperty(required=False, indexed=True)
    ip = db.StringProperty(required=False, indexed=True)
    name = db.StringProperty(required=False, indexed=False)
    visitors = db.IntegerProperty(required=False, default=0, indexed=True)
    longitude = db.FloatProperty(required=False, default=0.0, indexed=True)
    latitude = db.FloatProperty(required=False, default=0.0, indexed=True)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)

class PlaceMessage(db.Model):
    num = db.IntegerProperty(indexed=True)
    place = db.ReferenceProperty(Place)
    place_num = db.IntegerProperty(indexed=True)
    member = db.ReferenceProperty(Member)
    content = db.TextProperty(required=False)
    in_reply_to = db.SelfReferenceProperty()
    source = db.StringProperty(required=False, indexed=True)
    created = db.DateTimeProperty(auto_now_add=True)

class Checkin(db.Model):
    place = db.ReferenceProperty(Place)
    member = db.ReferenceProperty(Member)
    last_checked_in = db.DateTimeProperty(auto_now=True)
    
class Site(db.Model):
    num = db.IntegerProperty(required=False, indexed=True)
    title = db.StringProperty(required=False, indexed=False)
    slogan = db.StringProperty(required=False, indexed=False)
    description = db.TextProperty(required=False)
    domain = db.StringProperty(required=False, indexed=False)
    analytics = db.StringProperty(required=False, indexed=False)