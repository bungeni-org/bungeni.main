log = __import__("logging").getLogger("bungeni.core.content")

import sys

from zope import interface
from zope import component
from zope.container.ordered import OrderedContainer
from zope.container.traversal import ItemTraverser
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.defaultview import getDefaultViewName
from zope.publisher.interfaces import NotFound
from zope.security.proxy import removeSecurityProxy
from zope.app.component.hooks import getSite
from zope.location.interfaces import ILocation

from bungeni.core.proxy import NavigationProxy
from bungeni.core.proxy import DublinCoreDescriptivePropertiesProxy
from bungeni.ui.utils import debug
from bungeni.ui.interfaces import IBungeniAPILayer

from interfaces import ISection, IAkomaNtosoSection
from interfaces import IQueryContent

class Section(OrderedContainer):
    """A site section, e.g. 'Business'.

    Note that items are not persisted.

    """
    interface.implements(ISection, IDCDescriptiveProperties, IBrowserPublisher)

    # NOTE: __parent__ here is turned into a property for debug/monitoring 
    # purpose -- Section.__parent__ is being set multiple times but, once set, 
    # always to the same value
    def _get_parent(self):
        return self._parent
    def _set_parent(self, obj):
        self._parent = obj
    __parent__ = property(_get_parent, _set_parent)


    def __init__(self, title=None, description=None, default_name=None, 
            marker=None, 
            publishTraverseResolver=None):
        self._parent = None
        super(Section, self).__init__()
        self.title = title
        self.description = description
        self.default_name = default_name
        if marker is not None:
            interface.alsoProvides(self, marker)
        # publishTraverseResolver: callable(context, request, name)
        # returns domain container object
        # raises zope.publisher.interfaces.NotFound
        # !+ we add this as a callback because subclassing Section and 
        # overriding publishTraverse() insists on giving ForbiddenAttribute 
        # erros. 
        self.publishTraverseResolver = publishTraverseResolver
        log.debug(" __init__ %s (title:%s, default_name:%s)" % (self, title, default_name))
    # !+ section.title is duplicated in ZCML menuItem definitions
    # Section should be modified to just get its title from the associated
    # view descriptor (via default_name)

    def __getitem__(self, key):
        item = super(Section, self).__getitem__(key)
        if IQueryContent.providedBy(item):
            obj = item.query(self)
            obj.__name__ = item.__name__
            obj.__parent__ = DublinCoreDescriptivePropertiesProxy(
                NavigationProxy(obj.__parent__, item.__parent__),
                title=self.title, description=self.description)
            return obj
        return item

    def __setitem__(self, key, value):
        super(Section, self).__setitem__(key, value)
        value.__parent__ = self
        value.__name__ = key

    def browserDefault(self, request):
        """See zope.container.traversal.ContainerTraverser.
            -> context, (view_uri,)
        """
        default_name = self.default_name
        if default_name is None or IBungeniAPILayer.providedBy(request):
            default_name = getDefaultViewName(self, request)
        return self, (default_name,)
    
    # !+ all methods should indicate what the expected input parameter
    # types and return value types should be e.g. by adopting a 
    # python3-style type annotations as a doc string, 
    # as indicated in the SAMPLE docstring here:
    def publishTraverse(self, request, name):
        """Lookup a name -  (request:IRequest, name:str) -> IView

        The 'request' argument is the publisher request object.  The
        'name' argument is the name that is to be looked up; it must
        be an ASCII string or Unicode object.

        If a lookup is not possible, raise a NotFound error.

        This method should return an object having the specified name and
        `self` as parent. The method can use the request to determine the
        correct object.
        """
        _meth_id = "%s.publishTraverse" % self.__class__.__name__
        log.debug("%s: name=%s __name__=%s __parent__=%s context=%s" % (
            _meth_id, name, self.__name__, self.__parent__, 
            getattr(self, "context", "UNDEFINED")))
        try:
            assert self.publishTraverseResolver is not None
            return self.publishTraverseResolver(self, request, name)
        except (AssertionError,):
            pass # self.publishTraverseResolver is None, not an error
        except (NotFound,):
            pass # this is not really an error
            #debug.log_exc_info(sys.exc_info(), log.debug)
        except (TypeError, Exception):
            debug.log_exc_info(sys.exc_info(), log.error)
        traverser = ItemTraverser(self, request)
        return traverser.publishTraverse(request, name)


