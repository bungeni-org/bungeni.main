# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Loading of workflows and and set-up and registering of associated adapters.

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflows")

from zope import component
from zope.interface import classImplements
import zope.securitypolicy.interfaces
from bungeni.models import interfaces
from bungeni.core.workflow import xmlimport
from bungeni.core.workflow.interfaces import IWorkflow, IWorkflowed, \
    IStateController, IWorkflowController
from bungeni.core.workflow.states import StateController, WorkflowController, \
    get_object_state_rpm, get_head_object_state_rpm
import bungeni.core.audit
import bungeni.core.version
import bungeni.core.interfaces
from bungeni.utils.capi import capi

__all__ = ["get_workflow"]


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
            descriptor
                the descriptor for UI views for the type
    """
    def __init__(self, workflow_key, iface):
        self.workflow_key = workflow_key
        self.interface = iface
        self.workflow = self.domain_model = self.descriptor = None
    def __str__(self):
        return str(self.__dict__)
'''
!+TYPE_REGISTRY externalize further to bungeni_custom, currently:
- association of type key and dedicated interface are hard-wired here
- ti.workflow/ti.domain_model/ti.descriptor are added dynamically when 
  loading workflows and descriptors
- ti.workflow_key AND orm polymorphic_identity value SHOULD be == type_key!

Usage:
    from bungeni.utils.capi import capi
    capi.get_type_info(key) -> TypeInfo
    capi.iter_type_info() -> iterator of all registered (key, TypeInfo)
'''
TYPE_REGISTRY = [
    # (key, ti)
    # - order is relevant (dictates workflow loading order)
    # - the type key, unique for each type, is the underscore-separated 
    #   lowercase name of the domain_model (the domain class)
    # - 
    ("user_address", TI("address", interfaces.IUserAddress)),
    ("group_address", TI("address", interfaces.IGroupAddress)),
    # !+Attachment (mr, jul-2011)
    # a) must be loaded before any other type that *may* support attachments!
    # b) MUST support versions
    ("attachment", TI("attachment", interfaces.IAttachment)),
    ("agenda_item", TI("agendaitem", interfaces.IAgendaItem)),
    ("bill", TI("bill", interfaces.IBill)),
    ("committee", TI("committee", interfaces.ICommittee)),
    ("event", TI("event", interfaces.IEvent)),
    ("group", TI("group", interfaces.IBungeniGroup)),
    ("sitting", TI("sitting", interfaces.ISitting)),
    ("group_membership", TI("membership", interfaces.IBungeniGroupMembership)),
    ("heading", TI("heading", interfaces.IHeading)),
    ("motion", TI("motion", interfaces.IMotion)),
    ("parliament", TI("parliament", interfaces.IParliament)),
    ("question", TI("question", interfaces.IQuestion)),
    ("report", TI("report", interfaces.IReport)),
    ("tabled_document", TI("tableddocument", interfaces.ITabledDocument)),
    ("user", TI("user", interfaces.IBungeniUser)),
    ("signatory", TI("signatory", interfaces.ISignatory)),
]

# !+ dedicated interfaces for archetype incantations should be auto-generated, 
# from specific workflow name/attr... e.g. via:
# zope.interface.interface.InterfaceClass(iname, bases, __module__)

def get_workflow(name):
    """Get the named workflow utility.
    """
    #return component.getUtility(IWorkflow, name) !+BREAKS_DOCTESTS(mr, apr-2011)
    return get_workflow._WORKFLOWS[name]
# a mapping of workflow names workflow instances as a supplementary register 
# of instantiated workflows -- not cleared when componenet registry is cleared
get_workflow._WORKFLOWS = {} # { name: workflow.states.Workflow }


# component.provideUtility(component, provides=None, name=u''):
def provideUtilityWorkflow(utility, name):
    #component.provideUtility(utility, IWorkflow, name) !+BREAKS_DOCTESTS
    get_workflow._WORKFLOWS[name] = utility

# component.provideAdapter(factory, adapts=None, provides=None, name="")
def provideAdapterWorkflow(factory, adapts_kls):
    component.provideAdapter(factory, (adapts_kls,), IWorkflow)


def load_workflow(name, path_custom_workflows=capi.get_path_for("workflows")):
    """Setup (once) and return the Workflow instance, from XML definition, 
    for named workflow.
    """
    # load / register as utility / retrieve
    #
    #if not component.queryUtility(IWorkflow, name): !+BREAKS_DOCTESTS
    if not get_workflow._WORKFLOWS.has_key(name):
        wf = xmlimport.load(path_custom_workflows, name)
        log.debug("Loading WORKFLOW: %s %s" % (name, wf))
        # debug info
        for state_key, state in wf.states.items():
            log.debug("   STATE: %s %s" % (state_key, state))
            for p in state.permissions:
                log.debug("          %s" % (p,))
        # register Workflow instance as a named utility
        provideUtilityWorkflow(wf, name)
    else:
        wf = get_workflow(name)
        log.warn("Already Loaded WORKFLOW : %s %s" % (name, wf))
    return wf

def apply_customization_workflow(name, ti):
    """Apply customizations, features as per configuration from a workflow. 
    Must (currently) be run after db setup.
    """
    # support to infer/get the domain class from the type key
    def camel(name):
        """Convert an underscore-separated word to CamelCase.
        """
        return "".join([ s.capitalize() for s in name.split("_") ])
    from bungeni.models import domain, orm
    def get_domain_kls(name):
        """Infer the target domain kls from the type key, following underscore 
        naming to camel case convention.
        """
        return getattr(domain, camel(name))
    
    # get the domain class, and associate with type
    kls = get_domain_kls(name)
    ti.domain_model = kls
    
    # We "mark" the domain class with IWorkflowed, to be able to 
    # register/lookup adapters generically on this single interface.
    classImplements(kls, IWorkflowed)
    
    # dynamic features from workflow
    wf = ti.workflow
    # decorate/modify domain/schema/mapping as needed
    kls = domain.configurable_domain(kls, wf)
    orm.configurable_mappings(kls)
    
    # !+ following should be part of the domain.feature_audit(kls) logic
    if wf.has_feature("audit"):
        # create/set module-level dedicated auditor singleton for auditable kls
        bungeni.core.audit.set_auditor(kls)


def load_workflows():
    # workflow instances (+ adapter *factories*)
    for type_key, ti in TYPE_REGISTRY:
        # load/get Workflow instance for this key, and associate with type
        ti.workflow = load_workflow(ti.workflow_key)
        # adjust domain_model as per workflow, register/associate domain_model
        apply_customization_workflow(type_key, ti)


def register_workflow_adapters():
    """Register general and specific worklfow-related adapters.
    
    Note: as the registry is cleared when placelessetup.tearDown() is called,
    this needs to be called independently on each doctest.
    """
    # General adapters on generic IWorkflowed (once for all workflows).
    
    # IRolePermissionMap adapter for IWorkflowed objects
    component.provideAdapter(get_object_state_rpm, 
        (IWorkflowed,),
        zope.securitypolicy.interfaces.IRolePermissionMap)
    
    # !+VersionRolePermissionMap(mr, may-2012) superfluous, given Version is 
    # just a kind of Change?
    # IRolePermissionMap adapter for a version of an IWorkflowed object
    #component.provideAdapter(get_head_object_state_rpm, 
    #    (interfaces.IVersion,),
    #    zope.securitypolicy.interfaces.IRolePermissionMap)
    
    # IRolePermissionMap adapter for a change of an IWorkflowed object
    component.provideAdapter(get_head_object_state_rpm, 
        (interfaces.IChange,),
        zope.securitypolicy.interfaces.IRolePermissionMap)
    
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
    
    # Specific adapters, a specific iface per workflow.
    
    for name, ti in TYPE_REGISTRY:
        # Workflows are also the factory of own AdaptedWorkflows
        provideAdapterWorkflow(ti.workflow, ti.interface)


def _setup_all():
    """Do all workflow related setup.
    """
    load_workflows()
    # !+zcml_check_regenerate(mr, sep-2011) should be only done *once* and 
    # when *all* workflows are loaded i.e. only first time (on module import).
    # check/regenerate zcml directives for workflows
    xmlimport.zcml_check_regenerate()
    # cleared by each call to zope.app.testing.placelesssetup.tearDown()
    register_workflow_adapters()
    # import events module, registering handlers
    import bungeni.core.workflows.events

# do it, when this module is imported. 
_setup_all()

#

