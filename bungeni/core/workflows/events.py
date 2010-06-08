# encoding: utf-8

from zope import interface
from zope import component
from zope.event import notify
from zope.component.interfaces import ObjectEvent
from ore.workflow import interfaces
from ore.workflow.interfaces import IWorkflow
from ore.workflow.interfaces import IWorkflowInfo


# global workflow transition event map
workflow_transition_event_map = {}

def get_workflow_transitions(wf):
    return wf._id_transitions.values()
    
def register_workflow_transitions(wf, kls):
    """Use this method to register workflow transitions, such that
    events will be fired after a transition."""
    
    for t in get_workflow_transitions(wf):
        if t.event:
            workflow_transition_event_map[
                (kls, t.source, t.destination)] = t.event

@component.adapter(interfaces.IWorkflowTransitionEvent)
def workflowTransitionEventDispatcher(event):
    source = event.source
    destination = event.destination

    iface = workflow_transition_event_map.get(
        (type(event.object), source, destination))

    if iface is None:
        for specification in interface.providedBy(event.object):
            iface = workflow_transition_event_map.get(
                (specification, source, destination))
            if iface is not None:
                break

    if iface is not None:
        transition_event = ObjectEvent(event.object)
        interface.alsoProvides(transition_event, iface)
        notify(transition_event)

def initializeWorkflow( object, event):
    """ in response to object created events """

    if IWorkflow(object, None) is None:
        return
    
    workflow = IWorkflowInfo(object, None)
    if workflow is not None:
        workflow.fireAutomatic()

def fireAutomaticTransitions( object, event ):
    """ fire automatic transitions for a new state """
    
    if IWorkflow(object, None) is None:
        return
    
    workflow = IWorkflowInfo(object, None)
    if workflow is not None:
        workflow.fireAutomatic()


