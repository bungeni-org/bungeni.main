# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist UI [alchemist.ui]

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


# used directly in bungeni
__all__ = [
    "DynamicFields",        # redefn -> alchemist.ui.core
    "getSelected",          # redefn -> alchemist.ui.core
    "null_validator",       # redefn -> alchemist.ui.core
    "setUpFields",          # redefn -> alchemist.ui.core
    "unique_columns",       # redefn -> alchemist.ui.core
    "setUpColumns",         # redefn -> alchemist.ui.core
    "createInstance",       # redefn -> alchemist.ui.generic
]

#

from zope.i18nmessageid import MessageFactory
_ = MessageFactory("bungeni")

import copy, math, itertools
from zope import interface
from zope.security.proxy import removeSecurityProxy
from zope.formlib import form, namedtemplate
from zope.event import notify
from zope.lifecycleevent import Attributes, \
    ObjectCreatedEvent, ObjectModifiedEvent
from zope.traversing.browser import absoluteURL
from zope.publisher.browser import BrowserView
from sqlalchemy import orm
from bungeni.alchemist.interfaces import (
    IAlchemistContent,
)
import bungeni.alchemist

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
    form_fields = form.Fields(*fields)
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
def setUpColumns(domain_model):
    """Use model descriptor on domain model extract columns for table listings
    """
    columns = []
    domain_interface = bungeni.alchemist.model.queryModelInterface(domain_model)
    
    if not domain_interface:
        raise SyntaxError("Model must have domain interface %r" % (domain_model))
    
    descriptor_model = bungeni.alchemist.utils.get_descriptor(domain_interface)
    
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
                    getter=DateGetter(field.query)))
            continue
        columns.append(
            column.GetterColumn(title=(field.title or field.__name__),
                getter=Getter(field.query)))
    columns.extend(remainder)
    return columns

# alchemist.ui.core

class Getter(object):
    def __init__(self, getter):
        self.getter = getter
    
    def __call__(self, item, formatter):
        return self.getter(item)

class DateGetter(object):
    def __init__(self, getter, format="%d %B %Y %r"):
        self.getter = getter
        self.format = format
    def __call__(self, item, formatter):
        value = self.getter(item)
        if not value:
            return "N/A"
        return value.strftime(self.format)

def null_validator(form, action, data):
    return ()

def unique_columns(mapper):
    def columns(mapper):
        for p in mapper.iterate_properties:
            if isinstance(p, orm.properties.ColumnProperty):
                yield p
    for cp in columns(mapper):
        for c in cp.columns:
            try:
                if c.unique:
                    yield cp.key, c
            except:
                continue

class DynamicFields(object):
    mode = None # required string attribute
    template = None # namedtemplate.NamedTemplate("alchemist.form")
    form_fields = form.Fields()
    
    def getDomainModel(self):
        return getattr(self.context, "domain_model", self.context.__class__)
    
    def update(self):
        """Override update method to setup fields dynamically before widgets
        are setup and actions called.
        """
        domain_model = self.getDomainModel()
        self.form_fields = setUpFields(domain_model, self.mode)
        super(DynamicFields, self).update()
        def setWidgetErrors(widgets, errors):
            for widget in widgets:
                name = widget.context.getName()
                for error in errors:
                    if isinstance(error, interface.Invalid) and name in error.args[1:]:
                        if widget._error is None:
                            widget._error = error
        setWidgetErrors(self.widgets, self.errors)
    
    @property
    def form_name(self):
        # play nice w/ containers or content views, or content
        domain_model = getattr(self.context, "domain_model", None)
        if domain_model is None:
            domain_model = getattr(self, "domain_model", None)
            if (domain_model is None and 
                    IAlchemistContent.providedBy(self.context)
                ):
                domain_model = self.context.__class__
        if domain_model is None:
            return self.mode.title()
        return "%s %s" % (self.mode.title(), domain_model.__name__)
    
    def splitwidgets(self):
        """
        return two lists of form fields split into two, int overflow into
        first column.
        """
        # give first and second set of field names
        field_count = len(self.form_fields)
        first_half_count = math.ceil(field_count / 2.0)
        first_half_widgets, second_half_widgets = [], []
        for idx, field in itertools.izip(itertools.count(), self.form_fields):
            if idx < first_half_count:
                first_half_widgets.append(self.widgets[ field.__name__ ])
            else:
                second_half_widgets.append(self.widgets[ field.__name__ ])
        return first_half_widgets, second_half_widgets

    def validateUnique(self, action, data):
        """
        verification method for adding or editing against anything existing
        that conflicts with an existing row, as regards unique column constraints.
        
        this is somewhat costly as we basically reinvoke parsing form data twice,
        we need to extend zope.formlib to ignore existing values in the data dictionary
        to avoid this.
        
        its also costly because we're doing a query per unique column data we find, in
        order to unambigously identify the field thats problematic. but presumably those
        are very fast due to the unique constraint.
        
        TODO : assumes column == attribute         
        """
        errors = form.getWidgetsData(self.widgets, self.prefix, data) + \
            form.checkInvariants(self.form_fields, data) 
        if errors:
            return errors
        
        domain_model = removeSecurityProxy(self.getDomainModel())
        
        # find unique columns in data model.. TODO do this statically
        mapper = orm.class_mapper(domain_model)
        ucols = list(unique_columns(mapper))
        
        errors = []
        # query out any existing values with the same unique values,
        
        s = bungeni.alchemist.Session()        
        # find data matching unique columns
        for key, col in ucols:
            if key in data:
                # on edit ignore new value if its the same as the previous value
                if isinstance(self.context, domain_model) \
                   and data[key] == getattr(self.context, key, None):
                   continue
                value = s.query(domain_model).filter(col == data[key]).count()
                if not value:
                    continue
                widget = self.widgets[ key ]
                error = form.WidgetInputError(widget.name, widget.label, 
                    u"Duplicate Value for Unique Field")
                widget._error = error
                errors.append(error)
        if errors:
            return tuple(errors)

# alchemist.ui.content

class AddFormBase(object):
    
    _next_url = None
    adapters = None

    def createAndAdd(self, data):
        domain_model = removeSecurityProxy(self.context.domain_model)
        # create the object, inspect data for constructor args      
        try:  
            ob = createInstance(domain_model, data)
        except TypeError:
            ob = domain_model()
        
        # apply any context values
        self.finishConstruction(ob)
        
        # apply extra form values
        form.applyChanges(ob, self.form_fields, data, self.adapters)
        
        # save the object, id is generated by db on flush
        self.context[""] = ob
        
        # flush so we have database id
        bungeni.alchemist.Session().flush()
        
        # fire an object created event
        notify(ObjectCreatedEvent(ob))
        
        # signal to add form machinery to go to next url
        self._finished_add = True
        
        mapper = orm.object_mapper(ob)
        
        # TODO single primary key (need changes to base container)
        oid = mapper.primary_key_from_instance(ob)
        
        # retrieve the object with location and security information
        return self.context[oid]
    
    def finishConstruction(self, ob):
        """No op, subclass to provide additional initialization behavior"""
        return
        
    def nextURL(self):
        if not self._next_url:
            return absoluteURL(self.context, self.request)
        return self._next_url
        
    def update(self):
        self.status = self.request.get("portal_status_message", "")
        super(AddFormBase, self).update()
    
    def validateAdd(self, action, data):
        errors = self.validateUnique(action, data)
        return errors
        
    @form.action(_(u"Cancel"), validator=null_validator)
    def handle_cancel(self, action, data):
        url = self.nextURL()
        return self.request.response.redirect(url)
    
    @form.action(_(u"Save and continue editing"), 
        condition=form.haveInputWidgets, validator="validateAdd")
    def handle_add_edit(self, action, data):
        ob = self.createAndAdd(data)
        name = self.context.domain_model.__name__
        self._next_url = "%s/@@edit?portal_status_message=%s Added" % (
            absoluteURL(ob, self.request), name)
        
    @form.action(_(u"Save and add another"), condition=form.haveInputWidgets)
    def handle_add_and_another(self, action, data):
        self.createAndAdd(data)
        name = self.context.domain_model.__name__
        self._next_url = "%s/@@add?portal_status_message=%s Added" % (
            absoluteURL(self.context, self.request), name)
        
    def invariantErrors(self):        
        errors = []
        for error in self.errors:
            if isinstance(error, interface.Invalid):
                errors.append(error)
        return errors

class Add(AddFormBase, form.AddForm):
    """Static add form for db content.
    """

class EditForm(form.EditForm):
    
    adapters = None
    
    def setUpWidgets(self, ignore_request=False):
        self.adapters = self.adapters or {}
        self.widgets = form.setUpEditWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            adapters=self.adapters, ignore_request=ignore_request)
    
    @form.action(_(u"Save"), condition=form.haveInputWidgets)
    def handle_edit_action(self, action, data):
        return _handle_edit_action(self, action, data)
    
    @form.action(_(u"Cancel"), condition=form.haveInputWidgets, validator=null_validator)
    def handle_cancel_action(self, action, data):
        return _handle_edit_action(self, action, data)            
        
    def invariantErrors(self):        
        errors = []
        for error in self.errors:
            if isinstance(error, interface.Invalid):
                errors.append(error)
        return errors
        
# alchemist.ui.core.handle_edit_action
# formlib 3.5.0 backports.. these variants will send field descriptions on edit
def _handle_edit_action(self, action, data):
    
    def applyData(context, form_fields, data, adapters=None):
        if adapters is None:
            adapters = {}
        descriptions = {}
        for form_field in form_fields:
            field = form_field.field
            # Adapt context, if necessary
            interface = form_field.interface
            adapter = adapters.get(interface)
            if adapter is None:
                if interface is None:
                    adapter = context
                else:
                    adapter = interface(context)
                adapters[interface] = adapter
            name = form_field.__name__
            newvalue = data.get(name, form_field) # using form_field as marker
            if (newvalue is not form_field) and (field.get(adapter) != newvalue):
                descriptions.setdefault(interface, []).append(field.__name__)
                field.set(adapter, newvalue)
        return descriptions            
    
    descriptions = applyData(self.context, self.form_fields, data, self.adapters)
    if descriptions:
        descriptions = [ Attributes(iface, *tuple(keys))
            for iface, keys in descriptions.items() ]
        notify(ObjectModifiedEvent(self.context, *descriptions))
        formatter = self.request.locale.dates.getFormatter("dateTime", "medium")
        import pytz, datetime
        try:
            time_zone = interface.common.idatetime.ITZInfo(self.request)
        except TypeError:
            time_zone = pytz.UTC
        status = _(
            "Updated on ${date_time}",
            mapping={"date_time": formatter.format(datetime.datetime.now(time_zone))})
        self.status = status
    else:
        self.status = _("No changes")


class Display(BrowserView):
    """Content Display
    """
    template = None # bungeni/ui/forms/templates/content-view.pt
    form_name = _("View")    
    def __call__( self ):
        return self.template()
ContentDisplayForm = Display


# alchemist.ui.generic

# based on zope.publisher.mapply adapted for class instantiation and 
# sa initialization hooks
_marker = object()
wrapper_type = type(object.__init__)
def createInstance(cls, data):
    """Generically create an instance of a sqlalchemy object with a dictionary 
    of data, and then return the instance and the remainder of the data. 
    Uses default args if found and no value for arg present in data.
    """
    func = cls.__init__.im_func
    func = func.func_dict.get("_oldinit", func)
    
    if isinstance(func, wrapper_type):
        defaults = ()
        names = ()
    else:
        defaults = func.func_defaults
        names = func.func_code.co_varnames[1:]
    args = []
    used = []

    nrequired = len(names)
    if defaults:
        nrequired -= len(defaults)
    
    for i in range(len(names)):
        n = names[i]
        v = data.get(n, _marker)
        
        if v is _marker:
            if i < nrequired:
                raise TypeError("missing argument %s" % n)
            else:
                v = defaults[ i-nrequired ]
        else:
            used.append(n)
        args.append(v)
        
    for n in used:
        del data[n]

    ob = cls(*args)

    return ob
    
