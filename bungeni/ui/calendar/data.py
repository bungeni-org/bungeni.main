# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Data loader module for scheduler

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.calendar")

import json

from zope.security import checkPermission

from sqlalchemy import orm, sql

from bungeni.core.dc import IDCDescriptiveProperties
from bungeni.core.workflow.interfaces import IWorkflow
from bungeni.models.interfaces import ISchedulingManager, IScheduleText
from bungeni.models.utils import get_login_user_chamber
from bungeni.ui.utils import date, common
from bungeni.alchemist import Session
from bungeni.ui.i18n import _

from bungeni.capi import capi

#!+CACHING(mb, Feb-2013) cache this
def get_schedulable_states(type_key):
    ti = capi.get_type_info(type_key)
    manager = ISchedulingManager(ti.domain_model(), None)
    if manager:
        return ISchedulingManager(ti.domain_model()).schedulable_states
    else:
        return []

def get_scheduled_states(type_key):
    ti = capi.get_type_info(type_key)
    manager = ISchedulingManager(ti.domain_model(), None)
    if manager:
        return ISchedulingManager(ti.domain_model()).scheduled_states
    else:
        return []
def can_schedule(type_key, workflow):
    """Determine if the current user can schedule this document type.
    i.e. if they have the global workflow permission to schedule a document.
    """
    allow = False
    schedulable_states = get_schedulable_states(type_key)
    scheduled_states = get_scheduled_states(type_key)
    if schedulable_states and scheduled_states:
        transitions = workflow.get_transitions_from(schedulable_states[0])
        transitions = [ trans for trans in transitions if
            trans.destination == scheduled_states[0]
         ]
        if transitions:
            allow = checkPermission(
                transitions[0].permission, get_login_user_chamber())
    return allow

def get_schedulable_types(skip_permission_check=False):
    """Get types that may be scheduled. Limit to those that the current user
    has the right to transition to a scheduled state.
    You can skip the `limit to allowed types` behaviour by calling with 
    `skip_permission_check` set to `True`
    """
    schedulable_types = []
    for (key, ti) in capi.iter_type_info():
        if ti.workflow and ti.workflow.has_feature("schedule"):
            schedulable_types.append((key, ti))
    return dict([
        (type_key, dict(
            title=ti.descriptor_model.container_name,
            domain_model=ti.domain_model,
            workflow=ti.workflow,
            display_name=ti.descriptor_model.display_name
        ))
        for (type_key, ti) in schedulable_types
        if (skip_permission_check or can_schedule(type_key, ti.workflow))
    ])


def get_filter_config():
    """Get schedulable item filters"""
    return dict(
        [ (type_key, { 
                "label": _(u"choose status"),
                "menu": [ {
                        "text": ti.get("workflow").get_state(status).title,
                        "value": status 
                    }
                    for status in get_schedulable_states(type_key) ]
            })
            for (type_key, ti) in get_schedulable_types().iteritems() ]
    )

class ReportContext(object):
    def __init__(self, **kw):
        for key, value in kw.iteritems():
            setattr(self, key, value)

class SchedulableItemsGetter(object):
    item_type = None
    filter_states = []
    group_filter = True
    domain_class = None
    
    #!+(SCHEDULING, April-2012) There still needs to be a way to filter 
    # documents per group - at least for documents that may be created
    # in various group contexts e.g. AgendaItems, Headings e.t.c
    def __init__(self, context, type_key, filter_states=None, 
            group_filter=True, item_filters={}
        ):
        self.context = context
        self.item_type = type_key
        ti = capi.get_type_info(type_key)
        self.filter_states = get_schedulable_states(type_key)
        self.group_filter = group_filter
        try:
            self.domain_class = get_schedulable_types()[type_key].get(
                "domain_model")
        except KeyError:
            # !+try/except not necessary?
            try:
                self.domain_class = ti.domain_model
            except KeyError:
                raise KeyError("Unable to locate domain class for type %s" %
                    type_key
                )
        self.item_filters = item_filters
    
    @property
    def group_id(self):
        parent = self.context
        while parent is not None:
            group_id = getattr(parent, "group_id", None)
            if group_id:
                return group_id
            else:
                parent = parent.__parent__
        return None
    
    def query(self):
        items_query = Session().query(self.domain_class)
        if not IScheduleText.implementedBy(self.domain_class):
            items_query = items_query.filter(
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
                            expression = (column<=value)
                        else:
                            continue
                    else:
                        expression = (column==value)
                else:
                    expression = (column==value)
                items_query = items_query.filter(expression)
        if self.group_filter and not IScheduleText.implementedBy(self.domain_class):
            if hasattr(self.domain_class, "parliament_id") and self.group_id:
                items_query = items_query.filter(
                    self.domain_class.parliament_id==self.group_id
                )
            elif hasattr(self.domain_class, "group_id") and self.group_id:
                items_query = items_query.filter(
                    self.domain_class.group_id==self.group_id
                )
        return tuple(items_query)
    
    def as_json(self):
        is_text = IScheduleText.implementedBy(self.domain_class)
        date_formatter = date.getLocaleFormatter(common.get_request(), "date",
            "medium"
        )
        items = [
            dict(
                item_type = self.item_type,
                item_id = orm.object_mapper(item).primary_key_from_instance(
                    item
                )[0],
                item_title = IDCDescriptiveProperties(item).title,
                status = (IWorkflow(item).get_state(item.status).title 
                    if not is_text else None),
                status_date = ( date_formatter.format(item.submission_date) 
                    if (hasattr(item, "submission_date") and 
                        getattr(item, "submission_date")
                    )
                    else None
                ),
                registry_number = ( item.registry_number if
                    hasattr(item, "registry_number") else None
                ),
                item_mover = ( IDCDescriptiveProperties(item.owner).title if
                    hasattr(item, "owner") else None
                ),
                item_uri = "%s-%d" % (self.item_type,
                    orm.object_mapper(item).primary_key_from_instance(item)[0]
                )
            )
            for item in self.query()
        ]
        items = sorted(items, key=lambda item:item.get("status_date"),
            reverse=True
        )
        return json.dumps(dict(items=items))


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

