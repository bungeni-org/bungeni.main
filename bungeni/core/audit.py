# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Auditing of Changes for Domain Objects

$Id$


Auditing implementation rules to be aware of and comply with:

- Any change on an instance is audited ONLY on that instance i.e. for when 
instance is "contained" in some parent/head object, and changes on it must 
not be logged also as changes on the parent.

- Only the change action keywords should be used (verbs in present tense?):
    add
    modify
    workflow
    remove
    version
    reversion

- Each single "logical" change should only generate a single change record 
e.g. a workflow change implies a modify change but should only be logged once 
and using the "logical origin" of the change to determine what action verb to 
use, that in this example would therefore be "workflow". !+TBD

- !+ Distinguish between automatic and manual version actions?


"""
log = __import__("logging").getLogger("bungeni.core.audit")


__all__ = ["get_auditor", "set_auditor"]


from datetime import datetime
from types import StringTypes

from zope.lifecycleevent import IObjectModifiedEvent, IObjectCreatedEvent, \
    IObjectRemovedEvent
    
from zope.annotation.interfaces import IAnnotations
from zope.security.proxy import removeSecurityProxy
from zope import lifecycleevent

from sqlalchemy import orm
from bungeni.alchemist import Session
from bungeni.alchemist.interfaces import IRelationChange

from bungeni.models.utils import get_db_user_id
from bungeni.models.interfaces import IAuditable
from bungeni.models import schema
from bungeni.models import domain
from bungeni.core.workflow.interfaces import IWorkflow, IWorkflowTransitionEvent
from bungeni.core.interfaces import IVersionCreated, IVersionReverted
from bungeni.ui.utils import common
from bungeni.utils import register

from bungeni.core.i18n import _


def _trace_audit_handler(ah):
    """Simple decorator to log.debug each call to (specifically) an 
    audit handler. 
    """
    def _ah(ob, event):
        log.debug("AUDITING %s(%s, %s) originator=%s" % (
            ah.__name__, ob, event, getattr(event, "originator", None)))
        ah(ob, event)
    return _ah


# change handlers

@register.handler(adapts=(IAuditable, IObjectCreatedEvent))
@_trace_audit_handler
def _object_add(ob, event):
    auditor = get_auditor(ob)
    auditor.object_add(removeSecurityProxy(ob), event)

@register.handler(adapts=(IAuditable, IObjectModifiedEvent))
@_trace_audit_handler
def _object_modify(ob, event):
    # no audit ObjectModifiedEvent if originates from a WorkflowTransitionEvent
    orginator = getattr(event, "originator", None)
    if IWorkflowTransitionEvent.providedBy(orginator):
        log.debug("NOT AUDITING event [%s] as it originates from [%s]" % (
            event, orginator))
        return
    auditor = get_auditor(ob)
    auditor.object_modify(removeSecurityProxy(ob), event)

@register.handler(adapts=(IAuditable, IObjectRemovedEvent))
@_trace_audit_handler
def _object_remove(ob, event):
    auditor = get_auditor(ob)
    auditor.object_remove(removeSecurityProxy(ob), event)

@register.handler(adapts=(IAuditable, IWorkflowTransitionEvent))
@_trace_audit_handler
def _object_workflow(ob, event):
    auditor = get_auditor(ob)
    change_id = auditor.object_workflow(removeSecurityProxy(ob), event)
    event.change_id = change_id


@register.handler(adapts=(IAuditable, IVersionCreated))
@_trace_audit_handler
def _object_version(ob, event):
    """When an auditable object is versioned, we audit creation of new version.
    
    As version objects are objects that never change, no audit trail on them 
    is needed. But a change record on the head object is needed to provide the 
    following valuable information:
    
    - The "owner" of the object being versioned is categorically also always 
    the owner of any version made of it, irresepctive of who actually makes it. 
    The "user" who authored the change is recorded in the change record.
    - Possibly to specify an effective date (date_active)
    - Possibility to add a description of the change (as well as notes/extras).
    """
    auditor = get_auditor(ob)
    change_id = auditor.object_version(removeSecurityProxy(ob), event)
    event.version.change_id = change_id

@register.handler(adapts=(IAuditable, IVersionReverted))
@_trace_audit_handler
def _object_reversion(ob, event):
    auditor = get_auditor(ob)
    change_id = auditor.object_reversion(removeSecurityProxy(ob), event)
    event.change_id = change_id


# internal utilities

def _get_auditable_ancestor(obj):
    parent = obj.__parent__
    while parent:
        if  IAuditable.providedBy(parent):
            return parent
        else:
            parent = getattr(parent, "__parent__", None)


class _AuditorFactory(object):
    
    def __init__(self, change_table, change_class):
        self.change_table = change_table
        self.change_class = change_class
    
    # handlers, return the change_id
    
    def object_add(self, ob, event):
        return self._object_changed("add", ob)
    
    def object_modify(self, ob, event):
        attrset = []
        for attr in event.descriptions:
            if lifecycleevent.IAttributes.providedBy(attr):
                attrset.extend(
                    [ attr.interface[a].title for a in attr.attributes ]
                )
            elif IRelationChange.providedBy(attr):
                if attr.description:
                    attrset.append(attr.description)
        attrset.append(getattr(ob, "note", ""))
        str_attrset = []
        for a in attrset:
            if type(a) in StringTypes:
                str_attrset.append(a)
        description = u", ".join(str_attrset)
        change_data = self._get_change_data()
        if change_data["note"]:
            extras = {"comment": change_data["note"]}
        else:
            extras = None
        return self._object_changed("modify", ob, 
                        description=description,
                        extras=extras,
                        date_active=change_data["date_active"])
    
    def object_remove(self, ob, event):
        # !+AUDIT_REMOVE(mr, feb-2011) if this is a real delete (of a record 
        # from the db) then there is really no sense in auditing it at all in 
        # the first place (really deleting an item should also mean deleting 
        # what is owned by it e.g. its change records). [Plus, trying to audit
        # such a deletion gives a sqlalchemy.exc.InvalidRequestError, 
        # "Instance ... has been deleted".
        #
        # If this is a semantic "delete" e.g. to mark the item as obsolete, 
        # then it would be desireable to audit it as any other change action.
        #return self._object_changed("remove", ob)
        log.warn("!+AUDIT_REMOVE not auditing deletion of [%s]" % (ob))
    
    def object_workflow(self, ob, event):
        """
        ob: origin domain workflowed object 
        event: bungeni.core.workflow.states.WorkflowTransitionEvent
            .object # origin domain workflowed object 
            .source # source state
            .destination # destination state
            .transition # transition
            .comment #
        """
        change_data = self._get_change_data()
        # if note, attach it on object (if object supports such an attribute)
        if change_data["note"]:
            if hasattr(ob, "note"):
                ob.note = change_data["note"]
        # update object's workflow status date (if supported by object)
        if hasattr(ob, "status_date"):
            ob.status_date = change_data["date_active"] or datetime.now()
        # as a "base" description, use human readable workflow state title
        wf = IWorkflow(ob) # !+ adapters.get_workflow(ob)
        description = wf.get_state(event.destination).title # misc.get_wf_state
        # !+description is not being used by auditlog/timline views
        # extras, that may be used e.g. to elaborate description at runtime
        extras = {
            "source": event.source, 
            "destination": event.destination,
            "transition": event.transition.id,
            "comment": change_data["note"]
        }
        return self._object_changed("workflow", ob, 
                        description=description,
                        extras=extras,
                        date_active=change_data["date_active"])
        # description field is a "building block" for a UI description;
        # extras/notes field becomes interpolation data
    
    def object_version(self, ob, event):
        """
        ob: origin domain workflowed object 
        event: bungeni.core.interfaces.VersionCreated
            .object # origin domain workflowed object 
            .message # title of the version object
            .version # bungeni.models.domain.*Version
            .versioned # bungeni.core.version.Versioned
        """
        session = Session()
        session.add(event.version)

        # !+version_id At this point, new version instance (at event.version) is not yet 
        # persisted to the db (or added to the session!) so its version_id is
        # still None. We force the issue, by adding it to session and flushing.
        session.flush()
        # as base description, record a the version object's title
        description = event.message
        # extras, that may be used e.g. to elaborate description at runtime        
        extras = {
            "version_id": event.version.version_id # !+version_id
        }
        return self._object_changed("version", ob, description, extras)
        #vkls = getattr(domain, "%sVersion" % (ob.__class__.__name__))
        #versions = session.query(vkls
        #            ).filter(vkls.content_id==event.version.content_id
        #            ).order_by(vkls.status_date).all()
    
    def object_reversion(self, ob, event):
        return self._object_changed("reversion", ob,
            description=event.message)
    
    #
    
    def _object_changed(self, action, ob, 
            description="", extras=None, date_active=None):
        """
        description: 
            this is a non-localized string as base description of the log item,
            offers a (building block) for the description of this log item. 
            UI components may use this in any of the following ways:
            - AS IS, optionally localized
            - as a building block for an elaborated description e.g. for 
              generating descriptions that are hyperlinks to an event or 
              version objects
            - ignore it entirely, and generate a custom description via other
              means e.g. from the "notes" extras dict.
        
        extras: !+CHANGE_EXTRAS(mr, dec-2010)
            a python dict, containing "extra" information about the log item, 
            with the "key/value" entries depending on the change "action"; 

            Specific examples, for actions: 
                workflow: self.object_workflow()
                    source
                    destination
                    transition
                    comment
                version: self.object_version()
                    version_id
                modify: self.object_modify()
                    comment
            
            For now, this dict is serialized (using repr(), values are assumed 
            to be simple strings or numbers) as the value of the notes column, 
            for storing in the db--but if and when the big picture of these 
            extra keys is understood clearly then the changes table may be 
            remodeled with dedicated table columns.
        
        date_active:
            the UI for some changes allow the user to manually set the 
            date_active -- this is what should be used as the *effective* date 
            i.e. the date to be used for all intents and purposes other than 
            for data auditing. When not user-modified, the value should be equal 
            to date_audit. 
        """
        domain.assert_valid_change_action(action)
        oid, otype = self._getKey(ob)
        user_id = get_db_user_id()
        assert user_id is not None, "Audit error. No user logged in."
        session = Session()
        change = self.change_class()
        change.action = action
        change.date_audit = datetime.now()
        if date_active:
            change.date_active = date_active
        else:
            change.date_active = change.date_audit
        change.user_id = user_id
        change.description = description
        change.extras = extras
        change.content_type = otype
        change.head = ob # attach change to parent object
        change.status = ob.status # remember parent's status at time of change
        # !+SUBITEM_CHANGES_PERMISSIONS(mr, jan-2012) permission on change 
        # records for something like item[@draft]->file[@attached]->fileversion 
        # need to remember also the root item's state, else when item later 
        # becomes visible to clerk and others, the file itself will also become 
        # visible to the clerk (CORRECT) but so will ALL changes on the file 
        # while that file itself was @attached (WRONG!). May best be addressed
        # when change persistence is reworked along with single document table.
        session.add(change)
        session.flush()
        log.debug("AUDITED [%s] %s" % (action, change.__dict__))
        return change.change_id
    
    #
    
    def _getKey(self, ob):
        mapper = orm.object_mapper(ob)
        primary_key = mapper.primary_key_from_instance(ob)[0]
        return primary_key, unicode(ob.__class__.__name__)

    def _get_change_data(self):
        """If request defines change_data, use it, else return a dummy dict.
        """
        try:
            cd = IAnnotations(common.get_request()).get("change_data")
            assert cd is not None, "change_data dict is None."
        except (TypeError, AssertionError):
            # Could not adapt... under testing, the "request" is a 
            # participation that has no IAnnotations.
            cd = {}
        cd.setdefault("note", cd.get("note", ""))
        cd.setdefault("date_active", cd.get("date_active", None))
        return cd


# module-level dedicated auditor singleton instance per auditable class

def get_auditor(ob):
    """Get the module-level dedicated auditor singleton instance for the 
    auditable ob.__class__ -- raise KeyError if no such auditor singleton.
    """
    return globals()["%sAuditor" % (ob.__class__.__name__)]

def set_auditor(kls):
    """Set the module-level dedicated auditor singleton instance for the 
    auditable kls.
    """
    name = kls.__name__
    auditor_name = "%sAuditor" % (name)
    log.debug("Setting AUDITOR %s [for type %s]" % (auditor_name, name))
    change_kls = getattr(domain, "%sChange" % (name))
    change_tbl = getattr(schema, "%s_changes" % (schema.un_camel(name)))
    globals()[auditor_name] = _AuditorFactory(change_tbl, change_kls)

for kls in domain.CUSTOM_DECORATED["auditable"]:
    set_auditor(kls)
    
#

