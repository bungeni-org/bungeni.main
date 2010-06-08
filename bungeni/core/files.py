import os
from datetime import date

from zope import interface, component
from zope.publisher.interfaces import NotFound
from zope.security.proxy import removeSecurityProxy
from zope.location.interfaces import ILocation
from zope.event import notify

from sqlalchemy import orm
from ore.alchemist import Session

from bungeni.core import interfaces
from bungeni.models import schema as dbschema
from bungeni.models import domain
from bungeni.core import audit, interfaces


def fileAddedSubscriber( ob, event ):
    """ when a file is added notify the object it is added to """
    ob = removeSecurityProxy( ob )
    obj = audit.getAuditableParent(ob)
    if obj:
        event.description = u"File %s %s added"  %  (
                ob.file_title,
                ob.file_name)
        notify(audit.objectAttachment(obj, event)) 

def fileEditedSubscriber( ob, event ):
    """ when a file is edited notify the parent object """
    ob = removeSecurityProxy( ob ) 
    obj = audit.getAuditableParent(ob)
    if obj:
        event.description = u"File %s %s edited"  % (
                ob.file_title,
                ob.file_name)
        notify(audit.objectAttachment(obj, event)) 

def objectNewVersion( ob, event ):
    """ when an object is versioned we copy the attachments 
    to the version"""
    if type(ob) == domain.AttachedFileVersion:
        return
    ob = removeSecurityProxy( ob ) 
    session = Session()
    session.merge(ob)
    session.flush()
    for attached_file in ob.head.attached_files:
        versions = interfaces.IVersioned(attached_file)
        version = versions.create('version created on object versioning: %s' % 
                getattr(ob.change,'description',''))
        version.file_version_id = ob.version_id
          
