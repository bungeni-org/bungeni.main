# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist interfaces - [
    ore.alchemist.interfaces
    alchemist.ui.interfaces
]

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


# used directly in bungeni
__all__ = [
    "IAlchemistContent",    # alias -> ore.alchemist.interfaces
    "IAlchemistContainer",  # alias -> ore.alchemist.interfaces
    "IDatabaseEngine",      # alias -> ore.alchemist.interfaces
    "IRelationChange",      # alias -> ore.alchemist.interfaces
    "IIModelInterface",     # alias -> ore.alchemist.interfaces
    "IModelAnnotation",     # alias -> ore.alchemist.interfaces
    "IModelDescriptor",     # alias -> ore.alchemist.interfaces
    
    "IManagedContainer",    # alias -> alchemist.traversal.interfaces
    "IContentViewManager",    # alias -> alchemist.ui.interfaces
]


# ore.alchemist.interfaces

from ore.alchemist.interfaces import (
    IAlchemistContent,
    IAlchemistContainer,
    
    IDatabaseEngine,
    IRelationChange,

    IIModelInterface,
    IModelAnnotation,
    IModelDescriptor
)

from alchemist.traversal.interfaces import IManagedContainer

from alchemist.ui.interfaces import IContentViewManager


