# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Specific forms for Bungeni user interface

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.forms.forms")

import copy

from zc.resourcelibrary import need
from zope.formlib import form, namedtemplate
from zope import schema, interface
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy
#import zope.security.management

from sqlalchemy import sql

from bungeni.alchemist import Session

from bungeni.models import domain
from bungeni.models import schema as model_schema
from bungeni.models.utils import get_current_parliament, get_db_user
from bungeni.models.interfaces import ISessionContainer, ISittingContainer
from bungeni.core.i18n import _
from bungeni.core.interfaces import ISchedulingContext
#from bungeni.ui.forms import validations
from bungeni.ui.forms.common import ReorderForm
from bungeni.ui.forms.common import PageForm
from bungeni.ui.forms.common import AddForm
from bungeni.ui.forms.common import EditForm
from bungeni.ui.forms.common import DeleteForm
from bungeni.ui.forms.common import DisplayForm
from bungeni.ui.interfaces import IBungeniSkin

from interfaces import Modified
from zope import component
from zope.formlib.interfaces import IDisplayWidget
from zope.schema.interfaces import IText, ITextLine
from bungeni.ui.widgets import IDiffDisplayWidget
from bungeni.ui.htmldiff import htmldiff

from bungeni.utils import register


FormTemplate = namedtemplate.NamedTemplateImplementation(
    ViewPageTemplateFile("templates/form.pt")
)
SubFormTemplate = namedtemplate.NamedTemplateImplementation(
    ViewPageTemplateFile("templates/subform.pt")
)
ContentTemplate = namedtemplate.NamedTemplateImplementation(
    ViewPageTemplateFile("templates/content.pt")
)

''' !+UNUSED(mr, nov-2012)
def hasDeletePermission(context):
    """Generic check if the user has rights to delete the object. The
    permission must follow the convention:
    ``bungeni.<classname>.Delete`` where "classname" is the lowercase
    of the name of the python class.
    """
    interaction = zope.security.management.getInteraction()
    class_name = context.__class__.__name__ 
    permission_name = "bungeni.%s.Delete" % class_name.lower()
    return interaction.checkPermission(permission_name, context)
'''

def set_widget_errors(widgets, errors):
    """Display invariant errors / custom validation errors in the
    context of the field."""

    for widget in widgets:
        name = widget.context.getName()
        for error in errors:
            if isinstance(error, interface.Invalid) and name in error.args[1:]:
                if widget._error is None:
                    widget._error = error

''' !+UNUSED(mr, nov-2012)
def flag_changed_widgets(widgets, context, data):
    for widget in widgets:
        name = widget.context.getName()
        # If the field is not in the data, then go on to the next one
        if name not in data:
            widget.changed = False
            continue
        if data[name] == getattr(context, name):
            widget.changed = False
        else:
            widget.changed = True
    return []
'''

''' !+UNUSED(mr, nov-2012)
class ResponseEditForm(EditForm):
    """ Answer a Question
    UI for ministry to input response
    Display the question when adding the answer.
    """
    CustomValidations = validations.null_validator

class ResponseAddForm(AddForm):
    """
    Answer a Question
    UI for ministry to input response
    Display the question when adding the answer.
    """
    CustomValidation = validations.null_validator
'''

class ItemScheduleContainerReorderForm(ReorderForm):
    """Specialization of the general reorder form for item
    schedulings."""
    
    def save_ordering(self, ordering):
        for name, scheduling in self.context.items():
            scheduling.planned_order = ordering.index(name)


class ItemScheduleReorderForm(PageForm):
    """Form to reorder a scheduling within a list of schedulings."""

    class IReorderForm(interface.Interface):
        mode = schema.Choice(
            ("up", "down"),
            title=_(u"Direction"),
            required=True)
        field = schema.Choice(
            ("planned_order", "real_order"),
            title=_(u"AM"),
            required=True)
            
    form_fields = form.Fields(IReorderForm)

    @form.action(_(u"Move"), name="move")
    def handle_move(self, action, data):
        """Move scheduling.

        This logic handles both reordering within the container and
        maintenance of category assignments.

        If we move up:

        - Next item inherits any assigned category
        - This item gets its category cleared

        If we move down:

        - We inherit category of the following item
        - Next item gets its category cleared 

        """
        field = data["field"]
        mode = data["mode"]
        container = copy.copy(removeSecurityProxy(self.context.__parent__))
        name = self.context.__name__
        schedulings = container.batch(order_by=field, limit=None)
        ordering = [scheduling.__name__ for scheduling in schedulings]
        for i in range(0,len(ordering)):
            setattr(container[ordering[i]], field, i+1)
            
        index = ordering.index(name)

        # !+LOGIC(mr, feb-2012) what is next for??
        if mode == "up" and index > 0:
            # if this item has a category assigned, and there's an
            # item after it, swap categories with it
            if  index < len(ordering)-1:
                next = container[ordering[index+1]]
            prev = container[ordering[index-1]]
            order = getattr(self.context, field)
            setattr(self.context, field, getattr(prev, field))
            setattr(prev, field, order)

        if mode == "down" and index < len(ordering) - 1:
            next = container[ordering[index+1]]

