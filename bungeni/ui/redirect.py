# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Redirect views

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.redirect")

import datetime

from zope.publisher.browser import BrowserView
from zope import interface
from zope.publisher.interfaces import IPublishTraverse

from bungeni.ui.utils import url, common
from bungeni.models.utils import get_login_user, get_chamber_for_context
from bungeni.core.workflow.interfaces import IWorkflowController


class RedirectToCurrent(BrowserView):
    """Redirect to current.
    
    Goto a url like current/parliamentmembers or current/committees
    and you will be redirected to the apropriate container
    
    """
    interface.implements(IPublishTraverse)
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.traverse_subpath = []
    
    def publishTraverse(self, request, name):
        self.traverse_subpath.append(name)
        return self
        
    def __call__(self):
        """Redirect to container.
        """
        #context = proxy.removeSecurityProxy( self.context )
        response = self.request.response
        root_url = url.absoluteURL(self.context, self.request)
        #response.setHeader('Content-Type', 'application/octect-stream')
        #if len(self.traverse_subpath) != 1:
        #    return
        #fname = self.traverse_subpath[0]
        qstr =  self.request['QUERY_STRING']
        if 'date' not in self.request.form:
            qstr = "%s&date=%s" % (qstr,
                    datetime.date.strftime(datetime.date.today(),'%Y-%m-%d'))
        to_url = root_url + '/parliament/'
        if len(self.traverse_subpath) >= 1:
            # we have a traversal to redirect to
            if self.traverse_subpath[0] == 'parliament':
                to_url = "%s/parliament/obj-%s/%s?%s" % (
                        root_url,
                        get_chamber_for_context(self.context).group_id,
                        '/'.join(self.traverse_subpath[1:]),
                        qstr)
        return response.redirect(to_url)


class WorkspaceRootRedirect(BrowserView):
    """Redirect logged in users to workspace"""
    def __call__(self):
        request = self.request
        if common.is_admin(self.context):
            to_url = "/admin"
        else:
            to_url = "/workspace"
        request.response.redirect(to_url)

class _IndexRedirect(BrowserView):
    """Redirect to the named "index" view."""
    index_name = "index"
    def __call__(self):
        request = self.request
        log.warn("%s: %s -> %s" % (
            self.__class__.__name__, request.getURL(), self.index_name))
        request.response.redirect(self.index_name)
class WorkspaceContainerIndexRedirect(_IndexRedirect):
    # !+TRAILING_SLASH(mr, sep-2010) this is still needed?
    index_name = url.set_url_context("pi")
class BusinessIndexRedirect(_IndexRedirect):
    index_name = "whats-on"
class MembersIndexRedirect(_IndexRedirect):
    index_name = "current"
class ArchiveIndexRedirect(_IndexRedirect):
    index_name = "browse"
class AdminIndexRedirect(_IndexRedirect):
    index_name = "content"

class SignatoryReview(BrowserView):
    """Redirect to signatory document workflow page
    """
    def __call__(self):
        request = self.request
        context = self.context
        user_id = get_login_user().user_id
        signatories = context.signatories
        _filters = {"user_id": user_id}
        _signatories = signatories.query(**_filters)
        if len(_signatories) == 1:
            signatory = _signatories[0]
            _signatory = signatories.get(signatory.signatory_id)
            review_url = "/".join(
                (url.absoluteURL(_signatory, request), u"workflow")
            )
            return request.response.redirect(review_url)
        

class Favicon(BrowserView):
    """Map requests to favicon.ico to favicon browser resource
    """
    def __call__(self):
        return self.request.response.redirect("/@@/images/favicon.ico",
            status=301
        )        

class WorkflowRedirect(BrowserView):
    """Default redirect after workflow transitions (menu based)
    """
    redirect_to = "./"
    def __call__(self):
        return self.request.response.redirect(self.redirect_to)

class WorkflowRedirectSitting(WorkflowRedirect):
    """For sittings, we redirect to the schedule editor if we are in edit
    mode. Otherwise, we redirect to the default view.
    """
    @property
    def redirect_to(self):
        wfc = IWorkflowController(self.context)
        if "draft" in wfc.state_controller.get_status():
            return "./schedule"
        return WorkflowRedirect.redirect_to
