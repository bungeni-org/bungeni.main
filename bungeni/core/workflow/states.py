# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Workflow Library

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflow.state")

import zope.interface
import zope.securitypolicy.interfaces
import zope.security.management
import zope.security.interfaces
from zope.security.proxy import removeSecurityProxy
import zope.event
import zope.lifecycleevent
from zope.dottedname.resolve import resolve
from bungeni.alchemist import Session
import ore.workflow.interfaces
import ore.workflow.workflow

#

BUNGENI_BASEPATH = "bungeni.core.workflows"
ACTIONS_MODULE = resolve("._actions", BUNGENI_BASEPATH)

#

GRANT = 1
DENY  = 0

#

def NullCondition(context): return True
def NullAction(context): pass

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
                class WorkflowStateActionError(Exception): pass
                raise WorkflowStateActionError("%s" % (e))
        # permissions
        rpm = zope.securitypolicy.interfaces.IRolePermissionMap(context)
        for action, permission, role in self.permissions:
            if action==GRANT:
               rpm.grantPermissionToRole(permission, role)
            if action==DENY:
               rpm.denyPermissionToRole(permission, role)


class Transition(ore.workflow.workflow.Transition):
    """A workflow transition from source status to destination.
    
    A transition from a *single* source state to a *single* destination state,
    irrespective of how it may be defined e.g. in XML from multiple possible 
    sources to a single destination (this is simply a shorthand for defining
    multiple transitions). 
    
    Each Transition ID is automatically determined from the source and 
    destination states (therefore it is not passed in as a constructor 
    parameter) in the following predictable way:
    
        transition_id = "%s-%s" % (source or "", destination)
    
    This is the id to be used when calling WorkflowInfo.fireTransition(id), 
    as well as being the HTML id used in generated menu items, etc. 
    """
    
    def __init__(self, title, source, destination,
        condition=NullCondition,
        trigger=ore.workflow.interfaces.MANUAL, 
        permission=ore.workflow.workflow.CheckerPublic,
        order=0, 
        event=None, 
        require_confirmation=False,
        **user_data
    ):
        transition_id = "%s-%s" % (source or "", destination)
        super(Transition, self).__init__(
            transition_id, title, source, destination, condition,
            NullAction, 
            trigger, permission, order=0, **user_data)
        self.event = event
        self.require_confirmation = require_confirmation

#

# replaces ore.workflow.workflow.WorkflowState
class StateController(object):
    zope.interface.implements(ore.workflow.interfaces.IWorkflowState)
    
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
        # note: called *after* StateController.setState(status) 
        # i.e. self.context.status is already set to destination state
        wfc = ore.workflow.interfaces.IWorkflowInfo(self.context) # WorkflowController
        workflow = wfc.workflow().workflow # AdaptedWorkflow.workflow
        # taking defensive stance, asserting on workflow and state
        # !+ZCA(mr, mar-2011) requiring that workflow is an instance of
        # bungeni.core.workflow.states.Workflow undermines the whole point of
        # using ZCA in the first place? No gain, just more convoluted code.
        assert isinstance(workflow, Workflow), \
            "Workflow must be an instance of Workflow: %s" % (workflow)
        state = workflow.states.get(destination)
        assert state is not None, "May not have a None state" 
        state.execute_actions(self.context)
    
    def getId(self):
        return "1"
    def setId(self, id):
        pass # print "setting id", id

# <!-- silly versioning thingy for wf runtime -->
class NullVersions(ore.workflow.workflow.WorkflowVersions):
    def hasVersionId(self, id): 
        return False


class Workflow(ore.workflow.workflow.Workflow):
    
    def __init__(self, transitions, states):
        self.refresh(transitions, states)
    
    def refresh(self, transitions, states=None):
        super(Workflow, self).refresh(transitions)
        self.states = {}
        state_names = set()
        for s in states:
            self.states[s.id] = s
            state_names.add(s.id)
        # find any states given that don't match a transition state
        t_state_names = set([ t.destination for t in transitions ])
        t_state_names.update(set([ t.source for t in transitions ]))
        unreachable_states = state_names - t_state_names
        if unreachable_states:
            raise SyntaxError("Workflow Contains Unreachable States %s" % (
                    unreachable_states))


class WorkflowController(ore.workflow.workflow.WorkflowInfo):
    
    #interface.implements(ore.workflow.interfaces.IWorkflowInfo)
    
    def __init__(self, context):
        # assume context is trusted... 
        # and unlitter all actions/conditions of calls to removeSecurityProxy
        self.context = removeSecurityProxy(context)
    
    def _get_checkPermission(self):
        try:
            return zope.security.management.getInteraction().checkPermission
        except zope.security.interfaces.NoInteraction:
            return ore.workflow.workflow.nullCheckPermission
            
    def _check(self, transition, check_security):
        """Check whether we may execute this workflow transition.
        """
        if check_security:
            checkPermission = self._get_checkPermission()
        else:
            checkPermission = ore.workflow.workflow.nullCheckPermission
        if not checkPermission(transition.permission, self.context):
            raise Unauthorized(self.context,
                "transition: %s" % transition.transition_id,
                transition.permission)
        # now make sure transition can still work in this context
        if not transition.condition(self.context):
            raise ore.workflow.interfaces.ConditionFailedError
    
    def fireTransition(self, transition_id, 
        comment=None, side_effect=None, check_security=True
    ):
        # !+fireTransitionParams(mr, mar-2011) needed?
        if not (comment is None and side_effect is None and 
            check_security is True
        ):
            log.warn("%s.fireTransition(%s, comment=%s, side_effect=%s, "
                "check_security=%s" % (self, transition_id, 
                    comment, side_effect, check_security)) 
        state = self.state() # StateController
        wf = self.workflow() # Workflow
        # this raises InvalidTransitionError if id is invalid for current state
        transition = wf.getTransition(state.getState(), transition_id)
        self._check(transition, check_security)
        transition.action(self.context)
        # !+ore.workflow.workflow.WorkflowState.initialize !+side_effect
        # change state of context or new object
        state.setState(transition.destination)
        # notify wf event observers
        event = ore.workflow.workflow.WorkflowTransitionEvent(self.context, 
            transition.source, transition.destination, transition, comment)
        zope.event.notify(event)
        # send modified event for original or new object
        zope.event.notify(zope.lifecycleevent.ObjectModifiedEvent(self.context))
    
    # !+CONDITION_SIGNATURE(mr, mar-2011) overridden because of change in 
    # the condition API, but are seemingly never called.
    def getManualTransitionIds(self):
        checkPermission = self._get_checkPermission()
        return [ transition.transition_id 
            for transition in sorted(
                self._getTransitions(ore.workflow.interfaces.MANUAL)) 
            if transition.condition(self.context) and 
                checkPermission(transition.permission, self.context) ]
    
    def getSystemTransitionIds(self):
        # ignore permission checks
        return [ transition.transition_id 
            for transition in sorted(
                self._getTransitions(ore.workflow.interfaces.SYSTEM)) 
            if transition.condition(self.context) ]

