log = __import__("logging").getLogger("bungeni.core.workflows")

import os
import events
from bungeni.core.workflow import xmlimport

import bill
import question
import motion
import version
import groupsitting
import group
import address
import tableddocument
import agendaitem
import committee
import parliament
import attachedfile
import event
import heading
import user
import report
from bungeni.models import domain
from bungeni.models.interfaces import IVersion

from bungeni.utils.capi import capi
PATH_CUSTOM_WORKLFOWS = capi.get_path_for("workflows")

def load_workflow(module, kls):
    """Get the Workflow instance, from XML definition, for module and kls.
    """
    name = module.__name__.rsplit('.')[-1]
    wf = xmlimport.load("%s/%s.xml" % (PATH_CUSTOM_WORKLFOWS, name), name)
    events.register_workflow_transitions(wf, kls)
    module.wf = wf
    module.states = wf._states_by_id
    _log = log.debug
    _log("WORKFLOW: %s %s" % (name, wf))
    for state_key, state in wf._states_by_id.items():
        _log("   STATE: %s %s" % (state_key, state))
        for p in state.permissions:
            _log("          %s" % (p,))
    return wf

# WorkflowAdapter *factories* -- 
# a Workflow instance is itself the factory of own AdaptedWorkflows.
UserAddressWorkflowAdapter = load_workflow(address, domain.UserAddress)
GroupAddressWorkflowAdapter = load_workflow(address, domain.GroupAddress)
AgendaItemWorkflowAdapter = load_workflow(agendaitem, domain.AgendaItem)
AttachedFileWorkflowAdapter = load_workflow(attachedfile, domain.AttachedFile)
BillWorkflowAdapter = load_workflow(bill, domain.Bill)
CommitteeWorkflowAdapter = load_workflow(committee, domain.Committee)
EventWorkflowAdapter = load_workflow(event, domain.EventItem)
GroupWorkflowAdapter = load_workflow(group, domain.Group)
GroupSittingWorkflowAdapter = load_workflow(groupsitting, domain.GroupSitting)
HeadingWorkflowAdapter = load_workflow(heading, domain.Heading)
MotionWorkflowAdapter = load_workflow(motion, domain.Motion)
ParliamentWorkflowAdapter = load_workflow(parliament, domain.Parliament)
QuestionWorkflowAdapter = load_workflow(question, domain.Question)
ReportWorkflowAdapter = load_workflow(report, domain.Report)
TabledDocumentWorkflowAdapter = load_workflow(tableddocument, domain.TabledDocument)
UserWorkflowAdapter = load_workflow(user, domain.User)
VersionWorkflowAdapter = load_workflow(version, IVersion)

# check/regenerate zcml directives for workflows
xmlimport.zcml_check_regenerate()

