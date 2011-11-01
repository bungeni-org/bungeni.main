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

__all__ = ["handler"]


from zope import component


def adapter(adapts=None, provides=None, name=""):
    """provideAdapter(factory, adapts=None, provides=None, name="")
    """
    def _adapter(factory):
        component.provideAdapter(factory, adapts, provides, name)
        return factory
    return _adapter


def utility(provides=None, name=""):
    """provideUtility(ob, provides=None, name="")
    """
    def _utility(ob):
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

def viewlet(for_, layer=None, view=None, manager=None, provides=None, name=""):
    """Register a browser viewlet, using provideAdapter().
    """
    if provides is None:
        from zope.viewlet.interfaces import IViewlet as provides
    def _viewlet(factory):
        component.provideAdapter(factory, 
            adapts=(for_, layer, view, manager),
            provides=provides, 
            name=name)
        return factory
    return _viewlet



