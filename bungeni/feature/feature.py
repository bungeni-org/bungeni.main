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
log = __import__("logging").getLogger("bungeni.feature")


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
from bungeni.models import domain, schema
from bungeni.models.interfaces import (
    IAttachment,
    IEvent,
    IVersion
)
from bungeni.models import orm # !+ needed to execute mappings
from bungeni.feature import interfaces
from bungeni.utils import naming, register, misc
from bungeni.capi import capi


# utils

def get_feature_cls(feature_name):
    return globals()[naming.camel(feature_name)]


# param parser/validator utils

def ppv_space_separated_tokens(value, default):
    return (value or default or "").split()
ppv_space_separated_type_keys = ppv_space_separated_tokens
ppv_space_separated_role_ids = ppv_space_separated_tokens
ppv_space_separated_state_ids = ppv_space_separated_tokens

def ppv_int(value, default=None):
    return int(value or default or 0)


# Optional Workflow Features

class Feature(object):
    """Base class for implementation of an optional feature on a workflowed type.
    """
    feature_interface = None # interface class
    feature_parameters = None # {param_name: {"type": param_type:str, "default": default_value:any}
    
    def __init__(self, name, enabled=True, note=None, **kws):
        self.name = name
        self.enabled = enabled
        self.note = note
        self.params = self.validated_params(kws)
    
    def validated_params(self, kws):
        for key in self.feature_parameters:
            if key not in kws:
                kws[key] = self.feature_parameters[key]["default"]
        for key in kws:
            assert key in self.feature_parameters, key
            p_desc = self.feature_parameters[key]
            pp = globals()["ppv_%s" % (p_desc["type"])]
            kws[key] = pp(kws[key], p_desc["default"])
        return kws
    
    def assert_available_for_type(self, cls):
        assert self.name in cls.available_dynamic_features, \
            "Feature %r not one that is available %s for this type %s" % (
                self.name, cls.available_dynamic_features, cls)
    
    def setup(self, cls):
        """Executed on adapters.load_workflow().
        """
        self.assert_available_for_type(cls)
        if self.enabled:
            self.validate(cls)
            interface.classImplements(cls, self.feature_interface)
            self.decorate(cls)
    
    def validate(self, cls):
        pass
    
    def decorate(self, cls):
        pass
    
    def __str__(self):
        return misc.named_repr(self, self.name)
    __repr__ = __str__


# Feature Implementations

class Audit(Feature):
    """Support for the "audit" feature.
    """
    feature_interface = interfaces.IFeatureAudit
    feature_parameters = {}
    
    def decorate(self, cls):
        # Assumption: if a domain class is explicitly pre-defined, then it is 
        # assumed that all necessary setup is also taken care of. 
        # Typically, only the sub-classes of an archetype (mapped to a same 
        # table) need dynamic creation/setup.
        
        def get_audit_class_for(auditable_class):
            audit_cls_name = "%sAudit" % (auditable_class.__name__)
            return getattr(MODEL_MODULE, audit_cls_name, None)
        
        def get_base_audit_class(cls):
            """Identify what should be the BASE audit class for a 
            {cls}Audit class to inherit from, and return it.
            """
            assert interfaces.IFeatureAudit.implementedBy(cls), cls
            ti = capi.get_type_info(cls)
            if ti.archetype is None:
                # !+ should this be allowed to ever happen? 
                # i.e. require each type to declare an archetype?
                base_audit_class = domain.Audit
            else:
                base_audit_class = get_audit_class_for(ti.archetype)
                if base_audit_class is None:
                    # fallback to get the audit class for the sys archetype
                    base_audit_class = get_audit_class_for(ti.sys_archetype)
                assert base_audit_class is not None, (cls, ti.archetype, base_audit_class)
            return base_audit_class
        
        def new_audit_class(cls):
            """Create, set on MODEL_MODULE, and map {cls}Audit class.
            """
            base_audit_cls = get_base_audit_class(cls)
            audit_cls = base_audit_cls.auditFactory(cls)
            # set on MODEL_MODULE
            setattr(MODEL_MODULE, audit_cls.__name__, audit_cls)
            # mapper for newly created audit_cls
            mapper(audit_cls,
                inherits=base_audit_cls,
                polymorphic_identity=naming.polymorphic_identity(cls)
            )
            log.info("GENERATED new_audit_class %s(%s) for type %s",
                audit_cls, base_audit_cls, cls)
            return audit_cls
        
        # audit class - domain
        audit_cls = get_audit_class_for(cls)
        if audit_cls is None: 
            audit_cls = new_audit_class(cls)
        
        # set auditor for cls
        import bungeni.core.audit
        bungeni.core.audit.set_auditor(cls)
        
        # mapper 
        # assumption: audit_cls uses single inheritance only (and not only for 
        # those created dynamically in feature_audit())
        base_audit_cls = audit_cls.__bases__[0]
        assert issubclass(base_audit_cls, domain.Audit), \
            "Audit class %s is not a proper subclass of %s" % (
                audit_cls, domain.Audit)
        
        # propagate any extended attributes on head cls also to its audit_cls
        for vp_name, vp_type in cls.extended_properties:
            mapper_add_relation_vertical_property(audit_cls, vp_name, vp_type)
        # !+NOTE: capi.get_type_info(cls).descriptor_model is still None

        # kls.changes <-> change.audit.audit_head=doc:
        # doc[@TYPE] <-- TYPE_audit <-> audit <-> change
                
        # get head table for kls, and its audit table.
        tbl = utils.get_local_table(cls)
        # NOT mapped_table, as when cls_mapper.single=False (e.g. for 
        # the case of the group type) it gves an sa.sql.expression.Join,
        # and not a table object:
        #   principal JOIN "group" ON principal.principal_id = "group".group_id
        audit_tbl = getattr(schema, naming.audit_table_name(tbl.name))
        cls_mapper = class_mapper(cls)
        cls_mapper.add_property("changes", relation(domain.Change,
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
            ))