class AkomaNtosoSection(OrderedContainer):

    lang = u""
    type = u""
    id = u""
    date = u""

    interface.implements(IAkomaNtosoSection, IDCDescriptiveProperties)

    # NOTE: __parent__ here is turned into a property for debug/monitoring 
    # purpose -- Section.__parent__ is being set multiple times but, once set, 
    # always to the same value
    def _get_parent(self):
        return self._parent
    def _set_parent(self, obj):
        if self._parent is not None and obj is not None:
            # __parent__ is nullified when deleting a Section from parent container
            assert self._parent is obj, \
                "Section parent may not be changed! %s -> %s" % (self._parent, obj)
            log.warn(" [Section:%s] IGNORING reset of __parent__ to same " \
                    "value: %s" % (self.title, obj))
            return
        self._parent = obj
    __parent__ = property(_get_parent, _set_parent)
    
    
    def __init__(self, title=None, description=None, default_name=None, 
            marker=None, 
            publishTraverseResolver=None):
        self._parent = None
        super(AkomaNtosoSection, self).__init__()
        self.title = title
        self.description = description
        self.default_name = default_name
        if marker is not None:
            interface.alsoProvides(self, marker)
        # publishTraverseResolver: callable(context, request, name)
        # returns domain container object
        # raises zope.publisher.interfaces.NotFound
        # !+ we add this as a callback because subclassing Section and 
        # overriding publishTraverse() insists on giving ForbiddenAttribute 
        # erros. 
        self.publishTraverseResolver = publishTraverseResolver
        log.debug(" __init__ %s (title:%s, default_name:%s)" % (self, title, default_name))
        
        
    # !+ section.title is duplicated in ZCML menuItem definitions
    # Section should be modified to just get its title from the associated
    # view descriptor (via default_name)
    
    
    def __getitem__(self, key):
        item = super(AkomaNtosoSection, self).__getitem__(key)
        if IQueryContent.providedBy(item):
            obj = item.query(self)
            obj.__name__ = item.__name__
            obj.__parent__ = DublinCoreDescriptivePropertiesProxy(
                NavigationProxy(obj.__parent__, item.__parent__),
                title=self.title, description=self.description)
            return obj
        return item
    
    def __setitem__(self, key, value):
        super(AkomaNtosoSection, self).__setitem__(key, value)
        value.__parent__ = self
        value.__name__ = key
    
    def browserDefault(self, request):
        """See zope.container.traversal.ContainerTraverser.
            -> context, (view_uri,)
        """
        default_name = self.default_name
        if default_name is None:
            default_name = getDefaultViewName(self, request)
        return self, (default_name,)


class AdminSection(Section):
    pass


class WorkspaceSection(Section):
    pass


class APISection(Section):

    def __setitem__(self, key, value):
        value.__parent__ = self
        value.__name__ = key
        super(APISection, self).__setitem__(key, value)


class OAuthSection(Section):
    pass

#!+SECURITY (miano, nov-2010) the security checker below does not seem to be
# used.
# ensure public security setting for these Section attributes
#from zope.security.checker import CheckerPublic, Checker, defineChecker
#_PUBLIC_ATTRS = { 
#    'browserDefault':CheckerPublic, 
#    '__call__':CheckerPublic,
#    'publishTraverse':CheckerPublic
#}
#defineChecker(Section, Checker(_PUBLIC_ATTRS))


class QueryContent(object):
    interface.implements(IQueryContent, IDCDescriptiveProperties)

    def __init__(self, query, title=None, description=None, marker=None):
        if marker is not None:
            def query(parent, query=query):
                obj = query(parent)
                interface.alsoProvides(obj, marker)
                return obj
        self.query = query
        self.title = title
        self.description = description
     
