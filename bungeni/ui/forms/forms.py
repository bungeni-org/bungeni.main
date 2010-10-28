# encoding: utf-8


import copy
import datetime

from zope.event import notify
from zope.formlib import form, namedtemplate
from zope.lifecycleevent import ObjectCreatedEvent
from zope import schema, interface
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy
import zope.security.management

from sqlalchemy import sql

from bungeni.alchemist import Session

from bungeni.models import domain
from bungeni.models import schema as model_schema
from bungeni.core.i18n import _
from bungeni.ui.forms import validations
from bungeni.ui.forms.common import ReorderForm
from bungeni.ui.forms.common import PageForm
from bungeni.ui.forms.common import AddForm
from bungeni.ui.forms.common import EditForm
from bungeni.ui.forms.common import DeleteForm


FormTemplate = namedtemplate.NamedTemplateImplementation(
    ViewPageTemplateFile('templates/form.pt')
)

ContentTemplate = namedtemplate.NamedTemplateImplementation(
    ViewPageTemplateFile('templates/content.pt')
)

def hasDeletePermission(context):
    """Generic check if the user has rights to delete the object. The
    permission must follow the convention:
    ``bungeni.<classname>.Delete`` where 'classname' is the lowercase
    of the name of the python class.
    """
    
    interaction = zope.security.management.getInteraction()
    class_name = context.__class__.__name__ 
    permission_name = 'bungeni.' + class_name.lower() +'.Delete'
    return interaction.checkPermission(permission_name, context)

def set_widget_errors(widgets, errors):
    """Display invariant errors / custom validation errors in the
    context of the field."""

    for widget in widgets:
        name = widget.context.getName()
        for error in errors:
            if isinstance(error, interface.Invalid) and name in error.args[1:]:
                if widget._error is None:
                    widget._error = error

def flag_changed_widgets( widgets, context, data):
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

class ResponseEditForm( EditForm ):
    """ Answer a Question
    UI for ministry to input response
    Display the question when adding the answer.
    """
    CustomValidations =  validations.null_validator

    
class ResponseAddForm( AddForm ):
    """
    Answer a Question
    UI for ministry to input response
    Display the question when adding the answer.
    """
    CustomValidation =  validations.null_validator

    
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
            ('up', 'down'),
            title=_(u"Direction"),
            required=True)
        field = schema.Choice(
            ('planned_order', 'real_order'),
            title=_(u"AM"),
            required=True)
            
    form_fields = form.Fields(IReorderForm)

    @form.action(_(u"Move"))
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
        field = data['field']
        mode = data['mode']
        container = copy.copy(removeSecurityProxy(self.context.__parent__))
        name = self.context.__name__
        schedulings = container.batch(order_by=field, limit=None)
        ordering = [scheduling.__name__ for scheduling in schedulings]
        for i in range(0,len(ordering)):
            setattr(container[ordering[i]], field, i+1)
            
        index = ordering.index(name)

        if mode == 'up' and index > 0:
            # if this item has a category assigned, and there's an
            # item after it, swap categories with it
            if  index < len(ordering)-1:
                next = container[ordering[index+1]]
            prev = container[ordering[index-1]]
            order = getattr(self.context, field)
            setattr(self.context, field, getattr(prev, field))
            setattr(prev, field, order)

        if mode == 'down' and index < len(ordering) - 1:
            next = container[ordering[index+1]]
 

class ItemScheduleDeleteForm(DeleteForm):
    def get_subobjects(self):
        items = []
        discussion = self.context.discussion
        if discussion is not None:
            items.append(discussion)
        return items

    def delete_subobjects(self):
        """Delete subobjects.

        1) For category maintenance, move the scheduling to the bottom
        of the container.

        2) Delete any discussion items that have been associated to
        this scheduling.
        """
        try:
            field = self.request.form['field']
        except:
            import pdb; pdb.set_trace()
        reorder_form = ItemScheduleReorderForm(self.context, self.request)
        container = copy.copy(removeSecurityProxy(self.context.__parent__))
        subset_query = container.subset_query
        container.subset_query = sql.and_(
            subset_query,
            container.domain_model.planned_order > self.context.planned_order)
        for i in range(len(container) * 2):
            reorder_form.handle_move.success({'mode': 'down', 'field': field})
        container.subset_query = subset_query

        count = 0
        session = Session()
        unproxied = removeSecurityProxy(self.context)
        for key, discussion in unproxied.discussions.items():
            del unproxied.discussions[key]
            session.delete(discussion)
            count += 1
        #session.close()
        return count
        
class ItemScheduleContainerDeleteForm(DeleteForm):
    class IDeleteForm(interface.Interface):
        item_id = schema.Int(
            title=_(u"Item ID"),
            required=True)
    form_fields = form.Fields(IDeleteForm)
    
    @form.action(_(u"Delete"))
    def handle_delete(self, action, data):
        session = Session()
        sitting_id = self.context.__parent__.sitting_id
        sch = session.query(domain.ItemSchedule).filter(
            sql.and_(
                model_schema.item_schedules.c.sitting_id == sitting_id,
                model_schema.item_schedules.c.item_id == data['item_id']
            )).all()        
        for i in sch:
            session.delete(i)
        self.request.response.redirect(self.next_url)

