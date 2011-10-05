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


def handler(adapts=None):
    """provideHandler(factory, adapts=None)
    """
    def _d_handler(factory):
        component.provideHandler(factory, adapts)
        return factory
    return _d_handler


