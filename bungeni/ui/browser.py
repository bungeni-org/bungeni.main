# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Browser Views

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.browser")

import sys
from zope.security.proxy import removeSecurityProxy
from zope.publisher.browser import BrowserView

from bungeni.core.dc import IDCDescriptiveProperties
from bungeni.models.interfaces import IBungeniContent
from bungeni.ui import z3evoque
from bungeni.ui.utils import debug, misc
from bungeni.ui.i18n import _

class BungeniBrowserView(BrowserView):
    
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
        # then try to determine it from DC annotations
        context = removeSecurityProxy(self.context)
        try:
            # This is the equivalent of the ZPT expression "context/dc:title"
            # i.e. to "load the value of the variable context, then find a 
            # component that adapts that object to Dublin Core and read the 
            # title attribute of the component."
            return IDCDescriptiveProperties(context).title
        except (Exception,):
            pass
            
        # otherwise try to determine it from the context
        if getattr(context, "title", None):
            return context.title 
        else:
            debug.log_exc(sys.exc_info(), log_handler=log.debug)
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
        
        # then try to determine it from DC annotations
        context = removeSecurityProxy(self.context)
        try:
            # This is equivalent of the ZPT expression "context/dc:description"
            # i.e. to "load the value of the variable context, then find a 
            # component that adapts that object to Dublin Core and read the 
            # description attribute of the component."
            return IDCDescriptiveProperties(context).description
        except (Exception,):
            pass
         
        # otherwise try to determine it from the context
        if getattr(context, "description", None):
            return context.description  
        else:
            debug.log_exc(sys.exc_info(), log_handler=log.debug)
            return "Bungeni"
    # View subclasses may set a custom page_description by resetting this attr
    # Note: description values are localized in the template itself.
    _page_description = None
    
    @property
    def is_workflowed(self):
        """() -> bool : is this view's context a workflowed object?
        """
        return IBungeniContent.providedBy(self.context)
    
    def get_wf_state(self):
        """Get the human readable, and localized, workflow state title.
        """
        return _(misc.get_wf_state(removeSecurityProxy(self.context)))

