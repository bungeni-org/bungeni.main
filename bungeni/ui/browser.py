# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Browser Views

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.browser")

import sys
from zope.security.proxy import removeSecurityProxy
import zope.publisher.browser
import zope.viewlet.viewlet

from bungeni.core.dc import IDCDescriptiveProperties
from bungeni.core.workflow.interfaces import IWorkflowed
from bungeni.ui import z3evoque
from bungeni.ui.utils import date, debug, misc
from bungeni.ui.i18n import _


# browser page

class BungeniBrowserView(zope.publisher.browser.BrowserPage):
    """A Bungeni page view. 
    
    We adopt the "View" as the general term for a page view i.e. not the 
    non-page-bound base zope.publisher.browser.BrowserView. 
    
    In-place registration of (page) adapters do not magically up a BrowserView
    to a BrowserPage, so one needs to be more specific about which of these is
    intended. 
    
    Note that BrowserPage extends BrowserView with following features: 
    - implements(IBrowserPage)
    - browserDefault(self, request)
    - publishTraverse(self, request, name),
    - __call__(self, *args, **kw)  
    
    """
    
    # the instance of the ViewProvideViewletManager
    provide = z3evoque.ViewProvideViewletManager()    
    
    @property
    def page_title(self):
        """Formalize view.page_title as a view property to factor the logic
        for determining the page title for a view out of the template.
        
        Templates should always simply call: view.page_title
        """
        # if view explicitly sets a page_title, use it
        if self._page_title:
            return self._page_title
        # otherwise try to determine it from DC annotations
        context = removeSecurityProxy(self.context)
        try:
            # This is the equivalent of the ZPT expression "context/dc:title"
            # i.e. to "load the value of the variable context, then find a 
            # component that adapts that object to Dublin Core and read the 
            # title attribute of the component."
            return IDCDescriptiveProperties(context).title
        except (Exception,):
            debug.log_exc(sys.exc_info(), log_handler=log.debug)
        # otherwise try to determine it from the context
        if getattr(context, "title", None):
            return context.title 
        else:
            return "Bungeni"
    # View subclasses may set a custom page_title by overriding this attr
    # Note: title values are localized in the template itself.
    _page_title = None
    
    
    @property
    def page_description(self):
        """Formalize view.page_description as a view property to factor the 
        logic for determining the page description for a view out of the 
        template.
        
        Templates should always simply call: view.page_description
        """
        # if view explicitly sets a page_description, use it
        if self._page_description:
            return self._page_description
        # otherwise try to determine it from DC annotations
        context = removeSecurityProxy(self.context)
        try:
            # This is equivalent of the ZPT expression "context/dc:description"
            # i.e. to "load the value of the variable context, then find a 
            # component that adapts that object to Dublin Core and read the 
            # description attribute of the component."
            return IDCDescriptiveProperties(context).description
        except (Exception,):
            debug.log_exc(sys.exc_info(), log_handler=log.debug)
        # otherwise try to determine it from the context
        if getattr(context, "description", None):
            return context.description  
        else:
            return "Bungeni"
    # View subclasses may set a custom page_description by resetting this attr
    # Note: description values are localized in the template itself.
    _page_description = None
    
    @property
    def is_workflowed(self):
        """() -> bool : is this view's context a workflowed object?
        """
        return IWorkflowed.providedBy(self.context)
    
    def get_wf_state(self):
        """Get the human readable, and localized, workflow state title.
        """
        return _(misc.get_wf_state(removeSecurityProxy(self.context)))


# bungeni viewlet

class BungeniViewlet(zope.viewlet.viewlet.ViewletBase):
    
    def __init__(self,  context, request, view, manager):
        # the following 4 lines do exactly what calling 
        # zope.viewlet.viewlet.ViewletBase.__init__ does --
        # we re-state them here for convenient explicitness.
        self.__parent__ = view
        self.context = context
        self.request = request
        self.manager = manager
    
    view_id = None # a unique identifier, NOT localized
    view_name = None # a (not necessarily unique) identifier, NOT localized
    view_title = None # localized
    # !+ID/NAME/TITLE/LABEL(mr, oct-2010) standardize usage & naming: view_*
    # !+form_*(mr, oct-2010) rename to view_* e.g. form_name to view_name

    def get_view_id(self):
        return self.view_id or id(self)

class BungeniItemsViewlet(BungeniViewlet):
    """A viewlet listing items (a common case).
    """
    
    # list of data items to be displayed
    items = None
    
    # typically, may want that no items means no display e.g. bool(self.items)
    for_display = True
    
    # locale formatter instance, subclasses use self.get_date_formatter() to set
    formatter = None 
    def get_date_formatter(self, category="date", length="long"):
        return date.getLocaleFormatter(self.request, category, length)

