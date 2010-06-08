from zope import interface
from zope import schema
from zope.formlib import form

from zope.app.component.hooks import getSite
from zope.publisher.browser import BrowserView
from zope.app.security.interfaces import IUnauthenticatedPrincipal

import bungeni.ui.utils as ui_utils
from alchemist.ui.core import BaseForm
from bungeni.core.i18n import _

class ILoginForm( interface.Interface ):
    login = schema.TextLine( title=_(u"Username"))
    password = schema.Password( title=_(u"Password"))
    
class Login( BaseForm ):
    form_fields = form.Fields( ILoginForm )
    prefix = ""
    form_name = _(u"Login")
    
    @form.action( _(u"Login") )
    def handle_login(self, action, data):
        if IUnauthenticatedPrincipal.providedBy(self.request.principal):
            self.status = _(u"Invalid account credentials")
        else:
            site_url = ui_utils.url.absoluteURL(getSite(), self.request)
            camefrom = self.request.get('camefrom', site_url+'/')
            self.status = _("You are now logged in")
            self.request.response.redirect( camefrom )

class Logout( BrowserView ):
    def __call__( self ):
        self.request.response.expireCookie( "wc.cookiecredentials" )
        site_url = ui_utils.url.absoluteURL(getSite(), self.request)
        self.request.response.redirect( site_url )
