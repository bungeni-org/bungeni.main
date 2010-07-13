# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Auditing of Changes for Domain Objects

$Id$
"""

from datetime import datetime
from types import StringTypes

from zope.security.proxy import removeSecurityProxy

from zope import lifecycleevent

from ore.workflow.interfaces import IWorkflowInfo
from ore.alchemist.interfaces import IRelationChange
from ore.alchemist import Session
from sqlalchemy import orm

from bungeni.models import schema, domain
from bungeni.models.utils import get_principal_id
from bungeni.core import interfaces

from i18n import _ 


# public handlers

def objectAdded(ob, event):
    auditor = getAuditor(ob)
    auditor.objectAdded(removeSecurityProxy(ob), event)

def objectModified(ob, event):
    auditor = getAuditor(ob)
    if getattr(event, "change_id", None):
        return
    auditor.objectModified(removeSecurityProxy(ob), event)

def objectDeleted(ob, event):
    auditor = getAuditor(ob)
    auditor.objectDeleted(removeSecurityProxy(ob), event)

def objectStateChange(ob, event):
    auditor = getAuditor(ob)
    change_id = auditor.objectStateChanged(removeSecurityProxy(ob), event)
    event.change_id = change_id

def objectNewVersion(ob, event):
    auditor = getAuditor(ob)
    if not getattr(event, "change_id", None):
        change_id = auditor.objectNewVersion(removeSecurityProxy(ob), event)
    else:
        change_id = event.change_id
    event.version.change_id = change_id

def objectRevertedVersion(ob, event):
    # slightly obnoxious hand off between event handlers (objectnewV, objectrevertedV),
    # stuffing onto the event for value passing
    auditor = getAuditor(ob)
    change_id = auditor.objectRevertedVersion(removeSecurityProxy(ob), event)
    event.change_id = change_id

def objectAttachment(ob, event):
    auditor = getAuditor(ob) 
    auditor.objectAttachment(removeSecurityProxy(ob), event)

def objectContained(ob, event):
    auditor = getAuditor(ob) 
    auditor.objectContained(removeSecurityProxy(ob), event)


# internal auditing utilities

def getAuditableParent(obj):
    parent = obj.__parent__
    while parent:
        if  interfaces.IAuditable.providedBy(parent):
            return parent
        else:
            parent = getattr(parent, "__parent__", None)

def getAuditor(ob):
    return globals().get("%sAuditor" %(ob.__class__.__name__))


class AuditorFactory(object):
    
    def __init__(self, change_table, change_object):
        self.change_table = change_table
        self.change_object = change_object
    
    def objectContained(self, object, event):
        self._objectChanged(event.cls, object, event.description)
    
    def objectAttachment(self, object, event):
        self._objectChanged("attachment", object, event.description)
    
    def objectAdded(self, object, event):
        return self._objectChanged("added", object)
    
    def objectModified(self, object, event):
        attrset =[]
        for attr in event.descriptions:
            if lifecycleevent.IAttributes.providedBy(attr):
                attrset.extend(
                    [ attr.interface[a].title for a in attr.attributes]
                   )
            elif IRelationChange.providedBy(attr):
                if attr.description:
                    attrset.append(attr.description)
        attrset.append(getattr(object, "note", u""))
        str_attrset = []
        for a in attrset:
            if type(a) in StringTypes:
                str_attrset.append(a)
        description = u", ".join(str_attrset)
        return self._objectChanged("modified", object, description)
        
    def objectStateChanged(self, object, event):
        """
        object: origin domain workflowed object 
        event: ore.workflow.workflow.WorkflowTransitionEvent
            .object # origin domain workflowed object 
            .source # souirce state
            .destination # destination state
            .transition # transition
            .comment #
        """
        comment = event.comment
        if comment is None:
            comment = u""
        else:
            if hasattr(object, "note") and len(comment)>1:
                object.note = comment
        if hasattr(object, "status_date"):
            object.status_date = datetime.now()
        # as base description, record a human readable title of workflow state
        wf = IWorkflowInfo(object).workflow().workflow
        description = wf.states[event.destination].title
        # extras, that may be used e.g. to elaborate description at runtime
        notes = {
            "source": event.source, 
            "destination": event.destination,
            "transition": event.transition.transition_id,
            "comment": comment
        }
        return self._objectChanged("workflow", object, description, notes)
        # description field becomes templates string?
        # notes field becomes interpolation data
        
    def objectDeleted(self, object, event):
        #return self._objectChanged("deleted", object)
        return

    def objectNewVersion(self, object, event):
        """
        object: origin domain workflowed object 
        event: bungeni.core.interfaces.VersionCreated
            .object # origin domain workflowed object 
            .message # title of the version object
            .version # bungeni.models.domain.*Version
            .versioned # bungeni.core.version.Versioned
        """
        # At this point, the new version instance (at event.version) is not yet 
        # persisted to the db (or added to the session!) so its version_id is
        # still None. We force the issue, by adding it to session and flushing.
        session = Session()
        session.add(event.version)
        session.flush()
        # as base description, record a the version object's title
        description = event.message
        # extras, that may be used e.g. to elaborate description at runtime        
        notes = {
            "version_id": event.version.version_id
        }
        return self._objectChanged("new-version", object, description, notes)
        #vkls = getattr(domain, "%sVersion" % (object.__class__.__name__))
        #versions = session.query(vkls
        #            ).filter(vkls.content_id==event.version.content_id
        #            ).order_by(vkls.status_date).all()

    def objectRevertedVersion(self, object, event):
        return self._objectChanged("reverted-version", object, description=event.message)
        
    def _objectChanged(self, change_kind, object, description="", notes=None):
        """
        description: 
            this is a non-localized string as base description of the log item.
             offers a (building block) for 
            the description of this log item. 
            UI components may use this in any of the following ways:
            - AS IS, optionally localized
            - as a building block for an elaborated description e.g. for 
              generating descriptions that are hyperlinks to an event or 
              version objects
            - ignore it entirely, and generate a custom descrition via other
              means e.g. from the "notes" extras dict.
        
        notes:
            a python dict, containing "extra" information about the log item;
            the entries in this dict are a function of the "change_kind".
            It is serialized for storing in the db.
            For specific examples, see:
                "workflow": self.objectStateChanged()
                "new-version": self.objectNewVersion()
        """
        oid, otype = self._getKey(object)
        user_id = get_principal_id()
        assert user_id is not None, _("No IRequest in interaction")
        session = Session()
        change = self.change_object()
        change.action = change_kind
        change.date = datetime.now()
        change.user_id = user_id
        change.description = description
        if notes:
            change.notes = repr(notes)
        else:
            change.notes = None
        change.content_type = otype
        change.origin = object
        session.add(change)
        session.flush()
        return change.change_id
        
    def _getKey(self, ob):
        mapper = orm.object_mapper(ob)
        primary_key = mapper.primary_key_from_instance(ob)[0]
        return primary_key, unicode(ob.__class__.__name__)


# dedicated auditor instances

BillAuditor = AuditorFactory(
                schema.bill_changes, domain.BillChange)
MotionAuditor = AuditorFactory(
                schema.motion_changes, domain.MotionChange)
QuestionAuditor = AuditorFactory(
                schema.question_changes, domain.QuestionChange)
AgendaItemAuditor =  AuditorFactory(
                schema.agenda_item_changes, domain.AgendaItemChange)
TabledDocumentAuditor =  AuditorFactory(
                schema.tabled_document_changes, domain.TabledDocumentChange)
AttachedFileAuditor =  AuditorFactory(
                schema.attached_file_changes, domain.AttachedFileChange)

#

