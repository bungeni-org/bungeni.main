# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Auditing of Changes for Domain Objects

$Id$
"""

from datetime import datetime
from types import StringTypes

from zope.security.proxy import removeSecurityProxy
from zope.security.management import getInteraction
from zope.publisher.interfaces import IRequest

from zope import lifecycleevent

from ore.workflow.interfaces import IWorkflowInfo
from ore.alchemist.interfaces import IRelationChange
from ore.alchemist import Session
from sqlalchemy import orm

from bungeni.models import schema, domain
from bungeni.core import interfaces, dc

from i18n import _ 

def getAuditableParent(obj):
    parent = obj.__parent__
    while parent:
        if  interfaces.IAuditable.providedBy(parent):
            return parent
        else:
            parent = getattr(parent, '__parent__', None)
 

def getAuditor( ob ):
    return globals().get('%sAuditor' %(ob.__class__.__name__))
    
def objectAdded( ob, event):
    auditor = getAuditor( ob )
    auditor.objectAdded( removeSecurityProxy(ob), event )
    
def objectModified( ob, event ):
    auditor = getAuditor( ob )
    if getattr( event, 'change_id', None):
        return
    auditor.objectModified( removeSecurityProxy(ob), event )
    
def objectDeleted( ob, event ):
    auditor = getAuditor( ob )
    auditor.objectDeleted( removeSecurityProxy(ob), event )

def objectStateChange( ob, event ):
    auditor = getAuditor( ob )
    change_id = auditor.objectStateChanged( removeSecurityProxy(ob), event )
    event.change_id = change_id
    
def objectNewVersion( ob, event ):
    auditor = getAuditor( ob )
    if not getattr( event, 'change_id', None):
        change_id = auditor.objectNewVersion( removeSecurityProxy(ob), event )
    else:
        change_id = event.change_id
    event.version.change_id = change_id

def objectRevertedVersion( ob, event ):
    # slightly obnoxious hand off between event handlers (objectnewV, objectrevertedV),
    # stuffing onto the event for value passing
    auditor = getAuditor( ob )
    change_id = auditor.objectRevertedVersion( removeSecurityProxy(ob), event )
    event.change_id = change_id
        
def objectAttachment( ob, event ):
    auditor = getAuditor( ob ) 
    auditor.objectAttachment( removeSecurityProxy(ob), event )

def objectContained( ob, event):
    auditor = getAuditor( ob ) 
    auditor.objectContained( removeSecurityProxy(ob), event )
    
class AuditorFactory( object ):

    def __init__( self, change_table, change_object ):
        self.change_table = change_table
        self.change_object = change_object

    def objectContained( self, object, event):
        self._objectChanged(event.cls, object, event.description )
        
    def objectAttachment( self, object, event):
        self._objectChanged(u'Files', object, event.description )
    

    def objectAdded( self, object, event ):
        return self._objectChanged(u'added', object )
    
    def objectModified( self, object, event ):
        attrset =[]
        for attr in event.descriptions:
            if lifecycleevent.IAttributes.providedBy( attr ):
                attrset.extend(
                    [ attr.interface[a].title for a in attr.attributes]
                    )
            elif IRelationChange.providedBy(attr):
                if attr.description:
                    attrset.append( attr.description )
        attrset.append(getattr(object, 'note', u""))
        str_attrset = []
        for a in attrset:
            if type(a) in StringTypes:
                str_attrset.append(a)
        description = u", ".join( str_attrset )
        return self._objectChanged(u'modified', object, description )
        
    def objectStateChanged( self, object, event):
        comment = event.comment
        if comment is None:
            comment =u""
        else:
            if hasattr(object, 'note') and len(comment)>1:
                object.note = comment
        wf = IWorkflowInfo(object)
        if hasattr(object, 'status_date'):
            object.status_date = datetime.now()
        if event.source:
            #get human readable titles for workflow state
            event_title = wf.workflow().workflow.states[event.source].title
        else:
            event_title = 'new'
        event_description={ 'source': event_title, 
                            'destination': wf.workflow().workflow.states[event.destination].title,
                            'transition': event.transition.title,
                            'comment': comment }
        
        description = (_(u"""%(transition)s : %(comment)s [ transition from %(source)s to %(destination)s ]""")
                      %event_description  )
        return self._objectChanged(u'workflow', object, description )
        
    def objectDeleted( self, object, event ):
        #return self._objectChanged(u'deleted', object )
        return

    def objectNewVersion( self, object, event ):
        return self._objectChanged(u"new-version", object, description=event.message )

    def objectRevertedVersion( self, object, event ):
        return self._objectChanged(u'reverted-version', object, description=event.message )
        
    def _objectChanged( self, change_kind, object, description=u'' ):
        oid, otype = self._getKey( object )
        user_id = self._getCurrentUserId()
        session = Session()
        change = self.change_object()
        change.action = change_kind
        change.date = datetime.now()
        change.user_id = user_id
        change.description = description
        change.content_type = otype
        change.origin = object
        session.add(change)
        session.flush()
        return change.change_id
        
        
    def _getKey( self, ob ):
        mapper = orm.object_mapper( ob )
        primary_key = mapper.primary_key_from_instance( ob )[0]
        return primary_key, unicode( ob.__class__.__name__ )

    def _getCurrentUserId( self ):
        interaction = getInteraction()
        for participation in interaction.participations:
            if IRequest.providedBy(participation):
                return participation.principal.id
        raise RuntimeError(_("No IRequest in interaction"))

BillAuditor = AuditorFactory( schema.bill_changes, domain.BillChange )
MotionAuditor = AuditorFactory( schema.motion_changes, domain.MotionChange )
QuestionAuditor = AuditorFactory( schema.question_changes, domain.QuestionChange )
AgendaItemAuditor =  AuditorFactory( schema.agenda_item_changes, domain.AgendaItemChange )
TabledDocumentAuditor =  AuditorFactory( schema.tabled_document_changes, domain.TabledDocumentChange )
AttachedFileAuditor =  AuditorFactory( schema.attached_file_changes, domain.AttachedFileChange )

