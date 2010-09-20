from zope import interface
from zope import component
from zope.location.interfaces import ILocation
from zope.location.interfaces import LocationError
from bungeni.core.proxy import LocationProxy
from bungeni.core.interfaces import IContainerLocation
from bungeni.core.interfaces import IQueryContent

from bungeni.alchemist.container import stringKey

def location_wrapped(context, location):
    """Provides location information to ``context`` based on the
    existing ``location`` tree using a location proxy.
    """
    return component.getMultiAdapter((context, location), ILocation)


@interface.implementer(ILocation)
@component.adapter(interface.Interface, ILocation)
def get_location_from_parent(context, location):
    return component.getMultiAdapter(
        (context, location.__parent__), ILocation)


class ContainerLocation(object):
    interface.implements(IContainerLocation)

    def __init__(self, *containers):
        self.containers = containers
        interface.implementer(ILocation)(self)

    def __call__(self, context, location):
        key = stringKey(context)
        for container in self.containers:
            if IQueryContent.providedBy(container):
                parent = container.__parent__
                container = container.query(location)
                if parent is not None:
                    container.__parent__ = parent
            if key in container:
                return LocationProxy(context, container, key)
        raise LocationError(key)

