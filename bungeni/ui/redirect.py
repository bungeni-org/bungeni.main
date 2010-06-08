import datetime

from zope.publisher.browser import BrowserView
from zope.interface import implements
from zope.publisher.interfaces import IPublishTraverse

import bungeni.core.globalsettings as prefs
from bungeni.ui.utils import url as ui_url

class RedirectToCurrent(BrowserView):
    """Redirect to current.
    
    Goto a url like current/parliamentmembers or current/committees
    and you will be redirected to the apropriate container
    
    """
    implements(IPublishTraverse)
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.traverse_subpath = []
        self.currParliament = prefs.getCurrentParliamentId()

    def publishTraverse(self, request, name):
        self.traverse_subpath.append(name)
        return self
        
    def __call__(self):
        """redirect to container"""
        #context = proxy.removeSecurityProxy( self.context )
        response = self.request.response
        rooturl = ui_url.absoluteURL(self.context, self.request)
        #response.setHeader('Content-Type', 'application/octect-stream')
        #if len(self.traverse_subpath) != 1:
        #    return
        #fname = self.traverse_subpath[0]
        qstr =  self.request['QUERY_STRING']
        if 'date' not in self.request.form:
            qstr = "%s&date=%s" % (qstr,
                    datetime.date.strftime(datetime.date.today(),'%Y-%m-%d'))
        url = rooturl + '/parliament/'
        if len(self.traverse_subpath) >= 1:
            # we have a traversal to redirect to
            if self.traverse_subpath[0] == 'parliament':
                url = "%s/parliament/obj-%s/%s?%s" % (
                        rooturl,
                        self.currParliament,
                        '/'.join(self.traverse_subpath[1:]),
                        qstr)
        return response.redirect(url)

