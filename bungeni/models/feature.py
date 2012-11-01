# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""The Bungeni Application - Feature handling for domain models

Features (as per a deployment's configuration) - decorators for domain types
to support a "feature", to collect in one place all that is needed for the 
domain type to support that "feature".
 
The quality of a domain type to support a specific feature is externalized 
to localization and its implementation must thus be completely isolated, 
depending only on that one declaration.

$Id$
"""
log = __import__("logging").getLogger("bungeni.models.feature")


from zope import interface
import sqlalchemy as rdb
from sqlalchemy.orm import mapper, class_mapper, relation
from bungeni.alchemist.traversal import one2many
from bungeni.models import interfaces, domain, orm, schema
from bungeni.core import audit
from bungeni.utils import naming


# utils

def set_one2many_attr(kls, name, container_qualname, rel_attr):
    """Add an alchemist container attribute to kls. 
    These attributes are only catalysed (re-instrumented on kls) if defined 
    directly on kls i.e. are not inherited, must be defined on each class.
    """
    assert not kls.__dict__.has_key(name), \
        "type %s already has a %r attribute %r" % (kls, name, kls.__dict__[name])
    setattr(kls, name, one2many(name, container_qualname, rel_attr))
    assert kls.__dict__.has_key(name)


# domain models

def configurable_domain(kls, workflow):
    """Executed on adapters.load_workflow().
    """
    for feature in workflow.features:
        if feature.enabled:
            assert feature.name in kls.available_dynamic_features, \
                "Class [%s] does not allow dynamic feature [%s]" % (
                    kls, feature.name)
            feature_decorator = globals()["feature_%s" % (feature.name)]
            kls = feature_decorator(kls, **feature.params)
    return kls

def feature_audit(kls, **params):
    """Decorator for domain types to support "audit" feature.
    """
    interface.classImplements(kls, interfaces.IFeatureAudit)
    # If a domain class is explicitly defined, then it is assumed that all 
    # necessary setup is also taken care of. Typically, only the sub-classes
    # of an archetype (mapped to a same table) need dynamic creation/setup.
    def audit_cls_exists_for(auditable_cls):
        audit_cls_name = "%sAudit" % (auditable_cls.__name__)
        return bool(getattr(domain, audit_cls_name, None))
    if not audit_cls_exists_for(kls):
        # define {kls}Audit class
        feature_audit.CREATED_AUDIT_CLASS_FOR.add(kls)
        def base_audit_class(kls):
            """Identify what should be the BASE audit class for a 
            {kls}Audit class to inherit from, and return it.
            """
            # !+ may have a deeper inheritance
            # !+ other archetypes
            if kls is not domain.Doc and issubclass(kls, domain.Doc):
                return domain.DocAudit
            return domain.Audit
        audit_kls = base_audit_class(kls).auditFactory(kls)
        setattr(domain, audit_kls.__name__, audit_kls)
    # set_auditor
    audit.set_auditor(kls)
    return kls
# keep track of domain classes for which an audit class was created dynamically
feature_audit.CREATED_AUDIT_CLASS_FOR = set()

def feature_version(kls, **params):
    """Decorator for domain types to support "version" feature.
    """
    # domain.Version itself may NOT support versions
    assert not interfaces.IVersion.implementedBy(kls)
    # !+ @version requires @audit
    assert interfaces.IFeatureAudit.implementedBy(kls)
    interface.classImplements(kls, interfaces.IFeatureVersion)
    return kls

def feature_attachment(kls, **params):
    """Decorator for domain types to support "attachment" feature.
    !+ currently assumes that kls is versionable.
    """
    # !+ domain.Attachment is versionable
    # domain.Attachment itself may NOT support attachments
    assert not interfaces.IAttachment.implementedBy(kls)
    interface.classImplements(kls, interfaces.IFeatureAttachment)
    set_one2many_attr(kls, "files", 
        "bungeni.models.domain.AttachmentContainer", "head_id")
    return kls

def feature_event(kls, **params):
    """Decorator for domain types to support "event" feature.
    For Doc types (other than Event itself).
    """
    # domain.Event itself may NOT support events
    assert not interfaces.IEvent.implementedBy(kls)
    interface.classImplements(kls, interfaces.IFeatureEvent)
    set_one2many_attr(kls, "events", 
        "bungeni.models.domain.EventContainer", "head_id")
    return kls

def feature_signatory(kls, **params):
    """Decorator for domain types to support "signatory" feature.
    For Doc types.
    """
    from bungeni.models.signatories import createManagerFactory
    interface.classImplements(kls, interfaces.IFeatureSignatory)
    set_one2many_attr(kls, "signatories", 
        "bungeni.models.domain.SignatoryContainer", "head_id")
    createManagerFactory(kls, **params)
    return kls

def feature_schedule(kls, **params):
    """Decorator for domain types to support "schedule" feature.
    For Doc types, means support for being scheduled in a group sitting.
    """
    interface.classImplements(kls, interfaces.IFeatureSchedule)
    return kls

def feature_address(kls, **params):
    """Decorator for domain types to support "address" feature.
    For User and Group types, means support for possibility to have addresses.
    """
    interface.classImplements(kls, interfaces.IFeatureAddress)
    if issubclass(kls, domain.Group):
        set_one2many_attr(kls, "addresses",
            "bungeni.models.domain.GroupAddressContainer", "group_id")
    elif issubclass(kls, domain.User):
        set_one2many_attr(kls, "addresses",
            "bungeni.models.domain.UserAddressContainer", "user_id")
    return kls

def feature_workspace(kls):
    """Decorator for domain types that support "workspace" feature.
    """
    interface.classImplements(kls, interfaces.IFeatureWorkspace)
    return kls

def feature_notification(kls):
    """Decorator for domain types to support "notification" feature.
    """
    interface.classImplements(kls, interfaces.IFeatureNotification)
    return kls

def feature_download(kls):
    """Decorator for domain types that support downloading as 
    pdf/odt/rss/akomanoto
    """
    interface.classImplements(kls, interfaces.IFeatureDownload)
    return kls

def feature_user_assignment(kls, **params):
    """Decorator for domain types that support "user_assignment" feature.
    """
    interface.classImplements(kls, interfaces.IFeatureUserAssignment)
    return kls

def feature_group_assignment(kls, **params):
    """Decorator for domain types that support "group_assignment" feature.
    """
    interface.classImplements(kls, interfaces.IFeatureGroupAssignment)
    set_one2many_attr(kls, "group_assignments",
        "bungeni.models.domain.GroupDocumentAssignmentContainer", "doc_id")
    return kls


# mappings

def configurable_mappings(kls):
    """Configuration mappings for declarative-model types.
    """
    name = kls.__name__
    orm.mapper_add_relation_vertical_properties(kls)
    
    # auditable, determine properties, map audit class/table
    if interfaces.IFeatureAudit.implementedBy(kls):
        # either defined manually or created dynamically in domain.feature_audit()
        audit_kls = getattr(domain, "%sAudit" % (name))
        # assumption: audit_kls only uses single inheritance (at least for 
        # those created dynamically in feature_audit())
        base_audit_kls = audit_kls.__bases__[0] 
        assert issubclass(base_audit_kls, domain.Audit), \
            "Audit class %s is not a proper subclass of %s" % (
                audit_kls, domain.Audit)
        # mapper for the audit_cls for this kls, if it was created dynamically
        if kls in feature_audit.CREATED_AUDIT_CLASS_FOR:
            mapper(audit_kls,
                inherits=base_audit_kls,
                polymorphic_identity=naming.polymorphic_identity(kls)
            )
        # propagate any extended attributes on head kls also to its audit_kls
        for vp_name, vp_type in kls.extended_properties:
            orm.mapper_add_relation_vertical_property(audit_kls, vp_name, vp_type)
        # !+NOTE: capi.get_type_info(kls).descriptor_model is still None
    
    # add any properties to the head kls itself
    def mapper_add_configurable_properties(kls):
        kls_mapper = class_mapper(kls)
        
        def configurable_properties(kls, mapper_properties):
            """Add properties, as per configured features for a domain type.
            """
            
            # auditable
            if interfaces.IFeatureAudit.implementedBy(kls):
                # kls.changes <-> change.audit.audit_head=doc:
                # doc[@TYPE] <-- TYPE_audit <-> audit <-> change
                
                # get head table for kls, and its audit table.
                tbl = kls_mapper.mapped_table
                audit_tbl = getattr(schema, "%s_audit" % (tbl.name))
                
                # get tbl PK column
                assert len(tbl.primary_key) == 1
                # !+ASSUMPTION_SINGLE_COLUMN_PK(mr, may-2012)
                pk_col = [ c for c in tbl.primary_key ][0]
                mapper_properties["changes"] = relation(domain.Change,
                    primaryjoin=rdb.and_(
                        pk_col == audit_tbl.c.get(pk_col.name),
                    ),
                    secondary=audit_tbl,
                    secondaryjoin=rdb.and_(
                        audit_tbl.c.audit_id == schema.change.c.audit_id,
                    ),
                    lazy=True,
                    order_by=schema.change.c.audit_id.desc(),
                    cascade="all",
                    passive_deletes=False, # SA default
                )
            
            # versionable
            if interfaces.IFeatureVersion.implementedBy(kls):
                pass
            return mapper_properties
        
        for key, prop in configurable_properties(kls, {}).items():
            kls_mapper.add_property(key, prop)
    
    mapper_add_configurable_properties(kls)


