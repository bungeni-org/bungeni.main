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
import sqlalchemy as sa
from sqlalchemy.orm import mapper, class_mapper, relation
from bungeni.alchemist.catalyst import MODEL_MODULE
from bungeni.alchemist.model import mapper_add_relation_vertical_property
from bungeni.alchemist.descriptor import classproperty
from bungeni.alchemist import utils
from bungeni.models import domain, schema, interfaces as model_ifaces
from bungeni.models import orm # !+ needed to execute mappings
from bungeni.feature import interfaces
from bungeni.utils import naming, misc
from bungeni.capi import capi


# utils

def get_feature_interface(feature_name):
    return getattr(interfaces, "IFeature%s" % naming.model_name(feature_name))

def get_feature_cls(feature_name):
    feature_cls_name = naming.model_name(feature_name)
    try:
        return globals()[feature_cls_name]
    except KeyError:
        feature_module_name = "feature_%s" % (feature_name)
        feature_module = __import__("bungeni.feature.%s" % (feature_module_name),
            fromlist=[feature_module_name])
        return getattr(feature_module, feature_cls_name)


def get_feature(discriminator, feature_name):
    return capi.get_type_info(discriminator).workflow.get_feature(feature_name)

def provides_feature(discriminator, feature_name):
    """Does the domain model identified by discriminator provide the named feature?
    """
    if not (type(discriminator) is type and issubclass(discriminator, domain.Entity)):
        model = capi.get_type_info(discriminator).domain_model
    else:
        model = discriminator
    return get_feature_interface(feature_name).implementedBy(model)



class PPV(object):
    """param parser/validator (convenient namespace)
    """
    
    @staticmethod
    def sst(value, default):
        """Space separated tokens."""
        return (value or default or "").split()
    space_separated_type_keys = sst
    space_separated_role_ids = sst
    space_separated_state_ids = sst
    
    @staticmethod
    def integer(value, default=None):
        return int(value or default or 0)


# containers

def add_info_container_to_descriptor(model, 
        container_attr_name, target_type_key, rel_attr_name, indirect_key=None
    ):
    """For containers that are defined as part of a feature, need an 
    InfoContainer instance added to the descriptor (corresponding 
    bungeni.alchemist.model.add_container_property_to_model() and creation 
    of SubFormViewlet viewlet are done downstream).
    """
    ti = capi.get_type_info(model)
    from bungeni.ui.descriptor.localization import add_info_container
    add_info_container(ti.type_key, ti.descriptor_model.info_containers,
        container_attr_name, target_type_key, rel_attr_name, indirect_key, 
        viewlet=True, _origin="feature")


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
        self.p = misc.bunch(**self.parse_parameters(kws))
        self.validate_parameters()
    
    def __str__(self):
        return misc.named_repr(self, self.name)
    __repr__ = __str__
    
    #
    
    def parse_parameters(self, kws):
        """Parse and normalize (add missing entries, using defaults) parameters, 
        returning them as a dict object.
        """
        for key in self.feature_parameters:
            if key not in kws:
                kws[key] = self.feature_parameters[key]["default"]
        for key in kws:
            assert key in self.feature_parameters, "Unknown parameter %r for " \
            "feature %r - configurable parameters here are: %s" % (
                key, self.name, self.feature_parameters.keys())
            fp = self.feature_parameters[key]
            ppv = getattr(PPV, fp["type"])
            kws[key] = ppv(kws[key], fp["default"])
        return kws
    
    def validate_model(self, model):
        # assert this feature is available for model
        assert self.name in model.available_dynamic_features, \
            "Feature %r not one that is available %s for this type %s" % (
                self.name, model.available_dynamic_features, model)
        # "feature recursion" is categorically NOT allowed
        if self.subordinate_interface:
            assert not self.subordinate_interface.implementedBy(model), \
                (self, model, "feature recursion")
        if self.enabled:
            # dependent features
            if self.depends_on:
                for fi in self.depends_on:
                    assert provides_feature(model, fi.name), \
                        (self, model, fi, "dependent feature disabled")
            # !+determine if class implements an interface NOT via inheritance
            # e.g. EventResponse will already "implement" Audit as super class 
            # Event already does !+get_base_cls?
            #assert not self.feature_interface.implementedBy(model), \
            #    (self, model, "feature already supported")
    
    def setup_model(self, model):
        """Executed on adapters.load_workflow().
        """
        self.validate_model(model)
        if self.enabled:
            interface.classImplements(model, self.feature_interface)
            self.decorate_model(model)
    
    def setup_ui(self, model):
        """Executed on localization.forms_localization_check_reload().
        """
        if self.enabled: # !+ only ever gets called for enabled types?
            self.decorate_ui(model)
    
    # hooks to be redefined by subclasses
    
    def validate_parameters(self):
        """Additional feature parameter validation."""
        pass
    
    def decorate_model(self, model):
        pass
    
    def decorate_ui(self, model):
        pass
    