class Version(Feature):
    """Support for the "version" feature.
    """
    feature_interface = interfaces.IFeatureVersion
    feature_parameters = {}
    
    def validate(self, cls):
        # domain.{Type}Version itself may NOT support versions
        assert not IVersion.implementedBy(cls), cls
        # !+ @version requires @audit
        assert interfaces.IFeatureAudit.implementedBy(cls), cls
        # !+VERSION_CLASS_PER_TYPE


class Attachment(Feature):
    """Support for the "attachment" feature.
    """
    feature_interface = interfaces.IFeatureAttachment
    feature_parameters = {}
    
    def validate(self, cls):
        # !+assumption: domain.Attachment is versionable
        # domain.Attachment itself may NOT support attachments
        assert not IAttachment.implementedBy(cls)
    
    def decorate(self, cls):
        add_container_property_to_model(cls, "files", 
            "bungeni.models.domain.AttachmentContainer", "head_id")


class Event(Feature):
    """Support for the "event" feature. For Doc types (other than Event itself).
    """
    feature_interface = interfaces.IFeatureEvent
    feature_parameters = {
        # parameter "types":
        # - may "allow" multiple event types
        # - if none specified, "event" is assumed as the default.
        "types": dict(type="space_separated_type_keys", default="event")
    }
    
    def validate(self, cls):
        # domain.Event itself may NOT support events
        assert not IEvent.implementedBy(cls)
    
    def decorate(self, cls):
        # container property per enabled event type
        for event_type_key in self.params["types"]:
            if capi.has_type_info(event_type_key):
                container_property_name = naming.plural(event_type_key)
                container_class_name = naming.container_class_name(event_type_key)
                add_container_property_to_model(cls, container_property_name,
                    "bungeni.models.domain.%s" % (container_class_name), "head_id")
            else:
                log.warn("IGNORING feature %r ref to disabled type %r", 
                    self.name, event_type_key)


class Signatory(Feature):
    """Support for the "signatory" feature. For Doc types.
    """
    feature_interface = interfaces.IFeatureSignatory
    feature_parameters = {
        "min_signatories": dict(type="int", default=0),
        "max_signatories": dict(type="int", default=0),
        "submitted_states": dict(type="space_separated_state_ids", default="submitted_signatories"),
        "draft_states": dict(type="space_separated_state_ids", default="draft redraft"),
        "expire_states": dict(type="space_separated_state_ids", default="submitted"),
        "open_states": dict(type="space_separated_state_ids", default=None),
    }
    
    def decorate(self, cls):
        add_container_property_to_model(cls, "signatories", 
            "bungeni.models.domain.SignatoryContainer", "head_id")
        import bungeni.models.signatories
        bungeni.models.signatories.createManagerFactory(cls, **self.params)