class ItemScheduleContainerDeleteForm(DeleteForm):
    class IDeleteForm(interface.Interface):
        item_id = schema.Int(
            title=_(u"Item ID"),
            required=True
        )
        item_type = schema.TextLine(
            title=_(u"Item Type"),
            required=True
        )
    form_fields = form.Fields(IDeleteForm)
    
    @form.action(_(u"Delete"))
    def handle_delete(self, action, data):
        session = Session()
        sitting_id = self.context.__parent__.sitting_id
        sch = session.query(domain.ItemSchedule).filter(
            sql.and_(
                model_schema.item_schedule.c.sitting_id == sitting_id,
                model_schema.item_schedule.c.item_id == data["item_id"],
                model_schema.item_schedule.c.item_type == data["item_type"]
            )).all()
        for i in sch:
            session.delete(i)
        self.request.response.redirect(self.next_url)

''' !+DiffEditForm(mr, nov-2102) prior to r10032, doc-archetyped types were 
being **ZCML declared** to use bungeni.ui.forms.forms.DiffEditForm, but this
is not the edit view tht was actually being used!

class DiffEditForm(EditForm):
    """ Form to display diff view if timestamp was changes.
    """
    CustomValidation = validations.diff_validator
    template = ViewPageTemplateFile("templates/diff-form.pt")
    
    def __init__(self, context, request):
        self.diff_widgets = []
        self.diff = False
        self.last_timestamp = None
        super(DiffEditForm, self).__init__(context, request)
        need("diff-form")
    
    def update(self):
        """ Checks if we have Modified errors and renders split view 
            with display widgets for db values and normal for input 
        """
        super(DiffEditForm, self).update()
        for error in self.errors:
            if error.__class__ == Modified:
                # Set flag that form is in diff mode
                if not self.diff:
                    self.diff=True
                
        if self.diff:
            # Set last timestamp which we store in hidden field because
            # document may be modified during diff and from.timestamp field
            # contains old value
            self.last_timestamp = self.context.timestamp
            for widget in self.widgets:
                try:
                    value = widget.getInputValue()
                except:
                    value = ""
                
                # Get widget's field    
                form_field = self.form_fields.get(widget.context.__name__)                    
                field = form_field.field.bind(self.context)
                
                # Form display widget for our field 
                if form_field.custom_widget is not None:
                    display_widget = form_field.custom_widget(
                        field, self.request)                 
                else:
                    display_widget = component.getMultiAdapter(
                        (field, self.request), IDisplayWidget)
                
                # If field is Text or TextLine we display HTML diff
                if IText.providedBy(field) or ITextLine.providedBy(field):
                    if value:
                        diff_val = htmldiff(field.get(self.context), value)
                    else:
                        diff_val = ""
                    display_widget = component.getMultiAdapter(
                        (field, self.request), IDiffDisplayWidget)
                    display_widget.setRenderedValue(diff_val)
                else:
                    display_widget.setRenderedValue(field.get(self.context))
                display_widget.name = widget.name + ".diff.display"
                # Add display - input widgets pair to list of diff widgets
                self.diff_widgets.append((widget, display_widget))
'''

class UserAddressDisplayForm(DisplayForm):
    
    @property
    def page_title(self):
        return "%s address" % self.context.logical_address_type.title()


@register.view(ISessionContainer, layer=IBungeniSkin, name="add",
    protect={"bungeni.session.Add": register.VIEW_DEFAULT_ATTRS})
class SessionAddForm(AddForm):
    def finishConstruction(self, ob):
        """We add the parliament ID if adding a session in contexts
        not bound to the the parliament in traversal hierarchy
        """
        super(SessionAddForm, self).finishConstruction(ob)
        if ob.parliament_id is None:
            ob.parliament_id = get_current_parliament(get_db_user).parliament_id

@register.view(ISittingContainer, layer=IBungeniSkin, name="add",
    protect={"bungeni.sitting.Add": register.VIEW_DEFAULT_ATTRS})
class SittingAddForm(AddForm):
    def finishConstruction(self, ob):
        """We add the group ID if adding a sitting in contexts
        not bound to groups in traversal hierarchy
        """
        super(SittingAddForm, self).finishConstruction(ob)
        if ob.group_id is None:
            ob.group_id = removeSecurityProxy(
                ISchedulingContext(self.context.__parent__)).group_id

