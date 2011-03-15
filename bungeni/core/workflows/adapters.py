log = __import__("logging").getLogger("bungeni.core.workflows")

import os
import events
from bungeni.core.workflow import xmlimport

import bill
import question
import motion
import version
import groupsitting
import groups
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

from ore.workflow import workflow

path = os.path.split(os.path.abspath(__file__))[0]

def load_workflow(module, kls):
    name = module.__name__.rsplit('.')[-1]
    wf = xmlimport.load("%s/%s.xml" % (path, name))
    events.register_workflow_transitions(wf, kls)
    module.wf = wf
    module.states = wf.states
    _log = log.debug
    _log("WORKFLOW: %s %s" % (name, wf))
    for state_key, state in wf.states.items():
        _log("   STATE: %s %s" % (state_key, state))
        for p in state.permissions:
            _log("          %s" % (p,))
    return wf

UserAddressWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(address, domain.UserAddress))
GroupAddressWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(address, domain.GroupAddress))
AgendaItemWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(agendaitem, domain.AgendaItem))
AttachedFileWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(attachedfile, domain.AttachedFile))
BillWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(bill, domain.Bill))
CommitteeWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(committee, domain.Committee))
EventWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(event, domain.EventItem))
GroupWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(groups, domain.Group))
GroupSittingWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(groupsitting, domain.GroupSitting))
HeadingWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(heading, domain.Heading))
MotionWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(motion, domain.Motion))
ParliamentWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(parliament, domain.Parliament))
QuestionWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(question, domain.Question))
ReportWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(report, domain.Report))
TabledDocumentWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(tableddocument, domain.TabledDocument))
UserWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(user, domain.User))
VersionWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(version, IVersion))


# check/regenerate zcml directives for workflows
xmlimport.zcml_check_regenerate()
    

