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
from bungeni.alchemist.model import mapper_add_relation_vertical_property
from bungeni.alchemist.descriptor import classproperty
from bungeni.alchemist import utils
from bungeni.models import domain, schema, interfaces as model_ifaces
from bungeni.models import orm # !+ needed to execute mappings
from bungeni.feature import interfaces
from bungeni.utils import naming, register, misc
from bungeni.capi import capi


# utils

def get_feature_interface(feature_name):
    return getattr(interfaces, "IFeature%s" % naming.model_name(feature_name))

def get_feature_cls(feature_name):
    return globals()[naming.model_name(feature_name)]

#def get_cls_workflow_feature(cls, feature_name):
#    return capi.get_type_info(cls).workflow.get_feature(feature_name)
def provides_feature(discriminator, feature_name):
    """Does the domain model identified by discriminator provide the named feature?
    """
    if not (type(discriminator) is type and issubclass(discriminator, domain.Entity)):
        cls = capi.get_type_info(discriminator).domain_model
    else:
        cls = discriminator
    return get_feature_interface(feature_name).implementedBy(cls)


# param parser/validator utils

def ppv_sst(value, default):
    """Space separated tokens."""
    return (value or default or "").split()
ppv_space_separated_type_keys = ppv_sst
ppv_space_separated_role_ids = ppv_sst
ppv_space_separated_state_ids = ppv_sst

def ppv_int(value, default=None):
    return int(value or default or 0)


# containers

def add_info_container_to_descriptor(cls, 
        container_attr_name, target_type_key, rel_attr_name, indirect_key=None
    ):
    """For containers that are defined as part of a feature, need an 
    InfoContainer instance added to the descriptor (corresponding 
    bungeni.alchemist.model.add_container_property_to_model() and creation 
    of SubFormViewlet viewlet are done downstream).
    """
    ti = capi.get_type_info(cls)
    info_containers = ti.descriptor_model.info_containers
    container_attr_names = [ ci.container_attr_name for ci in info_containers ]
    assert container_attr_name not in container_attr_names, \
        (container_attr_name, container_attr_names)
    from bungeni.ui.descriptor.localization import InfoContainer
    # !+INFO_CONTAINER_SEQ for "feature" containers, we remember a "smallish" 
    # seq number, so that we can sort later, and they order before those from 
    # explicit "container" 
    seq = len(info_containers)
    # note: feature-bound containers always get a viewlet
    info_containers.append(
        InfoContainer(container_attr_name, target_type_key, rel_attr_name, 
            indirect_key, seq, "feature", viewlet=True))


# Base Workflow Feature

class Feature(object):
    """Base class for implementation of an optional feature on a workflowed type.
    """
    # interface class that marks support for this feature
    feature_interface = None
    
    # spec of all parameters supported by this feature
    feature_parameters = None # {param_name: {"type": str, "default": any}
    
    # the interface of the subtype, if any, implicated by this feature -- 
    # "feature recursion" is categorically NOT allowed
    subordinate_interface = None
    
    # other features (must be enabled) that this feature depends on, if any
    depends_on = None # tuple(Feature)
    
    @classproperty
    def name(cls):
        return naming.polymorphic_identity(cls)
    
    def __init__(self, enabled=True, note=None, **kws):
        self.enabled = enabled
        self.note = note
        self.params = self.validated_params(kws)
    
    def validated_params(self, kws):
        for key in self.feature_parameters:
            if key not in kws:
                kws[key] = self.feature_parameters[key]["default"]
        for key in kws:
            assert key in self.feature_parameters, "Unknown parameter %r for " \
            "feature %r - configurable parameters here are: %s" % (
                key, self.name, self.feature_parameters.keys())
            fp = self.feature_parameters[key]
            ppv = globals()["ppv_%s" % (fp["type"])]
            kws[key] = ppv(kws[key], fp["default"])
        return kws
    
    def assert_available_for_type(self, cls):
        assert self.name in cls.available_dynamic_features, \
            "Feature %r not one that is available %s for this type %s" % (
                self.name, cls.available_dynamic_features, cls)
    
    def setup_model(self, cls):
        """Executed on adapters.load_workflow().
        """
        self.assert_available_for_type(cls)
        # "feature recursion" is categorically NOT allowed
        if self.subordinate_interface:
            assert not self.subordinate_interface.implementedBy(cls), \
                (self, cls, "feature recursion")
        if self.enabled:
            # dependent features
            if self.depends_on:
                for fi in self.depends_on:
                    assert provides_feature(cls, fi.name), \
                        (self, cls, fi, "dependent feature disabled")
            self.validate(cls)
            # !+determine if class implements an interface NOT via inheritance
            # e.g. EventResponse will already "implement" Audit as super class 
            # Event already does
            #assert not self.feature_interface.implementedBy(cls), \
            #    (self, cls, "feature already supported")
            interface.classImplements(cls, self.feature_interface)
            self.decorate_model(cls)
    
    def setup_ui(self, cls):
        """Executed on localization.forms_localization_check_reload().
        """
        self.decorate_ui(cls)
    
    def validate(self, cls):
        pass
    
    def decorate_model(self, cls):
        pass
    
    def decorate_ui(self, cls):
        pass
    
    def __str__(self):
        return misc.named_repr(self, self.name)
    __repr__ = __str__


# Feature Implementations

