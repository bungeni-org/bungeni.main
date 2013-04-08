# -*- coding: utf-8 -*-
# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Misc utilities for the UI

recommended usage:
from bungeni.ui.utils import misc

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.utils.misc")

from types import StringTypes, ListType
import os
import re
import string
from lxml import html

from bungeni.core.workflow import interfaces
from bungeni.ui.i18n import _


# file system 

def pathjoin(basefilepath, filepath):
    return os.path.join(os.path.dirname(basefilepath), filepath)


# workflow 

# !+RENAME(mr, mar-2011) to get_workflow_state_title
def get_wf_state(context, wf_status=None):
    """Get the human readable title for the context's workflow state
    """
    workflow = interfaces.IWorkflow(context, None)
    if workflow is None:
        log.warn("No workflow exists for %s", context)
        return "" # !+ !!
    if wf_status is None:
        # retrieve and use current status
        wf_status = interfaces.IStateController(context).get_status()
    # ok, pick off the current state's title
    return workflow.get_state(wf_status).title


# request 

def is_ajax_request(request):
    return request.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


# list

def makeList(itemIds):
    if type(itemIds) == ListType:
        return itemIds
    elif type(itemIds) in StringTypes:
        # only one item in this list
        return [itemIds,]
    else:
         raise TypeError(_("Form values must be of type string or list"))

# object

class bunch(dict):
    """
    A dictionary-bunch of values, with convenient dotted access.
    Limitation: keys must be valid object attribute names.
    Inspiration: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52308
    """
    def __init__(self, **kwds):
        dict.__init__(self, kwds)
        self.__dict__ = self

    def __getstate__(self):
        return self

    def __setstate__(self, state):
        self.update(state)
        self.__dict__ = self

    def update_from_object(self, obj, no_underscored=True):
        """ (obj:object) -> None
        Sets each key in dir(obj) as key=getattr(object, key) in self.
        If no_underscored, then exclude "private" (leading "_") and 
        "protected" (leading "__") attributes.
        """
        for name in dir(obj):
            if not (no_underscored and name.startswith("_")):
                self[name] = getattr(obj, name)


REGEX_FOR_SLUGS = re.compile(u"[^\w\.]")
def slugify(string_to_slug):
    """Generate slugified versions of a string
    
    Replace all all non-alphanumeric and stops characters with underscores
    
    Test with various character combinations
    >>> from bungeni.ui.utils import misc
    >>> misc.slugify("")
    u''
    >>> misc.slugify("simple")
    u'simple'
    >>> misc.slugify("textNumber1")
    u'textNumber1'
    >>> misc.slugify(u"specialasciiA1^&00")
    u'specialasciiA1__00'
    >>> misc.slugify(u"non ascii and spaces ĆýĊĔ")
    u'non_ascii_and_spaces_____'
    
    """
    assert isinstance(string_to_slug, basestring)
    slug = unicode(string_to_slug)
    slug = re.sub(REGEX_FOR_SLUGS, u'_', slug)
    return slug


def text_snippet(text, length):
    """Generates a text snippet no longer than `length` from `text`
    
    >>> from bungeni.ui.utils.misc import text_snippet
    >>> text_snippet("", 10)
    u'No Text'
    >>> text_snippet("Some Text", 10)
    u'Some Text'
    >>> text_snippet("Some Text", 5)
    u'Some'
    >>> text_snippet("SomeText", 5)
    u'SomeT'
    >>> text_snippet("non ascii and spaces ĆýĊĔ", 30)
    u'non ascii and spaces \xc4\x86\xc3\xbd\xc4\x8a\xc4\x94'
    >>> text_snippet("non ascii and spaces ĆýĊĔ", 20)
    u'non ascii and spaces'
    >>> text_snippet("<div>HTML</div> Content", 10)
    u'HTML'
    >>> text_snippet("<div>HTML</div> Content", 20)
    u'HTML Content'

    """
    if not len(text):
        return _(u"No Text")
    html_body = html.fromstring(text)
    html_text = html.tostring(html_body, method="text", encoding=unicode)
    title = html_text[0:length]
    if len(title) == length:
        if (html_text[length] not in (string.whitespace + string.punctuation)):
            parts = title.split()
            if len(parts) > 1:
                parts.pop()
                title = u" ".join(parts).strip()
    return title.strip()


def set_json_headers(request):
    """Set appropriate headers on JSON response"""
    request.response.setHeader("Content-type", "application/json")
