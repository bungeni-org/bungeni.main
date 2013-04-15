# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Aggregation of information about loaded domain types.

No public methods here -- all available methods from this are those exposed 
via bungeni.capi.

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist.type_info")

from zope.interface.interfaces import IInterface
from zope.security.proxy import removeSecurityProxy
from zope.dottedname.resolve import resolve

from bungeni.alchemist.interfaces import IModelDescriptor, IIModelInterface
from bungeni.alchemist.model import (
    new_custom_domain_interface,
    new_custom_domain_model,
)
from bungeni.alchemist.catalyst import (
    INTERFACE_MODULE, 
    MODEL_MODULE
)
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
        discri = naming.type_key("table_schema_interface_name", discri.__name__)
    elif IInterface.providedBy(discri):
        discri = naming.type_key("model_interface_name", discri.__name__)
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
    log.debug(m)
    raise KeyError(m)


# following getters return "first matching" TypeInfo instance in registry
    
def _get_by_type_key(key):
    for type_key, ti in _iter():
        if type_key == key:
            return ti
#def _get_by_interface(iface):
''' !+IALCHEMISTCONTENT fails on different interfaces with same name!
    !+mar-2013 is above still true?
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
                the workflow file name
                defaults to the type_key for workflowed types that DO NOT specify
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
            archetype
                the domain model for:
                a) either the (system or custom) archetype of the custom type
                b) or the (mapped) base type of the system type, or None
            descriptor_model
                the descriptor model for UI views for the type
            container_class
                container class for domain_model
            container_interface
                interface for the container class for domain_model
    """
    def __init__(self, workflow_key, iface, domain_model, archetype):
        self.workflow_key = workflow_key
        self.interface = iface
        self.derived_table_schema = None # provides IIModelInterface
        self.workflow = None
        self.domain_model = domain_model
        self.archetype = archetype
        self.descriptor_model = None
        self.container_class = None
        self.container_interface = None
        self.custom = False # type loaded from custom configuration 
        # NOTE: only needed temporarily during loading (until descriptor_model 
        # is set) -- but from then on ti.custom must not be inconsistent with 
        # descriptor_model.scope i.e.
        #if self.custom: assert self.descriptor_model.scope == "custom"
    
    def __str__(self):
        return str(self.__dict__)
    
    @property
    def scope(self):
        # !+CUSTOM_TYPE_DESCRIPTOR the self.custom check below MUST precede the
        # check on self.descriptor_model.scope as otherwise the "in-transit" 
        # custom types will not be picked up as custom types -- as during
        # loading the descriptors for all custom types may not yet have been 
        # autogenerated (and would therefore correctly have 
        # descriptor_model.scope="custom" set).
        if self.custom:
            return "custom"
        if self.descriptor_model is not None:
            return self.descriptor_model.scope
    
    @property
    def permission_type_key(self):
        if self.custom:
            # custom types ALWAYS have a type_key-bound workflow instance - that
            # may therefore have a different name than workflow_key e.g. Office
            # uses the "group" workflow, that is type-relative reloaded as the
            # "office" workflow instance.
            return self.workflow.name
        # system types ALWAYS use workflow_key - even if multiple types use the 
        # same workflow e.g. UserAddress & GroupAddress. 
        # if no workflow, compute type_key from domain_model
        # #!+REDUNDANT(mb, 2012) This type key is already known during type
        # setup i.e. TYPE_REGISTRY
        return (self.workflow_key or 
            naming.type_key("model_name", self.domain_model.__name__)
        )

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
    from bungeni.capi import capi
    capi.get_type_info(discriminator) -> TypeInfo
    capi.iter_type_info() -> iterator of all registered (key, TypeInfo)
'''
TYPE_REGISTRY = [
    # (key, ti)
    # - the type key, unique for each type, is the underscore-separated 
    #   lowercase name of the domain_model (the domain class)
    # - order is relevant (dictates workflow loading order)
    
    # feature "support" types, system types, required
    
    # workflowed
    ("user_address", TI("address", interfaces.IUserAddress, domain.UserAddress, domain.Address)),
    ("group_address", TI("address", interfaces.IGroupAddress, domain.GroupAddress, domain.Address)),
    # !+Attachment (mr, jul-2011)
    # a) must be loaded before any other type that *may* support attachments!
    # b) MUST support versions
    ("attachment", TI("attachment", interfaces.IAttachment, domain.Attachment, None)),
    ("event", TI("event", interfaces.IEvent, domain.Event, domain.Doc)),
    ("sitting", TI("sitting", interfaces.ISitting, domain.Sitting, None)),
    ("heading", TI("heading", interfaces.IHeading, domain.Heading, None)),
    ("user", TI("user", interfaces.IBungeniUser, domain.User, domain.Principal)),
    ("signatory", TI("signatory", interfaces.ISignatory, domain.Signatory, None)),
    
    # !+NAMING: member-related -> Group name + "Member" (no + "ship")
    ("group", TI("group", interfaces.IBungeniGroup, domain.Group, domain.Principal)),
    ("group_membership", TI("group_membership", interfaces.IBungeniGroupMembership, domain.GroupMembership, None)),
    ("group_document_assignment", 
        TI("group_assignment", interfaces.IGroupDocumentAssignment, domain.GroupDocumentAssignment, None)),
    ("debate_record", TI("debate_record", interfaces.IDebateRecord, domain.DebateRecord, None)),
    # non-workflowed
    ("o_auth_application", TI(None, interfaces.IOAuthApplication, domain.OAuthApplication, None)),
    ("debate_media", TI(None, interfaces.IDebateMedia, domain.DebateMedia, None)),
    ("user_delegation", TI(None, interfaces.IUserDelegation, domain.UserDelegation, None)),
    ("title_type", TI(None, interfaces.ITitleType, domain.TitleType, None)),
    ("member_title", TI(None, interfaces.IMemberTitle, domain.MemberTitle, None)),
    ("change", TI(None, interfaces.IChange, domain.Change, None)),
    ("doc", TI(None, interfaces.IDoc, domain.Doc, None)),
    ("doc_version", TI(None, interfaces.IDocVersion, domain.DocVersion, domain.Change)),
    ("attachment_version", TI(None, None, domain.AttachmentVersion, domain.Change)), #interfaces.IAttachmentVersion)), #!+IVERSION
    ("venue", TI(None, interfaces.IVenue, domain.Venue, None)),
    ("session", TI(None, interfaces.ISession, domain.Session, None)),
    ("sitting_attendance", TI(None, interfaces.ISittingAttendance, domain.SittingAttendance, None)),
    ("country", TI(None, interfaces.ICountry, domain.Country, None)),
    ("item_schedule", TI(None, interfaces.IItemSchedule, domain.ItemSchedule, None)),
    ("item_schedule_discussion", TI(None, interfaces.IItemScheduleDiscussion, domain.ItemScheduleDiscussion, None)),
    ("item_schedule_vote", TI(None, interfaces.IItemScheduleVote, domain.ItemScheduleVote, None)),
    ("editorial_note", TI(None, interfaces.IEditorialNote, domain.EditorialNote, None)),
    ("agenda_text_record", TI(None, interfaces.IAgendaTextRecord, domain.AgendaTextRecord, None)),
    ("sitting_report", TI(None, interfaces.ISittingReport, domain.SittingReport, None)),
    ("group_membership_role", TI(None, interfaces.IGroupMembershipRole, domain.GroupMembershipRole, None)),
    
    # additional custom types are loaded dynamically from bungeni_custom/types.xml
]




