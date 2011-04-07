log = __import__("logging").getLogger("bungeni.core.workflows")

from zope.component import provideAdapter
from bungeni.models import interfaces
from bungeni.core import workflow
from bungeni.core.workflow import xmlimport
import bungeni.core.version
import bungeni.core.interfaces

from bungeni.utils.capi import capi
PATH_CUSTOM_WORKLFOWS = capi.get_path_for("workflows")

__all__ = ["WORKFLOWS", "wf"]

# a global container to easily retrieve workflow instances
WORKFLOWS = {} # { name: workflow.states.Workflow }

def wf(name):
    """Get the named workflow."""
    return WORKFLOWS[name]

# provideAdapter(factory, adapts=None, provides=None, name="")

def provideAdapterWorkflow(factory, adapts_kls):
    provideAdapter(factory, (adapts_kls,), workflow.interfaces.IWorkflow)

def provideAdapterStateController(adapts_kls):
    provideAdapter(workflow.states.StateController, (adapts_kls,), 
        workflow.interfaces.IStateController)

def provideAdapterWorkflowController(adapts_kls):
    provideAdapter(workflow.states.WorkflowController, (adapts_kls,), 
        workflow.interfaces.IWorkflowController)

def load_workflow(name, iface):
    """Get the Workflow instance, from XML definition, for named workflow.
    """
    _log = log.debug
    global WORKFLOWS
    if not WORKFLOWS.has_key(name):
        w = xmlimport.load("%s/%s.xml" % (PATH_CUSTOM_WORKLFOWS, name), name)
        WORKFLOWS[name] = w
        _log("Loading WORKFLOW: %s %s" % (name, w))
        for state_key, state in w.states.items():
            _log("   STATE: %s %s" % (state_key, state))
            for p in state.permissions:
                _log("          %s" % (p,))
    else:
        w = WORKFLOWS[name]
        _log("Already Loaded WORKFLOW : %s %s" % (name, w))
    # a Workflow instance is itself the factory of own AdaptedWorkflows
    provideAdapterWorkflow(w, iface)
    provideAdapterStateController(iface)
    if name != "version": # !+VERSION_WORKFLOW(mr, apr-2011)
        provideAdapterWorkflowController(iface)
    else:
        provideAdapter(bungeni.core.version.ContextVersioned,
            (bungeni.core.interfaces.IVersionable,),
            bungeni.core.interfaces.IVersioned)

#

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

