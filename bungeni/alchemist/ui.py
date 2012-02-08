# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist ui - [
    alchemist.ui
    alchemist.ui.core
    alchemist.ui.viewlet
    alchemist.ui.widgets
]

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


# used directly in bungeni
__all__ = [
    "DynamicFields",        # alias -> alchemist.ui.core
    "getSelected",          # alias -> alchemist.ui.core
    "handle_edit_action",   # alias -> alchemist.ui.core
    "null_validator",       # alias -> alchemist.ui.core
    "setUpFields",          # alias -> alchemist.ui.core
    "unique_columns",       # alias -> alchemist.ui.core
]


from alchemist.ui.core import DynamicFields
from alchemist.ui.core import getSelected
from alchemist.ui.core import handle_edit_action
from alchemist.ui.core import null_validator
from alchemist.ui.core import setUpFields
from alchemist.ui.core import unique_columns

#from alchemist.ui.viewlet import EditFormViewlet


