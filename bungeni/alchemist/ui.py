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
    "DynamicFields",        # redefn -> alchemist.ui.core
    "getSelected",          # redefn -> alchemist.ui.core
    "null_validator",       # alias -> alchemist.ui.core
    "setUpFields",          # redefn -> alchemist.ui.core
    "unique_columns",       # alias -> alchemist.ui.core
    "setUpColumns",         # redefn -> alchemist.ui.core
    "createInstance",       # alias -> alchemist.ui.generic
]


from alchemist.ui.core import null_validator
#from alchemist.ui.core import setUpFields
from alchemist.ui.core import unique_columns
from alchemist.ui.generic import createInstance

#from alchemist.ui.viewlet import EditFormViewlet

#

import copy
from zope.security.proxy import removeSecurityProxy
from zope.formlib import form
import bungeni.alchemist
from bungeni.utils.capi import capi
def setUpFields(domain_model, mode):
    """
    setup form fields for add/edit/view/search modes, with custom widgets
    enabled from model descriptor. this expects the domain model and mode
    passed in and will return a form.Fields instance
    """
    domain_model = removeSecurityProxy(domain_model)
    #import time
    #t = time.time()
    domain_interface = bungeni.alchemist.model.queryModelInterface(domain_model)
    descriptor_model = bungeni.alchemist.utils.get_descriptor(domain_interface)
    
    search_mode = mode == "search"
    
    if not descriptor_model:
        if search_mode:
            form_fields = form.Fields(*setUpSearchFields(domain_interface))
        else:
            form_fields = form.Fields(domain_interface)
        return form_fields
    
    fields = []
    columns = getattr(descriptor_model, "%s_columns" % mode)
    
    for field_info in columns:
        if not field_info.name in domain_interface:
            #print "bad field", field_info.name, domain_interface.__name__
            continue
        custom_widget = getattr(field_info, "%s_widget" % mode)
        if search_mode:
            fields.append(form.Field(
                    setUpSearchField(domain_interface[field_info.name]),
                    custom_widget=custom_widget))
        else:
            fields.append(form.Field(
                    domain_interface[field_info.name],
                    custom_widget=custom_widget))
    form_fields = form.Fields( *fields )
    #print "field setup cost", time.time()-t    
    return form_fields

def setUpSearchFields(iface):
    fields = []
    for name, field in schema.getFieldsInOrder(iface):
        fields.append(setUpSearchField(field))
    return fields

def setUpSearchField(field):
    "Search fields shouldn't be required"    
    if field.required:
        field = copy.deepcopy(field)
        field.required = False
    return field

import alchemist.ui.core
class DynamicFields(alchemist.ui.core.DynamicFields):

    def update(self):
        """Override update method to setup fields dynamically before widgets
        are setup and actions called.
        """
        domain_model = self.getDomainModel()
        self.form_fields = setUpFields(domain_model, self.mode)
        super(alchemist.ui.core.DynamicFields, self).update()
        alchemist.ui.core.setWidgetErrors(self.widgets, self.errors)


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
from bungeni.alchemist import model, utils
import alchemist.ui
def setUpColumns(domain_model):
    """Use model descriptor on domain model extract columns for table listings
    """
    columns = []
    domain_interface = model.queryModelInterface(domain_model)
    
    if not domain_interface:
        raise SyntaxError("Model must have domain interface %r" % (domain_model))
    
    descriptor_model = utils.get_descriptor(domain_interface)
    
    field_column_names = \
        descriptor_model and descriptor_model.listing_columns \
        or schema.getFieldNamesInOrder(domain_interface)
    
    # quick hack for now, dates are last in listings
    remainder = []
    
    for field_name in field_column_names:
        if not field_name in domain_interface:
            # we can specify additional columns for tables that are not present in the
            # the interface, iff they are fully spec'd as columns in the descriptor/annotation
            if (descriptor_model and 
                    field_name in descriptor_model and 
                    descriptor_model[field_name].listing_column
                ):
                pass
            else:
                #print "bad field, container", field_name, domain_interface.__name__
                continue
        
        info = descriptor_model and descriptor_model.get(field_name) or None
        
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


