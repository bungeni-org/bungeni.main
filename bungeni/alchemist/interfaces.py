# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist interfaces - [
    ore.alchemist.interfaces
]

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


# used directly in bungeni
__all__ = [
    "IAlchemistContent",    # alias -> ore.alchemist.interfaces
    "IAlchemistContainer",  # alias -> ore.alchemist.interfaces
    "IDatabaseEngine",      # alias -> ore.alchemist.interfaces
    "IIModelInterface",     # alias -> ore.alchemist.interfaces
    "IModelDescriptor",     # alias -> ore.alchemist.interfaces
    
    "IManagedContainer",    # redefn -> alchemist.traversal.interfaces
    "IContentViewManager",  # redefn -> alchemist.ui.interfaces
]


# ore.alchemist.interfaces

from ore.alchemist.interfaces import (
    IAlchemistContent, # provides IIModelInterface
    IIModelInterface, # marker interface provided by all "I%TableSchema" interfaces
    IAlchemistContainer,
    
    IDatabaseEngine,

    IModelDescriptor
)

#

from zope import interface
from zope.viewlet.interfaces import IViewletManager

# alchemist.security.interfaces
class IAlchemistUser(interface.Interface):
    """The domain class for authentication."""
    def checkPassword(password):
        """Return true if the password matches."""

# alchemist.traversal.interfaces
class IManagedContainer(interface.Interface):
    """ """

# alchemist.ui.interfaces
class IContentViewManager(IViewletManager):
    """Viewlet manager interface."""    


