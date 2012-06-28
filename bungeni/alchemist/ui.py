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
    "getSelected",          # redefn -> alchemist.ui.core
    "null_validator",       # alias -> alchemist.ui.core
    "setUpFields",          # alias -> alchemist.ui.core
    "unique_columns",       # alias -> alchemist.ui.core
    "setUpColumns",         # redefn -> alchemist.ui.core
]

from alchemist.ui.core import DynamicFields

from alchemist.ui.core import null_validator
from alchemist.ui.core import setUpFields
from alchemist.ui.core import unique_columns

#from alchemist.ui.viewlet import EditFormViewlet


# replaces alchemist.ui.core.getSelected
# !+zc.table(miano, march 2012) This version does not expect base64 encoded
# values. See bungeni.ui.versions.CustomSelectionColumn
def getSelected(selection_column, request):
    """
    the formlib selection column implementation wants us to pass a value
    set.. lame. we manually poke at it to get ids and dereference.
    
    these pair of functions assume single column integer primary keys
    """
    keys = [ k[len(selection_column.prefix)+1:-1] 
        for k in request.form.keys()
        if k.startswith(selection_column.prefix) and 
            request.form.get(k, "") == "on" ]
    return map(int, keys)


from zope import schema
from zc.table import column
from bungeni.alchemist import model
import alchemist.ui
def setUpColumns(domain_model):
    """Use model descriptor on domain model extract columns for table listings
    """
    columns = []
    domain_interface = model.queryModelInterface(domain_model)
    
    if not domain_interface:
        raise SyntaxError("Model must have domain interface %r" % (domain_model))
    
    domain_annotation = model.queryModelDescriptor(domain_interface)
    
    field_column_names = \
        domain_annotation and domain_annotation.listing_columns \
        or schema.getFieldNamesInOrder(domain_interface)
    
    # quick hack for now, dates are last in listings
    remainder = []
    
    for field_name in field_column_names:
        if not field_name in domain_interface:
            # we can specify additional columns for tables that are not present in the
            # the interface, iff they are fully spec'd as columns in the descriptor/annotation
            if (domain_annotation and 
                    field_name in domain_annotation and 
                    domain_annotation[field_name].listing_column
                ):
                pass
            else:
                #print "bad field, container", field_name, domain_interface.__name__
                continue
        
        info = domain_annotation and domain_annotation.get(field_name) or None
        
        if info is not None and info.listing_column:
            columns.append(info.listing_column)
            continue
        
        field = domain_interface[field_name]
        
        if isinstance(field, schema.Datetime):
            remainder.append(
                column.GetterColumn(title=field.title or field.__name__,
                    getter=alchemist.ui.core.DateGetter(field.query)))
            continue
        columns.append(
            column.GetterColumn(title=(field.title or field.__name__),
                getter=alchemist.ui.core.Getter(field.query)))
    columns.extend(remainder)
    return columns


