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
        super(ModelDescriptor, self).__init__()
        log.info("Initializing ModelDescriptor: %s" % self)

