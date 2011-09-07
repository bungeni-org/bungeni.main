# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Browser Views

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.errors")

import zope.publisher.browser
from zope.authentication.interfaces import IUnauthenticatedPrincipal

from bungeni.ui.i18n import _
from bungeni.ui.utils import url

class BaseErrorView(zope.publisher.browser.BrowserView):
    
    http_status_code = 500
    additional_headers = {}

    @property
    def error_message(self):
        return _(u"An error occurred in Bungeni.")

    @property
    def page_title(self):
        return _(u"Bungeni - [Error]")

    def set_extra_headers(self):
        for header_name, header_value in self.additional_headers.iteritems():
            self.request.response.setHeader(header_name, header_value)

    def __call__(self):
        self.set_extra_headers()
        self.request.response.setStatus(self.http_status_code)
        return super(BaseErrorView, self).__call__()

class SystemError(BaseErrorView):

    @property
    def error_message(self):
        return _(u"A system error occurred.")

class Unauthorized(BaseErrorView):

    http_status_code = 403
    additional_headers = {
        "Expires": "Thu, 01 Dec 1994 16:00:00 GMT",
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
    }

    @property
    def error_message(self):
        return _(u"Your account is not authorized to view this item.")

    def __call__(self):
        if IUnauthenticatedPrincipal.providedBy(self.request.principal):
            self.http_status_code = 401
            self.additional_headers.update(
                [("WWW-Authenticate", "Basic realm=Bungeni")]
            )
        return super(Unauthorized, self).__call__()
        
