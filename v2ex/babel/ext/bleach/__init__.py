import itertools
import logging
import re
import sys
import urlparse

import html5lib
from html5lib.sanitizer import HTMLSanitizer
from html5lib.serializer.htmlserializer import HTMLSerializer

from encoding import force_unicode
from sanitizer import BleachSanitizer


VERSION = (1, 1, 1)
__version__ = '.'.join(map(str, VERSION))

__all__ = ['clean', 'linkify']

log = logging.getLogger('bleach')

ALLOWED_TAGS = [
    'a',
    'abbr',
    'acronym',
    'b',
    'blockquote',
    'code',
    'em',
    'i',
    'li',
    'ol',
    'strong',
    'ul',
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'abbr': ['title'],
    'acronym': ['title'],
}

ALLOWED_STYLES = []

TLDS = """ac ad ae aero af ag ai al am an ao aq ar arpa as asia at au aw ax az
       ba bb bd be bf bg bh bi biz bj bm bn bo br bs bt bv bw by bz ca cat
       cc cd cf cg ch ci ck cl cm cn co com coop cr cu cv cx cy cz de dj dk
       dm do dz ec edu ee eg er es et eu fi fj fk fm fo fr ga gb gd ge gf gg
       gh gi gl gm gn gov gp gq gr gs gt gu gw gy hk hm hn hr ht hu id ie il
       im in info int io iq ir is it je jm jo jobs jp ke kg kh ki km kn kp
       kr kw ky kz la lb lc li lk lr ls lt lu lv ly ma mc md me mg mh mil mk
       ml mm mn mo mobi mp mq mr ms mt mu museum mv mw mx my mz na name nc ne
       net nf ng ni nl no np nr nu nz om org pa pe pf pg ph pk pl pm pn pr pro
       ps pt pw py qa re ro rs ru rw sa sb sc sd se sg sh si sj sk sl sm sn so
       sr st su sv sy sz tc td tel tf tg th tj tk tl tm tn to tp tr travel tt
       tv tw tz ua ug uk us uy uz va vc ve vg vi vn vu wf ws xn ye yt yu za zm
       zw""".split()

TLDS.reverse()

url_re = re.compile(
    r"""\(*  # Match any opening parentheses.
    \b(?<![@.])(?:\w[\w-]*:/{0,3}(?:(?:\w+:)?\w+@)?)?  # http://
    ([\w-]+\.)+(?:%s)(?:\:\d+)?(?!\.\w)\b   # xx.yy.tld(:##)?
    (?:[/?][^\s\{\}\|\\\^\[\]`<>"]*)?
        # /path/zz (excluding "unsafe" chars from RFC 1738,
        # except for # and ~, which happen in practice)
    """ % u'|'.join(TLDS), re.VERBOSE | re.UNICODE)

proto_re = re.compile(r'^[\w-]+:/{0,3}')

punct_re = re.compile(r'([\.,]+)$')

email_re = re.compile(
    r"""(?<!//)
    (([-!#$%&'*+/=?^_`{}|~0-9A-Z]+
        (\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*  # dot-atom
    |^"([\001-\010\013\014\016-\037!#-\[\]-\177]
        |\\[\001-011\013\014\016-\177])*"  # quoted-string
    )@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6})\.?  # domain
    """,
    re.IGNORECASE | re.MULTILINE | re.VERBOSE)

NODE_TEXT = 4  # The numeric ID of a text node in simpletree.

identity = lambda x: x  # The identity function.


def clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES,
          styles=ALLOWED_STYLES, strip=False, strip_comments=True):
    """Clean an HTML fragment and return it"""
    if not text:
        return u''

    text = force_unicode(text)
    if text.startswith(u'<!--'):
        text = u' ' + text

    class s(BleachSanitizer):
        allowed_elements = tags
        allowed_attributes = attributes
        allowed_css_properties = styles
        strip_disallowed_elements = strip
        strip_html_comments = strip_comments

    parser = html5lib.HTMLParser(tokenizer=s)

    return _render(parser.parseFragment(text)).strip()


