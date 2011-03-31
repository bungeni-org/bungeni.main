log = __import__("logging").getLogger("bungeni.core.workflows")

from bungeni.models import domain
from bungeni.models import interfaces
from bungeni.core.workflow import xmlimport

from bungeni.utils.capi import capi
PATH_CUSTOM_WORKLFOWS = capi.get_path_for("workflows")

# a global container to easily retrieve workflow instances
WORKFLOWS = {} # { name: bungeni.core.workflow.states.Workflow }

def wf(name):
    """Get the named workflow."""
    return WORKFLOWS[name]

#

def load_workflow(name, kls):
    """Get the Workflow instance, from XML definition, for named workflow.
    !+KLS(mr, mar-2011) kls parametr not being used, what is it for?
    """
    wf = xmlimport.load("%s/%s.xml" % (PATH_CUSTOM_WORKLFOWS, name), name)
    global WORKFLOWS
    assert not WORKFLOWS.has_key(name)
    WORKFLOWS[name] = wf
    _log = log.debug
    _log("WORKFLOW: %s %s" % (name, wf))
    for state_key, state in wf.states.items():
        _log("   STATE: %s %s" % (state_key, state))
        for p in state.permissions:
            _log("          %s" % (p,))
    return wf

# WorkflowAdapter *factories* -- 
# a Workflow instance is itself the factory of own AdaptedWorkflows.
UserAddressWorkflowAdapter = load_workflow("address", domain.UserAddress)
GroupAddressWorkflowAdapter = wf("address") # domain.GroupAddress
AgendaItemWorkflowAdapter = load_workflow("agendaitem", domain.AgendaItem)
AttachedFileWorkflowAdapter = load_workflow("attachedfile", domain.AttachedFile)
BillWorkflowAdapter = load_workflow("bill", domain.Bill)
CommitteeWorkflowAdapter = load_workflow("committee", domain.Committee)
EventWorkflowAdapter = load_workflow("event", domain.EventItem)
GroupWorkflowAdapter = load_workflow("group", domain.Group)
GroupSittingWorkflowAdapter = load_workflow("groupsitting", domain.GroupSitting)
HeadingWorkflowAdapter = load_workflow("heading", domain.Heading)
MotionWorkflowAdapter = load_workflow("motion", domain.Motion)
ParliamentWorkflowAdapter = load_workflow("parliament", domain.Parliament)
QuestionWorkflowAdapter = load_workflow("question", domain.Question)
ReportWorkflowAdapter = load_workflow("report", domain.Report)
TabledDocumentWorkflowAdapter = load_workflow("tableddocument", 
    domain.TabledDocument)
UserWorkflowAdapter = load_workflow("user", domain.User)
VersionWorkflowAdapter = load_workflow("version", interfaces.IVersion)

# check/regenerate zcml directives for workflows
xmlimport.zcml_check_regenerate()

