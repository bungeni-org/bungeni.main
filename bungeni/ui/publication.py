# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Manipulation of request publications

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.publication")

import re

from zope import interface
from zope import component
from zope.app.publication.interfaces import IBeforeTraverseEvent
from zope.app.publication.interfaces import IEndRequestEvent
from zope.app.security.interfaces import IUnauthenticatedPrincipal
from zope.annotation.interfaces import IAnnotations

from bungeni.alchemist import Session

from bungeni.ui import interfaces
from bungeni.ui.utils import url, common
from bungeni.utils.common import has_feature
from bungeni.ui.descriptor.localization import check_reload_localization


# !+IStartRequestEvent(mr, jun-2011) the once_per_request() below is a 
# workaround to simulate the above event, gthat was introduced in. 
# zope.app.publication 3.12.0. This utility and code using it should be
# cleaned out after updating to that package.

def once_per_request(event_handler):
    """Wrap event_handler to limit execution of it to once per request."""
    flag_name = "%s_DONE" % (event_handler.func_name)
    def event_handler_closure(event):
        if not IAnnotations(event.request).get(flag_name, False): 
            IAnnotations(event.request)[flag_name] = True
            event_handler(event)
        else:
            log.debug(" [once_per_request->%s] IGNORING..." % (flag_name))
    return event_handler_closure


# guard event handlers to be called only ONCE per request
check_reload_localization = once_per_request(check_reload_localization)


# event subscribers, dispatch co-ordinators

@component.adapter(IBeforeTraverseEvent)
def on_before_traverse(event):
    """Subscriber to intercept traversal, and dispatch as needed to dedicated 
    request pre-processors. We intercept centrally and then call processors
    explicitly to guarantee execution order.
    """
    log.debug("IBeforeTraverseEvent:%s:%s:%s" % (
        id(event.request), event.request.getURL(), event.object))
    apply_request_layer_by_url(event)
    if not IUnauthenticatedPrincipal.providedBy(event.request.principal):
        interface.alsoProvides(event.request,
            interfaces.IBungeniAuthenticatedSkin)
    remember_traversed_context(event)
    if has_feature("devmode"):
        check_reload_localization(event)

@component.adapter(IEndRequestEvent)
def on_end_request(event):
    """Subscriber to catch end of request processing, and dispatch cleanup 
    tasks as needed. 
    """
    session = Session()
    log.debug("IEndRequestEvent:%s:%s:%s\n"
        "    closing SqlAlchemy session: %s" % (
            id(event.request), event.request.getURL(), event.object, session))
    common._clear_request_cache()

    

# some actual handlers

from zope.security.proxy import removeSecurityProxy
def remember_traversed_context(event):
    """Called per IBeforeTraverseEvent -- remember request's context
    (event.object) at each traversal, for downstream convenience.
    
    The intended usage is for generic non-contextual code -- that needs to 
    do some action depending on the context -- called by framework/3rd-party 
    code using an API not under the control of this application.
    """
    IAnnotations(event.request).setdefault("contexts", []
        ).append(removeSecurityProxy(event.object))

#

mapping_on_path = (
    (re.compile(r'^/$'), interfaces.IHomePageLayer),
    (re.compile(r'^/profile(/.*)?$'), 
        interfaces.IWorkspaceSectionLayer
    ), 
    
    #matches "workspace/under-consideration"
    (re.compile(r'^/workspace/under-consideration(/.*)?$'),
        interfaces.IWorkspaceUnderConsiderationSectionLayer
    ),
    # Matches "workspace/scheduling"
    (re.compile(r'^/workspace/scheduling(/.*)?$'),
        interfaces.IWorkspaceSchedulingSectionLayer
    ),
    #matches "workspace/my-documents"
    (re.compile(r'^/workspace/my-documents(/.*)?$'),
        interfaces.IWorkspaceMyDocumentsSectionLayer
    ),
    #matches "workspace/groups"
    (re.compile(r'^/workspace/groups(/.*)?$'),
        interfaces.IWorkspaceGroupsSectionLayer
    ),
    #matches "workspace"
    (re.compile(r'^/workspace(/.*)?$'),
        interfaces.IWorkspaceMyDocumentsSectionLayer
    ),
    (re.compile(r'^/admin(/.*)?$'), interfaces.IAdminSectionLayer),
    (re.compile(r'^/bungeni(/.*)?$'), interfaces.IPermalinkSectionLayer),
    (re.compile(r'^/api(/.*)?$'), interfaces.IBungeniAPILayer),
)
mapping_on_path_info = (
    (re.compile(r'^/(\+\+)|(@@)'), interfaces.IResourceNonLayer),
)
def apply_request_layer_by_url(event):
    """Apply a request layer by URL.

    This subscriber applies a request-layer on the ``request`` object
    based on the request to allow layer-based component registration
    of user interface elements.
    
    NOTE: only one layer is applied -- the first one to match.
    """
    request = event.request
    #path = "/".join(reversed(request.getTraversalStack()))
    path = url.get_destination_url_path(request)
    path_info = request.get("PATH_INFO")
    log.debug(" [apply_request_layer_by_url] path=%s path_info=%s" % (
                                                            path, path_info))
    for condition, layer in mapping_on_path:
        if condition.match(path) is not None:
            log.debug("Adding %s layer to request for path <%s>" % (layer, path))
            interface.alsoProvides(request, layer)
            break # only apply first matching layer
    else: # there was no break, no mapping_on_path layer added
        # !+IResourceNonLayer(mr, nov-2010) almost never passes thru here
        for condition, layer in mapping_on_path_info:
            if condition.match(path_info) is not None:
                log.debug("Adding %s layer to request for path_info <%s>" % (
                                                            layer, path_info))
                interface.alsoProvides(request, layer)
                break
# filter this event handler to be called only ONCE per request
apply_request_layer_by_url = once_per_request(apply_request_layer_by_url)


