# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Versioning of Domain Objects

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.version")

from zope.security.proxy import removeSecurityProxy
from zope import event

from bungeni.alchemist import Session
import bungeni.models.interfaces
import bungeni.core.interfaces
from bungeni.models import domain
from bungeni.core import audit


def get_feature_interface(feature_name):
    return getattr(bungeni.models.interfaces,
        "IFeature%s" % feature_name.capitalize())


def version_tree(ob, root=False, reversion=False):
    """Create (if needed) a snapshot of the object graph starting at ob.
    
    Recursively visit all ob children, and:
        - check if they are cleanly versioned
        - version them if not (procedure="a"), set dirty True
        - version ob if necessary, and relate version of ob to children
        - return (version, dirty) -- dirty flag is also propagated upwards, and 
          when True the version returned is just newly created else it is the 
          latest previously-existing version found.
    
    root:bool -- a version of the root ob itself, even if cleanly vesrioned, 
        is always created. Plus, parameters for other sub-calls are affected
        by whether we are daling with root instance or not.
    
    reversion:bool -- whether this is a revert to a previous version or not, in 
        which case ob is the older version to revert to.
    
    --
    current root types: Doc (only Event...), Attachment 
    current child types: (only Event doc, that may not parent Events), Attachment
    """
    assert get_feature_interface("version").providedBy(ob), \
        "Not versionable! %s" % (ob) # !+reversion?
    
    # ob must be newly versioned if dirty, we always explicitly version root ob
    dirty = root or False
    
    child_obs = []
    child_versions = []
    # process children (determine via child-implicating features)
    if get_feature_interface("attachment").providedBy(ob):
        child_obs.extend(ob.attachments)
    #!+event-as-feature
    if hasattr(ob, "sa_events") and ob.sa_events:
        child_obs.extend(ob.sa_events)
    #!+signatory-as-feature
    #if hasattr(ob, "item_signatories") and ob.item_signatories:
    #   child_obs.extend(ob.item_signatories)
    for child in child_obs:
        child_dirty, child_version = version_tree(child)
        child_versions.append(child_version)
        dirty = dirty or child_dirty
    
    def changed_since_last_version(ob):
        """Does ob need to be freshly versioned?
        """
        try:
            # ordered by audit_id, newest first
            return ob.changes[0].action != "version"
            # !+what if a sub-child has been reversioned since last child version?
        except IndexError:
            return True
    
    dirty = dirty or changed_since_last_version(ob)
    if dirty:
        # create version if needed
        if reversion:
            auditor = audit.get_auditor(ob.audit_head)
        else:
            auditor = audit.get_auditor(ob)
        last_version = auditor.object_version(ob, root=root)
        session = Session()
        for cv in child_versions:
            # relate newly created ob last_version to child versions
            ct = domain.ChangeTree()
            ct.parent_id = last_version.audit_id
            ct.child_id = cv.audit_id
            session.add(ct)
    else:
        # retrieve newest version for ob
        last_version = ob.changes[0]
    
    return dirty, last_version

def _notify_version_created(ob, dirty, last_version):
    # sanity cheack !+ comparing with *is* fails
    assert last_version.head == ob 
    if dirty:
        # ok, a version was created, notify of new version creation
        version_created = bungeni.core.interfaces.VersionCreatedEvent(last_version)
        event.notify(version_created)

def create_version(ob):
    """Establish a new version of an object tree (with ob as the root).
    """
    dirty, last_version = version_tree(removeSecurityProxy(ob), root=True, reversion=False)
    _notify_version_created(ob, dirty, last_version)

def create_reversion(ob):
    """Revert to an older version an object tree (with ob as the root).
       ob is the older version to revert to.
    """
    dirty, last_version = version_tree(removeSecurityProxy(ob), root=True, reversion=True)
    _notify_version_created(ob, dirty, last_version)


''' !+OBSOLETE_VERSIONING
from zope import interface
from zope.lifecycleevent import ObjectCreatedEvent
from zope.security import canWrite
from zope.security.interfaces import Unauthorized, ForbiddenAttribute
from sqlalchemy import orm
from bungeni.alchemist import container
from bungeni.core import interfaces

class Versioned(container.PartialContainer):
    interface.implements(interfaces.IVersioned)
    
    def _copyFields(self, source, dest):
        table = domain.get_mapped_table(source.__class__)
        for column in table.columns:
            if column.primary_key:
                continue
            value = getattr(source, column.name)
            setattr(dest, column.name, value)

    def _copy_writeableFields(self, source, dest, context):
        """Only revert the fields which the user has edit rights for
        """
        table = domain.get_mapped_table(source.__class__)
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
        table = domain.get_mapped_table(context.__class__)
        for column in table.columns:
            if canWrite(context, column.name):
                return True
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
'''