# register custom types

def register_new_custom_type(type_key, workflow_key, 
        custom_archetype_key, sys_archetype_key
    ):
    """Retrieve (create if needed) a domain interface and model for type_key,
    and register as new entry on TYPE_REGISTER.
    """
    archetype_model = resolve("%s.%s" % (
            MODEL_MODULE.__name__, naming.model_name(custom_archetype_key)))
    # validate that custom archetype uses correct system archetype
    if custom_archetype_key != sys_archetype_key:
        sys_archetype_model = resolve("%s.%s" % (
                MODEL_MODULE.__name__, naming.model_name(sys_archetype_key)))
        assert issubclass(archetype_model, sys_archetype_model), \
            "Custom archetype %r for type %r is not a sub-type of %r." % (
                custom_archetype_key, type_key, sys_archetype_key)
    
    # generate custom domain interface
    domain_iface_name = naming.model_interface_name(type_key)
    try:
        domain_iface = resolve("%s.%s" % (INTERFACE_MODULE.__name__, domain_iface_name))
        log.warn("Custom interface ALREADY EXISTS: %s" % (domain_iface))
    except ImportError:
        domain_iface = new_custom_domain_interface(type_key, domain_iface_name)
    
    # generate custom domain_model
    domain_model_name = naming.model_name(type_key)
    try:
        domain_model = resolve("%s.%s" % (MODEL_MODULE.__name__, domain_model_name))
        log.warn("Custom domain model ALREADY EXISTS: %s" % (domain_model))
    except ImportError:
        domain_model = new_custom_domain_model(type_key, domain_iface, custom_archetype_key)
    
    # type_info entry
    ti = TI(workflow_key, domain_iface, domain_model, archetype_model)
    ti.custom = True
    TYPE_REGISTRY.append((type_key, ti))
    
    log.info("Registered custom type [%s]: %s" % (custom_archetype_key, type_key))
    return type_key, ti







