# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Misc utilities for the UI

recommended usage:
from bungeni.ui.utils import misc

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.utils.misc")

from bungeni.ui.i18n import _
from types import StringTypes, ListType

from bungeni.core.workflow import interfaces

import os

# pick data

def get_parent_with_interface(context, iface):
    """Get first parent to implement the interface."""
    parent = context.__parent__
    if parent:
        if iface.providedBy(parent):
            return parent
        else:
            return get_parent_with_interface(parent, iface)
    return None


# file system 

def pathjoin(basefilepath, filepath):
    return os.path.join(os.path.dirname(basefilepath), filepath)


# workflow 

def get_wf_state(context, wf_status=None):
    """Get the human readable title for the context's workflow state
    """
    # !+RENAME(mr, mar-2011) to get_workflow_state_title
    workflow = interfaces.IWorkflow(context)
    if wf_status is None:
        wf_status = interfaces.IStateController(context).get_status()
    return workflow.get_state(wf_status).title


# request 

def is_ajax_request(request):
    return request.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


# list

def makeList(itemIds):
    if type(itemIds) == ListType:
        return itemIds
    elif type(itemIds) in StringTypes:
        # only one item in this list
        return [itemIds,]
    else:
         raise TypeError(_("Form values must be of type string or list"))

def get_keyed_item(seq, value, key="name"):
    """Get the item in the sequence that has a {key} entry set to {value}.
    """
    for s in seq:
        if s[key] == value:
            return s
        

# object

class bunch(dict):
    """
    A dictionary-bunch of values, with convenient dotted access.
    Limitation: keys must be valid object attribute names.
    Inspiration: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52308
    """
    def __init__(self, **kwds):
        dict.__init__(self, kwds)
        self.__dict__ = self

    def __getstate__(self):
        return self

    def __setstate__(self, state):
        self.update(state)
        self.__dict__ = self

    def update_from_object(self, obj, no_underscored=True):
        """ (obj:object) -> None
        Sets each key in dir(obj) as key=getattr(object, key) in self.
        If no_underscored, then exclude "private" (leading "_") and 
        "protected" (leading "__") attributes.
        """
        for name in dir(obj):
            if not (no_underscored and name.startswith("_")):
                self[name] = getattr(obj, name)


