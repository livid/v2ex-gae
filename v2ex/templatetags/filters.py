import re
import logging

from django import template
from datetime import timedelta
import urllib, hashlib
register = template.Library()

def timezone(value, offset):
    if offset > 12:
        offset = 12 - offset
    return value + timedelta(hours=offset)
register.filter(timezone)

# auto convert img.ly/abcd links to image tags
def imgly(value):
    imgs = re.findall('(http://img.ly/[a-zA-Z0-9]+)\s?', value)
    if (len(imgs) > 0):
        for img in imgs:
            img_id = re.findall('http://img.ly/([a-zA-Z0-9]+)', img)
            if (img_id[0] != 'system' and img_id[0] != 'api'):
                value = value.replace('http://img.ly/' + img_id[0], '<a href="http://img.ly/' + img_id[0] + '" target="_blank"><img src="http://zdxproxy.appspot.com/img.ly/show/large/' + img_id[0] + '" class="imgly" border="0" /></a>')
        return value
    else:
        return value
register.filter(imgly)

# auto convert cl.ly/abcd links to image tags
def clly(value):
    imgs = re.findall('(http://cl.ly/[a-zA-Z0-9]+)\s?', value)
    if (len(imgs) > 0):
        for img in imgs:
            img_id = re.findall('http://cl.ly/([a-zA-Z0-9]+)', img)
            if (img_id[0] != 'demo' and img_id[0] != 'whatever'):
                value = value.replace('http://cl.ly/' + img_id[0], '<a href="http://cl.ly/' + img_id[0] + '" target="_blank"><img src="http://cl.ly/' + img_id[0] + '/content" class="imgly" border="0" /></a>')
        return value
    else:
        return value
register.filter(clly)

# auto convert youtube.com links to player
def youtube(value):
    videos = re.findall('(http://www.youtube.com/watch\?v=[a-zA-Z0-9\-\_]+)\s?', value)
    if (len(videos) > 0):
        for video in videos:
            video_id = re.findall('http://www.youtube.com/watch\?v=([a-zA-Z0-9\-\_]+)', video)
            value = value.replace('http://www.youtube.com/watch?v=' + video_id[0], '<object width="480" height="385"><param name="movie" value="http://www.youtube.com/v/' + video_id[0] + '?fs=1&amp;hl=en_US"></param><param name="allowFullScreen" value="true"></param><param name="allowscriptaccess" value="always"></param><embed src="http://www.youtube.com/v/' + video_id[0] + '?fs=1&amp;hl=en_US" type="application/x-shockwave-flash" allowscriptaccess="always" allowfullscreen="true" width="480" height="385"></embed></object>')
        return value
    else:
        return value
register.filter(youtube)

# auto convert @username to clickable links
def mentions(value):
    ms = re.findall('(@[a-zA-Z0-9\_]+\.?)\s?', value)
    if (len(ms) > 0):
        for m in ms:
            m_id = re.findall('@([a-zA-Z0-9\_]+\.?)', m)
            if (len(m_id) > 0):
                if (m_id[0].endswith('.') != True):
                    value = value.replace('@' + m_id[0], '@<a href="/member/' + m_id[0] + '">' + m_id[0] + '</a>')
        return value
    else:
        return value
register.filter(mentions)

# avatar filter
def avatar(value,arg):
    default = "http://v2ex.com/static/img/avatar_" + str(arg) + ".png"
    if type(value).__name__ != 'Member':
        return '<img src="' + default + '" border="0" align="absmiddle" />'
    if arg == 'large':
        number_size = 73
        member_avatar_url = value.avatar_large_url
    elif arg == 'normal':
        number_size = 48
        member_avatar_url = value.avatar_normal_url
    elif arg == 'mini':
        number_size = 24
        member_avatar_url = value.avatar_mini_url
        
    if member_avatar_url:
        return '<img src="'+ member_avatar_url +'" border="0" alt="' + value.username + '" />'
    else:
        gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(value.email.lower()).hexdigest() + "?"
        gravatar_url += urllib.urlencode({'s' : str(number_size), 'd' : default})
        return '<img src="' + gravatar_url + '" border="0" alt="' + value.username + '" align="absmiddle" />'
register.filter(avatar)

# github gist script support
def gist(value):
    return re.sub(r'(http://gist.github.com/[\d]+)', r'<script src="\1.js"></script>', value)
register.filter(gist)

_base_js_escapes = (
    ('\\', r'\u005C'),
    ('\'', r'\u0027'),
    ('"', r'\u0022'),
    ('>', r'\u003E'),
    ('<', r'\u003C'),
    ('&', r'\u0026'),
    ('=', r'\u003D'),
    ('-', r'\u002D'),
    (';', r'\u003B'),
    (u'\u2028', r'\u2028'),
    (u'\u2029', r'\u2029')
)

# Escape every ASCII character with a value less than 32.
_js_escapes = (_base_js_escapes +
               tuple([('%c' % z, '\\u%04X' % z) for z in range(32)]))

def escapejs(value):
    """Hex encodes characters for use in JavaScript strings."""
    for bad, good in _js_escapes:
        value = value.replace(bad, good)
    return value
register.filter(escapejs)