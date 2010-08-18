import os
import events
import xmlimport

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
    return wf

QuestionWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(question, domain.Question))
MotionWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(motion, domain.Motion))
BillWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(bill, domain.Bill))
VersionWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(version, IVersion))
GroupSittingWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(groupsitting, domain.GroupSitting))
AddressWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(address, domain.UserAddress))
TabledDocumentWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(tableddocument, domain.TabledDocument))
AgendaItemWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(agendaitem, domain.AgendaItem))
ParliamentWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(parliament, domain.Parliament))
CommitteeWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(committee, domain.Committee))
GroupWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(groups, domain.Group))
AttachedFileWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(attachedfile, domain.AttachedFile))
EventWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(event, domain.EventItem))
HeadingWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(heading, domain.Heading))
UserWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(user, domain.User))
ReportWorkflowAdapter = workflow.AdaptedWorkflow(
    load_workflow(report, domain.Report))

