# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Browser Views

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.errors")

import zope.publisher.browser
from bungeni.ui.i18n import _



class BaseErrorView(zope.publisher.browser.BrowserView):
    
    @property
    def page_title(self):
        return _(u"Bungeni - [Error]")
    
    @property
    def error_message(self):
        return _(u"An error occured in Bungeni")


class Unauthorized(BaseErrorView):

    @property
    def error_message(self):
        return _(u"Your account is not authorized to view this item.")
