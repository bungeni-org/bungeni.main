# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Aggregation of information about loaded domain types.

No public methods here -- all available methods from this are those exposed 
via bungeni.utils.capi.

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.type_info")

from zope.interface.interfaces import IInterface
from zope.security.proxy import removeSecurityProxy
from bungeni.alchemist.interfaces import IModelDescriptor
from bungeni.models import interfaces
from bungeni.models import domain
from bungeni.core.workflow.interfaces import IWorkflow
from bungeni.utils import naming

__all__ = []


# acessors exposed via capi

def _iter():
    """Return iterator on all (key, TypeInfo) entries in TYPE_REGISTRY.
    
    Usage: capi.iter_type_info()
    """
    for type_key, ti in TYPE_REGISTRY:
        yield type_key, ti

def _add(workflow_key, iface, workflow, domain_model, 
        descriptor_model, descriptor
    ):
    """Create and add a TypeInfo instance for supplied information.
    Raise ValueError is an entry exists already.
    """
    assert iface and domain_model, "Must at least specify interface and model."
    type_key = naming.polymorphic_identity(domain_model)
    try:
        from bungeni.utils.capi import capi
        ti = capi.get_type_info(type_key)
    except KeyError:
        # ok, no TI entry for type_key as yet
        ti = TI(workflow_key, iface)
        ti.workflow = workflow
        ti.domain_model = domain_model
        ti.descriptor_model = descriptor_model
        if descriptor is None and descriptor_model is not None:
            desciptor = descriptor_model()
        ti.descriptor = descriptor
        TYPE_REGISTRY.append((type_key, ti))
    else:
        raise ValueError, "An type entry for [%s] already exists." % (type_key)

def _get(discriminator):
    """Get the TypeInfo instance for discriminator, that may be any of:
            type_key: str (the lowercase underscore-separated of domain cls name)
            workflow: an instance of Workflow, provides IWorkflow
            interface: provides IInterface
            domain model: provides IBungeniContent
            domain model instance: type provides IBungeniContent
            descriptor: provides IModelDescriptor
    
    Raise KeyError if no entry matched.
    
    Usage: capi.get_type_info(discriminator)
    """
    if discriminator is None:
        m = "type_info._get discriminator is None"
        log.error(m)
        raise ValueError(m)
    discriminator = removeSecurityProxy(discriminator)
    getter = None
    
    if isinstance(discriminator, basestring):
        getter = _get_by_type_key
    elif IInterface.providedBy(discriminator):
        getter = _get_by_interface
    #!+elif interfaces.IBungeniContent.implementedBy(discriminator):
    elif issubclass(discriminator, domain.Entity):
        getter = _get_by_model
    #!+elif interfaces.IBungeniContent.providedBy(discriminator):
    elif isinstance(discriminator, domain.Entity):
        getter = _get_by_instance
    elif IWorkflow.providedBy(discriminator):
        getter = _get_by_workflow
    elif IModelDescriptor.implementedBy(discriminator):
        getter = _get_by_descriptor_model
    elif IModelDescriptor.providedBy(discriminator):
        getter = _get_by_descriptor
    
    if getter is None:
        m = "Invalid type info lookup discriminator: %s" % (discriminator)
        log.error(m)
        raise KeyError(m)
    ti = getter(discriminator)
    if ti is None:
        m = "No type registered for discriminator: %s" % (discriminator)
        log.error(m)
        raise KeyError(m)
    return ti


# following getters return "first matching" TypeInfo instance in registry
    
def _get_by_type_key(key):
    for type_key, ti in _iter():
        if type_key == key:
            return ti
def _get_by_interface(iface):
    for type_key, ti in _iter():
        if iface is ti.interface: #!+issubclass(iface, ti.interface)?
            return ti
def _get_by_model(model):
    for type_key, ti in _iter():
        if model is ti.domain_model: #!+issubclass(model, ti.domain_model)?
            return ti
def _get_by_instance(instance):
    return _get_by_model(type(instance))
def _get_by_workflow(wf):
    for type_key, ti in _iter():
        if wf is ti.workflow:
            return ti
def _get_by_descriptor_model(descriptor_model):
    for type_key, ti in _iter():
        if descriptor_model is ti.descriptor_model:
            return ti
def _get_by_descriptor(descriptor):
    return _get_by_descriptor_model(type(descriptor))

# 

class TI(object):
    """TypeInfo, associates together the following attributes for a given type:
            workflow_key 
                the workflow file name, should be same as type_key
                is None for non-workflowed types
            workflow 
                same workflow insatnce may be used by multiple types
                is None for non-workflowed types
            interface
                the dedicated interface for the type
            domain_model
                the domain class
            descriptor_model
                the descriptor model for UI views for the type
            descriptor
                a descriptor instance for UI views for the type
    """
    def __init__(self, workflow_key, iface):
        self.workflow_key = workflow_key
        self.interface = iface
        self.workflow = None
        self.domain_model = None
        self.descriptor_model = None
        self.descriptor = None
    def __str__(self):
        return str(self.__dict__)

'''
!+TYPE_REGISTRY externalize further to bungeni_custom, currently:
- association of type key and dedicated interface are hard-wired here
- ti.workflow/ti.domain_model/ti.descriptor are added dynamically when 
  loading workflows and descriptors
- type_key IS the underscore-separated lowercase of the domain cls name 
  i.e. utils.naming.polymorphic_identity(domain_model)
- !+ ti.workflow_key SHOULD always be equal to type_key

Usage:
    from bungeni.utils.capi import capi
    capi.get_type_info(discriminator) -> TypeInfo
    capi.iter_type_info() -> iterator of all registered (key, TypeInfo)
'''
TYPE_REGISTRY = [
    # (key, ti)
    # - order is relevant (dictates workflow loading order)
    # - the type key, unique for each type, is the underscore-separated 
    #   lowercase name of the domain_model (the domain class)
    # - this is the initial list only... other types added dynamically
    ("user_address", TI("address", interfaces.IUserAddress)),
    ("group_address", TI("address", interfaces.IGroupAddress)),
    # !+Attachment (mr, jul-2011)
    # a) must be loaded before any other type that *may* support attachments!
    # b) MUST support versions
    ("attachment", TI("attachment", interfaces.IAttachment)),
    ("agenda_item", TI("agendaitem", interfaces.IAgendaItem)),
    ("bill", TI("bill", interfaces.IBill)),
    ("motion", TI("motion", interfaces.IMotion)),
    ("question", TI("question", interfaces.IQuestion)),
    ("report", TI("report", interfaces.IReport)),
    ("tabled_document", TI("tableddocument", interfaces.ITabledDocument)),
    ("event", TI("event", interfaces.IEvent)),
    ("group", TI("group", interfaces.IBungeniGroup)),
    ("group_membership", TI("membership", interfaces.IBungeniGroupMembership)),
    ("committee", TI("committee", interfaces.ICommittee)),
    ("committee_member", TI("membership", interfaces.ICommitteeMember)),
    ("committee_staff", TI("membership", interfaces.ICommitteeStaff)),
    ("parliament", TI("parliament", interfaces.IParliament)),
    ("sitting", TI("sitting", interfaces.ISitting)),
    ("heading", TI("heading", interfaces.IHeading)),
    ("user", TI("user", interfaces.IBungeniUser)),
    ("signatory", TI("signatory", interfaces.ISignatory)),
]

# !+ dedicated interfaces for archetype incantations should be auto-generated, 
# from specific workflow name/attr... e.g. via:
# zope.interface.interface.InterfaceClass(iname, bases, __module__)

