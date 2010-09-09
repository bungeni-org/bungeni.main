from zope.interface import implements
from zope.component import getUtility

from zope.publisher.interfaces import NotFound
from zope.publisher.browser import applySkin
from zope.publisher.browser import BrowserView  
from zope.traversing.namespace import view
from zope.publisher.interfaces.browser import IBrowserView
from zope.publisher.interfaces.browser import IBrowserPublisher

from bungeni.rest.interfaces import IREST, MethodNotAllowed, IRESTLayer
from bungeni.rest.interfaces import IRESTSkinType
from zope.component.interfaces import ComponentLookupError
from zope.traversing.interfaces import TraversalError

import simplejson

ALLOWED_METHODS = ('GET', 'POST', 'HEAD', 'PUT',)
from zope.location import Location

class REST(Location):
    """A base REST component
    """
    implements(IREST)

    def __init__(self, context, request):
        self.context = self.__parent__ = context
        self.request = request
        self.response = request.response

    def browserDefault(self, request):
        """Render the component using a method called the same way
        that the HTTP method name.
        """
        if request.method in ALLOWED_METHODS:
            if hasattr(self, request.method):
                return self, (request.method,)
        raise MethodNotAllowed(request.method)

    def publishTraverse(self, request, name):
        """You can traverse to a method called the same way that the
        HTTP method name.
        """

        if name in ALLOWED_METHODS and name == request.method:
            if hasattr(self, name):
                return getattr(self, name)
        raise NotFound(name)

    def json_response(self, result):
        """Encode a result as a JSON response.
        """
        self.response.setHeader('Content-Type', 'application/json')
        return simplejson.dumps(result)


class MethodNotAllowedView(BrowserView):

    def update(self):
        self.response.setStatus(405)

    def render(self):
        return u"Method not allowed"


class RESTNamespace(view):
    """Implement a namespace ++rest++.
    """

    def traverse(self, name, ignored):
        self.request.shiftNameToApplication()
        try:
            skin = getUtility(IRESTSkinType, name)
        except ComponentLookupError:
            raise TraversalError("++rest++%s" % name)
        applySkin(self.request, skin)
        return self.context
