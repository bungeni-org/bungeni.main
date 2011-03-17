import zope.interface
import zope.securitypolicy.interfaces

from zope.security.proxy import removeSecurityProxy

from bungeni.alchemist import Session

from ore.workflow.workflow import Workflow
from ore.workflow.workflow import WorkflowInfo
from ore.workflow.workflow import WorkflowVersions
from ore.workflow.workflow import Transition
from ore.workflow.workflow import NullCondition
from ore.workflow.workflow import NullAction
from ore.workflow.workflow import MANUAL
from ore.workflow.workflow import CheckerPublic
from ore.workflow.interfaces import IWorkflowState

GRANT = 1
DENY  = 0


class WorkflowState(object):
    zope.interface.implements(IWorkflowState)
    
    __slots__ = "context",
    
    def __init__(self, context):
        self.context = context
    
    def initialize(self):
        return
    
    #!+STATE(mr, mar-2011) rename to "status"
    def setState(self, state):
        if state!=self.getState():
            context = removeSecurityProxy(self.context)
            context.status = state
    
    def setId(self, id):
        pass # print "setting id", id
    
    def getState(self):
        return self.context.status
    
    def getId(self):
        return "1"


class NullVersions(WorkflowVersions):
    def hasVersionId( self, id): 
        return False


class State(object):
    
    def __init__(self, id, title, version_action, permissions):
        self.id = id
        self.title = title
        self.version_action = version_action # either(None, callable)
        self.permissions = permissions
    
    def initialize(self, context):
        """Initialize content now in this state.
        """
        assert context.status == self.id, \
            "Context [%s] status [%s] has not been updated to [%s]" % (
                context, context.status, self.id)
        session = Session()
        instance = removeSecurityProxy(context)
        session.merge(instance)
        # version
        if self.version_action:
            self.version_action(instance)
        # permissions
        rpm = zope.securitypolicy.interfaces.IRolePermissionMap(instance)
        for action, permission, role in self.permissions:
            if action==GRANT:
               rpm.grantPermissionToRole(permission, role)
            if action==DENY:
               rpm.denyPermissionToRole(permission, role)


class StateTransition(Transition):
    """A state transition.
    
    A transition from a *single* source state to a *single* destination state,
    irrespective of how it may be defined e.g. in XML from multiple possible 
    sources to a single destination (this is simply a shorthand for defining
    multiple transition). 
    
    Each Transition ID is automatically determined from the source and 
    destination states (therefore it is not passed in as a constructor 
    parameter) in the following predicatbale way:
    
        transition_id = "%s-%s" % (source or "", destination)
    
    This is the id to be used when calling WorkflowInfo.fireTransition(id), 
    as well as being the HTML id used in generated menu items, etc. 
    """
    
    def __init__(self, title, source, destination,
                 condition=NullCondition, action=NullAction,
                 trigger=MANUAL, permission=CheckerPublic,
                 order=0, event=None, require_confirmation=False,
                 **user_data):
        transition_id = "%s-%s" % (source or "", destination)
        super(StateTransition, self).__init__(
            transition_id, title, source, destination, condition,
            action, trigger, permission, order=0, **user_data)
        self.event = event
        self.require_confirmation = require_confirmation


class StateWorkflow(Workflow):
    
    def __init__(self, transitions, states):
        self.refresh(transitions, states)
    
    def refresh(self, transitions, states=None):
        super(StateWorkflow, self).refresh(transitions)
        self.states = {}
        state_names = set()
        for s in states:
            self.states[ s.id ] = s
            state_names.add(s.id)
        # find any states given that don't match a transition state
        t_state_names = set([ t.destination for t in transitions ])
        t_state_names.update(set([ t.source for t in transitions ]))
        unreachable_states = state_names - t_state_names
        if unreachable_states:
            raise SyntaxError("Workflow Contains Unreachable States %s" % (
                    unreachable_states))


class StateWorkflowInfo(WorkflowInfo):
    
    #interface.implements(interfaces.IWorkflowInfo)
    
    def _setState(self, state_id):
        # note: this is called *after* WorkflowState.setState(status) i.e. the 
        # value of self.context.status is already updated to the destination 
        # state.
        awf = self.workflow() # AdaptedWorkflow
        # taking defensive stance, asserting on awf.workflow and state
        # !+ZCA(mr, mar-2011) requiring that awf.workflow is an instance of
        # StateWorkflow undermines the whole point of using ZCA in the first 
        # place? No gain, just more convoluted code.
        assert isinstance(awf.workflow, StateWorkflow), \
            "Workflow must be an instance of StateWorkflow: %s" % (awf.workflow)
        state = awf.workflow.states.get(state_id)
        assert state is not None, "May not have a None state" 
        state.initialize(self.context)

