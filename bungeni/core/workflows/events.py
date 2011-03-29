# encoding: utf-8

from zope import component
from bungeni.core.workflow import states, interfaces
from bungeni.core.workflows import notification


@component.adapter(interfaces.IWorkflowTransitionEvent)
def workflowTransitionNotifier(event):
    type_name, status = type(event.object).__name__, event.destination
    try:
        for notifier in notification.NOTIFIER_REGISTRY[type_name][status]:
            try:
                # execute: create notifier, and if condition, send notification
                notifier(event.object)
            except Exception, e:
                states.exception_as(e, interfaces.WorkflowNotificationError)
    except KeyError, e:
        pass # no notifiers registered for (type, status)


def initializeWorkflow(object, event):
    """In response to object created events.
    event:zope.lifecycleevent.ObjectCreatedEvent
    """
    if interfaces.IWorkflow(object, None) is None:
        return
    
    workflow = interfaces.IWorkflowController(object, None)
    if workflow is not None:
        workflow.fireAutomatic()


def fireAutomaticTransitions(object, event):
    """Fire automatic transitions for a new state.
    event:bungeni.core.workflow.interfaces.IWorkflowTransitionEvent
    """
    if interfaces.IWorkflow(object, None) is None:
        return
    
    workflow = interfaces.IWorkflowController(object, None)
    if workflow is not None:
        workflow.fireAutomatic()


