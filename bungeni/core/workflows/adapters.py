# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Loading of workflows and and set-up and registering of associated adapters.

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflows")

from lxml import etree
from zope import component
from zope.interface import classImplements
import zope.securitypolicy.interfaces
from zope.dottedname.resolve import resolve
from bungeni.models import interfaces
from bungeni.core.workflow import xmlimport
from bungeni.core.workflow.interfaces import IWorkflow, IWorkflowed, \
    IStateController, IWorkflowController
from bungeni.core.workflow.states import StateController, WorkflowController, \
    Workflow, get_object_state_rpm, get_head_object_state_rpm
import bungeni.core.audit
from bungeni.alchemist import utils
from bungeni.utils import naming, misc
from bungeni.utils.capi import capi, bungeni_custom_errors

from bungeni.alchemist.catalyst import (
    INTERFACE_MODULE, 
    MODEL_MODULE
)

def new_custom_model_interface(type_key, model_iname):
    import zope.interface
    model_iface = zope.interface.interface.InterfaceClass(
        model_iname,
        bases=(interfaces.IBungeniContent,), # !+archetype?
        __module__=INTERFACE_MODULE.__name__
    )
    # set on INTERFACE_MODULE (register on type_info downstream)
    setattr(INTERFACE_MODULE, model_iname, model_iface)
    log.info("new_custom_model_interface [%s] %s.%s" % (
            type_key, INTERFACE_MODULE.__name__, model_iname))
    return model_iface

