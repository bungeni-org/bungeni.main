# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Workflows

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflows.events")

from bungeni.utils import register
from bungeni.core.workflow import interfaces
from bungeni.alchemist.interfaces import IAlchemistContent
from zope.lifecycleevent import IObjectCreatedEvent


@register.handler(adapts=(interfaces.IWorkflowTransitionEvent,))
def workflowTransitionEventHandler(event):
    log.debug(" ".join(["<%s %s",
        "source=%s",
        "destination=%s",
        "object=%s",
        "comment=%s",
        ">"]) % (event.__class__.__name__, hex(id(event)),
                event.source, event.destination, event.object, event.comment))


@register.handler(adapts=(IAlchemistContent, IObjectCreatedEvent))
def initializeWorkflow(object, event):
    """In response to object created events.
    event:zope.lifecycleevent.ObjectCreatedEvent
    """
    fireAutomaticTransitions(object, event)


@register.handler(adapts=(IAlchemistContent, interfaces.IWorkflowTransitionEvent))
def fireAutomaticTransitions(object, event):
    """Fire automatic transitions for a new state.
    event:bungeni.core.workflow.interfaces.IWorkflowTransitionEvent
    """
    wfc = interfaces.IWorkflowController(object, None)
    if wfc is not None:
        wfc.fireAutomatic()


