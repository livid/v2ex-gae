import re, string
import logging
from v2ex.babel.ext import bleach

from django import template

from datetime import timedelta
import urllib, hashlib
register = template.Library()

# Configuration for urlize() function
LEADING_PUNCTUATION  = ['(', '<', '&lt;']
TRAILING_PUNCTUATION = ['.', ',', ')', '>', '\n', '&gt;']

# list of possible strings used for bullets in bulleted lists
DOTS = ['&middot;', '*', '\xe2\x80\xa2', '&#149;', '&bull;', '&#8226;']

unencoded_ampersands_re = re.compile(r'&(?!(\w+|#\d+);)')
word_split_re = re.compile(r'(\s+)')
punctuation_re = re.compile('^(?P<lead>(?:%s)*)(?P<middle>.*?)(?P<trail>(?:%s)*)$' % \
    ('|'.join([re.escape(x) for x in LEADING_PUNCTUATION]),
    '|'.join([re.escape(x) for x in TRAILING_PUNCTUATION])))
simple_email_re = re.compile(r'^\S+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+$')
link_target_attribute_re = re.compile(r'(<a [^>]*?)target=[^\s>]+')
html_gunk_re = re.compile(r'(?:<br clear="all">|<i><\/i>|<b><\/b>|<em><\/em>|<strong><\/strong>|<\/?smallcaps>|<\/?uppercase>)', re.IGNORECASE)
hard_coded_bullets_re = re.compile(r'((?:<p>(?:%s).*?[a-zA-Z].*?</p>\s*)+)' % '|'.join([re.escape(x) for x in DOTS]), re.DOTALL)
trailing_empty_content_re = re.compile(r'(?:<p>(?:&nbsp;|\s|<br \/>)*?</p>\s*)+\Z')
del x # Temporary variable

def timezone(value, offset):
    if offset > 12:
        offset = 12 - offset
    return value + timedelta(hours=offset)
register.filter(timezone)

def autolink2(text):
    return bleach.linkify(text)
register.filter(autolink2)

def autolink(text, trim_url_limit=None, nofollow=False):
    """
    Converts any URLs in text into clickable links. Works on http://, https:// and
    www. links. Links can have trailing punctuation (periods, commas, close-parens)
    and leading punctuation (opening parens) and it'll still do the right thing.

    If trim_url_limit is not None, the URLs in link text will be limited to
    trim_url_limit characters.

    If nofollow is True, the URLs in link text will get a rel="nofollow" attribute.
    """
    trim_url = lambda x, limit=trim_url_limit: limit is not None and (x[:limit] + (len(x) >=limit and '...' or ''))  or x
    words = word_split_re.split(text)
    nofollow_attr = nofollow and ' rel="nofollow"' or ''
    for i, word in enumerate(words):
        match = punctuation_re.match(word)
        if match:
            lead, middle, trail = match.groups()
            if middle.startswith('www.') or ('@' not in middle and not middle.startswith('http://') and not middle.startswith('https://') and \
                    len(middle) > 0 and middle[0] in string.letters + string.digits and \
                    (middle.endswith('.org') or middle.endswith('.net') or middle.endswith('.com'))):
                middle = '<a href="http://%s"%s target="_blank">%s</a>' % (middle, nofollow_attr, trim_url(middle))
            if middle.startswith('http://') or middle.startswith('https://'):
                middle = '<a href="%s"%s target="_blank">%s</a>' % (middle, nofollow_attr, trim_url(middle))
            if '@' in middle and not middle.startswith('www.') and not ':' in middle \
                and simple_email_re.match(middle):
                middle = '<a href="mailto:%s">%s</a>' % (middle, middle)
            if lead + middle + trail != word:
                words[i] = lead + middle + trail
    return ''.join(words)
register.filter(autolink)

# auto convert img.ly/abcd links to image tags
def imgly(value):
    imgs = re.findall('(http://img.ly/[a-zA-Z0-9]+)\s?', value)
    if (len(imgs) > 0):
        for img in imgs:
            img_id = re.findall('http://img.ly/([a-zA-Z0-9]+)', img)
            if (img_id[0] != 'system' and img_id[0] != 'api'):
                value = value.replace('http://img.ly/' + img_id[0], '<a href="http://img.ly/' + img_id[0] + '" target="_blank"><img src="http://picky-staging.appspot.com/img.ly/show/large/' + img_id[0] + '" class="imgly" border="0" /></a>')
        return value
    else:
        return value
register.filter(imgly)