class Audit(Feature):
    """Support for the "audit" feature.
    """
    feature_interface = interfaces.IFeatureAudit
    feature_parameters = {
        "audit_actions": dict(type="sst",
            # "add modify workflow remove version translate"
            default=" ".join(domain.AUDIT_ACTIONS)),
        "include_subtypes": dict(type="sst",
            default="attachment event signatory group_assignment member"),
        "display_columns": dict(type="sst", 
            default="user date_active object description note date_audit"),
    }
    subordinate_interface = model_ifaces.IChange # !+IAudit?
    
    def decorate_model(self, cls):
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
        
        # domain - audit class
        audit_cls = get_audit_class_for(cls)
        if audit_cls is None: 
            audit_cls = new_audit_class(cls)
        
        # auditor - head cls
        import bungeni.core.audit
        bungeni.core.audit.set_auditor(cls)
        
        # mapper - audit class
        # assumption: audit_cls uses single inheritance only (and not only for 
        # those created dynamically in feature_audit())
        base_audit_cls = audit_cls.__bases__[0]
        assert issubclass(base_audit_cls, domain.Audit), \
            "Audit class %s is not a proper subclass of %s" % (
                audit_cls, domain.Audit)
        
        # extended attributes - propagate any on head cls also to its audit_cls
        for vp_name, vp_type in cls.extended_properties:
            mapper_add_relation_vertical_property(
                audit_cls, vp_name, vp_type)
        # !+NOTE: capi.get_type_info(cls).descriptor_model is still None

        # cls.changes <-> change.audit.audit_head=doc:
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
    subordinate_interface = model_ifaces.IVersion
    depends_on = Audit,
    # !+VERSION_CLASS_PER_TYPE


class Attachment(Feature):
    """Support for the "attachment" feature.
    """
    feature_interface = interfaces.IFeatureAttachment
    feature_parameters = {}
    subordinate_interface = model_ifaces.IAttachment
    depends_on = Version, # !+ domain.Attachment is expected to be versionable
    
    def decorate_ui(self, cls):
        add_info_container_to_descriptor(cls, "files", "attachment", "head_id")
    

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
    subordinate_interface = model_ifaces.IEvent
    
    def decorate_ui(self, cls):
        # container property per enabled event type
        for event_type_key in self.params["types"]:
            if capi.has_type_info(event_type_key):
                container_property_name = naming.plural(event_type_key)
                add_info_container_to_descriptor(cls, container_property_name, event_type_key, "head_id")
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
    subordinate_interface = model_ifaces.ISignatory
    
    def decorate_model(self, cls):
        import bungeni.models.signatories
        bungeni.models.signatories.createManagerFactory(cls, **self.params)
    
    def decorate_ui(self, cls):
        add_info_container_to_descriptor(cls, "signatories", "signatory", "head_id")


class Sitting(Feature):
    """Support for the "sitting" feature.
    For Group types, means support for holding sittings.
    """
    feature_interface = interfaces.IFeatureSitting
    feature_parameters = {}
    subordinate_interface = model_ifaces.ISitting
    
    # !+ chamber MUST have "sitting" feature enabled! 
    # !+ agenda_item should probably not be a custom type
    
    def decorate_ui(self, cls):
        add_info_container_to_descriptor(cls, "sittings", "sitting", "group_id")
        add_info_container_to_descriptor(cls, "agenda_items", "agenda_item", "group_id")


class Schedule(Feature):
    """Support for the "schedule" feature.
    For Doc types, means support for being scheduled in a group sitting.
    """
    feature_interface = interfaces.IFeatureSchedule
    feature_parameters = {
        "schedulable_states": dict(type="space_separated_state_ids", default=None),
        "scheduled_states": dict(type="space_separated_state_ids", default=None),
    }
    subordinate_interface = None # !+?
    
    def decorate_model(self, cls):
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
    subordinate_interface = model_ifaces.IAddress
    
    def decorate_ui(self, cls):
        if issubclass(cls, domain.Group):
            add_info_container_to_descriptor(cls, "addresses", "group_address", "principal_id")
        elif issubclass(cls, domain.User):
            add_info_container_to_descriptor(cls, "addresses", "user_address", "principal_id")


class Workspace(Feature):
    """Support for the "workspace" feature.
    """
    feature_interface = interfaces.IFeatureWorkspace
    feature_parameters = {}
    subordinate_interface = None


class Notification(Feature):
    """Support "notification" feature.
    """
    feature_interface = interfaces.IFeatureNotification
    feature_parameters = {}
    subordinate_interface = None


class Email(Feature):
    """Support "email" notification feature.
    """
    feature_interface = interfaces.IFeatureEmail
    feature_parameters = {}
    subordinate_interface = None
    depends_on = Notification,


class Download(Feature):
    """Support downloading as pdf/odt/rss/akomantoso.
    """
    feature_interface = interfaces.IFeatureDownload
    feature_parameters = {
        "allowed_types": dict(type="sst", default=None)
    }
    subordinate_interface = None
    
    def decorate_model(self, cls):
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
    subordinate_interface = None


class GroupAssignment(Feature):
    """Support for the "group_assignment" feature.
    """
    feature_interface = interfaces.IFeatureGroupAssignment
    feature_parameters = {}
    # !+param assignable_types
    subordinate_interface = model_ifaces.IGroupAssignment
    
    # !+QUALIFIED_FEATURES(mr, apr-2013) may need to "qualify" each assignment!
    # Or, alternatively, each "group_assignment" enabling needs to be "part of" 
    # a qualified "event" feature.
    
    def decorate_ui(self, cls):
        add_info_container_to_descriptor(cls, "group_assignments", "group_assignment", "doc_id")



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
    assert manager_name not in globals(), "Feature manager named %s already exists" % (manager_name)
    
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