# Feature Implementations

class Audit(Feature):
    """Support for the "audit" feature.
    """
    # parameter defaults
    AUDIT_ACTIONS = " ".join(domain.AUDIT_ACTIONS) # "add modify workflow remove version translate"
    INCLUDE_SUBTYPES = "attachment event signatory group_assignment member"
    DISPLAY_COLUMNS = "user date_active object description note date_audit"
    
    feature_interface = interfaces.IFeatureAudit
    feature_parameters = {
        "audit_actions": dict(type="sst", default=AUDIT_ACTIONS),
        "include_subtypes": dict(type="sst", default=INCLUDE_SUBTYPES),
        "display_columns": dict(type="sst", default=DISPLAY_COLUMNS),
    }
    subordinate_interface = model_ifaces.IChange # !+IAudit?
    
    def decorate_model(self, model):
        # Assumption: if a domain class is explicitly pre-defined, then it is 
        # assumed that all necessary setup is also taken care of. 
        # Typically, only the sub-classes of an archetype (mapped to a same 
        # table) need dynamic creation/setup.
        
        def get_audit_class_for(auditable_class):
            audit_cls_name = "%sAudit" % (auditable_class.__name__)
            return getattr(MODEL_MODULE, audit_cls_name, None)
        
        def get_base_audit_class(model):
            """Identify what should be the BASE audit class for a 
            {model}Audit class to inherit from, and return it.
            """
            assert interfaces.IFeatureAudit.implementedBy(model), model
            ti = capi.get_type_info(model)
            if ti.archetype is None:
                # !+ should this be allowed to ever happen? 
                # i.e. require each type to declare an archetype?
                base_audit_class = domain.Audit
            else:
                base_audit_class = get_audit_class_for(ti.archetype)
                if base_audit_class is None:
                    # fallback to get the audit class for the sys archetype
                    base_audit_class = get_audit_class_for(ti.sys_archetype)
                assert base_audit_class is not None, (model, ti.archetype, base_audit_class)
            return base_audit_class
        
        def new_audit_class(model):
            """Create, set on MODEL_MODULE, and map {model}Audit class.
            """
            base_audit_cls = get_base_audit_class(model)
            audit_cls = base_audit_cls.auditFactory(model)
            # set on MODEL_MODULE
            setattr(MODEL_MODULE, audit_cls.__name__, audit_cls)
            # mapper for newly created audit_cls
            mapper(audit_cls,
                inherits=base_audit_cls,
                polymorphic_identity=naming.polymorphic_identity(model)
            )
            log.info("GENERATED new_audit_class %s(%s) for type %s",
                audit_cls, base_audit_cls, model)
            return audit_cls
        
        # domain - audit class
        audit_cls = get_audit_class_for(model)
        if audit_cls is None: 
            audit_cls = new_audit_class(model)
        
        # auditor - head cls
        import bungeni.core.audit
        bungeni.core.audit.set_auditor(model)
        
        # mapper - audit class
        # assumption: audit_cls uses single inheritance only (and not only for 
        # those created dynamically in feature_audit())
        base_audit_cls = audit_cls.__bases__[0]
        assert issubclass(base_audit_cls, domain.Audit), \
            "Audit class %s is not a proper subclass of %s" % (
                audit_cls, domain.Audit)
        
        # extended attributes - propagate any on head cls also to its audit_cls
        for vp_name, vp_type in model.extended_properties:
            mapper_add_relation_vertical_property(
                audit_cls, vp_name, vp_type)
        # !+NOTE: capi.get_type_info(model).descriptor_model is still None

        # model.changes <-> change.audit.audit_head=doc:
        # doc[@TYPE] <-- TYPE_audit <-> audit <-> change
                
        # get head table for kls, and its audit table.
        tbl = utils.get_local_table(model)
        # NOT mapped_table, as when cls_mapper.single=False (e.g. for 
        # the case of the group type) it gves an sa.sql.expression.Join,
        # and not a table object:
        #   principal JOIN "group" ON principal.principal_id = "group".group_id
        audit_tbl = getattr(schema, naming.audit_table_name(tbl.name))
        cls_mapper = class_mapper(model)
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
    
    def decorate_ui(self, model):
        add_info_container_to_descriptor(model, "files", "attachment", "head_id")
    

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
    
    def decorate_ui(self, model):
        # container property per enabled event type
        for event_type_key in self.p.types:
            if capi.has_type_info(event_type_key):
                container_property_name = naming.plural(event_type_key)
                add_info_container_to_descriptor(model, container_property_name, event_type_key, "head_id")
            else:
                log.warn("IGNORING feature %r ref to disabled type %r", 
                    self.name, event_type_key)


