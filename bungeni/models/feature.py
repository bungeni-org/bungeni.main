# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""The Bungeni Application - Feature handling for domain models

Decorator utilities for a domain types to support a "feature" (as per a 
deployment's configuration); to collect in one place all that is needed for 
the domain type to support that "feature".
 
The quality of a domain type to support a specific feature is externalized 
to localization and its implementation must thus be completely isolated, 
depending only on that one declaration.

$Id$
"""
log = __import__("logging").getLogger("bungeni.models.feature")


from zope import interface
from zope.component import getGlobalSiteManager
import sqlalchemy as sa
from sqlalchemy.orm import mapper, class_mapper, relation
from bungeni.alchemist.catalyst import MODEL_MODULE
from bungeni.alchemist.model import (
    add_container_property_to_model,
    mapper_add_relation_vertical_property
)
from bungeni.alchemist import utils
from bungeni.models import interfaces, domain, orm, schema
from bungeni.core import audit
from bungeni.utils import naming, register
from bungeni.capi import capi


# domain models

def configurable_domain(kls, workflow):
    """Setup/decorate domain class from feature configurations in the workflow.
    Executed on adapters.load_workflow().
    """
    for feature in workflow.features:
        feature.assert_available_for_type(kls)
        if feature.enabled:
            # !+ break decorators up also by archetype?
            feature_decorator = globals()["feature_%s" % (feature.name)]
            feature_decorator(kls, feature)


def feature_audit(kls, feature):
    """Decorator for domain types to support "audit" feature.
    
    If a domain class is explicitly defined, then it is assumed that all 
    necessary setup is also taken care of. Typically, only the sub-classes
    of an archetype (mapped to a same table) need dynamic creation/setup.
    """
    def get_audit_class_for(auditable_class):
        audit_cls_name = "%sAudit" % (auditable_class.__name__)
        return getattr(MODEL_MODULE, audit_cls_name, None)
    
    def get_base_audit_class(kls):
        """Identify what should be the BASE audit class for a 
        {kls}Audit class to inherit from, and return it.
        """
        assert interfaces.IFeatureAudit.implementedBy(kls), kls
        ti = capi.get_type_info(kls)
        if ti.archetype is None:
            # !+ should this be allowed to ever happen? 
            # i.e. require each type to declare an archetype?
            base_audit_class = domain.Audit
        else:
            base_audit_class = get_audit_class_for(ti.archetype)
            if base_audit_class is None:
                # fallback to get the audit class for the sys archetype
                base_audit_class = get_audit_class_for(ti.sys_archetype)
            assert base_audit_class is not None, (kls, ti.archetype, base_audit_class)
        return base_audit_class
    
    def new_audit_class(kls):
        """Create, set on MODEL_MODULE, and map {kls}Audit class.
        """
        base_audit_kls = get_base_audit_class(kls)
        audit_kls = base_audit_kls.auditFactory(kls)
        # set on MODEL_MODULE
        setattr(MODEL_MODULE, audit_kls.__name__, audit_kls)
        # mapper for newly created audit_kls
        mapper(audit_kls,
            inherits=base_audit_kls,
            polymorphic_identity=naming.polymorphic_identity(kls)
        )
        log.info("GENERATED new_audit_class %s(%s) for type %s",
            audit_kls, base_audit_kls, kls)
        return audit_kls
    
    interface.classImplements(kls, interfaces.IFeatureAudit)
    audit_kls = get_audit_class_for(kls)
    if audit_kls is None: 
        audit_kls = new_audit_class(kls)
    # set auditor for kls
    audit.set_auditor(kls)


def feature_version(kls, feature):
    """Decorator for domain types to support "version" feature.
    """
    # domain.{Type}Version itself may NOT support versions
    assert not interfaces.IVersion.implementedBy(kls)
    # !+ @version requires @audit
    assert interfaces.IFeatureAudit.implementedBy(kls)
    interface.classImplements(kls, interfaces.IFeatureVersion)
    # !+VERSION_CLASS_PER_TYPE


def feature_attachment(kls, feature):
    """Decorator for domain types to support "attachment" feature.
    !+ currently assumes that kls is versionable.
    """
    # domain.Attachment itself may NOT support attachments
    assert not interfaces.IAttachment.implementedBy(kls)
    interface.classImplements(kls, interfaces.IFeatureAttachment)
    add_container_property_to_model(kls, "files", 
        "bungeni.models.domain.AttachmentContainer", "head_id")
    # !+ domain.Attachment is versionable
    

def feature_event(kls, feature):
    """Decorator for domain types to support "event" feature.
    For Doc types (other than Event itself).
    """
    # !+ feature "descriptor/processing/validation", move elsewhere?
    # parameter "types":
    # - may "allow" multiple event types
    # - if none specified, "event" is assumed as the default.
    feature.params["types"] = feature.params.get("types", "event").split()
    
    # domain.Event itself may NOT support events
    assert not interfaces.IEvent.implementedBy(kls)
    interface.classImplements(kls, interfaces.IFeatureEvent)
    
    # container property per enabled event type
    for event_type_key in feature.params["types"]:
        if capi.has_type_info(event_type_key):
            container_property_name = naming.plural(event_type_key)
            container_class_name = naming.container_class_name(event_type_key)
            add_container_property_to_model(kls, container_property_name,
                "bungeni.models.domain.%s" % (container_class_name), "head_id")
        else:
            log.warn('IGNORING feature "event" ref to disabled type %r', event_type_key)


def feature_signatory(kls, feature):
    """Decorator for domain types to support "signatory" feature.
    For Doc types.
    """
    interface.classImplements(kls, interfaces.IFeatureSignatory)
    add_container_property_to_model(kls, "signatories", 
        "bungeni.models.domain.SignatoryContainer", "head_id")
    import bungeni.models.signatories
    bungeni.models.signatories.createManagerFactory(kls, **feature.params)


# schedule

class SchedulingManager(object):
    """Store scheduling configuration properties for a schedulable type.
    """
    interface.implements(interfaces.ISchedulingManager)
    
    schedulable_states = ()
    scheduled_states = ()
    
    def __init__(self, context):
        self.context = context

@register.adapter(adapts=(interfaces.IFeatureDownload,))
class DownloadManager(object):
    """ Store download feature properties for a downloadable type.
    """
    interface.implements(interfaces.IDownloadManager)
    
    allowed_types = ()
    
    def get_allowed_types(self):
        if len(self.allowed_types):
            return filter(lambda typ: typ[0] in self.allowed_types,
                interfaces.DOWNLOAD_TYPES)
        else:
            return interfaces.DOWNLOAD_TYPES
    
    def __init__(self, context):
        self.context = context

def create_feature_manager(domain_class, base_class, manager_iface, suffix, **params):
    """Instantiate a scheduling manager instance for `domain_class`.
    """
    manager_name = "%s%s" % (domain_class.__name__, suffix)
    if manager_name in globals().keys():
        log.error("Feature manager named %s already exists", manager_name)
        return

    ti = capi.get_type_info(domain_class)
    domain_iface = ti.interface

    globals()[manager_name] = type(manager_name, (base_class,), {})
    manager = globals()[manager_name]
    known_params = manager_iface.names()
    for config_name, config_value in params.iteritems():
        assert config_name in known_params, ("Check your feature "
            "configuration for %s. Only these parameters may be "
            "configured %s" % (domain_class.__name__, known_params))
        config_type = type(getattr(manager, config_name))
        if config_type in (tuple, list):
            config_value = map(str.strip, config_value.split())
        setattr(manager, config_name, config_type(config_value))
    manager_iface.validateInvariants(manager)
    
    gsm = getGlobalSiteManager()
    gsm.registerAdapter(manager, (domain_iface,), manager_iface)
    return manager_name

def feature_schedule(kls, feature):
    """Decorator for domain types to support "schedule" feature.
    For Doc types, means support for being scheduled in a group sitting.
    """
    manager = create_feature_manager(kls, SchedulingManager,
        interfaces.ISchedulingManager, "SchedulingManager", 
        **feature.params
    )
    if manager is not None:
        interface.classImplements(kls, interfaces.IFeatureSchedule)
    else:
        log.warning("Scheduling manager was not created for class %s. "
            "Check your logs for details", kls)

# /schedule


def feature_sitting(kls, feature):
    """Decorator for group types to support the "sitting" feature.
    For Group types, means support for holding sittings.
    """
    # !+ chamber MUST have "sitting" feature enabled! 
    # !+ agenda_item should probably not be a custom type
    interface.classImplements(kls, interfaces.IFeatureSitting)
    # add containers required by "sitting" feature:
    add_container_property_to_model(kls, "sittings",
            "bungeni.models.domain.SittingContainer", "group_id")    
    add_container_property_to_model(kls, "agenda_items",
            "bungeni.models.domain.AgendaItemContainer", "group_id")


def feature_address(kls, feature):
    """Decorator for domain types to support "address" feature.
    For User and Group types, means support for possibility to have addresses.
    """
    interface.classImplements(kls, interfaces.IFeatureAddress)
    if issubclass(kls, domain.Group):
        add_container_property_to_model(kls, "addresses",
            "bungeni.models.domain.GroupAddressContainer", "principal_id")
    elif issubclass(kls, domain.User):
        add_container_property_to_model(kls, "addresses",
            "bungeni.models.domain.UserAddressContainer", "principal_id")


def feature_workspace(kls, feature):
    """Decorator for domain types that support "workspace" feature.
    """
    interface.classImplements(kls, interfaces.IFeatureWorkspace)


def feature_notification(kls, feature):
    """Decorator for domain types to support "notification" feature.
    """
    interface.classImplements(kls, interfaces.IFeatureNotification)


def feature_email(kls, feature):
    """Decorator for domain types to support "email" notifications feature.
    """
    interface.classImplements(kls, interfaces.IFeatureEmail)


def feature_download(kls, feature):
    """Decorator for domain types that support downloading as 
    pdf/odt/rss/akomantoso.
    """
    manager = create_feature_manager(kls, DownloadManager,
        interfaces.IDownloadManager, "DownloadManager", 
        **feature.params
    )
    if manager:
        interface.classImplements(kls, interfaces.IFeatureDownload)
    else:
        log.warning("Download manager was not created for class %s. "
            "Downloads will be unavailable for this type.", kls)

def feature_user_assignment(kls, feature):
    """Decorator for domain types that support "user_assignment" feature.
    """
    # !+params: "assigner_roles", "assignable_roles"
    interface.classImplements(kls, interfaces.IFeatureUserAssignment)


def feature_group_assignment(kls, feature):
    """Decorator for domain types that support "group_assignment" feature.
    """
    # !+QUALIFIED_FEATURES(mr, apr-2013) may need to "qualify" each assignment!
    # Or, alternatively, each "group_assignment" enabling needs to be "part of" 
    # a qualified "event" feature.
    interface.classImplements(kls, interfaces.IFeatureGroupAssignment)
    add_container_property_to_model(kls, "group_assignments",
        "bungeni.models.domain.GroupAssignmentContainer", "doc_id")


# mappings

def configurable_mappings(kls):
    """Configuration mappings for declarative-model types.
    """
    name = kls.__name__
    
    # auditable, determine properties, map audit class/table
    if interfaces.IFeatureAudit.implementedBy(kls):
        # either defined manually or created dynamically in feature_audit()
        audit_kls = getattr(MODEL_MODULE, "%sAudit" % (name))
        # assumption: audit_kls uses single inheritance only (and not only for 
        # those created dynamically in feature_audit())
        base_audit_kls = audit_kls.__bases__[0]
        assert issubclass(base_audit_kls, domain.Audit), \
            "Audit class %s is not a proper subclass of %s" % (
                audit_kls, domain.Audit)
        # propagate any extended attributes on head kls also to its audit_kls
        for vp_name, vp_type in kls.extended_properties:
            mapper_add_relation_vertical_property(audit_kls, vp_name, vp_type)
        # !+NOTE: capi.get_type_info(kls).descriptor_model is still None
    
    # add any properties to the head kls itself
    def mapper_add_configurable_properties(kls):
        def configurable_properties(kls, mapper_properties):
            """Add properties, as per configured features for a domain type.
            """
            # auditable
            if interfaces.IFeatureAudit.implementedBy(kls):
                # kls.changes <-> change.audit.audit_head=doc:
                # doc[@TYPE] <-- TYPE_audit <-> audit <-> change
                
                # get head table for kls, and its audit table.
                tbl = utils.get_local_table(kls)
                # NOT mapped_table, as when kls_mapper.single=False (e.g. for 
                # the case of the group type) it gves an sa.sql.expression.Join,
                # and not a table object:
                #   principal JOIN "group" ON principal.principal_id = "group".group_id
                audit_tbl = getattr(schema, naming.audit_table_name(tbl.name))
                mapper_properties["changes"] = relation(domain.Change,
                    # join condition, may be determined by a composite primary key
                    primaryjoin=sa.and_( *[
                        pk_col == audit_tbl.c.get(pk_col.name)
                        for pk_col in tbl.primary_key ]),
                    secondary=audit_tbl,
                    secondaryjoin=sa.and_(
                        audit_tbl.c.audit_id == schema.change.c.audit_id,
                    ),
                    lazy=True,
                    order_by=schema.change.c.audit_id.desc(),
                    cascade="all",
                    passive_deletes=False, # SA default
                )
            # versionable
            if interfaces.IFeatureVersion.implementedBy(kls):
                pass # !+VERSION_CLASS_PER_TYPE
            return mapper_properties
        
        kls_mapper = class_mapper(kls)
        for key, prop in configurable_properties(kls, {}).items():
            kls_mapper.add_property(key, prop)
    
    mapper_add_configurable_properties(kls)


