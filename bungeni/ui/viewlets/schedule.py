# encoding: utf-8

from zope import interface
from zope import component

from zope.app.pagetemplate import ViewPageTemplateFile
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.location.interfaces import ILocation
from zope.viewlet.manager import WeightOrderedViewletManager
from zc.resourcelibrary import need
from zope.app.component.hooks import getSite

import sqlalchemy.sql.expression as sql

from bungeni.core.workflows.adapters import get_workflow
from bungeni.models import domain
from bungeni.models.interfaces import IBungeniApplication, IBungeniGroup, ICommittee

from bungeni.alchemist import Session
from bungeni.core.workflow.interfaces import IWorkflow

from bungeni.ui import browser
from bungeni.ui.i18n import _
from bungeni.ui.utils import url
#from bungeni.ui.calendar.utils import datetimedict
from interfaces import ISchedulingManager


class SchedulingManager(WeightOrderedViewletManager):
    interface.implements(ISchedulingManager)


# !+BungeniViewlet(mr, oct-2010) standardize visible<->for_display ?

class SchedulableItemsViewlet(browser.BungeniItemsViewlet):
    """Renders a list of schedulable items for a particular ``model``,
    filtered by workflow ``states``.

    Must subclass.
    """
    model = states = container = view_title = None
    render = ViewPageTemplateFile("templates/schedulable-items.pt")

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

    @property
    def visible(self):
        return not(ICommittee.providedBy(self.group()))
    
    def _query_items(self):
        return tuple(Session().query(self.model).filter(
                self.model.status.in_(self.states)))
    
    def _item_date(self, item):
        return item.status_date
    
    def _item_url(self, item):
        return url.set_url_context("%s/business/%ss/obj-%s" % (
                url.absoluteURL(getSite(), self.request), 
                item.type, 
                item.doc_id))

    def _get_item_key(self, item):
        return item.doc_id

    def update(self):
        need("yui-dragdrop")
        need("yui-container")

        sitting = self._parent._parent.context
        scheduled_item_ids = [item.item_id for item in sitting.item_schedule]
        
        # add location to items
        gsm = component.getSiteManager()
        adapter = gsm.adapters.lookup(
            (interface.implementedBy(self.model), interface.providedBy(self)), 
            ILocation
        )
        
        date_formatter = self.get_date_formatter("date", "medium")
        items = [ adapter(item, None) for item in self._query_items() ]
        # for each item, format dictionary for use in template
        self.items = [{
                "title": properties.title,
                "name": item.__class__.__name__,
                "description": properties.description,
                #"date": _(u"$F", mapping={"F":
                #       datetimedict.fromdatetime(item.changes[-1].date)}),
                #"date":item.changes[-1].date,
                # not every item has a auditlog (headings) 
                # use last status change instead.
                "date": self._item_date(item) and date_formatter.format(self._item_date(item)),
                "state": IWorkflow(item).get_state(item.status).title,
                "id": self._get_item_key(item),
                "class": (
                    (self._get_item_key(item) in scheduled_item_ids and
                        "dd-disable") or 
                    ""),
                "url": self._item_url(item),
                "type": item.type
            } for item, properties in [
                (item, (IDCDescriptiveProperties.providedBy(item) and item or
                        IDCDescriptiveProperties(item))) 
                for item in items ]
        ]


class SchedulableHeadingsViewlet(SchedulableItemsViewlet):
    view_name = "heading"
    view_title = _("Headings")
    states = (get_workflow("heading").get_state("public").id,)
    model = domain.Heading
    
    def _item_url(self, item):
        return ""
        
    def _get_item_key(self, item):
        return item.heading_id

    def get_group_id(self):
        parent=self.context
        while parent is not None:
            group_id = getattr(parent, "group_id", None)
            if group_id:
                return group_id
            else:
                parent = parent.__parent__
        raise ValueError("Unable to determine group.")

    def _query_items(self):
        return tuple(Session().query(self.model).filter(
                sql.and_(
                    self.model.status.in_(self.states),
                    self.model.group_id == self.get_group_id()
                )
            )
        )

# !+Schedulable{TYPE}Viewlets (and their registration) should be just one, 
# parametrized on type_key
class SchedulableBillsViewlet(SchedulableItemsViewlet):
    view_name = "bill"
    view_title = _("Bills")
    states = get_workflow("bill").get_state_ids(tagged=["tobescheduled"])
    model = domain.Bill

class SchedulableQuestionsViewlet(SchedulableItemsViewlet):
    view_name = "question"
    view_title = _("Questions")
    states = get_workflow("question").get_state_ids(tagged=["tobescheduled"])
    model = domain.Question

class SchedulableMotionsViewlet(SchedulableItemsViewlet):
    view_name = "motion"
    view_title = _("Motions")
    states = get_workflow("motion").get_state_ids(tagged=["tobescheduled"])
    model = domain.Motion

class SchedulableTabledDocumentsViewlet(SchedulableItemsViewlet):
    view_name = "tableddocument"
    view_title = _("Tabled documents")
    states = get_workflow("tabled_document").get_state_ids(tagged=["tobescheduled"])
    model = domain.TabledDocument

class SchedulableAgendaItemsViewlet(SchedulableItemsViewlet):
    view_name = "agendaitem"
    view_title = _("Agenda items")
    visible = True
    states = get_workflow("agenda_item").get_state_ids(tagged=["tobescheduled"])
    model = domain.AgendaItem
    
    def get_group_id(self):
        parent=self.context
        while parent is not None:
            group_id = getattr(parent,"group_id", None)
            if group_id:
                return group_id
            else:
                parent = parent.__parent__
        raise ValueError("Unable to determine group.")
    
    def _query_items(self):
        return tuple(Session().query(self.model).filter(
            sql.and_(
            self.model.status.in_(self.states),
            self.model.group_id == self.get_group_id())
        ))
    
    def _item_date(self, item):
        return item.changes[-1].date_active
    
    def _item_url(self, item):
        return url.set_url_context(url.absoluteURL(item, self.request))