class Sitting(Feature):
    """Support for the "sitting" feature.
    For Group types, means support for holding sittings.
    """
    feature_interface = interfaces.IFeatureSitting
    feature_parameters = {}
    subordinate_interface = model_ifaces.ISitting
    
    # !+ chamber MUST have "sitting" feature enabled! 
    # !+ agenda_item should probably not be a custom type
    
    def decorate_ui(self, model):
        add_info_container_to_descriptor(model, "sittings", "sitting", "group_id")
        add_info_container_to_descriptor(model, "agenda_items", "agenda_item", "group_id")


class Schedule(Feature):
    """Support for the "schedule" feature.
    For Doc types, means support for being scheduled in a group sitting.
    """
    feature_interface = interfaces.IFeatureSchedule
    feature_parameters = {
        "schedulable_states": dict(type="space_separated_state_ids", default=None,
            doc="object's schedulable states"),
        "scheduled_states": dict(type="space_separated_state_ids", default=None,
            doc="object's scheduled states"),
    }
    subordinate_interface = None # !+?
    

class Address(Feature):
    """Support for the "address" feature.
    For User and Group types, means support for possibility to have addresses.
    """
    feature_interface = interfaces.IFeatureAddress
    feature_parameters = {}
    subordinate_interface = model_ifaces.IAddress
    
    def decorate_ui(self, model):
        if issubclass(model, domain.Group):
            add_info_container_to_descriptor(model, "addresses", "group_address", "principal_id")
        elif issubclass(model, domain.User):
            add_info_container_to_descriptor(model, "addresses", "user_address", "principal_id")


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


class UserAssignment(Feature):
    """Support for the "user_assignment" feature (Doc). !+User?
    """
    feature_interface = interfaces.IFeatureUserAssignment
    feature_parameters = {
        "assigner_roles": dict(type="space_separated_role_ids", default=None),
        "assignable_roles": dict(type="space_separated_role_ids", default=None),
    }
    subordinate_interface = None


class GroupAssignment(Feature):
    """Support for the "group_assignment" feature (Doc). !+Group?
    """
    feature_interface = interfaces.IFeatureGroupAssignment
    feature_parameters = {}
    # !+param assignable_types
    subordinate_interface = model_ifaces.IGroupAssignment
    
    # !+QUALIFIED_FEATURES(mr, apr-2013) may need to "qualify" each assignment!
    # Or, alternatively, each "group_assignment" enabling needs to be "part of" 
    # a qualified "event" feature.
    
    def decorate_ui(self, model):
        add_info_container_to_descriptor(model, "group_assignments", "group_assignment", "doc_id")


