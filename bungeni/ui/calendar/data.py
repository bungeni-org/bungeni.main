# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Data loader module for scheduler

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.calendar.data")

import json
from sqlalchemy import orm, sql
from bungeni.alchemist import model
from bungeni.models import domain
from bungeni.core.dc import IDCDescriptiveProperties
from bungeni.core.workflow.interfaces import IWorkflow
from bungeni.core.workflows.adapters import get_workflow
from bungeni.ui.utils import date, common
from bungeni.alchemist import Session
from bungeni.ui.i18n import _

#!+CALENDAR(mb, Jan-2012) This should come from capi or workflow configuration
#!+SCHEDULE(mr, feb-2012) this can already be added as a feature on each 
# respective workflow e.g. <feature name="schedule" enabled="true" />, and then
# can be tested for with: workflow.has_feature"schedule")
SCHEDULABLE_TYPES = ["bill", "question", "motion", "tableddocument", "agendaitem"]

def get_schedulable_types():
    return dict([
        (name, 
         model.queryModelDescriptor(domain.DOMAIN_CLASSES[name]).container_name)
        for name in SCHEDULABLE_TYPES
    ])



def get_filter_config(tag="tobescheduled"):
    return dict(
        [ (item_type, 
            { 
                "label": _(u"choose status"),
                "menu": [ 
                    { 
                        "text": IWorkflow(domain.DOMAIN_CLASSES[item_type]()).get_state(status).title, 
                        "value": status 
                    } 
                    for status in get_workflow(item_type).get_state_ids(tagged=[tag])
                ]
            }
           ) 
            for item_type in get_schedulable_types().keys()
        ]
    )

class SchedulableItemsGetter(object):
    item_type = None
    filter_states = []
    group_filter = False
    domain_class = None
    
    def __init__(self, context, item_type, filter_states=None, 
        group_filter=True, item_filters={}
    ):
        self.context = context
        self.item_type = item_type
        self.filter_states = filter_states or get_workflow(
            item_type
        ).get_state_ids(
            tagged=["tobescheduled"]
        )
        self.group_filter = group_filter
        try:
            self.domain_class = domain.DOMAIN_CLASSES[item_type]
        except AttributeError:
            raise AttributeError("Domain Class mapping has no such type %s" %
                item_type
            )
        self.item_filters = item_filters
    
    @property
    def group_id(self):
        parent=self.context
        while parent is not None:
            group_id = getattr(parent, "group_id", None)
            if group_id:
                return group_id
            else:
                parent = parent.__parent__
        raise ValueError("Unable to determine group.")
    
    def query(self):
        items_query = Session().query(self.domain_class).filter(
            self.domain_class.status.in_(self.filter_states)
        )
        if len(self.item_filters):
            for (key, value) in self.item_filters.iteritems():
                column = getattr(self.domain_class, key)
                #!+SCHEDULING(mb, Jan-2011) extend query spec to include sql filters
                if "date" in key:
                    if "|" in value:
                        start, end = value.split("|")
                        if start and end:
                            expression = sql.between(column, start, end)
                        elif start:
                            expression = (column>=value)
                        elif end:
                            expression= (column<=value)
                        else:
                            continue
                    else:
                        expression = (column==value)
                else:
                    expression = (column==value)
                items_query = items_query.filter(expression)
        if self.group_filter:
            if hasattr(self.domain_class, "group_id") and self.group_id:
                items_query = items_query.filter(
                    self.domain_class.group_id==self.group_id
                )
        return tuple(items_query)


    def as_json(self):
        date_formatter = date.getLocaleFormatter(common.get_request(), "date",
            "medium"
        )
        items_json = dict(
            items = [
                dict(
                    item_type = self.item_type,
                    item_id = orm.object_mapper(item).primary_key_from_instance(
                        item
                    )[0],
                    item_title = IDCDescriptiveProperties(item).title,
                    status = IWorkflow(item).get_state(item.status).title,
                    status_date = ( date_formatter.format(item.submission_date) 
                        if hasattr(item, "submission_date") else None
                    ),
                    registry_number = ( item.registry_number if
                        hasattr(item, "registry_number") else None
                    ),
                    item_mover = ( IDCDescriptiveProperties(item.owner).title if
                        hasattr(item, "owner") else None
                    ),
                    item_uri = IDCDescriptiveProperties(item).uri
                )
                for item in self.query()
            ]
        )
        return json.dumps(items_json)


class ExpandedSitting(object):
    """Contains list of sittings and groups of documents in the schedule
    """
    sitting = None
    grouped = {}
    
    def __init__(self, sitting=None):
        self.sitting = sitting
        if len(self.grouped.keys())==0:
            self.groupItems()
    
    def __getattr__(self, name):
        """ Attribute lookup fallback - Sitting should have access to item
        """
        if name in self.grouped.keys():
            return self.grouped.get(name)
        if hasattr(self.sitting, name):
            return getattr(self.sitting, name)
        dc_adapter = IDCDescriptiveProperties(self.sitting)
        if hasattr(dc_adapter, name):
            return getattr(dc_adapter, name)
        else:
            log.error("Sitting Context %s has no such attribute: %s",
                self.sitting.__str__(), name
            )
            return []
    
    def groupItems(self):
        for scheduled in self.sitting.item_schedule:
            item_group = "%ss" % scheduled.item.type
            if item_group not in self.grouped.keys():
                log.debug("[Reports] Setting up expanded listing with:: %s", 
                    item_group
                )
                self.grouped[item_group] = []
            self.grouped[item_group].append(scheduled.item)
