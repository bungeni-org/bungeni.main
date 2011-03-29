# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Workflow Library

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflow.state")

import zope.component
import zope.interface
import zope.securitypolicy.interfaces
import zope.security.management
import zope.security.interfaces
from zope.security.proxy import removeSecurityProxy
from zope.security.checker import CheckerPublic
import zope.event
import zope.lifecycleevent
from zope.dottedname.resolve import resolve
from bungeni.alchemist import Session
from bungeni.core.workflow import interfaces

#

BUNGENI_BASEPATH = "bungeni.core.workflows"
ACTIONS_MODULE = resolve("._actions", BUNGENI_BASEPATH)

GRANT = 1
DENY  = 0

# !+ needed to make the tests pass in the absence of interactions
# !+nullCheckPermission(mr, mar-2011) shouldn't the tests ensure there is 
# always an interaction?
def nullCheckPermission(permission, principal_id):
    return True

def exception_as(exc, exc_kls):
    return exc_kls("%s: %s" % (exc.__class__.__name__, exc))

    
#

class State(object):
    
    def __init__(self, id, title, action_names, permissions):
        self.id = id
        self.title = title
        self.action_names = action_names # [str]
        self.permissions = permissions
    
    def execute_actions(self, context):
        """Execute the actions and permissions associated with this state.
        """
        assert context.status == self.id, \
            "Context [%s] status [%s] has not been updated to [%s]" % (
                context, context.status, self.id)
        Session().merge(context)
        # actions -- resolve each action from current ACTIONS_MODULE and execute
        for action_name in self.action_names:
            action = getattr(ACTIONS_MODULE, action_name)
            try:
                action(context)
            except Exception, e:
                raise exception_as(e, interfaces.WorkflowStateActionError)
        # permissions
        rpm = zope.securitypolicy.interfaces.IRolePermissionMap(context)
        for action, permission, role in self.permissions:
            if action==GRANT:
               rpm.grantPermissionToRole(permission, role)
            if action==DENY:
               rpm.denyPermissionToRole(permission, role)


class Transition(object):
    """A workflow transition from source status to destination.
    
    A transition from a *single* source state to a *single* destination state,
    irrespective of how it may be defined e.g. in XML from multiple possible 
    sources to a single destination (this is simply a shorthand for defining
    multiple transitions). 
    
    Each Transition ID is automatically determined from the source and 
    destination states (therefore it is not passed in as a constructor 
    parameter) in the following predictable way:
    
        transition_id = "%s-%s" % (source or "", destination)
    
    This is the id to use when calling WorkflowController.fireTransition(id),
    as well as being the HTML id used in generated menu items, etc. 
    """
    
    def __init__(self, title, source, destination,
        condition=None,
        trigger=interfaces.MANUAL, 
        permission=CheckerPublic,
        order=0,
        require_confirmation=False,
        **user_data
    ):
        self.title = title
        self.source = source
        self.destination = destination
        self._raw_condition = condition # remember unwrapped condition
        self.condition = self._wrapped_condition(condition)
        self.trigger = trigger
        self.permission = permission
        self.order = order
        self.require_confirmation = require_confirmation
        self.user_data = user_data
   
    @property
    def transition_id(self):
        return "%s-%s" % (self.source or "", self.destination)
    
    def _wrapped_condition(self, condition):
        def test(context):
            if condition is None:
                return True
            try:
                return condition(context)
            except Exception, e:
                raise exception_as(e, interfaces.WorkflowTransitionConditionError)
        return test
    
    def __cmp__(self, other):
        return cmp(self.order, other.order)

#

class StateController(object):
    
    zope.interface.implements(interfaces.IStateController)
    
    __slots__ = "context",
    
    def __init__(self, context):
        self.context = context
    
    def getState(self):
        return self.context.status
    
    #!+STATE(mr, mar-2011) rename to "status"
    def setState(self, state_id):
        source_state_id = self.getState()
        if source_state_id != state_id:
            self.context.status = state_id
            # additional actions related to change of worklfow status
            self.on_state_change(source_state_id, state_id)
    
    def on_state_change(self, source, destination):
        workflow = interfaces.IWorkflow(self.context) 
        state = workflow._states_by_id.get(destination)
        assert state is not None, "May not have a None state" # !+NEEDED?
        state.execute_actions(self.context)
    

class Workflow(object):
    zope.interface.implements(interfaces.IWorkflow)
    
    def __init__(self, states, transitions):
        self.refresh(states, transitions)
    
    def refresh(self, states, transitions):
        self._transitions_by_source = {} # {source: {id: Transition}}
        self._transitions_by_id = {} # {id:str : Transition}
        self._states_by_id = {} # {id: State}
        # transitions
        def _register(t):
            transitions = self._transitions_by_source.setdefault(t.source, {})
            transitions[t.transition_id] = t
            self._transitions_by_id[t.transition_id] = t
        for transition in transitions:
            _register(transition)
        # states
        state_names = set()
        for s in states:
            self._states_by_id[s.id] = s
            state_names.add(s.id)
        # find any states given that don't match a transition state
        t_state_names = set([ t.destination for t in transitions ])
        t_state_names.update(set([ t.source for t in transitions ]))
        unreachable_states = state_names - t_state_names
        if unreachable_states:
            raise SyntaxError("Workflow Contains Unreachable States %s" % (
                    unreachable_states))
    
    def get_transitions_from(self, source):
        try:
            return self._transitions_by_source[source].values()
        except KeyError:
            return []
    
    # !+GET_TRANSITION(mr, mar-2011) change params to (source, dest) + combine? 
    def get_transition(self, source, transition_id):
        transition = self._transitions_by_id[transition_id]
        if transition.source != source:
            raise interfaces.InvalidTransitionError
        return transition
    
    def get_transition_by_id(self, transition_id):
        return self._transitions_by_id[transition_id]
    
    def __call__(self, context):
        """A Workflow instance is itself the factory of own AdaptedWorkflows.
        """
        # self is the workflow instance
        class AdaptedWorkflow(object):
            """A workflow adapted on context.
            """
            def __init__(awf, context):
                awf.context = context
                awf.workflow = self
            def __getattribute__(awf, name):
                try:
                    return object.__getattribute__(awf, name)
                except AttributeError:
                    return object.__getattribute__(self, name)
        return AdaptedWorkflow(context)


