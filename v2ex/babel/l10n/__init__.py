# coding=utf-8

import logging

# About language detecting logic:
#
# Step 1: if member.l10n is not empty/false, use it as the best choice
#
# Step 2: if Accept-Language header has something interesting, use it as the second choice
#
# Step 3: Fallback to site.l10n

def GetMessages(handler, member=False, site=False):
    logging.info(handler.request.headers)
    logging.info(site.l10n)
    if member is not False:
        if member.l10n == 'en':
            from v2ex.babel.l10n.messages import en as messages
            return messages
        if member.l10n == 'zh-Hans':
            from v2ex.babel.l10n.messages import zhHans as messages
            return messages
    else:
        if site.l10n == 'en':
            from v2ex.babel.l10n.messages import en as messages
            return messages
        if site.l10n == 'zh-Hans':
            from v2ex.babel.l10n.messages import zhHans as messages
            return messages

def GetSupportedLanguages():
    return ['en', 'zh-Hans']

def GetSupportedLanguagesNames():
    return {'en' : 'English', 'zh-Hans' : u'简体中文'}
    
def GetLanguageSelect(current):
    lang = GetSupportedLanguages()
    names = GetSupportedLanguagesNames()
    s = '<select name="l10n">'
    for l in lang:
        if l == current:
            s = s + '<option value="' + l + '" selected="selected">' + names[l] + '</option>'
        else:
            s = s + '<option value="' + l + '">' + names[l] + '</option>'
    s = s + '</select>'
    return s