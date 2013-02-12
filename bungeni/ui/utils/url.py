# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""URL path/name utilities for the UI

recommended usage:
from bungeni.ui.utils import url

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.utils.url")

import zope

from bungeni.ui.utils import common
from bungeni.utils import register
from ploned.ui.interfaces import IBodyCSS
from bungeni.models import utils

def get_destination_url_path(request=None):
    """Get the (effective, sans any "traversal namespace notation" components
    and other such "traversal processing instruction" url components) target 
    URL path of the (current) request.
    """
    if request is None:
        request = common.get_request()
    #_url = request.URL
    #_url = request.getURL(level=0, path_only=True)
    # NOTE: both URL and getURL() depend on where we are in the traversal 
    # process i.e. they return the *currently* traversed URL path and not 
    # the full requested path. 
    # 
    # So, we use the request's PATH_INFO but as this may contain:
    # - (++) any number of Zope "traversal namespace notation" url components
    # - (@@/) to indicate that the URL is for an object that is a resource
    # - (@@)) to indicate a view name
    # we need to get rid of them:
    _url = "/".join([ url_component 
            for url_component in request.get("PATH_INFO").split("/")
            if not url_component.startswith("++") and 
                not url_component.startswith("@@") ])
    log.debug(" [get_destination_url_path] %s " % _url)
    return _url


def get_section_name(request=None):
    """Pick off the first URL component i.e. the section name.
    """
    url_comps = get_destination_url_path(request).split("/")
    if len(url_comps)>1: 
       return url_comps[1]
    return ""

def get_subsection_name(request=None):
    url_comps = get_destination_url_path(request).split("/")
    if len(url_comps)>2: 
       return url_comps[2]
    return ""


@register.utility(provides=IBodyCSS)
class BodyCSSClass(object):
    
    def get_body_css_class(self):
        # Add custom css classes to the list below
        chamber_type = "default"
        chamber = utils.get_login_user_chamber()
        if chamber and chamber.parliament_type:
            chamber_type = chamber.parliament_type
        classes = ["yui-skin-sam", "section-bungeni-%s" % get_section_name(),
                   "chamber-%s" % chamber_type]
        return " ".join(classes)


def urljoin(base, action):
    if action is None:
        return
    if action.startswith("http://") or action.startswith("https://"):
        return action
    if action.startswith("/"):
        raise NotImplementedError(action)
    return "/".join((base, action.lstrip("./")))


indexNames = ("index", "index.html", "@@index.html")

def absoluteURL(context, request):
    """
    For cleaner public URLs, we ensure to use an empty string instead of "index".
    
    Throughout bungeni and ploned packages, this function should ALWAYS be
    used instead of zope.traversing.browser.absoluteURL.
    
    """
    try:
        url = zope.traversing.browser.absoluteURL(context, request).split("/")
    except:
        return ""
    while url[-1] in indexNames:
        log.warning(" POPPING: %s -> %s" % ("/".join(url), url[-1]))
        url.pop()
    return "/".join(url)

def same_path_names(base_path_name, path_name):
    """ (base_path_name, path_name) -> bool
    
    Checks if the two url path names are "equivalent" -- considering the case 
    for "" as base_path_name implying that we should be at an "index" URL node.
    
    """
    if base_path_name!=path_name:
        if base_path_name=="": # empty string -> index
            if path_name in indexNames:
                return True
    return base_path_name==path_name

def get_menu_item_descriptor(title, selected, url, name=None):
    if name in indexNames:
        name = ""
    if name is not None:
        url = "%s/%s" % (url, name)
    return {"title": title, "selected": selected, "url": url}


def set_url_context(url):
    """Append a trailing slash to any url that is used for navigation links 
    in viewlets, breadcrumbs and listings.
    """
    # !+ rename: ensure_trailing_slash()
    if not url.endswith("/"):
        return url + "/"
    return url

