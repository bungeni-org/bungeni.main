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
from bungeni.alchemist.model import (
    new_custom_model_interface,
    new_custom_domain_model,
)
from bungeni.utils import naming, misc
from bungeni.capi import capi
from bungeni.alchemist.catalyst import (
    INTERFACE_MODULE, 
    MODEL_MODULE
)


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


@capi.bungeni_custom_errors
def register_custom_types():
    """Extend TYPE_REGISTRY with the declarations from bungeni_custom/types.xml.
    This is called prior to loading of the workflows for these custom types.
    Returns (type_key, TI) for the newly created TI instance.
    """
    from bungeni.alchemist.type_info import TYPE_REGISTRY, TI
    from bungeni.models import feature
    from bungeni.capi import capi
    
    def register_type(type_elem):
        type_key = misc.xml_attr_str(type_elem, "name")
        workflow_key = misc.xml_attr_str(type_elem, "workflow", default=type_key)
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
            archetype_key = type_elem.tag # !+archetype? move to types?
            domain_model = new_custom_domain_model(type_key, model_iface, archetype_key)
        
        '''!+localize_domain_model_from_descriptor_class
        # !+archetype? move to types? what about extended/derived/container attrs?
        def get_descriptor_elem(type_key):
            file_path = capi.get_path_for("forms", "%s.xml" % (type_key))
            descriptor_doc = capi.schema.validate_file_rng("descriptor", file_path)
            assert misc.xml_attr_str(descriptor_doc, "name") == type_key, type_key
            return descriptor_doc
        
        # add declarations of any extended/derived properties
        descriptor_elem = get_descriptor_elem(type_key)
        if descriptor_elem is not None:
            archetype_key = misc.xml_attr_str(descriptor_elem, "archetype") # !+archetype? move to types?
            for f_elem in descriptor_elem.findall("field"):
                
                # extended
                extended_type = misc.xml_attr_str(f_elem, "extended")
                if extended_type is not None:
                    name = misc.xml_attr_str(f_elem, "name")
                    add_extended_property_to_model(domain_model, 
                        name, extended_type, archetype_key)
                
                # derived
                derived = misc.xml_attr_str(f_elem, "derived")
                if derived is not None:
                    name = misc.xml_attr_str(f_elem, "name")
                    add_derived_property_to_model(domain_model, name, derived)
            
            # !+instrument_extended_properties, doc
            MODEL_MODULE.instrument_extended_properties(domain_model, "doc")
        
        # !+ add containers, derived
        '''
        
        # type_info
        ti = TI(workflow_key, model_iface, domain_model)
        ti.custom = True
        TYPE_REGISTRY.append((type_key, ti))
        
        log.info("Registered custom type [%s]: %s" % (type_elem.tag, type_key))
        return type_key, ti
    
    attr_name_inconsistency_map = { # !+ correct incosistency, rel_attr config
        "agenda_items": ("agendaitems", "group_id"),
        "tabled_documents": ("tableddocuments", "parliament_id"),
        "reports": ("preports", "group_id"),
    }
    def set_one2many_attrs_on_domain_models(type_key, ti):
        container_qualname = "bungeni.models.domain.%s" % (
            naming.container_class_name(type_key))
        attr_name = naming.plural(type_key)
        # parliament
        attr_name, rel_attr = attr_name_inconsistency_map.get(
            attr_name, (attr_name, "parliament_id")) # !+
        parliament_model = resolve("%s.%s" % (MODEL_MODULE.__name__, "Parliament"))
        feature.set_one2many_attr(parliament_model, attr_name, container_qualname, rel_attr)
        # user
        user_model = resolve("%s.%s" % (MODEL_MODULE.__name__, "User"))
        feature.set_one2many_attr(user_model, attr_name, container_qualname, "owner_id")
        # !+ministry
        # ("questions", "group_id")
        # ("bills", "group_id")
    
    # load XML file
    etypes = etree.fromstring(misc.read_file(capi.get_path_for("types.xml")))
    # register enabled types
    for edoc in etypes.iterchildren("doc"):
        if not misc.xml_attr_bool(edoc, "enabled", default=True):
            # not enabled, ignore
            continue
        type_key, ti = register_type(edoc)
        set_one2many_attrs_on_domain_models(type_key, ti)
    # group/member types
    for egroup in etypes.iterchildren("group"):
        if not misc.xml_attr_bool(egroup, "enabled", default=True):
            # not enabled, ignore
            continue
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

