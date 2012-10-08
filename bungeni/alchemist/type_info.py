# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Aggregation of information about loaded domain types.

No public methods here -- all available methods from this are those exposed 
via bungeni.utils.capi.

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist.type_info")

from zope.interface.interfaces import IInterface
from zope.security.proxy import removeSecurityProxy
from bungeni.alchemist.interfaces import IModelDescriptor, IIModelInterface
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

''' !+UNUSED
def _add(workflow_key, iface, workflow, domain_model, descriptor_model):
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
        TYPE_REGISTRY.append((type_key, ti))
    else:
        raise ValueError, "An type entry for [%s] already exists." % (type_key)
'''

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
    discri = removeSecurityProxy(discriminator)
    getter = None
    
    # !+IALCHEMISTCONTENT normalize trickier discriminator cases to type_key
    if IIModelInterface.providedBy(discri):
        discri = naming.type_key_from_table_schema_interface_name(discri.__name__)
    elif IInterface.providedBy(discri):
        discri = naming.type_key_from_model_interface_name(discri.__name__)
    elif type(discri) is type and issubclass(discri, domain.Entity):
        discri = naming.polymorphic_identity(discri)
    elif isinstance(discri, domain.Entity):
        discri = naming.polymorphic_identity(type(discri))
    
    if isinstance(discri, basestring):
        getter = _get_by_type_key
    #elif IInterface.providedBy(discri):
    #    getter = _get_by_interface
    #!+elif interfaces.IBungeniContent.implementedBy(discri):
    #elif issubclass(discri, domain.Entity):
    #    getter = _get_by_model
    #!+elif interfaces.IBungeniContent.providedBy(discri):
    #elif isinstance(discri, domain.Entity):
    #    getter = _get_by_instance
    elif IWorkflow.providedBy(discri):
        getter = _get_by_workflow
    elif IModelDescriptor.implementedBy(discri):
        getter = _get_by_descriptor_model
    
    if getter is not None:
        ti = getter(discri)
        if ti is not None:
            return ti
        else:
            m = "No type registered for discriminator: %r" % (discriminator)
    else: 
        m = "Invalid type info lookup discriminator: %r" % (discriminator)
    from bungeni.ui.utils import debug
    log.debug(debug.interfaces(discriminator))
    log.error(m)
    raise KeyError(m)


# following getters return "first matching" TypeInfo instance in registry
    
def _get_by_type_key(key):
    for type_key, ti in _iter():
        if type_key == key:
            return ti
#def _get_by_interface(iface):
''' !+IALCHEMISTCONTENT fails on different interfaces with same name!
(Pdb) ti.interface
<InterfaceClass bungeni.models.interfaces.ISession>
(Pdb) ti.interface.__bases__
(<InterfaceClass ore.alchemist.interfaces.ITableSchema>, <InterfaceClass ore.alchemist.interfaces.IAlchemistContent>)
(Pdb) iface
<InterfaceClass bungeni.models.interfaces.ISession>
(Pdb) iface.__bases__
(<InterfaceClass zope.interface.Interface>,)
'''
#    for type_key, ti in _iter():
#        if iface is ti.interface: #!+issubclass(iface, ti.interface)?
#            return ti
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
                the manually applied application-dedicated model interface 
                (if any) for the type
            derived_table_schema
                auto-generated db schema interface, provides IIModelInterface
            domain_model
                the domain class
            descriptor_model
                the descriptor model for UI views for the type
            container_class
                conatiner class for domain_model
    """
    def __init__(self, workflow_key, iface):
        self.workflow_key = workflow_key
        self.interface = iface
        self.derived_table_schema = None # provides IIModelInterface
        self.workflow = None
        self.domain_model = None
        self.descriptor_model = None
        self.container_class = None
        self.custom = False # type loaded from custom configuration
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
- !+ corresponding Container/Version/X interfaces should ALWAYS be auto-generated
- !+ dedicated interfaces for archetype incantations should be auto-generated, 
    from specific workflow name/attr... e.g. via:
    zope.interface.interface.InterfaceClass(iname, bases, __module__)
- !+ should ti.interface be automatically generated also for system types?

Usage:
    from bungeni.utils.capi import capi
    capi.get_type_info(discriminator) -> TypeInfo
    capi.iter_type_info() -> iterator of all registered (key, TypeInfo)
'''
TYPE_REGISTRY = [
    # (key, ti)
    # - the type key, unique for each type, is the underscore-separated 
    #   lowercase name of the domain_model (the domain class)
    # - order is relevant (dictates workflow loading order)
    
    ## feature "support" types, system types, required
    
    # workflowed
    ("user_address", TI("address", interfaces.IUserAddress)),
    ("group_address", TI("address", interfaces.IGroupAddress)),
    # !+Attachment (mr, jul-2011)
    # a) must be loaded before any other type that *may* support attachments!
    # b) MUST support versions
    ("attachment", TI("attachment", interfaces.IAttachment)),
    ("event", TI("event", interfaces.IEvent)),
    ("sitting", TI("sitting", interfaces.ISitting)),
    ("heading", TI("heading", interfaces.IHeading)),
    ("user", TI("user", interfaces.IBungeniUser)),
    ("signatory", TI("signatory", interfaces.ISignatory)),
    ("report", TI("report", interfaces.IReport)),
    
    # !+NAMING: member-related -> Group name + "Member" (no + "ship")
    ("group", TI("group", interfaces.IBungeniGroup)),
    ("group_membership", TI("membership", interfaces.IBungeniGroupMembership)),
    
    # non-workflowed
    ("user_delegation", TI(None, interfaces.IUserDelegation)),
    ("title_type", TI(None, interfaces.ITitleType)),
    ("member_title", TI(None, interfaces.IMemberTitle)),
    ("doc", TI(None, interfaces.IDoc)),
    ("doc_version", TI(None, None)), #interfaces.IDocVersion)), #!+IVERSION
    ("change", TI(None, interfaces.IChange)),
    ("attachment_version", TI(None, None)), #interfaces.IAttachmentVersion)), #!+IVERSION
    ("venue", TI(None, interfaces.IVenue)),
    ("session", TI(None, interfaces.ISession)),
    ("sitting_attendance", TI(None, interfaces.ISittingAttendance)),
    ("country", TI(None, interfaces.ICountry)),
    ("item_schedule", TI(None, interfaces.IItemSchedule)),
    ("item_schedule_discussion", TI(None, interfaces.IItemScheduleDiscussion)),
    ("editorial_note", TI(None, interfaces.IEditorialNote)),
    ("report4_sitting", TI(None, interfaces.IReport4Sitting)),
    ("group_membership_role", TI(None, interfaces.IGroupMembershipRole)),
    ## custom types -- loaded dynamically from bungeni_custom/types.xml
]








