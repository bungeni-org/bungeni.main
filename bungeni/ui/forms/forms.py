# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Specific forms for Bungeni user interface

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.forms.forms")

import copy

from zope.formlib import form, namedtemplate
from zope import schema, interface
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy
#import zope.security.management

from sqlalchemy import sql

from bungeni.alchemist import Session

from bungeni.models import domain
from bungeni.models import schema as model_schema
from bungeni.core.i18n import _
#from bungeni.ui.forms import validations
from bungeni.ui.forms.common import ReorderForm
from bungeni.ui.forms.common import PageForm
from bungeni.ui.forms.common import DeleteForm
from bungeni.ui.forms.common import DisplayForm

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


class UserAddressDisplayForm(DisplayForm):
    
    @property
    def page_title(self):
        return "%s address" % self.context.logical_address_type.title()
