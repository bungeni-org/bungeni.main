log = __import__("logging").getLogger("bungeni.core.workflows")

from zope import component
from bungeni.models import interfaces
from bungeni.core.workflow import xmlimport
from bungeni.core.workflow.interfaces import IWorkflow, \
    IStateController, IWorkflowController
from bungeni.core.workflow.states import StateController, WorkflowController
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

PATH_CUSTOM_WORKLFOWS = capi.get_path_for("workflows")

def load_workflow(name, iface):
    """Setup the Workflow instance, from XML definition, for named workflow.
    """
    #
    # load / register as utility / retrieve
    #
    #if not component.queryUtility(IWorkflow, name): !+BREAKS_DOCTESTS
    if not _WORKFLOWS.has_key(name): 
        wf = xmlimport.load("%s/%s.xml" % (PATH_CUSTOM_WORKLFOWS, name), name)
        provideUtilityWorkflow(wf, name)
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


# check/regenerate zcml directives for workflows
xmlimport.zcml_check_regenerate()