class WorkflowController(object):
    
    zope.interface.implements(interfaces.IWorkflowController)
        
    def __init__(self, context):
        # assume context is trusted... 
        # and unlitter all actions/conditions of calls to removeSecurityProxy
        self.context = removeSecurityProxy(context)
        self._workflow = None # cache for workflow instance
        self._state_controller = None # cache for state_controller instance
    
    # !+ rename to state_controller
    def state(self):
        if self._state_controller is None:
            self._state_controller = interfaces.IStateController(self.context)
        return self._state_controller
    
    # !+ rename to adapted_workflow
    def workflow(self):
        if self._workflow is None:
            self._workflow = interfaces.IWorkflow(self.context)
        return self._workflow
    
    def _get_checkPermission(self):
        try:
            return zope.security.management.getInteraction().checkPermission
        except zope.security.interfaces.NoInteraction:
            return nullCheckPermission
    
    def _check(self, transition, check_security):
        """Check whether we may execute this workflow transition.
        """
        if check_security:
            checkPermission = self._get_checkPermission()
        else:
            checkPermission = nullCheckPermission
        if not checkPermission(transition.permission, self.context):
            raise zope.security.interfaces.Unauthorized(self.context,
                "transition: %s" % transition.transition_id,
                transition.permission)
        # now make sure transition can still work in this context
        if not transition.condition(self.context):
            raise interfaces.ConditionFailedError
    
    def fireTransition(self, transition_id, comment=None, check_security=True):
        # !+fireTransitionParams(mr, mar-2011) needed?
        if not (comment is None and check_security is True):
            log.warn("%s.fireTransition(%s, comment=%s, check_security=%s)" % (
                self, transition_id, comment, check_security))
        state = self.state() # StateController
        wf = self.workflow() # Workflow
        # raises InvalidTransitionError if id is invalid for current state
        transition = wf.get_transition(state.getState(), transition_id)
        self._check(transition, check_security)
        # change state of context or new object
        state.setState(transition.destination)
        # notify wf event observers
        event = WorkflowTransitionEvent(self.context, 
            transition.source, transition.destination, transition, comment)
        zope.event.notify(event)
        # send modified event for original or new object
        zope.event.notify(zope.lifecycleevent.ObjectModifiedEvent(self.context))
    
    def fireTransitionToward(self, state, comment=None, check_security=True):
        transition_ids = self.getFireableTransitionIdsToward(state)
        if not transition_ids:
            raise interfaces.NoTransitionAvailableError
        if len(transition_ids) != 1:
            raise interfaces.AmbiguousTransitionError
        return self.fireTransition(transition_ids[0], comment, check_security)
    
    def fireAutomatic(self):
        for transition in self._get_transitions(interfaces.AUTOMATIC):
            try:
                self.fireTransition(transition.transition_id)
            except interfaces.ConditionFailedError:
                # fine, then we weren't ready to fire the transition as yet
                pass
            else:
                # if we actually managed to fire a transition, we're done
                return
    
    def getFireableTransitionIdsToward(self, state):
        wf = self.workflow()
        result = []
        for transition_id in self.getFireableTransitionIds():
            transition = wf.get_transition_by_id(transition_id)
            if transition.destination == state:
                result.append(transition_id)
        return result
    
    def getFireableTransitionIds(self):
        return self.getManualTransitionIds() + self.getSystemTransitionIds()
    
    def getManualTransitionIds(self):
        checkPermission = self._get_checkPermission()
        return [ transition.transition_id 
            for transition in self._get_transitions(interfaces.MANUAL, True)
            if checkPermission(transition.permission, self.context) ]
    
    def getSystemTransitionIds(self):
        # ignore permission checks
        return [ transition.transition_id 
            for transition in self._get_transitions(interfaces.SYSTEM, False) ]
    
    def _get_transitions(self, trigger_ifilter=None, conditional=False):
        """Retrieve all possible transitions from current status.
        If trigger_ifilter is not None, filter on trigger interface.
        If conditional, then only transitions that pass the condition.
        """
        transitions = self.workflow().get_transitions_from(
            self.state().getState())
        # now filter these transitions to retrieve all possible
        # transitions in this context, and return their ids
        return [ transition for transition in transitions
            if ((trigger_ifilter is None or 
                    transition.trigger == trigger_ifilter) and
                (not conditional or transition.condition(self.context))) ]


class WorkflowTransitionEvent(zope.component.interfaces.ObjectEvent):
    """The generic transition event, systematically fired at end of EVERY
    transition.
    """
    zope.interface.implements(interfaces.IWorkflowTransitionEvent)
    
    def __init__(self, object, source, destination, transition, comment):
        super(WorkflowTransitionEvent, self).__init__(object)
        self.source = source
        self.destination = destination
        self.transition = transition
        self.comment = comment

