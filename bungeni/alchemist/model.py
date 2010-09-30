# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist model - [
    ore.alchemist.model
]

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


# ore.alchemist.model

from ore.alchemist.model import queryModelDescriptor
from ore.alchemist.model import queryModelInterface

import ore.alchemist.model

class ModelDescriptor(ore.alchemist.model.ModelDescriptor):
    """Model type descriptor
    
    Usage: always retrieve the *same* descriptor *instance* for a 
    model class via: queryModelDescriptor(model_interface).
    """
    def __init__(self):
        self._fields_by_name = {}
        self.fields = []
        for d in self.__class__.fields:
            self.add_field_from_dict(d)
        log.info("Initializing ModelDescriptor: %s" % self)
    
    def add_field_from_dict(self, info_dict):
        """Add a ore.alchemist.model.Field instance from an info dict, 
        doing some sanity checking.
        """
        name = info_dict["name"]
        assert name not in self._fields_by_name, \
            "[%s] Cannot have two fields with same name [%s]" % (
                self.__class__.__name__, name)
        f = ore.alchemist.model.Field.fromDict(info_dict)
        self._fields_by_name[name] = f
        self.fields.append(f)
    
    # we override the following methods as, thanks to self._fields_by_name, 
    # they may be redefined in a much simpler way (as well as being faster).
    
    def get(self, name, default=None):
        return self._fields_by_name.get(name, default)
    
    def __getitem__(self, name):
        return self._fields_by_name[name]
    
    def __contains__(self, name):
        return name in self._fields_by_name

