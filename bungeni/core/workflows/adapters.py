log = __import__("logging").getLogger("bungeni.core.workflows")

from zope.component import provideAdapter
from bungeni.models import domain
from bungeni.models import interfaces as model_interfaces
from bungeni.core.workflow import xmlimport, states, interfaces
import bungeni.core.version
import bungeni.core.interfaces

from bungeni.utils.capi import capi
PATH_CUSTOM_WORKLFOWS = capi.get_path_for("workflows")

__all__ = ["WORKFLOWS", "wf"]

# a global container to easily retrieve workflow instances
WORKFLOWS = {} # { name: bungeni.core.workflow.states.Workflow }

def wf(name):
    """Get the named workflow."""
    return WORKFLOWS[name]

# provideAdapter(factory, adapts=None, provides=None, name="")

def provideAdapterWorkflow(factory, adapts_kls):
    provideAdapter(factory, (adapts_kls,), interfaces.IWorkflow)

def provideAdapterStateController(adapts_kls):
    provideAdapter(states.StateController, (adapts_kls,), 
        interfaces.IStateController)

def provideAdapterWorkflowController(adapts_kls):
    provideAdapter(states.WorkflowController, (adapts_kls,), 
        interfaces.IWorkflowController)

def load_workflow(name, kls):
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
    provideAdapterWorkflow(w, kls)
    provideAdapterStateController(kls)
    if name != "version":
        provideAdapterWorkflowController(kls)
    else:
        provideAdapter(bungeni.core.version.ContextVersioned,
            (bungeni.core.interfaces.IVersionable,),
            bungeni.core.interfaces.IVersioned)

#

# workflow instances (+ adapter *factories*)
load_workflow("address", domain.UserAddress)
load_workflow("address", domain.GroupAddress)
load_workflow("agendaitem", domain.AgendaItem)
load_workflow("attachedfile", domain.AttachedFile)
load_workflow("bill", domain.Bill)
load_workflow("committee", domain.Committee)
load_workflow("event", domain.EventItem)
load_workflow("group", domain.Group)
load_workflow("groupsitting", domain.GroupSitting)
load_workflow("heading", domain.Heading)
load_workflow("motion", domain.Motion)
load_workflow("parliament", domain.Parliament)
load_workflow("question", domain.Question)
load_workflow("report", domain.Report)
load_workflow("tableddocument", domain.TabledDocument)
load_workflow("user", domain.User)
load_workflow("version", model_interfaces.IVersion)

# check/regenerate zcml directives for workflows
xmlimport.zcml_check_regenerate()

