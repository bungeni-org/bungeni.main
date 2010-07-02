# encoding: utf-8

from zope import interface
from zope import component

from zope.app.pagetemplate import ViewPageTemplateFile
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.location.interfaces import ILocation
from zope.viewlet import viewlet
from zope.viewlet.manager import WeightOrderedViewletManager
from zc.resourcelibrary import need
from zope.app.component.hooks import getSite

import sqlalchemy.sql.expression as sql

from bungeni.core.workflows.question import states as question_wf_state
from bungeni.core.workflows.motion import states as motion_wf_state
from bungeni.core.workflows.agendaitem import states as agendaitem_wf_state
from bungeni.core.workflows.heading import states as heading_wf_state
from bungeni.models import domain
from bungeni.models.interfaces import IBungeniApplication, IBungeniGroup, ICommittee
from bungeni.core.interfaces import ISchedulingContext

from ore.alchemist import Session
from ore.alchemist.container import stringKey
from ore.alchemist.container import contained
from ore.alchemist.model import queryModelDescriptor
from ore.workflow.interfaces import IWorkflow

from bungeni.ui.tagged import get_states
from bungeni.ui.i18n import _
import bungeni.ui.utils as ui_utils
from bungeni.ui.calendar.utils import datetimedict
from interfaces import ISchedulingManager

class SchedulingManager( WeightOrderedViewletManager ):
    interface.implements(ISchedulingManager)

class SchedulablesViewlet(viewlet.ViewletBase):
    """Renders a portlet which calls upon the scheduling viewlet
    manager to render a list of schedulable items."""
    
    for_display = True
    render = ViewPageTemplateFile('templates/scheduling.pt')
    title = _(u"Scheduling")

    def __init__(self, context, request, view, manager):
        while not ISchedulingContext.providedBy(context):
            context = ISchedulingContext(context, context.__parent__)
            if context is None:
                raise RuntimeError("Unable to locate a scheduling context.")
        super(SchedulablesViewlet, self).__init__(
            context, request, view, manager)

class SchedulableItemsViewlet(viewlet.ViewletBase):
    """Renders a list of schedulable items for a particular ``model``,
    filtered by workflow ``states``.

    Must subclass.
    """

    model = states = container = name = None

    render = ViewPageTemplateFile('templates/schedulable_items.pt')
                              

    @property
    def app(self):
        parent = self.context.__parent__
        while parent is not None:
            if IBungeniApplication.providedBy(parent):
                return parent
            parent = parent.__parent__
        raise ValueError("Unable to locate application.")

    def group(self):
        parent = self.context.__parent__
        while parent is not None:
            if IBungeniGroup.providedBy(parent):
                return parent
            parent = parent.__parent__
        return None
        raise ValueError("Unable to locate application.")

    def visible(self):
        return not(ICommittee.providedBy(self.group()))

    def update(self):
        need('yui-dragdrop')
        need('yui-container')
        session = Session()
        items = tuple(session.query(self.model).filter(
            self.model.status.in_(self.states)))

        sitting = self._parent._parent.context
        scheduled_item_ids = [item.item_id for item in sitting.item_schedule]
        
        # add location to items
        gsm = component.getSiteManager()
        adapter = gsm.adapters.lookup(
            (interface.implementedBy(self.model),
             interface.providedBy(self)), ILocation)

        items = [adapter(item, None) for item in items]

        # for each item, format dictionary for use in template
        self.items = [{
            'title': properties.title,
            'name': item.__class__.__name__,
            'description': properties.description,
#            'date': _(u"$F", mapping={"F":
#                      datetimedict.fromdatetime(item.changes[-1].date)}),
            #'date':item.changes[-1].date,
            # not every item has a auditlog (headings) use last status change instead.
            'date':item.status_date,
#
            'state': IWorkflow(item).workflow.states[item.status].title,
            'id': item.parliamentary_item_id,
            'class': (item.parliamentary_item_id in scheduled_item_ids) and "dd-disable" or "",
            'url': ui_utils.url.absoluteURL(item, self.request)
            } for item, properties in \
            [(item, (IDCDescriptiveProperties.providedBy(item) and item or \
            IDCDescriptiveProperties(item))) for
             item in items]]

class SchedulableHeadingsViewlet(SchedulableItemsViewlet):
    model = domain.Heading
    name = _('Headings')
    view_name="heading"
    states = (
        heading_wf_state[u"public"].id,
        )

class SchedulableBillsViewlet(SchedulableItemsViewlet):
    model = domain.Bill
    name = _('Bills')
    view_name="bill"
    states = get_states("bill", tagged=["tobescheduled"]) 

class SchedulableQuestionsViewlet(SchedulableItemsViewlet):
    model = domain.Question
    name = _('Questions')
    view_name="question"
    states = (
        question_wf_state[u"scheduled"].id,
        question_wf_state[u"schedule_pending"].id,
        question_wf_state[u"debate_adjourned"].id,
        )

class SchedulableMotionsViewlet(SchedulableItemsViewlet):
    model = domain.Motion
    name = _('Motions')
    view_name="motion"
    states = (
        motion_wf_state[u"scheduled"].id,
        motion_wf_state[u"schedule_pending"].id,
        motion_wf_state[u"debate_adjourned"].id,
        )

class SchedulableTabledDocumentsViewlet(SchedulableItemsViewlet):
    model = domain.TabledDocument
    name = _('Tabled documents')
    view_name="tableddocument"
    states = get_states("tableddocument", tagged=["tobescheduled"]) 
        
class SchedulableAgendaItemsViewlet(SchedulableItemsViewlet):
    model = domain.AgendaItem
    name = _('Agenda items')
    view_name="agendaitem"
    visible = True
    states = (
        agendaitem_wf_state[u"scheduled"].id,
        agendaitem_wf_state[u"schedule_pending"].id,
        agendaitem_wf_state[u"debate_adjourned"].id,
        )

    def get_group_id(self):
        parent=self.context
        while parent is not None:
            group_id = getattr(parent,'group_id',None)
            if group_id:
                return group_id
            else:
                parent = parent.__parent__
        raise ValueError("Unable to determine group.")
                
    def update(self):
        need('yui-dragdrop')
        need('yui-container')

        session = Session()
        group_id = self.get_group_id()
        
        items = tuple(session.query(self.model).filter(
            sql.and_(
            self.model.status.in_(self.states),
            self.model.group_id == group_id)
            ))
        sitting = self._parent._parent.context
        scheduled_item_ids = [item.item_id for item in sitting.item_schedule]
        # add location to items
        gsm = component.getSiteManager()
        adapter = gsm.adapters.lookup(
            (interface.implementedBy(self.model),
             interface.providedBy(self)), ILocation)

        items = [adapter(item, None) for item in items]

        # for each item, format dictionary for use in template
        self.items = [{
            'title': properties.title,
            'name': item.__class__.__name__,
            'description': properties.description,
#            'date': _(u"$F", mapping={'F':
#                      datetimedict.fromdatetime(item.changes[-1].date)}),
            'date': item.changes[-1].date,
#
            'state': _(IWorkflow(item).workflow.states[item.status].title),
            'id': item.parliamentary_item_id,
            'class': (item.parliamentary_item_id in scheduled_item_ids) and "dd-disable" or "",
            'url': ui_utils.url.absoluteURL(item, self.request)
            } for item, properties in \
            [(item, (IDCDescriptiveProperties.providedBy(item) and item or \
            IDCDescriptiveProperties(item))) for
             item in items]]