# auto convert cl.ly/abcd links to image tags
def clly(value):
    #imgs = re.findall('(http://cl.ly/[a-zA-Z0-9]+)\s?', value)
    #if (len(imgs) > 0):
    #    for img in imgs:
    #        img_id = re.findall('http://cl.ly/([a-zA-Z0-9]+)', img)
    #        if (img_id[0] != 'demo' and img_id[0] != 'whatever'):
    #            value = value.replace('http://cl.ly/' + img_id[0], '<a href="http://cl.ly/' + img_id[0] + '" target="_blank"><img src="http://cl.ly/' + img_id[0] + '/content" class="imgly" border="0" /></a>')
    #    return value
    #else:
    #    return value
    return value
register.filter(clly)

# auto convert *.sinaimg.cn/*/*.jpg and bcs.baidu.com/*.jpg links to image tags
def sinaimg(value):
    imgs = re.findall('(http://ww[0-9]{1}.sinaimg.cn/[a-zA-Z0-9]+/[a-zA-Z0-9]+.[a-z]{3})\s?', value)
    for img in imgs:
        value = value.replace(img, '<a href="' + img + '" target="_blank"><img src="' + img + '" class="imgly" border="0" /></a>')
    baidu_imgs = re.findall('(http://(bcs.duapp.com|img.xiachufang.com|i.xiachufang.com)/([a-zA-Z0-9\.\-\_\/]+).jpg)\s?', value)
    for img in baidu_imgs:
        value = value.replace(img[0], '<a href="' + img[0] + '" target="_blank"><img src="' + img[0] + '" class="imgly" border="0" /></a>')
    return value
register.filter(sinaimg)

# auto convert youtube.com links to player
def youtube(value):
    videos = re.findall('(http://www.youtube.com/watch\?v=[a-zA-Z0-9\-\_]+)\s?', value)
    if (len(videos) > 0):
        for video in videos:
            video_id = re.findall('http://www.youtube.com/watch\?v=([a-zA-Z0-9\-\_]+)', video)
            value = value.replace('http://www.youtube.com/watch?v=' + video_id[0], '<object width="620" height="500"><param name="movie" value="http://www.youtube.com/v/' + video_id[0] + '?fs=1&amp;hl=en_US"></param><param name="allowFullScreen" value="true"></param><param name="allowscriptaccess" value="always"></param><embed src="http://www.youtube.com/v/' + video_id[0] + '?fs=1&amp;hl=en_US" type="application/x-shockwave-flash" allowscriptaccess="always" allowfullscreen="true" width="620" height="500"></embed></object>')
        return value
    else:
        return value
register.filter(youtube)

# auto convert youku.com links to player
# example: http://v.youku.com/v_show/id_XMjA1MDU2NTY0.html
def youku(value):
    videos = re.findall('(http://v.youku.com/v_show/id_[a-zA-Z0-9\=]+.html)\s?', value)
    logging.error(value)
    logging.error(videos)
    if (len(videos) > 0):
        for video in videos:
            video_id = re.findall('http://v.youku.com/v_show/id_([a-zA-Z0-9\=]+).html', video)
            value = value.replace('http://v.youku.com/v_show/id_' + video_id[0] + '.html', '<embed src="http://player.youku.com/player.php/sid/' + video_id[0] + '/v.swf" quality="high" width="638" height="420" align="middle" allowScriptAccess="sameDomain" type="application/x-shockwave-flash"></embed>')
        return value
    else:
        return value
register.filter(youku)

# auto convert tudou.com links to player
# example: http://www.tudou.com/programs/view/ro1Yt1S75bA/
def tudou(value):
    videos = re.findall('(http://www.tudou.com/programs/view/[a-zA-Z0-9\=]+/)\s?', value)
    logging.error(value)
    logging.error(videos)
    if (len(videos) > 0):
        for video in videos:
            video_id = re.findall('http://www.tudou.com/programs/view/([a-zA-Z0-9\=]+)/', video)
            value = value.replace('http://www.tudou.com/programs/view/' + video_id[0] + '/', '<embed src="http://www.tudou.com/v/' + video_id[0] + '/" quality="high" width="638" height="420" align="middle" allowScriptAccess="sameDomain" type="application/x-shockwave-flash"></embed>')
        return value
    else:
        return value
register.filter(tudou)

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

# gravatar filter
def gravatar(value,arg):
    default = "http://v2ex.appspot.com/static/img/avatar_" + str(arg) + ".png"
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
register.filter(gravatar)

# avatar filter
def avatar(value, arg):
    default = "/static/img/avatar_" + str(arg) + ".png"
    if type(value).__name__ not in ['Member', 'Node']:
        return '<img src="' + default + '" border="0" />'
    if arg == 'large':
        number_size = 73
        member_avatar_url = value.avatar_large_url
    elif arg == 'normal':
        number_size = 48
        member_avatar_url = value.avatar_normal_url
    elif arg == 'mini':
        number_size = 24
        member_avatar_url = value.avatar_mini_url
        
    if value.avatar_mini_url:
        return '<img src="'+ member_avatar_url +'" border="0" />'
    else:
        return '<img src="' + default + '" border="0" />'
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