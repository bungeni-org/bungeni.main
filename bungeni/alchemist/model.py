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
    # set on INTERFACE_MODULE (register on type_info downstream)
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

