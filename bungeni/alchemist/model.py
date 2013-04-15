# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist model

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist.model")


import sqlalchemy as sa
from sqlalchemy.orm import class_mapper, relation

from zope.interface import interface, classImplements

from bungeni.models import interfaces
from bungeni.alchemist import utils
from bungeni.alchemist.catalyst import (
    INTERFACE_MODULE, 
    MODEL_MODULE
)
from bungeni.alchemist.traversal import one2many, one2manyindirect
from bungeni.utils import naming


def get_vp_kls(extended_type):
    kls_name = naming.model_name(extended_type)
    return getattr(MODEL_MODULE.vp, kls_name)


# domain model, create, update

def new_custom_domain_interface(type_key, domain_iface_name):
    domain_iface = interface.InterfaceClass(
        domain_iface_name,
        bases=(interfaces.IBungeniContent,), # !+archetype?
        __module__=INTERFACE_MODULE.__name__
    )
    # set on INTERFACE_MODULE (register on type_info downstream)
    setattr(INTERFACE_MODULE, domain_iface_name, domain_iface)
    log.info("new_custom_domain_interface [%s] %s.%s" % (
            type_key, INTERFACE_MODULE.__name__, domain_iface_name))
    return domain_iface

def new_custom_domain_model(type_key, domain_interface, archetype_key):
    domain_model_name = naming.model_name(type_key)
    assert archetype_key, \
        "Custom descriptor %r does not specify an archetype" % (type_key)
    archetype = getattr(MODEL_MODULE, naming.model_name(archetype_key)) # AttributeError
    # !+ assert archetype constraints
    domain_model = type(domain_model_name,
        (archetype,),
        {
            "__module__": MODEL_MODULE.__name__,
            "extended_properties": [],
        }
    )
    # apply domain_interface
    classImplements(domain_model, domain_interface)
    # set on MODEL_MODULE (register on type_info downstream)
    setattr(MODEL_MODULE, domain_model_name, domain_model)
    # db map custom domain class
    from sqlalchemy.orm import mapper
    mapper(domain_model, 
        inherits=archetype,
        polymorphic_on=utils.get_local_table(archetype).c.type,
        polymorphic_identity=type_key, #naming.polymorphic_identity(domain_model),
    )
    log.info("new_custom_domain_model [%s] %s.%s" % (
            type_key, MODEL_MODULE.__name__, domain_model_name))
    return domain_model


# extended properties

def vertical_property(object_type, vp_name, vp_type, *args, **kw):
    """Get the external (non-SQLAlchemy) extended Vertical Property
    (on self.__class__) as a regular python property.
    
    !+ Any additional args/kw are exclusively for instantiation of vp_type.
    """
    _vp_name = "_vp_%s" % (vp_name) # name for SA mapper property for this
    doc = "VerticalProperty %s of type %s" % (vp_name, vp_type)
    def fget(self):
        vp = getattr(self, _vp_name, None)
        if vp is not None:
            return vp.value
    def fset(self, value):
        vp = getattr(self, _vp_name, None)
        if vp is not None:
            vp.value = value
        else:
            vp = vp_type(self, object_type, vp_name, value, *args, **kw)
            setattr(self, _vp_name, vp)
    def fdel(self):
        setattr(self, _vp_name, None)
    return property(fget=fget, fset=fset, fdel=fdel, doc=doc)


def add_extended_property_to_model(domain_model, name, extended_type):
    assert not hasattr(domain_model, name), \
        "May not add %r as extended field, already defined in archetype" % (name)
    log.info("Adding %r extended field %r to domain model %s",
        extended_type, name, domain_model)
    vp_kls = get_vp_kls(extended_type)
    domain_model.extended_properties.append((name, vp_kls))


def mapper_add_relation_vertical_properties(kls):
    """Instrument any extended attributes as vertical properties.
    """
    for vp_name, vp_type in kls.extended_properties:
        mapper_add_relation_vertical_property(kls, vp_name, vp_type)
def mapper_add_relation_vertical_property(kls, vp_name, vp_type):
    """Add the SQLAlchemy internal mapper property for the vertical property.
    """
    kls_mapper = class_mapper(kls)
    object_type = kls_mapper.local_table.name # kls_mapper.mapped_table.name
    assert len(kls_mapper.primary_key) == 1
    object_id_column = kls_mapper.primary_key[0]
    kls_mapper.add_property("_vp_%s" % (vp_name),
        relation_vertical_property(
            object_type, object_id_column, vp_name, vp_type)
    )