def new_custom_domain_model(type_key, model_interface):
    # !+archetype? move to types? what about extended/derived/container attrs?
    def get_elem(type_key):
        import elementtree.ElementTree
        file_path = capi.get_path_for("forms", "custom.xml") # !+
        xml = elementtree.ElementTree.fromstring(misc.read_file(file_path))
        for elem in xml.findall("descriptor"):
            if misc.xml_attr_str(elem, "name") == type_key:
                return elem
        else:
            raise KeyError("No configuration for custom descriptor %r." % (type_key))
    edescriptor = get_elem(type_key)
    archetype_key = misc.xml_attr_str(edescriptor, "archetype")
    domain_model_name = naming.model_name(type_key)
    assert archetype_key, \
        "Custom descriptor %r does not specify an archetype" % (type_key)
    archetype = getattr(MODEL_MODULE, naming.model_name(archetype_key)) # AttributeError
    # !+ assert archetype constraints
    domain_model = type(domain_model_name,
        (archetype,),
        dict(__module__=MODEL_MODULE.__name__)
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


def apply_customization_workflow(type_key, ti):
    """Apply customizations, features as per configuration from a workflow. 
    Must (currently) be run after db setup.
    """
    domain_model, workflow = ti.domain_model, ti.workflow
    assert domain_model and workflow, ti
    # We "mark" the domain class with IWorkflowed, to be able to 
    # register/lookup adapters generically on this single interface.
    #!+directlyImplementedBy? assert not IWorkflowed.implementedBy(domain_model), domain_model
    if not IWorkflowed.implementedBy(domain_model):
        classImplements(domain_model, IWorkflowed)
    # dynamic features from workflow - setup domain/mapping as needed
    from bungeni.models import feature
    feature.configurable_domain(domain_model, workflow)
    feature.configurable_mappings(domain_model)

def register_specific_workflow_adapter(ti):
    # Specific adapter on specific iface per workflow.
    # Workflows are also the factory of own AdaptedWorkflows.
    # Note: cleared by each call to zope.app.testing.placelesssetup.tearDown()
    assert ti.workflow, ti
    assert ti.interface, ti
    # component.provideAdapter(factory, adapts=None, provides=None, name="")
    component.provideAdapter(ti.workflow, (ti.interface,), IWorkflow)

def register_generic_workflow_adapters():
    """Register general and specific worklfow-related adapters.
    
    Note: as the registry is cleared when placelessetup.tearDown() is called,
    this needs to be called independently on each doctest.
    """
    # General adapters on generic IWorkflowed (once for all workflows).
    
    # IRolePermissionMap adapter for IWorkflowed objects
    component.provideAdapter(get_object_state_rpm, 
        (IWorkflowed,),
        zope.securitypolicy.interfaces.IRolePermissionMap)
    # NOTE: the rpm instance returned by IRolePermissionMap(workflowed) is
    # different for different values of workflowed.status
    
    # IRolePermissionMap adapter for a change of an IWorkflowed object
    component.provideAdapter(get_head_object_state_rpm, 
        (interfaces.IChange,),
        zope.securitypolicy.interfaces.IRolePermissionMap)
    # NOTE: the rpm instance returned by IRolePermissionMap(change) is
    # different for different values of change.head.status
    
    # !+IPrincipalRoleMap(mr, aug-2011) also migrate principal_role_map from 
    # db to be dynamic and based on workflow definitions. Would need to infer
    # the Roles of a user with respect to the context e.g.owner, or signatory
    # and then check against the permissions required by the current object's
    # state. 
    
    # IStateController
    component.provideAdapter(
        StateController, (IWorkflowed,), IStateController)
    # IWorkflowController
    component.provideAdapter(
        WorkflowController, (IWorkflowed,), IWorkflowController)    
    

@bungeni_custom_errors
def register_custom_types():
    """Extend TYPE_REGISTRY with the declarations from bungeni_custom/types.xml.
    This is called prior to loading of the workflows for these custom types.
    """
    from bungeni.alchemist.type_info import TYPE_REGISTRY, TI
    def register_type(elem):
        if not misc.xml_attr_bool(elem, "enabled", default=True):
            # not enabled, ignore
            return
        type_key = misc.xml_attr_str(elem, "name")
        workflow_key = misc.xml_attr_str(elem, "workflow", default=type_key)
        # generate custom interface
        model_iname = naming.model_interface_name(type_key)
        try: 
            model_iface = resolve("%s.%s" % (INTERFACE_MODULE.__name__, model_iname))
            log.warn("Custom interface ALREADY EXISTS: %s" % (model_iface))
        except ImportError:
            model_iface = new_custom_model_interface(type_key, model_iname)
        # generate custom domain_model
        domain_model_name = naming.model_name(type_key)
        try:
            domain_model = resolve("%s.%s" % (MODEL_MODULE.__name__, domain_model_name))
            log.warn("Custom domain model ALREADY EXISTS: %s" % (domain_model))
        except ImportError:
            domain_model = new_custom_domain_model(type_key, model_iface)
        # type_info
        ti = TI(workflow_key, model_iface, domain_model)
        ti.custom = True
        TYPE_REGISTRY.append((type_key, ti))
        log.info("Registering custom type [%s]: %s" % (elem.tag, type_key))
    
    # load XML file
    etypes = etree.fromstring(misc.read_file(capi.get_path_for("types.xml")))
    # register types
    for edoc in etypes.iterchildren("doc"):
        register_type(edoc)
    # group/member types
    for egroup in etypes.iterchildren("group"):
        register_type(egroup)
        for emember in egroup.iterchildren("member"):
            register_type(emember)


def load_workflow(type_key, ti):
    """Load (from XML definition), set the workflow instance, and setup (once).
    """
    if ti.workflow_key is None:
        return
    assert ti.workflow is None
    workflow_file_key = ti.workflow_key # workflow file name
    
    # workflow_name -> what becomes workflow.name (and ti.permissions_type_key)
    workflow_name = workflow_file_key 
    if ti.custom and type_key != workflow_file_key:
        workflow_name = type_key         
    # !+ only (non-custom type) "address" wf is multi-used by user_address/group_address
    
    try:
        # retrieve
        ti.workflow = Workflow.get_singleton(workflow_name)
        log.warn("Already Loaded WORKFLOW: %s.xml as %r - %s" % (
            workflow_file_key, workflow_name, ti.workflow))
    except KeyError:
        # load
        ti.workflow = xmlimport.load(workflow_file_key, workflow_name)
        log.info("Loaded WORKFLOW: %s.xml as %r - %s" % (
            workflow_file_key, workflow_name, ti.workflow))
        # debug info
        for state_key, state in ti.workflow.states.items():
            log.debug("   STATE: %s %s" % (state_key, state))
            for p in state.permissions:
                log.debug("          %s" % (p,))
    
    # setup
    if ti.workflow:
        apply_customization_workflow(type_key, ti)
        register_specific_workflow_adapter(ti)


def retrieve_domain_model(type_key):
    """Infer and retrieve the target domain model class from the type key.
    Raise Attribute error if not defined on domain.
    """
    return resolve("%s.%s" % (MODEL_MODULE.__name__, naming.model_name(type_key)))

def _setup_all():
    """Do all workflow related setup.
    """
    log.info("adapters._setup_all() ------------------------------------------")
    # cleared by each call to zope.app.testing.placelesssetup.tearDown()
    register_generic_workflow_adapters()
    
    # system and archetypes
    for type_key, ti in capi.iter_type_info():
        # retrieve the domain class and associate domain class with this type
        utils.inisetattr(ti, "domain_model", retrieve_domain_model(type_key))
        # load/get workflow instance (if any) and associate with type
        load_workflow(type_key, ti)
    
    # custom types
    register_custom_types()
    for type_key, ti in capi.iter_type_info(scope="custom"):
        # load/get workflow instance (if any) and associate with type
        load_workflow(type_key, ti)
    
    # check/regenerate zcml directives for workflows - needs to be when and 
    # right-after *all* workflows are loaded (to pre-empt further application 
    # loading with possibly stale permission configuration).
    from bungeni.core.workflow import xmlimport
    xmlimport.zcml_check_regenerate()

# do it (when this module is loaded)
_setup_all()

#