def linkify(text, nofollow=True, target=None, filter_url=identity,
            filter_text=identity, skip_pre=False, parse_email=False):
    """Convert URL-like strings in an HTML fragment to links.

    linkify() converts strings that look like URLs or domain names in a
    blob of text that may be an HTML fragment to links, while preserving
    (a) links already in the string, (b) urls found in attributes, and
    (c) email addresses.

    If the nofollow argument is True (the default) then rel="nofollow"
    will be added to links created by linkify() as well as links already
    found in the text.

    The target argument will optionally add a target attribute with the
    given value to links created by linkify() as well as links already
    found in the text.

    linkify() uses up to two filters on each link. For links created by
    linkify(), the href attribute is passed through filter_url()
    and the text of the link is passed through filter_text(). For links
    already found in the document, the href attribute is passed through
    filter_url(), but the text is untouched.
    """
    text = force_unicode(text)

    if not text:
        return u''

    parser = html5lib.HTMLParser(tokenizer=HTMLSanitizer)

    forest = parser.parseFragment(text)

    if nofollow:
        rel = u'rel="nofollow"'
    else:
        rel = u''

    def replace_nodes(tree, new_frag, node):
        new_tree = parser.parseFragment(new_frag)
        for n in new_tree.childNodes:
            tree.insertBefore(n, node)
        tree.removeChild(node)

    def strip_wrapping_parentheses(fragment):
        """Strips wrapping parentheses.

        Returns a tuple of the following format::

            (string stripped from wrapping parentheses,
             count of stripped opening parentheses,
             count of stripped closing parentheses)
        """
        opening_parentheses = closing_parentheses = 0
        # Count consecutive opening parentheses
        # at the beginning of the fragment (string).
        for char in fragment:
            if char == '(':
                opening_parentheses += 1
            else:
                break

        if opening_parentheses:
            newer_frag = ''
            # Cut the consecutive opening brackets from the fragment.
            fragment = fragment[opening_parentheses:]
            # Reverse the fragment for easier detection of parentheses
            # inside the URL.
            reverse_fragment = fragment[::-1]
            skip = False
            for char in reverse_fragment:
                # Remove the closing parentheses if it has a matching
                # opening parentheses (they are balanced).
                if (char == ')' and
                        closing_parentheses < opening_parentheses and
                        not skip):
                    closing_parentheses += 1
                    continue
                # Do not remove ')' from the URL itself.
                elif char != ')':
                    skip = True
                newer_frag += char
            fragment = newer_frag[::-1]

        return fragment, opening_parentheses, closing_parentheses

    def linkify_nodes(tree, parse_text=True):
        for node in tree.childNodes:
            if node.type == NODE_TEXT and parse_text:
                new_frag = node.toxml()
                if parse_email:
                    new_frag = re.sub(email_re, email_repl, new_frag)
                    if new_frag != node.toxml():
                        replace_nodes(tree, new_frag, node)
                        linkify_nodes(tree, False)
                        continue
                new_frag = re.sub(url_re, link_repl, new_frag)
                replace_nodes(tree, new_frag, node)
            elif node.name == 'a':
                if 'href' in node.attributes:
                    if nofollow:
                        node.attributes['rel'] = 'nofollow'
                    if target is not None:
                        node.attributes['target'] = target
                    href = node.attributes['href']
                    node.attributes['href'] = filter_url(href)
            elif skip_pre and node.name == 'pre':
                linkify_nodes(node, False)
            else:
                linkify_nodes(node)

    def email_repl(match):
        repl = u'<a href="mailto:%(mail)s">%(mail)s</a>'
        return repl % {'mail': match.group(0).replace('"', '&quot;')}

    def link_repl(match):
        url = match.group(0)
        open_brackets = close_brackets = 0
        if url.startswith('('):
            url, open_brackets, close_brackets = (
                    strip_wrapping_parentheses(url)
            )
        end = u''
        m = re.search(punct_re, url)
        if m:
            end = m.group(0)
            url = url[0:m.start()]
        if re.search(proto_re, url):
            href = url
        else:
            href = u''.join([u'http://', url])

        repl = u'%s<a href="%s" %s>%s</a>%s%s'

        attribs = [rel]
        if target is not None:
            attribs.append('target="%s"' % target)

        return repl % ('(' * open_brackets,
                       filter_url(href), ' '.join(attribs), filter_text(url),
                       end, ')' * close_brackets)

    linkify_nodes(forest)

    return _render(forest)


def delinkify(text, allow_domains=None, allow_relative=False):
    """Remove links from text, except those allowed to stay."""
    text = force_unicode(text)
    if not text:
        return u''

    parser = html5lib.HTMLParser(tokenizer=HTMLSanitizer)
    forest = parser.parseFragment(text)

    if allow_domains is None:
        allow_domains = []
    elif isinstance(allow_domains, basestring):
        allow_domains = [allow_domains]

    def delinkify_nodes(tree):
        """Remove <a> tags and replace them with their contents."""
        for node in tree.childNodes:
            if node.name == 'a':
                if 'href' not in node.attributes:
                    continue
                parts = urlparse.urlparse(node.attributes['href'])
                host = parts.hostname
                if any(_domain_match(host, d) for d in allow_domains):
                    continue
                if host is None and allow_relative:
                    continue
                # Replace the node with its children.
                # You can't nest <a> tags, and html5lib takes care of that
                # for us in the tree-building step.
                for n in node.childNodes:
                    tree.insertBefore(n, node)
                tree.removeChild(node)
            elif node.type != NODE_TEXT: # Don't try to delinkify text.
                delinkify_nodes(node)

    delinkify_nodes(forest)
    return _render(forest)


def _domain_match(test, compare):
    test = test.lower()
    compare = compare.lower()
    if '*' not in compare:
        return test == compare
    c = compare.split('.')[::-1]
    if '**' in c and (c.count('**') > 1 or not compare.startswith('**')):
        raise ValidationError(
            'Only 1 ** is allowed, and must start the domain.')
    t = test.split('.')[::-1]
    z = itertools.izip_longest(c, t)
    for c, t in z:
        if c == t:
            continue
        elif c == '*':
            continue
        elif c == '**':
            return True
        return False
    # Got all the way through and everything matched.
    return True


class ValidationError(ValueError):
    pass


def _render(tree):
    """Try rendering as HTML, then XML, then give up."""
    try:
        return force_unicode(_serialize(tree))
    except Exception, e:
        log.error('HTML: %r' % e, exc_info=sys.exc_info())
        try:
            return force_unicode(tree.toxml())
        except Exception, e:
            log.error('XML: %r' % e, exc_info=sys.exc_info())
            return u''


def _serialize(domtree):
    walker = html5lib.treewalkers.getTreeWalker('simpletree')
    stream = walker(domtree)
    serializer = HTMLSerializer(quote_attr_values=True,
                                omit_optional_tags=False)
    return serializer.render(stream)
