log = __import__("logging").getLogger("bungeni.core.workflows")

from zope import component
import zope.securitypolicy.interfaces
from bungeni.models import interfaces
from bungeni.core.workflow import xmlimport
from bungeni.core.workflow.interfaces import IWorkflow, IWorkflowed, \
    IStateController, IWorkflowController, IWorkspaceTabsUtility
from bungeni.core.workflow.states import StateController, WorkflowController, \
    get_object_state
import bungeni.core.version
import bungeni.core.interfaces
from bungeni.utils.capi import capi
from bungeni.core.workflow import workspace
__all__ = ["get_workflow"]

def get_workflow(name):
    """Get the named workflow utility.
    """
    #return component.getUtility(IWorkflow, name) !+BREAKS_DOCTESTS(mr, apr-2011)
    return _WORKFLOWS[name]

# a global container with a named reference to each workflow instances
# as a supplementary register (by name) of instantiated workflows
_WORKFLOWS = {} # { name: workflow.states.Workflow }

# component.provideUtility(component, provides=None, name=u''):
def provideUtilityWorkflow(utility, name):
    #component.provideUtility(utility, IWorkflow, name) !+BREAKS_DOCTESTS
    _WORKFLOWS[name] = utility
# component.provideAdapter(factory, adapts=None, provides=None, name="")
def provideAdapterWorkflow(factory, adapts_kls):
    component.provideAdapter(factory, (adapts_kls,), IWorkflow)


def load_workflow(name, iface, 
        path_custom_workflows=capi.get_path_for("workflows")
    ):
    """Setup the Workflow instance, from XML definition, for named workflow.
    """
    #
    # load / register as utility / retrieve
    #
    #if not component.queryUtility(IWorkflow, name): !+BREAKS_DOCTESTS
    if not _WORKFLOWS.has_key(name):
        wf = xmlimport.load(path_custom_workflows, name)
        log.debug("Loading WORKFLOW: %s %s" % (name, wf))
        
        # debug info
        for state_key, state in wf.states.items():
            log.debug("   STATE: %s %s" % (state_key, state))
            for p in state.permissions:
                log.debug("          %s" % (p,))
    else:
        wf = get_workflow(name)
        log.debug("Already Loaded WORKFLOW : %s %s" % (name, wf))
    # We "mark" the supplied iface with IWorkflowed, as a means to mark type 
    # the iface is applied (that, at this point, may not be unambiguously 
    # determined). This has the advantage of then being able to 
    # register/lookup adapters on only this single interface.
    #
    # A simple way to "mark" the supplied iface with IWorkflowed is to 
    # "add" IWorkflowed as an inheritance ancestor to iface:
    if (IWorkflowed not in iface.__bases__):
        iface.__bases__ = (IWorkflowed,) + iface.__bases__
    
    # register related adapters
    
    # Workflow instances as utilities
    provideUtilityWorkflow(wf, name)
    # Workflows are also the factory of own AdaptedWorkflows
    provideAdapterWorkflow(wf, iface)
    # !+VERSION_WORKFLOW(mr, apr-2011)
    if name == "version":
        component.provideAdapter(bungeni.core.version.ContextVersioned,
            (bungeni.core.interfaces.IVersionable,),
            bungeni.core.interfaces.IVersioned)


def load_workflows():
    component.provideUtility(workspace.WorkspaceTabsUtility())
    # workflow instances (+ adapter *factories*)
    load_workflow("address", interfaces.IUserAddress)
    load_workflow("address", interfaces.IGroupAddress)
    load_workflow("agendaitem", interfaces.IAgendaItem)
    load_workflow("attachedfile", interfaces.IAttachedFile)
    load_workflow("bill", interfaces.IBill)
    load_workflow("committee", interfaces.ICommittee)
    load_workflow("event", interfaces.IEventItem)
    load_workflow("group", interfaces.IBungeniGroup)
    load_workflow("groupsitting", interfaces.IGroupSitting)
    load_workflow("heading", interfaces.IHeading)
    load_workflow("motion", interfaces.IMotion)
    load_workflow("parliament", interfaces.IParliament)
    load_workflow("question", interfaces.IQuestion)
    load_workflow("report", interfaces.IReport)
    load_workflow("tableddocument", interfaces.ITabledDocument)
    load_workflow("user", interfaces.IBungeniUser)
    load_workflow("signatory", interfaces.ISignatory)
    load_workflow("version", interfaces.IVersion) # !+VERSION_WORKFLOW(mr, apr-2011)
    
    # adapters on IWorkflowed needing registration only once
    
    # IRolePermissionMap adapter for IWorkflowed objects
    component.provideAdapter(get_object_state, (IWorkflowed,),
        zope.securitypolicy.interfaces.IRolePermissionMap)
    # !+RolePermissionMap(mr, may-2011) executing this adapter registration at 
    # module top level (i.e. not within this def) does not work for the tests 
    
    # IStateController
    component.provideAdapter(
        StateController, (IWorkflowed,), IStateController)
    # IWorkflowController
    component.provideAdapter(
        WorkflowController, (IWorkflowed,), IWorkflowController)

# load workflows
load_workflows()


# check/regenerate zcml directives for workflows
xmlimport.zcml_check_regenerate()


