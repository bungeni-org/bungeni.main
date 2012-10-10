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
    "IModelDescriptorField", # redefn -> ore.alchemist.interfaces
    
    "IManagedContainer",    # redefn -> alchemist.traversal.interfaces
    "IContentViewManager",  # redefn -> alchemist.ui.interfaces
]


# ore.alchemist.interfaces

from ore.alchemist.interfaces import (
    IAlchemistContent, # provides IIModelInterface, inherits ITableSchema->Interface
    IIModelInterface, # marker interface provided by all "I%TableSchema" interfaces
    IAlchemistContainer,
    
    IDatabaseEngine,

    IModelDescriptor
)

#

from zope import interface, schema
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


class IModelDescriptorField(interface.Interface):
    # name
    # label
    # description
    modes = schema.ASCIILine(
        title=u"View Usage Modes for Field",
        description=u"Whitespace separated string of different modes."
    )
    # property
    listing_column = schema.Object(interface.Interface,
        title=u"A Custom Column Widget for Listing Views",
        required=False
    )
    listing_column_filter = schema.Object(interface.Interface,
        title=u"A function that filters a listing column on a value",
        required=False
    )
    # !+LISTING_WIDGET(mr, nov-2010) why inconsistently named "listing_column"?
    view_widget = schema.Object(interface.Interface,
        title=u"A Custom Widget Factory for Read Views",
        required=False
    )
    edit_widget = schema.Object(interface.Interface,
        title=u"A Custom Widget Factory for Write Views",
        required=False,
    )
    add_widget = schema.Object(interface.Interface,
        title=u"A Custom Widget Factory for Add Views",
        required=False
    )
    search_widget = schema.Object(interface.Interface,
        title=u"A Custom Search Widget Factory",
        required=False
    )
    ''' !+FIELD_PERMISSIONS(mr, nov-2010) these params are deprecated -- when 
    applied to any field (that corresponds to an attribute of the domain's 
    class), the domain.zcml setting for that same class attribute will anyway 
    take precedence.

    view_permission = schema.ASCIILine(
        title=u"Read Permission",
        description=u"If the user does not have this permission this field "
            "will not appear in read views",
        required=False
    )
    edit_permission = schema.ASCIILine(
        title=u"Read Permission",
        description=u"If the user does not have this permission this field "
            "will not appear in write views",
        required=False
    )
    '''

