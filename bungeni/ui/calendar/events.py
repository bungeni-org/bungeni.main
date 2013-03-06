# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Calendar event handlers

Handlers for various scheduling objects after creation/change

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.calendar")

from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from bungeni.models import  interfaces
from bungeni.utils import register
from bungeni.core.workflow.interfaces import IWorkflowController

@register.handler(adapts=(interfaces.ISitting, IObjectRemovedEvent))
@register.handler(adapts=(interfaces.IItemSchedule, IObjectRemovedEvent))
def retract_scheduled_items(context, event):
    """This method will unschedule an item when it is removed from the agenda
    or when the sitting is deleted.
    """
    def retract_item(item):
        manager = interfaces.ISchedulingManager(item, None)
        if manager is None:
            return
        wfc = IWorkflowController(item, None)
        if wfc is None:
            return

        #take back to schedule pending
        for state in manager.schedulable_states:
            transitions = wfc.getFireableTransitionIdsToward(state)
            if transitions:
                wfc.fireTransition(transitions[0])
                break

    if interfaces.IItemSchedule.providedBy(context):
        retract_item(context.item)
    elif interfaces.ISitting.providedBy(context):
        map(retract_item, context.items.values())
