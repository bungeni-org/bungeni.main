# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Browser Views

$Id:  $
"""
log = __import__("logging").getLogger("bungeni.ui.browser")

import sys
from zope.publisher.browser import BrowserView

from bungeni.core.dc import IDCDescriptiveProperties
from bungeni.ui.utils import debug


class BungeniBrowserView(BrowserView):
    
    # View subclasses may set a custom page_title by overriding this attribute
    # Note: title values are localized in the template itself.
    _page_title = None
    
    @property
    def page_title(self):
        """Formalize view.page_title as a view property to factor the logic for 
        determining the page title for a view out of the template. 
        Templates should always simply call view.page_title.
        """
        if self._page_title:
            return self._page_title
        if getattr(self.context, "title"):
            return self.context.title 
        try:
            # This is the equivalent of the ZPT expression "context/dc:title"
            # i.e. to "load the value of the variable context, then find a 
            # component that adapts that object to Dublin Core and read the 
            # title attribute of the component."
            return IDCDescriptiveProperties(self.context).title
        except (Exception,):
            debug.log_exc(sys.exc_info(), log_handler=log.debug)
            return "Bungeni"

