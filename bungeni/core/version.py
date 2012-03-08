# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Versioning of Domain Objects

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.version")

from zope import interface
from zope import event
from zope.lifecycleevent import ObjectCreatedEvent
from zope.security import canAccess, canWrite
from zope.security.proxy import removeSecurityProxy
from zope.security.interfaces import Unauthorized, ForbiddenAttribute

from sqlalchemy import orm
from bungeni.alchemist import container
from bungeni.alchemist import Session

from i18n import _

from bungeni.models import domain
from bungeni.core import interfaces


def get_mapped_table(kls):
    return orm.class_mapper(kls).mapped_table


class Versioned(container.PartialContainer):
    interface.implements(interfaces.IVersioned)
    
    def _copyFields(self, source, dest):
        table = get_mapped_table(source.__class__)
        for column in table.columns:
            if column.primary_key:
                continue
            value = getattr(source, column.name)
            setattr(dest, column.name, value)

    def _copy_writeableFields(self, source, dest, context):
        """Only revert the fields which the user has edit rights for
        """
        table = get_mapped_table(source.__class__)
        for column in table.columns:
            if column.primary_key:
                continue
            value = getattr(source, column.name)
            try: # !+?
                if canWrite(context, column.name):
                    setattr(dest, column.name, value)
            except ForbiddenAttribute:
                setattr(dest, column.name, value)
    
    def has_write_permission(self, context):
        """check that  the user has the rights to edit 
             the object, if not we assume he has no rights 
             to make a version
             assumption is here that if he has the rights on any of the fields
             he may create a version.
        """
        table = get_mapped_table(context.__class__)
        for column in table.columns:
            if canWrite(context, column.name):
                return True
        else:
            return False

    def create(self, message, manual=False):
        """Store the existing state of the adapted context as a new version.
        """
        context = self.__parent__
        if manual:
            if not self.has_write_permission(context):
                raise Unauthorized
        version = self.domain_model()
        trusted = removeSecurityProxy(context)
        
        # set values on version from context
        self._copyFields(trusted, version)
        
        # content domain ids are typically not in the interfaces
        # manually inspect and look for one, by hand to save on the new version
        mapper = orm.object_mapper(trusted)
        version.content_id = mapper.primary_key_from_instance(trusted)[0]
        version.manual = manual
        
        # we rely on change handler to attach the change object to the version
        event.notify(
            interfaces.VersionCreated(context, self, version, message)) # !+?
        
        session = Session()
        session.add(version)
        
        version.context = context
        event.notify(ObjectCreatedEvent(version))
        
        return version
    
    def revert(self, version, message):
        """Revert the current state of the adapted object to the
        values specified in version, and create a new version with
        reverted state.
        """
        context = self.__parent__
        if not self.has_write_permission(context):
            raise Unauthorized
        trusted = removeSecurityProxy(context)
        ctx_class = trusted.__class__
        wf_status = getattr(context, "status")
        
        self._copy_writeableFields(version, trusted, context)
        
        if wf_status:
            context.status = wf_status
        
        msg = _(u"Reverted to previous version $version",
                mapping={"version": version.version_id})
        
        event.notify(
            interfaces.VersionReverted(context, self, version, msg))
        
        self.create(message=msg)


def ContextVersioned(context):
    """Context versions factory.
    """
    content_version_class = getattr(domain, 
        "%sVersion" % (context.__class__.__name__))
    versions = Versioned()
    versions._class = content_version_class
    trusted_ctx = removeSecurityProxy(context)
    mapper = orm.object_mapper(trusted_ctx)
    pk_value = mapper.primary_key_from_instance(trusted_ctx)[0]
    versions.setQueryModifier(
        getattr(content_version_class, "content_id") == pk_value)
    versions.__parent__ = context
    versions.__name__ = "versions"
    return versions

