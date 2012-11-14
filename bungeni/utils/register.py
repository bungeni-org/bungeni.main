# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""ZCA Register Utilities

Some simple utilities to help make component registration (a) more convneinet
and (b) enable it to be where it should be in vast majority of cases i.e. right
next to the component definition. 

This helps on both fronts of (a) readability, so code maintainability and 
(b) and helps reduce pieces of code becoming orphaned, that happens very 
frequently when registration is in a separate file (and in a differnet format,
typicall zcml).

Usage:
from bungeni.utils import register
    @register.NAME...

$Id$
"""

__all__ = [
    "adapter",
    "utility",
    "handler",
    "subscription_adapter",
    "viewlet_manager",
    "viewlet", "PROTECT_VIEWLET_PUBLIC",
    "view", "PROTECT_VIEW_PUBLIC",
    "protect",
]

from zope import component
from zope.security import protectclass


def adapter(adapts=None, provides=None, name=""):
    """provideAdapter(factory, adapts=None, provides=None, name="")
    """
    def _adapter(factory):
        component.provideAdapter(factory, adapts, provides, name)
        return factory
    return _adapter


def utility(provides=None, name="", args=(), kwargs={}):
    """provideUtility(ob, provides=None, name="")
    
    An utility instance is instantiated on each call, and any desired utility 
    instantiation parameters may be specified via decorator parameters args and 
    kwargs.
    
    If for some case the behaviour here is not ideal e.g. if you already have 
    the instance on hand, and may wish to register the *same* instance multiple
    times, then the following non-decorator way (cannot decorate instance types) 
    to register the instance may be prefereble:
    
        utility_instance = ...
        zope.component.provideUtility(utility_instance, providesA, nameA)
        zope.component.provideUtility(utility_instance, providesB, nameB)
        ...
    
    """
    def _utility(factory):
        ob = factory(*args, **kwargs)
        component.provideUtility(ob, provides, name)
        return ob
    return _utility


def handler(adapts=None):
    """provideHandler(factory, adapts=None)
    """
    def _handler(factory):
        component.provideHandler(factory, adapts)
        return factory
    return _handler


def subscription_adapter(adapts=None, provides=None):
    """provideSubscriptionAdapter(factory, adapts=None, provides=None)
    """
    def _subscription_adapter(factory):
        component.provideSubscriptionAdapter(factory, adapts, provides)
        return factory
    return _subscription_adapter


# wrapper registrators


# viewlet

def viewlet_manager(for_=None, layer=None, view=None, provides=None, name=""):
    """Register a browser viewlet manager, using provideAdapter().
    """
    if provides is None:
        from zope.viewlet.interfaces import IViewletManager as provides
    def _viewlet_manager(factory):
        component.provideAdapter(factory, 
            adapts=(for_, layer, view),
            provides=provides,
            name=name)
        return factory
    return _viewlet_manager

VIEWLET_DEFAULT_ATTRS = dict(attributes=["render"])
_PROTECT_VIEWLET_DEFAULT = {"zope.View": VIEWLET_DEFAULT_ATTRS}

def viewlet(for_, layer=None, view=None, manager=None, provides=None, name="",
        protect=_PROTECT_VIEWLET_DEFAULT, like_class=None
    ):
    """Register a browser viewlet, using provideAdapter(), and protecting 
    access as per protect/like_class.
    
    protect - provides convenient default protect for a viewlet:
    - see docstring for _protect for details of allowed values
    - as default for viewlets, we protect the "render" attr with "zope.View"
    - if protect==None, then no security protection is executed
    - if protect!=None, then factory must be a type, class or module.
    """
    if provides is None:
        from zope.viewlet.interfaces import IViewlet as provides
    if like_class is not None:
        # in this case default for protect should be None
        if protect is _PROTECT_VIEWLET_DEFAULT:
            protect = None
    def _viewlet(factory):
        if protect is not None or like_class is not None:
            _protect(factory, protect, like_class)
        component.provideAdapter(factory, 
            adapts=(for_, layer, view, manager),
            provides=provides, 
            name=name)
        return factory
    return _viewlet

# convenience, pre-defined value for a typical public viewlet
PROTECT_VIEWLET_PUBLIC = {"zope.Public": VIEWLET_DEFAULT_ATTRS}


# view
# note: layer default is zope.publisher.interfaces.browser.IDefaultBrowserLayer

VIEW_DEFAULT_ATTRS = dict(attributes=["browserDefault", "__call__"])
_PROTECT_VIEW_DEFAULT = {"zope.View": VIEW_DEFAULT_ATTRS}

def view(for_, layer=None, provides=None, name="",
        protect=_PROTECT_VIEW_DEFAULT, like_class=None
    ):
    """Register a browser view, using provideAdapter(), and protecting 
    access as per protect/like_class.
    
    protect/like_class - provides convenient default protect for a view:
    - see docstring for _protect for details of allowed values
    - as default for views, we protect "__call__, "browser" attrs w. "zope.View"
    - if protect==None, then no security protection is executed
    - if protect!=None, then factory must be a type, class or module.
    
    Should be used to replace both browser:view and very similar browser:page.
    Differences between the two are: 
    - browser:page adds support for a template attribute
    - browser:page automagically "promotes" a zope.publisher.browser 
    BrowserView factory to a BrowserPage. For the usage here, a BrowserPage 
    factory needs to be supplied explicitly.
    """
    if provides is None:
        from zope.publisher.interfaces.browser import IBrowserPublisher as provides
    if like_class is not None:
        # in this case default for protect should be None
        if protect is _PROTECT_VIEW_DEFAULT:
            protect = None
    def _view(factory):
        if protect is not None or like_class is not None:
            _protect(factory, protect, like_class)
        component.provideAdapter(factory, 
            adapts=(for_, layer),
            provides=provides, 
            name=name)
        return factory
    return _view

# convenience, pre-defined value for a typical public view
PROTECT_VIEW_PUBLIC = {"zope.Public": VIEW_DEFAULT_ATTRS}



# protect

def protect(protect=None, like_class=None):
    """Decorator to register security protections on a class.
    
    Intended to be used separately from view/viewlet decorators, as those 
    already specify default security protections. To use in conjunction with 
    view/viewlet decorators, specify protect=None on the decorator call.
    
    See docstring for _protect for allowed values for protect, like_class.
    """
    def _p(cls):
        _protect(cls, protect, like_class)
        return cls
    return _p


# utils

def _protect(cls, protect=None, like_class=None):
    """Register security protections for cls, as per protect/like_class.
    
    Constraint: cls must be a type, class or module.
    
    Attempt to reset to a different permission on a name raises an error.
    
    The protect parameter is a dictionary that can can specify whatever 
    a sequence of class/require zcml directives may specify (except for 
    the non-compatible like_class, that if needed may be provided as a 
    spearate parameter):
    
        protect:{
            permission:str: {
                attributes:[str], 
                set_attributes:[str],   # tbd, zope.security.metaconfigure
                interface:Interface,
                set_schema:Interface    # tbd
            }
        }
        
        like_class: either(type, class, module)
    
    """
    assert protect is not None or like_class is not None, \
        "[%s] params protect [%s] or like_class [%s] may not be both None." % (
            cls, protect, like_class)
    assert protect is None or like_class is None, \
        "[%s] One of params protect [%s] or like_class [%s] must be None." % (
            cls, protect, like_class)
    
    if like_class is not None:
        protectclass.protectLikeUnto(cls, like_class)
        return
    
    for permission in protect:
        
        interface = protect[permission].get("interface")
        if interface:
            for attr, d in interface.namesAndDescriptions(1):
                protectclass.protectName(cls, attr, permission)
        
        attributes = protect[permission].get("attributes")
        if attributes:
            for attr in attributes:
                # retrieve cls checker on each attr (may not be defined on first)
                checker = protectclass.getCheckerForInstancesOf(cls)
                # rememeber the (applied) previous protection for this attr
                previous_permission = None
                if checker is not None:
                    previous_permission = checker.get_permissions.get(attr)
                # (re-)apply the protection for this attr
                protectclass.protectName(cls, attr, permission)
                # compare the new value (AFTER being applied, as that value
                # CHANGES by being applied!) with previous (if any)
                if previous_permission is not None:
                    current_permission = checker.get_permissions.get(attr)
                    assert previous_permission == current_permission, \
                        "Cannot change protection of class [%s] " \
                        "attribute [%s] from [%s] to [%s]" % (
                            cls, attr, previous_permission, current_permission)
        
        #if set_attributes:
        #if set_schema:


