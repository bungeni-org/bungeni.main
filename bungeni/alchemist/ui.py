# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist UI

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

import copy, math, itertools
import sys
from zope import interface
from zope.security.proxy import removeSecurityProxy
from zope import formlib
from zope.schema.interfaces import RequiredMissing
from zope.viewlet import manager
from zope.event import notify
from zope.lifecycleevent import Attributes, \
    ObjectCreatedEvent, ObjectModifiedEvent
from zope.traversing.browser import absoluteURL
import sqlalchemy as sa
from bungeni.alchemist.interfaces import (
    IAlchemistContainer,
    IAlchemistContent,
)
from bungeni.alchemist import Session, utils
from bungeni.ui.utils import date, debug
from bungeni.utils import misc
from bungeni.capi import capi
from bungeni import _

TRUE_VALS = "true", "1"

class NoPrefix(unicode):
    """The ``formlib`` library insists on concatenating the form
    prefix with field names; we override the ``__add__`` method to
    prevent this.
    """

    def __add__(self, name):
        return name
NO_PREFIX = NoPrefix()

class DefaultAction(formlib.form.Action):
    def __init__(self, action):
        self.__dict__.update(action.__dict__)
    def submitted(self):
        return True

def set_widget_errors(widgets, errors):
    for widget in widgets:
        name = widget.context.getName()
        for error in errors:
            if isinstance(error, interface.Invalid) and name in error.args[1:]:
                if widget._error is None:
                    widget._error = error

def setUpFields(domain_model, mode):
    """
    setup form fields for add/edit/view/search modes, with custom widgets
    enabled from model descriptor. this expects the domain model and mode
    passed in and will return a formlib.form.Fields instance
    """
    domain_model = removeSecurityProxy(domain_model)
    #import time
    #t = time.time()
    table_schema = utils.get_derived_table_schema(domain_model)
    descriptor_model = utils.get_descriptor(table_schema)
    
    search_mode = mode == "search"
    
    if not descriptor_model:
        if search_mode:
            form_fields = formlib.form.Fields(*setUpSearchFields(table_schema))
        else:
            form_fields = formlib.form.Fields(table_schema)
        return form_fields
    
    fields = []
    columns = getattr(descriptor_model, "%s_columns" % mode)
    
    for field_info in columns:
        if not field_info.name in table_schema:
            #print "bad field", field_info.name, table_schema.__name__
            continue
        custom_widget = getattr(field_info, "%s_widget" % mode)
        if search_mode:
            fields.append(formlib.form.Field(
                    setUpSearchField(table_schema[field_info.name]),
                    custom_widget=custom_widget))
        else:
            fields.append(formlib.form.Field(
                    table_schema[field_info.name],
                    custom_widget=custom_widget))
    form_fields = formlib.form.Fields(*fields)
    #print "field setup cost", time.time()-t    
    return form_fields

def setUpSearchFields(iface):
    fields = []
    for name, field in schema.getFieldsInOrder(iface):
        fields.append(setUpSearchField(field))
    return fields

def setUpSearchField(field):
    """Search fields shouldn't be required.
    """
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
    table_schema = utils.get_derived_table_schema(domain_model)
    if not table_schema:
        raise SyntaxError("Model must have domain interface %r" % (domain_model))
    descriptor_model = utils.get_descriptor(table_schema)
    
    field_column_names = \
        descriptor_model and descriptor_model.listing_columns \
        or schema.getFieldNamesInOrder(table_schema)

    # quick hack for now, dates are last in listings
    remainder = []
    
    for field_name in field_column_names:
        if not field_name in table_schema:
            # we can specify additional columns for tables that are not present in the
            # the interface, iff they are fully spec'd as columns in the descriptor/annotation
            if (descriptor_model and 
                    field_name in descriptor_model.fields_by_name and 
                    descriptor_model.get(field_name).listing_column
                ):
                pass
            else:
                print "bad field, container", field_name, table_schema.__name__
                continue
        
        info = descriptor_model and descriptor_model.get(field_name) or None
        
        if info is not None and info.listing_column:
            columns.append(info.listing_column)
            continue
        
        field = table_schema[field_name]
        
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
            if isinstance(p, sa.orm.properties.ColumnProperty):
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
    template = None # formlib.namedtemplate.NamedTemplate("alchemist.form")
    form_fields = formlib.form.Fields()
    
    def getDomainModel(self):
        return getattr(self.context, "domain_model", self.context.__class__)
    
    def update(self):
        """Override update method to setup fields dynamically before widgets
        are setup and actions called.
        """
        domain_model = self.getDomainModel()
        self.form_fields = setUpFields(domain_model, self.mode)
        super_update = super(DynamicFields, self).update #!+crazy method resolution!
        super_update()
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

    def validate_unique(self, action, data):
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
        
        !+BASEFORM_VALIDATE_UNIQUE merge with almost identical BaseForm.validate_unique
        """
        errors = formlib.form.getWidgetsData(self.widgets, self.prefix, data) + \
            formlib.form.checkInvariants(self.form_fields, data) 
        if errors:
            return errors
        
        domain_model = removeSecurityProxy(self.getDomainModel())
        
        # find unique columns in data model.. TODO do this statically
        mapper = sa.orm.class_mapper(domain_model)
        ucols = list(unique_columns(mapper))
        
        errors = []
        # query out any existing values with the same unique values,
        s = Session()        
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
                error = formlib.form.WidgetInputError(widget.name, widget.label, 
                    u"Duplicate Value for Unique Field")
                widget._error = error
                errors.append(error)
        if errors:
            return tuple(errors)


# bungeni baseform

class BaseForm(formlib.form.FormBase):
    """Base form class for Bungeni content.

    Headless submission

        Adds support for "headless" submission, relying only on the
        schema field ids. The headless mode is enabled by giving a
        true value for the request parameter ``headless``.  In this
        mode, no form prefix is applied and the default action is
        always executed.

    Custom validation

        The ``CustomValidation`` attribute is queried for extra validation
        steps to be performed.

    Redirection

        If ``next_url`` is provided, a redirect is issued upon
        successful form submission.
        
    As a viewlet
        
        Two additional init params to the "view" standard init API of 
        (context, request) are specified for when usage is as as "viewlet"
        i.e. (context, request, view, manager)
    
    """
    Adapts = None
    CustomValidation = None
    
    legends = {} # { iface:_(str) } i.e. 
    # keys are of type Interface, values are localized strings

    status = None
    
    template = formlib.namedtemplate.NamedTemplate("alchemist.form")
    
    def __init__(self, context, request,
            # to support usage as a viewlet
            view=None, manager=None
        ):
        # !+view/viewlet(mr, jul-2011): (self, context, request, view, manager)
        # here, we make the distinction explicit, for some clarity, but in 
        # subclasses we simply use the open-ended *args
        if view is not None:
            # viewlet api
            super(BaseForm, self).__init__(context, request, view, manager)
        else:
            # view api
            super(BaseForm, self).__init__(context, request)
        
        if str(self.request.get("headless", "")).lower() in TRUE_VALS:
            self.setPrefix(NO_PREFIX)

            # in headless mode, the first action defined is submitted
            # by default
            for action in self.actions:
                default = DefaultAction(action)
                self.actions = formlib.form.Actions(default)
                break
        
        # the ``_next_url`` attribute is used internally by our
        # superclass to implement formlib's ``nextURL`` method
        next_url = self._next_url = self.request.get("next_url", None)
        if next_url == "...":
            self._next_url = self.request.get("HTTP_REFERER", "")

    def __call__(self):
        #session = Session()
        # XXX control the display order of the submit buttons 
        # the order seems to be determined by the self.actions.actions 
        # tuple of zope.formlib.form.Action instances
        print "XXX Order of Form Submit Buttons:", [ 
            (a.name, a.label) for a in self.actions.actions ]
        return super(BaseForm, self).__call__()
    
    @property
    def widget_groups(self):
        groups = {}
        for widget in self.widgets:
            iface = widget.context.interface
            legend = self.legends.get(iface)
            if legend is None:
                iface = interface.Interface
            group = groups.setdefault(iface, [])
            group.append(widget)
        return groups
    
    @property
    def is_headless(self):
        """Boolean flag if form has been submitted in headless mode
        """
        return str(self.request.get("headless", "")).lower() in TRUE_VALS

    def update(self):
        self.form_fields = self.filter_fields() # !+FORM_FILTER_FROM_FIELDS?!
        self.status = self.request.get("portal_status_message", self.status)
        super(BaseForm, self).update()
        set_widget_errors(self.widgets, self.errors)
    
    def filter_fields(self):
        return self.form_fields # !+FORM_FILTER_FROM_FIELDS?!
    
    def form_fields():
        doc = "The prepared fields for self.mode."
        def fget(self):
            try:
                fields = self.__dict__["form_fields"]
            except KeyError:
                fields = self.__dict__["form_fields"] = self.get_form_fields()
            return fields
        def fset(self, form_fields):
            self.__dict__["form_fields"] = form_fields
        return locals()
    form_fields = property(**form_fields())
    
    @property
    def model_interface(self):
        # !+ does this give the the correct interface? Switch to capi?
        return tuple(interface.implementedBy(self.domain_model))[0]
    
    def get_form_fields(self):
        return setUpFields(self.domain_model, self.mode)
    
    def validate(self, action, data):
        """Validation that require context must be called here,
        invariants may be defined in the descriptor."""
        errors = (
            formlib.form.getWidgetsData(self.widgets, self.prefix, data) +
            formlib.form.checkInvariants(self.form_fields, data))
        if not errors and self.CustomValidation is not None:
            return list(self.CustomValidation(self.context, data))
        return errors
    
    def set_widget_error(self, key, message):
        widget = self.widgets[key]
        widget._error = formlib.form.WidgetInputError(
            widget.name, widget.label, message)
        return widget._error
    
    def validate_unique(self, action, data):
        """Validate unique.
        
        Since this class always adds a single object, we can safely
        return an empty list of errors.
        """
        errors = []
        dm = removeSecurityProxy(self.domain_model)
        
        # find unique columns in data model.. TODO do this statically
        mapper = sa.orm.class_mapper(dm)
        ucols = list(unique_columns(mapper))
        
        # query out any existing values with the same unique values,
        session = Session()
        # find data matching unique columns
        ctx = removeSecurityProxy(self.context)
        ctx_is_dm_instance = isinstance(ctx, dm) # !+when is this not true?
        for key, col in ucols:
            if key in data:
                # on edit ignore new value if its the same as the previous value
                if ctx_is_dm_instance and data[key] == getattr(ctx, key, None):
                    continue
                value = session.query(dm).filter(col == data[key]).count()
                if not value:
                    continue
                errors.append(self.set_widget_error(key,
                        _(u"A record with this value already exists")))
        return errors
    
    def validate_derived_table_schema(self, action, data):
        """Look-ahead validate against database contraints.
        """
        dm = self.domain_model
        ti = capi.get_type_info(dm)
        derived_table_schema = ti.derived_table_schema
        errors = []
        for name in derived_table_schema:
            ff = self.form_fields.get(name)
            # skip if no form does not define a corresponding form field
            if not ff:
                continue
            # !+ skip if field not included in this form "mode"?
            #if name not in getattr("%s_columns" % (self.mode), ti.descriptor_model):
            #    continue
            
            field = derived_table_schema.get(name)
            assert field is ff.field, name # !+TMP sanity check
            value = data.get(name, None)
            
            ''' !+VTF disabling for now, as attempting to preset a contextualized
            vocab fails for subsequent lodaing of a *view*, as this is executed 
            when validating a *submit* -- may still work if executed right moment.
            
            # !+VTF bungeni.ui.fields.VocabularyTextField -- here a vocabulary 
            # field is not necessarily the type defined by bungeni 
            # e.g. zope.schema._field.Choice that during validation attempts to
            # retrieve the vocabulary and initialize it with a None context...
            # To preempt the error that this causes, we check for and stuff
            # an appropiately initialized vocabulary instance onto this field...
            if hasattr(field, "vocabulary"):
                # preset a vocabulary on self.context, or reset with one off current 
                # context if the one preset previously was off a different context
                if (field.vocabulary is None or (
                        # a vocab was preset previously
                        hasattr(field, "_vtf_last_context") and
                        # and it was prepared with a different context
                        getattr(field, "_vtf_last_context") is not self.context)
                    ):
                    from bungeni.alchemist.utils import get_vocabulary
                    field.vocabulary = get_vocabulary(field.vocabularyName)(self.context)
                    # remember last context used to preset vocabulary
                    field._vtf_last_context = self.context
                    log.debug("Validation of vocabulary field (%r, %r) with value=%r -- "
                        "stuffing vocabulary instance %s [context: %r] onto field %s ...", 
                        name, field.vocabularyName, value, field.vocabulary, self.context, field)
            '''
            # !+VTF a "temporary" and simpler version of above, to avoid 
            # AttributeError in try block below (and incorrectly failed validation).
            TMP_SET_VOCAB = False
            if hasattr(field, "vocabulary") and field.vocabulary is None:
                TMP_SET_VOCAB = True
                from bungeni.alchemist.utils import get_vocabulary
                field.vocabulary = get_vocabulary(field.vocabularyName)(self.context)
            # standard field validation !+ necessary, already called elsewhere? 
            try:
                widget_error = field.validate(value)
            except (RequiredMissing,) as exc:
                widget_error = exc
            # !+ other possible exceptions, should never pass here?
            except (formlib.form.NoInputData, interface.Invalid, Exception,) as exc:
                widget_error = exc
                debug.log_exc(sys.exc_info(), log_handler=log.error)
                log.debug(debug.class_inheritance(exc))
                log.error("\n"
                    "    %r.validate(%r) FAILED (field %r)\n"
                    "    [context: %r]", field, value, name, self.context)
                #raise # !+?
            # !+VTF clear any vocabulary that we preset above
            if TMP_SET_VOCAB:
                field.vocabulary = None
            if widget_error:
                errors.append(self.set_widget_error(name, widget_error))
                widget_error = None
                continue
            
            # get db column definition
            domain_attr = getattr(dm, name)
            if not isinstance(domain_attr, sa.orm.attributes.InstrumentedAttribute):
                continue
            domain_attr_property = domain_attr.property
            assert isinstance(domain_attr_property, sa.orm.properties.ColumnProperty), name # !+TMP sanity check
            # !+MULTIPLE_COLUMNS only single columns supported (so far)
            if len(domain_attr_property.columns) == 1:
                col = domain_attr_property.columns[0]
                #!+AttributeError: '_Label' object has no attribute 'nullable'
                # not: sa.sql.expression._Label, sa.sql.expression.ColumnElement
                assert isinstance(col, sa.schema.Column), col 
            else:
                log.warn("SQLAlchemy property %r NOT defined as a single column, "
                    "skipping derived_table_schema validation...", name)
                continue
            
            # validate against db column definition
            # nullable
            if value is None:
                if not col.nullable:
                    errors.append(self.set_widget_error(name, _(u"May not be null")))
                continue
            # sa.String
            if isinstance(col.type, sa.types.String):
                # length
                length = col.type.length
                if length is not None:
                    if length < len(value):
                        errors.append(self.set_widget_error(name, 
                                _(u"May not be longer than ${length}", 
                                    mapping={"length": length})))
        return errors
    
    @property
    def next_url(self):
        return self._next_url

    @property
    def invariantErrors(self):
        """ () -> [error:zope.interface.Invalid]
        """
        errors = []
        for error in self.errors:
            if isinstance(error, interface.Invalid):
                errors.append(error)
        return errors
    
    @property
    def invariantMessages(self):
        """ () -> [message:str]
        Called from the form.html#form template.
        """
        return filter(None,
                [ error.message for error in self.invariantErrors ])
    
    
    @misc.cached_property
    def model_descriptor(self):
        return utils.get_descriptor(self.domain_model)

    @misc.cached_property
    def domain_model(self):
        context = removeSecurityProxy(self.context)
        if IAlchemistContainer.providedBy(context):
            return context.domain_model
        elif IAlchemistContent.providedBy(context):
            return context.__class__
        else:
            raise AttributeError("Could not find domain model for context: %s",
                context)



# alchemist.ui.content

class AddForm(BaseForm, formlib.form.AddForm):
    """Static add form for db content.
    """
    mode = "add"
    defaults = {}
    _next_url = None
    adapters = None
    
    def createAndAdd(self, data):
        domain_model = self.domain_model
        # create the object, inspect data for constructor args      
        try:  
            ob = createInstance(domain_model, data)
        except TypeError:
            log.error("Failure: createInstance(%s, %s)", domain_model, data)
            debug.log_exc(sys.exc_info(), log_handler=log.error)
            ob = domain_model()
        # apply any context values
        self.finishConstruction(ob)
        # apply extra form values
        formlib.form.applyChanges(ob, self.form_fields, data, self.adapters)
        # set the object in container context, causing autosetting of 
        # constrained values e.g. one2many attributes, by triggering call to 
        # _ManagedContainer.constraints.setConstrainedValues()
        self.context[""] = ob
        # flush so we have database id
        Session().flush()
        # !+DataError reload form and display this error?
        # fire an object created event
        notify(ObjectCreatedEvent(ob)) # !+ would set doc_id (if session not flushed) !!
        # signal to add form machinery to go to next url
        self._finished_add = True
        # retrieve the object with location and security information
        oid = self.get_oid(ob)
        return self.context[oid]
    
    def get_oid(self, ob):
        """Return the string id to be used as the key for the container entry 
        for this object.
        """
        mapper = sa.orm.object_mapper(ob)
        # TODO single primary key (need changes to base container)
        return mapper.primary_key_from_instance(ob)
    
    def update(self):
        for name, value in self.defaults.items():
            self.form_fields[name].field.default = value
        super(AddForm, self).update()
    
    def finishConstruction(self, ob):
        """No op, subclass to provide additional initialization behavior"""
        return
        
    def nextURL(self):
        if not self._next_url:
            return absoluteURL(self.context, self.request)
        return self._next_url
    
    def validateAdd(self, action, data):
        errors = self.validate_unique(action, data)
        return errors
        
    @formlib.form.action(_(u"Cancel"), validator=null_validator)
    def handle_cancel(self, action, data):
        url = self.nextURL()
        return self.request.response.redirect(url)
    
    @formlib.form.action(_(u"Save and continue editing"), 
        condition=formlib.form.haveInputWidgets, validator="validateAdd")
    def handle_add_edit(self, action, data):
        ob = self.createAndAdd(data)
        name = self.domain_model.__name__
        self._next_url = "%s/@@edit?portal_status_message=%s Added" % (
            absoluteURL(ob, self.request), name)
    
    @formlib.form.action(_(u"Save and add another"), 
        condition=formlib.form.haveInputWidgets)
    def handle_add_and_another(self, action, data):
        self.createAndAdd(data)
        name = self.domain_model.__name__
        self._next_url = "%s/@@add?portal_status_message=%s Added" % (
            absoluteURL(self.context, self.request), name)


class EditForm(BaseForm, formlib.form.EditForm):
    mode = "edit"
    adapters = None
    
    def setUpWidgets(self, ignore_request=False):
        self.adapters = self.adapters or {}
        self.widgets = formlib.form.setUpEditWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            adapters=self.adapters, ignore_request=ignore_request)
    
    @formlib.form.action(_(u"Save"), condition=formlib.form.haveInputWidgets)
    def handle_edit_action(self, action, data):
        return _handle_edit_action(self, action, data)
    
    @formlib.form.action(_(u"Cancel"), condition=formlib.form.haveInputWidgets, validator=null_validator)
    def handle_cancel_action(self, action, data):
        return _handle_edit_action(self, action, data)            


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
        formatter = date.getLocaleFormatter(self.request, "dateTime", "medium")
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
    
    # !+REVIEW this logic !!
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
                # !+REVIEW
                raise TypeError("missing argument %r" % n)
            else:
                v = defaults[i - nrequired]
        else:
            used.append(n)
        args.append(v)
    
    for n in used:
        del data[n]
    
    ob = cls(*args)
    
    return ob


# viewlet

class ContentViewletManager(manager.ViewletManagerBase):
    template = formlib.namedtemplate.NamedTemplate("alchemist.content")



