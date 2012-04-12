from zope.proxy import ProxyBase, getProxiedObject, non_overridable
from zope.proxy.decorator import DecoratorSpecificationDescriptor
from zope.security.checker import getCheckerForInstancesOf

class ClassAndInstanceDescr(object):

    def __init__(self, *args):
        self.funcs = args

    def __get__(self, inst, cls):
        if inst is None:
            return self.funcs[1](cls)
        return self.funcs[0](inst)

''' !+UNUSED(mr, apr-2012)
class ShortNameProxy(ProxyBase):
    """This is a non-picklable proxy that can be put around objects to
    change the ``short_name`` attribute.
    """

    __slots__ = 'short_name', '__Security_checker__'
    __safe_for_unpickling__ = True

    def __new__(self, ob, short_name=None):
        checker = getCheckerForInstancesOf(type(ob))
        ob = ProxyBase.__new__(self, ob)
        ob.__Security_checker__ = checker
        return ob
    
    def __init__(self, ob, short_name=None):
        ProxyBase.__init__(self, ob)
        self.short_name = short_name

    @non_overridable
    def __reduce__(self, proto=None):
        raise TypeError("Not picklable")

    __doc__ = ClassAndInstanceDescr(
        lambda inst: getProxiedObject(inst).__doc__,
        lambda cls, __doc__ = __doc__: __doc__,
        )

    __reduce_ex__ = __reduce__

    __providedBy__ = DecoratorSpecificationDescriptor()
'''
