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
from bungeni.feature import feature
import bungeni.core.interfaces
from bungeni.models import domain
from bungeni.core import audit



VERSIONABLE_SUBTYPES_AS_FEATURES = (
    # feature_subtype_name, sa_container_attr_name
    ("attachment", "attachments"), # Doc
    ("event", "sa_events"), # Doc
    ("signatory", "sa_signatories"), # Doc
    ("group_assignment", "sa_group_assignments"), # Doc, Group !+not a group "optional feature"
    #("member", "group_members"), # Group !+not a group "optional feature"
)


def version_tree(ob, root=False, reversion=False):
    """Create (if needed) a snapshot of the object graph starting at ob.
    
    Recursively visit all ob children, and:
        - check if they are cleanly versioned
        - version them if not (procedure="a"), set dirty True
        - version ob if necessary, and relate version of ob to children
        - return (dirty, version) -- dirty flag is also propagated upwards, and 
          when True the version returned is just newly created else it is the 
          latest previously-existing version found.
    
    root:bool -- a version of the root ob itself, even if cleanly vesrioned, 
        is always created. Plus, parameters for other sub-calls are affected
        by whether we are daling with root instance or not.
    
    reversion:bool -- whether this is a revert to a previous version or not, in 
        which case ob is the older version to revert to.
    
    """
    assert feature.provides_feature(ob, "version"), "Not versionable! %s" % (ob) # !+reversion?
    
    # ob must be newly versioned if dirty, we always explicitly version root ob
    dirty = root or False
    
    # process children (determine via child-implicating features)
    child_obs = []
    child_versions = []
    
    for feature_subtype_name, sa_container_attr_name in VERSIONABLE_SUBTYPES_AS_FEATURES:
        if feature.get_feature_interface(feature_subtype_name).providedBy(ob):
            if feature.provides_feature(feature_subtype_name, "version"):
                child_obs.extend(getattr(ob, sa_container_attr_name))
    
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


