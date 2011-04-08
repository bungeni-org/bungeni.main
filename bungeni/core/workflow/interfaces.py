# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Workflow Interfaces

$Id$
"""
import zope.interface
import zope.component


MANUAL = 0
AUTOMATIC = 1
SYSTEM = 2


class InvalidTransitionError(Exception): pass
class NoTransitionAvailableError(InvalidTransitionError): pass
class AmbiguousTransitionError(InvalidTransitionError): pass
class ConditionFailedError(Exception): pass

class WorkflowRuntimeError(Exception): 
    """Error while executing a workflow action""" 
class WorkflowStateActionError(WorkflowRuntimeError): 
    """Error while executing a workflow state action""" 
class WorkflowConditionError(WorkflowRuntimeError):
    """Error while executing a workflow condition""" 
class WorkflowNotificationError(WorkflowRuntimeError):
    """Error while executing a workflow notification""" 


class IWorkflow(zope.interface.Interface):
    """Defines workflow in the form of transition objects. 
    """
    def refresh(states, transitions):
        """Refresh workflow completely with new transitions.
        """
    def get_transitions_from(source):
        """Get all transitions from source.
        """
    def get_transition(source, transition_id):
        """Get transition with transition_id given source state.

        If the transition is invalid from this source state,
        an InvalidTransitionError is raised.
        """
    def get_transition_by_id(transition_id):
        """Get transition with transition_id.
        """
    def __call__(context):
        """A Workflow instance is itself the factory of own AdaptedWorkflows.
        """

class IStateController(zope.interface.Interface):
    """Store state on workflowed objects. Defined as an adapter.
    """
    def getState():
        """Return workflow state of this object.
        """
    def setState(state):
        """Set workflow state for this object.
        """


class IWorkflowController(zope.interface.Interface):
    """Get workflow info about workflowed object, and drive workflow.

    Defined as an adapter.
    """
    
    def fireTransition(transition_id, comment=None, check_security=True):
        """Fire a transition for the context object.
        
        There's an optional comment parameter that contains some
        opaque object that offers a comment about the transition.
        This is useful for manual transitions where users can motivate
        their actions.
        
        If check_security is set to False, security is not checked
        and an application can fire a transition no matter what the
        user's permission is.
        """
    def fireTransitionToward(state, comment=None, check_security=True):
        """Fire transition toward state.
        
        Looks up a manual transition that will get to the indicated
        state.
        
        If no such transition is possible, NoTransitionAvailableError will
        be raised.
        
        If more than one manual transitions are possible,
        AmbiguousTransitionError will be raised.
        """
    def fireAutomatic():
        """Fire automatic transitions if possible by condition.
        """
    def getManualTransitionIds():
        """Returns list of valid manual transitions.
        These transitions have to have a condition that's True.
        """
    def getSystemTransitionIds():
        """Returns list of possible system transitions.
        Condition and permission not checked.
        """


class IWorkflowTransitionEvent(zope.component.interfaces.IObjectEvent):
    source = zope.interface.Attribute("Original state or None if initial state")
    destination = zope.interface.Attribute("New state") 
    transition = zope.interface.Attribute(
        "Transition that was fired or None if initial state")
    comment = zope.interface.Attribute("Comment that went with state transition")


