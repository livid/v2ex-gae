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
    from v2ex.babel.l10n.messages import en as messages
    return messages

def GetSupportedLanguages():
    return ['en', 'zh-Hans']

def GetSupportedLanguagesNames():
    return {'en' : 'English', 'zh-Hans' : u'简体中文'}