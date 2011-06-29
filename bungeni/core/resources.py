log = __import__("logging").getLogger("bungeni.core.resources")

from zope import interface
from zope import component
from zope.component import queryMultiAdapter
from zope.component import getMultiAdapter
from zope.traversing.namespace import view
from zope.traversing.browser.absoluteurl import SiteAbsoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.annotation.interfaces import IAnnotations
from zope.publisher.interfaces.browser import IHTTPRequest
from zope.publisher.http import DEFAULT_PORTS

from bungeni.models.interfaces import IBungeniApplication

annotation_key = "rh"
_safe = '@+' # see ``zope.traversing.browser.absoluteurl``

class ResourceHost(object):
    def __init__(self, host, proto, port):
        if port and str(port) != DEFAULT_PORTS.get(proto):
            host = '%s:%s' % (host, port)
        self.host = "%s://%s" % (proto, host)
        
    def setVirtualHostRoot(self, app_names):
        self.app_names = tuple(app_names)

    @property
    def url(self):
        return "/".join((self.host,)+self.app_names)
            
class rh(view):
    def traverse(self, name, ignored):
        traversal_stack = self.request.getTraversalStack()
        app_names = []
        if not name:
            return self.context
        
        try:
            proto, host, port = name.split(":")
        except ValueError:
            raise ValueError("Rhost directive should have the form "
                             "++rh++protocol:host:port")

        rhost = IAnnotations(self.request)[annotation_key] = ResourceHost(
            host, proto, port)

        if '++' in traversal_stack:
            segment = traversal_stack.pop()
            while segment != '++':
                app_names.append(segment)
                segment = traversal_stack.pop()
            self.request.setTraversalStack(traversal_stack)
        else:
            raise ValueError(
                "Must have a path element '++' after a virtual host "
                "directive.")

        rhost.setVirtualHostRoot(app_names)

        return self.context

class ResourceSiteAbsoluteURL(SiteAbsoluteURL):
    component.adapts(IBungeniApplication, IHTTPRequest)
    interface.implementsOnly(IAbsoluteURL)

    rhost = None
    
    def __new__(cls, context, request):
        rhost = IAnnotations(request).get(annotation_key)
        if rhost is not None:
            inst = object.__new__(cls, context, request)
            inst.rhost = rhost
            return inst
    
    def __str__(self):
        log.debug("ResourceSiteAbsoluteURL.__str__: %s [%s]" % (
                                                self.rhost.url, self.context))
        return self.rhost.url

    __call__ = __str__

