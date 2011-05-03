log = __import__("logging").getLogger("bungeni.core.workflows")

from zope import component
import zope.securitypolicy.interfaces
from bungeni.models import interfaces
from bungeni.core.workflow import xmlimport
from bungeni.core.workflow.interfaces import IWorkflow, \
    IStateController, IWorkflowController
from bungeni.core.workflow.states import StateController, WorkflowController, \
    get_object_state
import bungeni.core.version
import bungeni.core.interfaces
from bungeni.utils.capi import capi

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
def provideAdapterStateController(adapts_kls):
    component.provideAdapter(StateController, (adapts_kls,), IStateController)
def provideAdapterWorkflowController(adapts_kls):
    component.provideAdapter(WorkflowController, (adapts_kls,), 
        IWorkflowController)

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
        for state_key, state in wf.states.items():
            log.debug("   STATE: %s %s" % (state_key, state))
            for p in state.permissions:
                log.debug("          %s" % (p,))
    else:
        wf = get_workflow(name)
        log.debug("Already Loaded WORKFLOW : %s %s" % (name, wf))
    #
    # register related adapters
    #
    # Workflow instances as utilities
    provideUtilityWorkflow(wf, name)
    # Workflows are also the factory of own AdaptedWorkflows
    provideAdapterWorkflow(wf, iface)
    # StateController adapts all workflow context models
    provideAdapterStateController(iface)
    if name != "version": # !+VERSION_WORKFLOW(mr, apr-2011)
        # WorkflowController adapts all workflow context models
        provideAdapterWorkflowController(iface)
    else:
        component.provideAdapter(bungeni.core.version.ContextVersioned,
            (bungeni.core.interfaces.IVersionable,),
            bungeni.core.interfaces.IVersioned)


def load_workflows():
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
    load_workflow("version", interfaces.IVersion) # !+VERSION_WORKFLOW(mr, apr-2011)
    
    # IRolePermissionMap adapter for workflowed objects
    component.provideAdapter(get_object_state, (interfaces.IBungeniContent,), 
        zope.securitypolicy.interfaces.IRolePermissionMap)
    # !+RolePermissionMap(mr, may-2011) executing this adapter registration at 
    # module top level (i.e. not within this def) does not work for the tests 

# load workflows
load_workflows()


# check/regenerate zcml directives for workflows
xmlimport.zcml_check_regenerate()


