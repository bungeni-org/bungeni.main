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
    "null_validator",       # alias -> alchemist.ui.core
    "setUpFields",          # alias -> alchemist.ui.core
    "unique_columns",       # alias -> alchemist.ui.core
]

# replaces alchemist.ui.core.getSelected
# !+zc.table(miano, march 2012) This version does not expect base64 encoded
# values. See bungeni.ui.versions.CustomSelectionColumn
def getSelected( selection_column, request ):
    """
    the formlib selection column implementation wants us to pass a value
    set.. lame. we manually poke at it to get ids and dereference.

    these pair of functions assume single column integer primary keys
    """
    keys = [ k[len(selection_column.prefix)+1:-1] \
             for k in request.form.keys() \
             if k.startswith( selection_column.prefix )  \
             and request.form.get(k,'') == 'on']
    return map( int, keys ) 
    
from alchemist.ui.core import DynamicFields

from alchemist.ui.core import null_validator
from alchemist.ui.core import setUpFields
from alchemist.ui.core import unique_columns

#from alchemist.ui.viewlet import EditFormViewlet


