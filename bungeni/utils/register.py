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
    "viewlet",
    "view",
]

from zope import component

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

def viewlet(for_, layer=None, view=None, manager=None, provides=None, name="",
        protect={"zope.View": dict(attributes=["render"])}
    ):
    """Register a browser viewlet, using provideAdapter(), and protecting 
    access as specified by the protect dict.
    
    protect:
    - see docstring for protect_class_names for details of allowed values
    - as default for viewlets, we protect the "render" attr with "zope.View"
    - if protect==None, then no security protection is executed
    - if protect!=None, then factory must be a type, class or module.
    """
    if provides is None:
        from zope.viewlet.interfaces import IViewlet as provides
    def _viewlet(factory):
        if protect is not None:
            protect_class_names(factory, protect)
        component.provideAdapter(factory, 
            adapts=(for_, layer, view, manager),
            provides=provides, 
            name=name)
        return factory
    return _viewlet


# view
# note: layer default is zope.publisher.interfaces.browser.IDefaultBrowserLayer

def view(for_, layer=None, provides=None, name=""):
    """Register a browser view, using provideAdapter().
    
    Should be used to replace both browser:view and very similar browser:page.
    Differences between the two are: 
    - browser:page adds support for a template attribute
    - browser:page automagically "promotes" a zope.publisher.browser 
    BrowserView factory to a BrowserPage. For the usage here, a BrowserPage 
    factory needs to be supplied explicitly.
    """
    if provides is None:
        from zope.publisher.interfaces.browser import IBrowserPublisher as provides
    def _view(factory):
        component.provideAdapter(factory, 
            adapts=(for_, layer),
            provides=provides, 
            name=name)
        return factory
    return _view


# utils

from zope.security import protectclass

def protect_class_names(cls, protect):
    """Set the permission on the particular names of attributes of the cls.
    Attempt to reset to a different permission on a name raises an error.
    
    Constraint: cls must be a type, class or module.
    
    The protect parameter is a dictionary that can can specify whatever 
    a sequence of class/require zcml directives may specify (except for 
    the non-compatible like_class, that if needed may be provided as a 
    spearate parameter):
    
        protect:{
            permission:str: {
                attributes:[str], # only this is supported currently
                set_attributes:[str], 
                interface:Interface,
                set_schema:Interface
            }
        }
        
        like_class:either(type, class, module)
    
    """
    for permission in protect:
        attributes = protect[permission].get("attributes")
        if attributes:
            for attr in attributes:
                # retrieve cls checker each name (may not be defined on first)
                checker = protectclass.getCheckerForInstancesOf(cls)
                if checker is not None:
                    previous_permission = checker.get_permissions.get(attr)
                    if previous_permission is not None:
                        assert previous_permission == permission, \
                            "Cannot change protection of class [%s] " \
                            "attribute [%s] from [%s] to [%s]" % (
                                cls, attr, previous_permission, permission)
                        continue
                protectclass.protectName(cls, attr, permission)


