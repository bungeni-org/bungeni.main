# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Workflow Interfaces

$Id$
"""
import zope.interface

from ore.workflow.interfaces import (
    #InvalidTransitionError,
    NoTransitionAvailableError,
    #AmbiguousTransitionError,
    ConditionFailedError,
    IWorkflow,
    #IAdaptedWorkflow,
    #IReadWorkflowVersions,
    #IWriteWorkflowVersions,
    #IWorkflowVersions,
    IWorkflowTransitionEvent,
    IWorkflowVersionTransitionEvent,
)

MANUAL = 0
AUTOMATIC = 1
SYSTEM = 2


class IStateController(zope.interface.Interface):
    """Store state on workflowed objects.
    
    Defined as an adapter.
    """
    def getState():
        """Return workflow state of this object.
        """
    def setState(state):
        """Set workflow state for this object.
        """
    '''
    def setId(id):
        """Set workflow version id for this object.

        This is used to mark all versions of an object with the
        same id.
        """
    def getId():
        """Get workflow version id for this object.

        This is used to mark all versions of an object with the same id.
        """
    '''

class IWorkflowController(zope.interface.Interface):
    """Get workflow info about workflowed object, and drive workflow.

    Defined as an adapter.
    """
    
    ''' !+UNUSED(mr, mar-2011)
    def setInitialState(state, comment=None):
        """Set initial state for the context object.
        
        Will also set a unique id for this new workflow.
        
        Fires a transition event.
        """
    '''
    
    def fireTransition(transition_id, comment=None, side_effect=None,
            check_security=True):
        """Fire a transition for the context object.
        
        There's an optional comment parameter that contains some
        opaque object that offers a comment about the transition.
        This is useful for manual transitions where users can motivate
        their actions.
        
        There's also an optional side effect parameter which should
        be a callable which receives the object undergoing the transition
        as the parameter. This could do an editing action of the newly
        transitioned workflow object before an actual transition event is
        fired.
        
        If check_security is set to False, security is not checked
        and an application can fire a transition no matter what the
        user's permission is.
        """
    
    def fireTransitionToward(state, comment=None, side_effect=None,
            check_security=True):
        """Fire transition toward state.
        
        Looks up a manual transition that will get to the indicated
        state.
        
        If no such transition is possible, NoTransitionAvailableError will
        be raised.
        
        If more than one manual transitions are possible,
        AmbiguousTransitionError will be raised.
        """
    
    ''' !+UNUSED(mr, mar-2011)
    def fireTransitionForVersions(state, transition_id):
        """Fire a transition for all versions in a state.
        """
    '''
    
    def fireAutomatic():
        """Fire automatic transitions if possible by condition.
        """
    
    ''' !+UNUSED(mr, mar-2011)
    def hasVersion(state):
        """Return true if a version exists in state.
        """
    '''
    
    def getManualTransitionIds():
        """Returns list of valid manual transitions.

        These transitions have to have a condition that's True.
        """
    
    ''' !+UNUSED(mr, mar-2011)
    def getManualTransitionIdsToward(state):
        """Returns list of manual transitions towards state.
        """

    def getAutomaticTransitionIds():
        """Returns list of possible automatic transitions.
        
        Condition is not checked.
        """
    
    def hasAutomaticTransitions():
        """Return true if there are possible automatic outgoing transitions.
        
        Condition is not checked.
        """
    '''
    
    

