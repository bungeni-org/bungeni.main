# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Loading of workflows and and set-up and registering of associated adapters.

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflows")

from zope import component
import zope.securitypolicy.interfaces
from bungeni.models import interfaces
from bungeni.core.workflow import xmlimport
from bungeni.core.workflow.interfaces import IWorkflow, IWorkflowed, \
    IStateController, IWorkflowController
from bungeni.core.workflow.states import StateController, WorkflowController, \
    get_object_state_rpm, get_object_version_state_rpm
import bungeni.core.audit
import bungeni.core.version
import bungeni.core.interfaces
from bungeni.utils.capi import capi

__all__ = ["get_workflow"]

WORKFLOW_REG = [
    # (name, iface)
    ("address", interfaces.IUserAddress),
    ("address", interfaces.IGroupAddress),
    # !+AttachedFile (mr, jul-2011)
    # a) must be loaded before any other type that *may* support attachments!
    # b) MUST support versions
    ("attachedfile", interfaces.IAttachedFile),
    ("agendaitem", interfaces.IAgendaItem),
    ("bill", interfaces.IBill),
    ("committee", interfaces.ICommittee),
    ("event", interfaces.IEventItem),
    ("group", interfaces.IBungeniGroup),
    ("groupsitting", interfaces.IGroupSitting),
    ("heading", interfaces.IHeading),
    ("motion", interfaces.IMotion),
    ("parliament", interfaces.IParliament),
    ("question", interfaces.IQuestion),
    ("report", interfaces.IReport),
    ("tableddocument", interfaces.ITabledDocument),
    ("user", interfaces.IBungeniUser),
    ("signatory", interfaces.ISignatory),
]


def get_workflow(name):
    """Get the named workflow utility.
    """
    #return component.getUtility(IWorkflow, name) !+BREAKS_DOCTESTS(mr, apr-2011)
    return get_workflow._WORKFLOWS[name]
# a global container with a named reference to each workflow instances
# as a supplementary register (by name) of instantiated workflows
get_workflow._WORKFLOWS = {} # { name: workflow.states.Workflow }


# component.provideUtility(component, provides=None, name=u''):
def provideUtilityWorkflow(utility, name):
    #component.provideUtility(utility, IWorkflow, name) !+BREAKS_DOCTESTS
    get_workflow._WORKFLOWS[name] = utility
# component.provideAdapter(factory, adapts=None, provides=None, name="")
def provideAdapterWorkflow(factory, adapts_kls):
    component.provideAdapter(factory, (adapts_kls,), IWorkflow)


def load_workflow(name, iface,
        path_custom_workflows=capi.get_path_for("workflows")
    ):
    """Setup the Workflow instance, from XML definition, for named workflow.
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
        # Workflow instances as utilities
        provideUtilityWorkflow(wf, name)
    else:
        wf = get_workflow(name)
        log.warn("Already Loaded WORKFLOW : %s %s" % (name, wf))


def apply_customization_workflow(name):
    """Apply customizations, features as per configuration from a workflow. 
    Must (currently) be run after db setup.
    """
    def camel(name):
        """Convert an underscore-separated word to CamelCase."""
        return "".join([ s.capitalize() for s in name.split("_") ])
    from bungeni.models import domain, schema, orm
    def get_domain_kls(workflow_name):
        """Infer a workflow's target domain kls from the workflow file name, 
        following underscore naming to camel case convention; names that do 
        not follow the convention are custom handled, as per mapping below.
        """
        # !+ should state it explicitly as a param?
        # !+ problem with multiple types sharing same workflow e.g. 
        #    UserAddress, GroupAddress
        kls_name = camel(
            get_domain_kls.non_conventional.get(workflow_name, workflow_name))
        return getattr(domain, kls_name)
    # !+RENAME_TO_CONVENTION
    get_domain_kls.non_conventional = {
        "address": "user_address", # "group_address"?
        "agendaitem": "agenda_item",
        "attachedfile": "attached_file",
        "event": "event_item",
        "groupsitting": "group_sitting",
        "tableddocument": "tabled_document",
    }
    wf = get_workflow(name)
    if wf.auditable or wf.versionable:
        # decorate the kls
        kls = get_domain_kls(name)
        # versionable implies auditable
        if wf.versionable:
            kls = domain.versionable(kls)
        elif wf.auditable:
            kls = domain.auditable(kls)
        # modify schema/mapping as needed
        schema.configurable_schema(kls)
        orm.configurable_mappings(kls)
        # create/set module-level dedicated auditor singleton for auditable kls
        bungeni.core.audit.set_auditor(kls)


def load_workflows():
    # workflow instances (+ adapter *factories*)
    for name, iface in WORKFLOW_REG:
        load_workflow(name, iface)
        # !+ address: UserAddress, GroupAddress
        apply_customization_workflow(name)


def register_workflow_adapters():
    """Register general and specific worklfow-related adapters.
    
    Note: as the registry is cleared when placelessetup.tearDown() is called,
    this needs to be called independently on each docttest.
    """
    # General adapters on generic IWorkflowed (once for all workflows).
    
    # IRolePermissionMap adapter for IWorkflowed objects
    component.provideAdapter(get_object_state_rpm, 
        (IWorkflowed,),
        zope.securitypolicy.interfaces.IRolePermissionMap)
    # IRolePermissionMap adapter for a version of an IWorkflowed object
    component.provideAdapter(get_object_version_state_rpm, 
        (interfaces.IVersion,),
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
    
    # IVersioned
    component.provideAdapter(bungeni.core.version.ContextVersioned,
        (interfaces.IVersionable,),
        bungeni.core.interfaces.IVersioned)
    
    # Specific adapters, a specific iface per workflow.
    for name, iface in WORKFLOW_REG:
        wf = get_workflow(name)
        # Workflows are also the factory of own AdaptedWorkflows
        provideAdapterWorkflow(wf, iface)

        # We "mark" the supplied iface with IWorkflowed, as a means to mark type 
        # the iface is applied (that, at this point, may not be unambiguously 
        # determined). This has the advantage of then being able to 
        # register/lookup adapters on only this single interface.
        # 
        # Normally this is done by applying the iface to the target type, but
        # at this point may may not be unambiguously determined--so, we instead 
        # "mark" the interface itself... by simply adding IWorkflowed as an 
        # inheritance ancestor to iface (if it is not already):
        if (IWorkflowed not in iface.__bases__):
            iface.__bases__ = (IWorkflowed,) + iface.__bases__
        # !+IITEMVersionInheritsIITEM(mr, sep-2011) this does cause some pollution
        # sometimes e.g. given that an IBillVersion is NOT workflowed, but it 
        # inherits from IBill, that is workflowed, IBillVersion will incorrectly 
        # gain IWorklfowed via this monkey-patched interface inheritance.


def setup_all():
    """Do all workflow related setup.
    """
    load_workflows()
    # !+ should be only done when *all* workflows are loaded i.e. first time!
    # check/regenerate zcml directives for workflows
    xmlimport.zcml_check_regenerate()
    register_workflow_adapters()

# do it...
setup_all()

#