class Sitting(Feature):
    """Support for the "sitting" feature.
    For Group types, means support for holding sittings.
    """
    feature_interface = interfaces.IFeatureSitting
    feature_parameters = {}
    
    # !+ chamber MUST have "sitting" feature enabled! 
    # !+ agenda_item should probably not be a custom type
    
    def decorate(self, cls):
        # add containers required by "sitting" feature:
        add_container_property_to_model(cls, "sittings",
            "bungeni.models.domain.SittingContainer", "group_id")    
        add_container_property_to_model(cls, "agenda_items",
            "bungeni.models.domain.AgendaItemContainer", "group_id")


class Schedule(Feature):
    """Support for the "schedule" feature.
    For Doc types, means support for being scheduled in a group sitting.
    """
    feature_interface = interfaces.IFeatureSchedule
    feature_parameters = {
        "schedulable_states": dict(type="space_separated_state_ids", default=None),
        "scheduled_states": dict(type="space_separated_state_ids", default=None),
    }
    
    def decorate(self, cls):
        manager = create_feature_manager(cls, SchedulingManager,
            interfaces.ISchedulingManager, "SchedulingManager", 
            **self.params
        )
        assert manager is not None, cls


class Address(Feature):
    """Support for the "address" feature.
    For User and Group types, means support for possibility to have addresses.
    """
    feature_interface = interfaces.IFeatureAddress
    feature_parameters = {}
    
    def decorate(self, cls):
        if issubclass(cls, domain.Group):
            add_container_property_to_model(cls, "addresses",
                "bungeni.models.domain.GroupAddressContainer", "principal_id")
        elif issubclass(cls, domain.User):
            add_container_property_to_model(cls, "addresses",
                "bungeni.models.domain.UserAddressContainer", "principal_id")


class Workspace(Feature):
    """Support for the "workspace" feature.
    """
    feature_interface = interfaces.IFeatureWorkspace
    feature_parameters = {}


class Notification(Feature):
    """Support "notification" feature.
    """
    feature_interface = interfaces.IFeatureNotification
    feature_parameters = {}


class Email(Feature):
    """Support "email" notification feature.
    """
    feature_interface = interfaces.IFeatureEmail
    feature_parameters = {}


class Download(Feature):
    """Support downloading as pdf/odt/rss/akomantoso.
    """
    feature_interface = interfaces.IFeatureDownload
    feature_parameters = {
        "allowed_types": dict(type="space_separated_tokens", default=None)
    }
    
    def decorate(self, cls):
        manager = create_feature_manager(cls, DownloadManager,
            interfaces.IDownloadManager, "DownloadManager", 
            **self.params
        )
        assert manager is not None, cls


class UserAssignment(Feature):
    """Support for the "user_assignment" feature.
    """
    feature_interface = interfaces.IFeatureUserAssignment
    feature_parameters = {
        "assigner_roles": dict(type="space_separated_role_ids", default=None),
        "assignable_roles": dict(type="space_separated_role_ids", default=None),
    }

class GroupAssignment(Feature):
    """Support for the "group_assignment" feature.
    """
    feature_interface = interfaces.IFeatureGroupAssignment
    feature_parameters = {}
    # !+param assignable_types
    
    # !+QUALIFIED_FEATURES(mr, apr-2013) may need to "qualify" each assignment!
    # Or, alternatively, each "group_assignment" enabling needs to be "part of" 
    # a qualified "event" feature.
    
    def decorate(self, cls):
        add_container_property_to_model(cls, "group_assignments",
            "bungeni.models.domain.GroupAssignmentContainer", "doc_id")



# !+ unconvolute code below + cleanout "duplication" in models.signatories



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
    if manager_name in globals().keys(): #!+KEYS
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
            config_value = map(str.strip, config_value)
        setattr(manager, config_name, config_type(config_value))
    manager_iface.validateInvariants(manager)
    
    gsm = getGlobalSiteManager()
    gsm.registerAdapter(manager, (domain_iface,), manager_iface)
    return manager_name


