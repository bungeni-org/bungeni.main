import zope.interface

from zope.proxy import ProxyBase, getProxiedObject, non_overridable
from zope.proxy import removeAllProxies
from zope.proxy.decorator import DecoratorSpecificationDescriptor
from zope.security.checker import getCheckerForInstancesOf
from zope.location.interfaces import ILocation
from zope.dublincore.interfaces import IDCDescriptiveProperties

from interfaces import INavigationProxy

class ClassAndInstanceDescr(object):

    def __init__(self, *args):
        self.funcs = args

    def __get__(self, inst, cls):
        if inst is None:
            return self.funcs[1](cls)
        return self.funcs[0](inst)

class DublinCoreDescriptivePropertiesProxy(ProxyBase):
    """This is a non-picklable proxy that can be put around objects to
    add descriptive properties.
    """

    zope.interface.implements(IDCDescriptiveProperties)
    
    __slots__ = 'title', 'description', '__Security_checker__'
    __safe_for_unpickling__ = True

    def __new__(self, ob, title=None, description=None):
        checker = getCheckerForInstancesOf(type(removeAllProxies(ob)))
        ob = ProxyBase.__new__(self, ob)
        ob.__Security_checker__ = checker
        return ob
    
    def __init__(self, ob, title=None, description=None):
        ProxyBase.__init__(self, ob)
        self.title = title
        self.description = description
        
    @non_overridable
    def __reduce__(self, proto=None):
        raise TypeError("Not picklable")

    __doc__ = ClassAndInstanceDescr(
        lambda inst: getProxiedObject(inst).__doc__,
        lambda cls, __doc__ = __doc__: __doc__,
        )

    __reduce_ex__ = __reduce__

    __providedBy__ = DecoratorSpecificationDescriptor()

class NavigationProxy(ProxyBase):
    """Navigation proxy.

    Forwards the ``__getitem__`` attribute of the proxied object to
    that of another.
    """

    zope.interface.implements(INavigationProxy)
    
    __slots__ = '__target__', '__Security_checker__'
    __safe_for_unpickling__ = True

    def __new__(self, ob, target):
        checker = getCheckerForInstancesOf(type(removeAllProxies(ob)))
        ob = ProxyBase.__new__(self, ob)
        ob.__Security_checker__ = checker
        return ob

    def __init__(self, ob, target):
        ProxyBase.__init__(self, ob)
        self.__target__ = target

    def __getitem__(self, key):
        return self.__target__[key]

    def __setitem__(self, key, value):
        self.__target__[key] = value

    def __iter__(self):
        return iter(self.__target__)

    @property
    def __name__(self):
        return self.__target__.__name__

    @property
    def __parent__(self):
        return self.__target__.__parent__

    @property
    def items(self):
        return self.__target__.items

    @property
    def keys(self):
        return self.__target__.keys

    @property
    def values(self):
        return self.__target__.values

    @non_overridable
    def __reduce__(self, proto=None):
        raise TypeError("Not picklable")

    __doc__ = ClassAndInstanceDescr(
        lambda inst: getProxiedObject(inst).__doc__,
        lambda cls, __doc__ = __doc__: __doc__,
        )

    __reduce_ex__ = __reduce__

    __providedBy__ = DecoratorSpecificationDescriptor()
    
class LocationProxy(ProxyBase):
    """Location-object proxy

    This is a non-picklable proxy that can be put around objects that
    don't implement `ILocation`.
    """

    zope.interface.implements(ILocation)

    __slots__ = '__parent__', '__name__'
    __safe_for_unpickling__ = True

    def __new__(self, ob, container=None, name=None):
        checker = getCheckerForInstancesOf(type(removeAllProxies(ob)))
        ob = ProxyBase.__new__(self, ob)
        ob.__Security_checker__ = checker
        return ob

    def __init__(self, ob, container=None, name=None):
        ProxyBase.__init__(self, ob)
        self.__parent__ = container
        self.__name__ = name

    @non_overridable
    def __reduce__(self, proto=None):
        raise TypeError("Not picklable")

    __doc__ = ClassAndInstanceDescr(
        lambda inst: getProxiedObject(inst).__doc__,
        lambda cls, __doc__ = __doc__: __doc__,
        )

    __reduce_ex__ = __reduce__

    __providedBy__ = DecoratorSpecificationDescriptor()

