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

def new_custom_domain_model(type_key):
    # !+archetype? move to types? what about extended/derived/container attrs?
    def get_elem(type_key):
        import elementtree.ElementTree
        file_path = capi.get_path_for("forms", "custom.xml") # !+
        xml = elementtree.ElementTree.fromstring(misc.read_file(file_path))
        for elem in xml.findall("descriptor"):
            if misc.xml_attr_str(elem, "name") == type_key:
                return elem
    edescriptor = get_elem(type_key)
    archetype_key = misc.xml_attr_str(edescriptor, "archetype")
    domain_model_name = naming.model_name(type_key)
    assert archetype_key, \
        "Custom descriptor %r does not specify an archetype" % (type_key)
    archetype = getattr(MODEL_MODULE, naming.model_name(archetype_key))
    # !+ assert archetype constraints
    domain_model = type(domain_model_name,
        (archetype,),
        dict(__module__=MODEL_MODULE.__name__)
    )
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

def register_specific_workflow_adapter(ti):
    # Specific adapter on specific iface per workflow.
    # Workflows are also the factory of own AdaptedWorkflows
    assert ti.workflow, ti
    assert ti.interface, ti
    # component.provideAdapter(factory, adapts=None, provides=None, name="")
    component.provideAdapter(ti.workflow, (ti.interface,), IWorkflow)


def load_workflow(type_key, workflow_key,
        path_custom_workflows=capi.get_path_for("workflows")
    ):
    """Setup (once) and return the Workflow instance, from XML definition, 
    for named workflow.
    """
    # retrieve / load
    try:
        wf = Workflow.get_singleton(workflow_key)
        log.warn("Already Loaded WORKFLOW : %s %s" % (workflow_key, wf))
    except KeyError:
        wf = xmlimport.load(type_key, workflow_key, path_custom_workflows)
        log.info("Loaded WORKFLOW: %s %s" % (workflow_key, wf))
        # debug info
        for state_key, state in wf.states.items():
            log.debug("   STATE: %s %s" % (state_key, state))
            for p in state.permissions:
                log.debug("          %s" % (p,))
    return wf

def apply_customization_workflow(type_key, ti):
    """Apply customizations, features as per configuration from a workflow. 
    Must (currently) be run after db setup.
    """
    domain_model = ti.domain_model
    # We "mark" the domain class with IWorkflowed, to be able to 
    # register/lookup adapters generically on this single interface.
    #assert not IWorkflowed.implementedBy(domain_model), domain_model
    if not IWorkflowed.implementedBy(domain_model):
        classImplements(domain_model, IWorkflowed)
    
    # dynamic features from workflow
    wf = ti.workflow
    # decorate/modify domain/schema/mapping as needed
    from bungeni.models import feature
    domain_model = feature.configurable_domain(domain_model, wf)
    feature.configurable_mappings(domain_model)
    
    # !+ following should be part of the domain.feature_audit(domain_model) logic
    if wf.has_feature("audit"):
        # create/set module-level dedicated auditor singleton for auditable domain_model
        bungeni.core.audit.set_auditor(domain_model)


def load_workflows(type_info_iterator):
    def get_domain_model(type_key):
        """Infer and retrieve the target domain model class from the type key.
        Raise Attribute error if not defined on domain.
        """
        return resolve("bungeni.models.domain.%s" % (naming.model_name(type_key)))
    # workflow instances (+ adapter *factories*)
    for type_key, ti in type_info_iterator:
        if not ti.custom:
            # get the domain class and associate domain class with type
            utils.inisetattr(ti, "domain_model", get_domain_model(type_key))
        # load/get workflow instance (if any) and associate with type
        if ti.workflow_key is not None:
            ti.workflow = load_workflow(type_key, ti.workflow_key)

def setup_workflows(type_info_iterator):
    for type_key, ti in type_info_iterator:
        if ti.workflow:
            # adjust domain_model as per workflow
            apply_customization_workflow(type_key, ti)
            register_specific_workflow_adapter(ti)


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
            model_iface = resolve("bungeni.models.interfaces.%s" % (model_iname))
            log.warn("Custom interface ALREADY EXISTS: %s" % (model_iface))
        except ImportError:
            model_iface = new_custom_model_interface(type_key, model_iname)
        # generate custom domain_model
        domain_model_name = naming.model_name(type_key)
        try:
            domain_model = resolve("bungeni.models.domain.%s" % (domain_model_name))
            log.warn("Custom domain model ALREADY EXISTS: %s" % (domain_model))
        except ImportError:
            domain_model = new_custom_domain_model(type_key)
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


def _setup_all():
    """Do all workflow related setup.
    """
    log.info("adapters._setup_all() ------------------------------------------")
    # cleared by each call to zope.app.testing.placelesssetup.tearDown()
    register_generic_workflow_adapters()
    
    # load workflows for system/registered types
    load_workflows(capi.iter_type_info())
    setup_workflows(capi.iter_type_info())
    
    # extend type registry with custom types
    register_custom_types()
    load_workflows(capi.iter_type_info(scope="custom"))
    setup_workflows(capi.iter_type_info(scope="custom"))

# do it (when this module is loaded)
_setup_all()

#

