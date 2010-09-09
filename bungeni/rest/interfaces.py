from zope.interface.interfaces import IInterface
from zope.interface import Interface
from zope.interface import Attribute
from zope.publisher.interfaces.http import IHTTPRequest
from zope.publisher.interfaces.http import IHTTPResponse

class IRESTRequest(IHTTPRequest):
    """A special type of request for handling REST-based requests."""

class IRESTResponse(IHTTPResponse):
    """A special type of response for handling REST-based requests."""

class IRESTSkinType(IInterface):
    """Skin type for REST requests.
    """


class IREST(Interface):

    context = Attribute("Object that the REST handler presents.")

    request = Attribute("Request that REST handler was looked"
                        "up with.")

    body = Attribute("""The text of the request body.""")


class IRESTLayer(IHTTPRequest):
    """Layer for registering REST views."""


class MethodNotAllowed(Exception):
    """This method is not allowed."""