def relation_vertical_property(object_type, object_id_column, vp_name, vp_type):
    """Get the SQLAlchemy internal property for the vertical property.
    """
    vp_table = class_mapper(vp_type).mapped_table
    return relation(vp_type,
        primaryjoin=sa.and_(
            object_id_column == vp_table.c.object_id,
            object_type == vp_table.c.object_type,
            vp_name == vp_table.c.name,
        ),
        foreign_keys=[vp_table.c.object_id],
        uselist=False,
        # !+abusive, cannot create a same-named backref to multiple classes!
        #backref=object_type,
        # sqlalchemy.orm.relationship(cascade="save-update, merge, 
        #       refresh-expire, expunge, delete, delete-orphan")
        # False (default) -> "save-update, merge"
        # "all" -> "save-update, merge, refresh-expire, expunge, delete"
        cascade="all",
        single_parent=True,
        lazy=False, # !+LAZY(mr, jul-2012) gives orm.exc.DetachedInstanceError
        # e.g. in business/questions listing:
        # Parent instance <Question at ...> is not bound to a Session; 
        # lazy load operation of attribute '_vp_response_type' cannot proceed
    )


def instrument_extended_properties(cls, object_type=None, from_class=None):
    if object_type is None:
        object_type = utils.get_local_table(cls).name
    if from_class is None:
        from_class = cls
    # ensure cls.__dict__.extended_properties
    cls.extended_properties = cls.extended_properties[:]
    for vp_name, vp_type in from_class.extended_properties:
        if (vp_name, vp_type) not in cls.extended_properties:
            cls.extended_properties.append((vp_name, vp_type))
        setattr(cls, vp_name, vertical_property(object_type, vp_name, vp_type))
        mapper_add_relation_vertical_property(cls, vp_name, vp_type)


# derived properties

def add_derived_property_to_model(domain_model, name, derived):
    from bungeni.capi import capi
    
    # !+ do not allow clobbering of a same-named attribute
    assert not name in domain_model.__dict__, \
        "May not overwrite %r as derived field, a field with same name is " \
        "already defined directly by domain model class for type %r." % (
            name, naming.polymorphic_identity(domain_model))
    
    # set as property on domain class
    setattr(domain_model, name, 
        property(capi.get_form_derived(derived)))


# containers

def add_container_property_to_model(domain_model, 
        name, container_qualname, rel_attr, indirect_key=None
    ):
    """Add an alchemist container attribute to domain_model. 
    These attributes are only catalysed (re-instrumented on domain_model) if 
    defined directly on domain_model i.e. are not inherited, must be defined 
    on each class.
    """
    assert not domain_model.__dict__.has_key(name), \
        "type %s already has a %r attribute %r" % (
            domain_model, name, domain_model.__dict__[name])
    
    if indirect_key:
        setattr(domain_model, name, 
            one2manyindirect(name, container_qualname, rel_attr, indirect_key))
    else:
        setattr(domain_model, name,
            one2many(name, container_qualname, rel_attr))

#

def localize_domain_model_from_descriptor_class(domain_model, descriptor_cls):
    """Localize the domain model for configuration information in the 
    descriptor i.e. any extended/derived attributes.
    
    For any model/descriptor this should be called only once!
    """
    type_key = naming.polymorphic_identity(domain_model)
    # localize models from descriptors only once!
    assert type_key not in localize_domain_model_from_descriptor_class.DONE, \
        "May not re-localize [%s] domain model from descriptor" % (type_key)
    localize_domain_model_from_descriptor_class.DONE.append(type_key)
    
    for field in descriptor_cls.fields:
        
        # extended
        if field.extended is not None:
            add_extended_property_to_model(domain_model, 
                field.name, field.extended)
        
        # derived
        if field.derived is not None:
            add_derived_property_to_model(domain_model, 
                field.name, field.derived)
    
    # !+if domain_model.extended_properties: ?
    instrument_extended_properties(domain_model)
    mapper_add_relation_vertical_properties(domain_model)
    # !+AUDIT_EXTENDED_ATTRIBUTES as audit class was created prior to 
    # extended attributes being updated on domain type, need to push onto 
    # it any extended attrs that were read from model's descriptor
    if interfaces.IFeatureAudit.implementedBy(domain_model):
        # either defined manually or created dynamically in feature_audit()
        audit_kls = getattr(MODEL_MODULE, "%sAudit" % (domain_model.__name__))
        # propagate any extended attributes on head kls also to its audit_kls
        instrument_extended_properties(audit_kls, from_class=domain_model)
    
    # containers
    from bungeni.capi import capi
    for name, target_type_key, rel_attr, indirect in descriptor_cls.info_containers:
        try:
            tti = capi.get_type_info(target_type_key)
        except KeyError:
            # target type not enabled
            log.warn("Ignoring %r container property %r to disabled type: %s.%s", 
                type_key, name, target_type_key, rel_attr)
            continue
        
        container_qualname = "bungeni.models.domain.%s" % (
            naming.container_class_name(target_type_key))
        add_container_property_to_model(domain_model, 
            name, container_qualname, rel_attr, indirect)

localize_domain_model_from_descriptor_class.DONE = []


