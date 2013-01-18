# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist model

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist.model")


from zope.interface import interface, classImplements
from bungeni.models import interfaces
from bungeni.alchemist import utils
from bungeni.alchemist.catalyst import (
    INTERFACE_MODULE, 
    MODEL_MODULE
)
from bungeni.utils import naming
from bungeni.capi import capi


def get_vp_kls(extended_type):
    kls_name = naming.model_name(extended_type)
    return getattr(MODEL_MODULE.vp, kls_name)

def new_custom_model_interface(type_key, model_iname):
    model_iface = interface.InterfaceClass(
        model_iname,
        bases=(interfaces.IBungeniContent,), # !+archetype?
        __module__=INTERFACE_MODULE.__name__
    )
    # set on INTERFACE_MODULE (register on type_info downstream)
    setattr(INTERFACE_MODULE, model_iname, model_iface)
    log.info("new_custom_model_interface [%s] %s.%s" % (
            type_key, INTERFACE_MODULE.__name__, model_iname))
    return model_iface

def new_custom_domain_model(type_key, model_interface, archetype_key):
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
    # apply model_interface
    classImplements(domain_model, model_interface)
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


def add_extended_property_to_model(domain_model, name, extended_type, archetype_key):
    assert not hasattr(domain_model, name), \
        "May not add %r as extended field, already defined in archetype %r" % (
            name, archetype_key)
    log.info("Adding %r extended field %r to domain model %s",
        extended_type, name, domain_model)
    vp_kls = get_vp_kls(extended_type)
    domain_model.extended_properties.append((name, vp_kls))


def add_derived_property_to_model(domain_model, name, derived):
    # !+ do not allow clobbering of a same-named attribute
    assert not name in domain_model.__dict__, \
        "May not overwrite %r as derived field, a field with same name is " \
        "already defined directly by domain model class for type %r." % (
            name, naming.polymorphic_identity(domain_model))
    # set as property on domain class
    setattr(domain_model, name, 
        property(capi.get_form_derived(derived)))


def localize_domain_model_from_descriptor_class(domain_model, descriptor_cls):
    """Localize the domain model for configuration information in the 
    descriptor i.e. any extended/derived attributes.
    
    For any model/descriptor this should be called only once!
    """
    # only "localize" non-custom models from the descriptor once!
    type_key = naming.polymorphic_identity(domain_model)
    if type_key in localize_domain_model_from_descriptor_class.DONE:
        return
    localize_domain_model_from_descriptor_class.DONE.append(type_key)
    
    #!+GET_ARCHETYPE
    #!+archetype_key = naming.polymorphic_identity(domain_model.__bases__[0]) multiple inheritance...
    archetype_key = naming._type_key_from_descriptor_class_name(
            descriptor_cls.__bases__[0].__name__)
    
    for field in descriptor_cls.fields:
        
        # extended
        if field.extended is not None:
            add_extended_property_to_model(domain_model, 
                field.name, field.extended, archetype_key)
        
        # derived
        if field.derived is not None:
            add_derived_property_to_model(domain_model, 
                field.name, field.derived)
    
    # !+instrument_extended_propertie, archetype_key => table...
    MODEL_MODULE.instrument_extended_properties(domain_model, archetype_key)
localize_domain_model_from_descriptor_class.DONE = []


