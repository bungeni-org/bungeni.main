import zope.interface
import zope.securitypolicy.interfaces

from zope.security.proxy import removeSecurityProxy

from ore.alchemist import Session

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
    
    __slots__ = 'context',
    
    def __init__(self, context):
        self.context = context
    
    def initialize(self):
        return
    
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
    def __init__(self, id, title, permissions):
        self.id = id
        self.title = title
        self.permissions = permissions
    
    def initialize(self, context):
        """ initialize content now in this state """
        session = Session()
        _context = removeSecurityProxy(context)
        session.merge(_context)
        rpm = zope.securitypolicy.interfaces.IRolePermissionMap(_context)
        for action, permission, role in self.permissions:
            if action==GRANT:
               rpm.grantPermissionToRole(permission, role)
            if action==DENY:
               rpm.denyPermissionToRole(permission, role)

class StateTransition(Transition):
    """A state transition."""
    
    def __init__(self, transition_id, title, source, destination,
                 condition=NullCondition, action=NullAction,
                 trigger=MANUAL, permission=CheckerPublic,
                 order=0, event=None, require_confirmation=False,
                 **user_data):
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
        wf = self.workflow()
        if not isinstance(wf.workflow, StateWorkflow):
            return
        state = wf.workflow.states.get(state_id)
        if state is None:
            return
        state.initialize(self.context)

