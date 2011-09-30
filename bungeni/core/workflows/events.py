# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Workflows

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflows.events")

from zope import component
from bungeni.core.workflow import interfaces


@component.adapter(interfaces.IWorkflowTransitionEvent)
def workflowTransitionEventHandler(event):
    log.debug(" ".join(["<%s",
        "source=%s",
        "destination=%s",
        "object=%s",
        "comment=%s",
        ">"]) % (event.__class__.__name__, 
                event.source, event.destination, event.object, event.comment))


def initializeWorkflow(object, event):
    """In response to object created events.
    event:zope.lifecycleevent.ObjectCreatedEvent
    """
    wfc = interfaces.IWorkflowController(object, None)
    if wfc is not None:
        wfc.fireAutomatic()


def fireAutomaticTransitions(object, event):
    """Fire automatic transitions for a new state.
    event:bungeni.core.workflow.interfaces.IWorkflowTransitionEvent
    """
    if interfaces.IWorkflow(object, None) is None:
        return
    
    workflow = interfaces.IWorkflowController(object, None)
    if workflow is not None:
        workflow.fireAutomatic()


