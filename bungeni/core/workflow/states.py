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
from bungeni.alchemist import Session
from bungeni.core.workflow import interfaces

#

# we only have 1 or 0 i.e. only Allow or Deny, no Unset.
IntAsSetting = { 
    1: zope.securitypolicy.interfaces.Allow,
    0: zope.securitypolicy.interfaces.Deny
}

GRANT, DENY = 1, 0

# !+ needed to make the tests pass in the absence of interactions
# !+nullCheckPermission(mr, mar-2011) shouldn't the tests ensure there is 
# always an interaction?
def nullCheckPermission(permission, principal_id):
    return True

def exceptions_as(exc_kls, include_name=True):
    def _exceptions_as(f):
        """Decorator to intercept any error raised by function f and 
        re-raise it as a exc_kls. 
        """
        def _errorable_f(*args, **kw):
            try: 
                return f(*args, **kw)
            except Exception, e:
                if include_name:
                    raise exc_kls("%s: %s" % (e.__class__.__name__, e))
                else:
                    raise exc_kls("%s" % (e))
        return _errorable_f
    return _exceptions_as

def wrapped_condition(condition):
    def test(context):
        if condition is None:
            return True
        try:
            return condition(context)
        except Exception, e:
            raise interfaces.WorkflowConditionError("%s: %s [%s/%s]" % (
                e.__class__.__name__, e, context, condition))
    return test


class Feature(object):
    """Status/settings of an optional feature on a workflowed type.
    """
    def __init__(self, name, enabled=True, note=None, **kws):
        self.name = name
        self.enabled = enabled
        self.note = note
        self.params = kws


class State(object):
    """A workflow state instance. 
    
    For workflowed objects, we infer the permission setting from the permission
    declarations of each workflow state.
    """
    zope.interface.implements(zope.securitypolicy.interfaces.IRolePermissionMap)
    
    def __init__(self, id, title, note, actions, permissions, notifications,
            permissions_from_parent=False, obsolete=False
        ):
        self.id = id # status
        self.title = title
        self.note = note
        self.actions = actions # [callable]
        self.permissions = permissions
        self.notifications = notifications
        self.permissions_from_parent = permissions_from_parent
        self.obsolete = obsolete
    
    @exceptions_as(interfaces.WorkflowStateActionError)
    def execute_actions(self, context):
        """Execute the actions associated with this state.
        """
        assert context.status == self.id, \
            "Context [%s] status [%s] has not been updated to [%s]" % (
                context, context.status, self.id)
        Session().merge(context)
        # actions
        for action in self.actions:
            action(context)
        '''
        # permissions
        rpm = zope.securitypolicy.interfaces.IRolePermissionMap(context)
        for assign, permission, role in self.permissions:
            if assign == GRANT:
               rpm.grantPermissionToRole(permission, role)
            if assign == DENY:
               rpm.denyPermissionToRole(permission, role)
        '''
        # notifications
        for notification in self.notifications:
            # call notification to execute
            notification(context)
    
    # IRolePermissionMap
    #def getPermissionsForRole(self, role_id):
    def getRolesForPermission(self, permission):
        """Generator of (role, setting) tuples for the roles having the 
        permission, as per zope.securitypolicy.interfaces.IRolePermissionMap.
        """
        for setting, p, role in self.permissions:
            if p == permission:
                yield role, IntAsSetting[setting]
    #def getSetting(self, permission_id, role_id):
    #def getRolesAndPermissions(self):


class Transition(object):
    """A workflow transition from source status to destination.
    
    A transition from a *single* source state to a *single* destination state,
    irrespective of how it may be defined e.g. in XML from multiple possible 
    sources to a single destination (this is simply a shorthand for defining
    multiple transitions). 
    
    Each Transition ID is automatically determined from the source and 
    destination states (therefore it is not passed in as a constructor 
    parameter) in the following predictable way:
    
        id = "%s-%s" % (source or "", destination)
    
    This is the id to use when calling WorkflowController.fireTransition(id),
    as well as being the HTML id used in generated menu items, etc. 
    """
    
    def __init__(self, title, source, destination,
            grouping_unique_sources=None,
            condition=None,
            trigger=interfaces.MANUAL, 
            permission=CheckerPublic,
            order=0,
            require_confirmation=False,
            note=None,
            **user_data
        ):
        self.title = title
        self.source = source
        self.destination = destination
        self.grouping_unique_sources = grouping_unique_sources
        self._raw_condition = condition # remember unwrapped condition
        self.condition = wrapped_condition(condition)
        self.trigger = trigger
        self.permission = permission
        self.order = order
        self.require_confirmation = require_confirmation
        self.note = note
        self.user_data = user_data
    
    @property
    def id(self):
        # source may be either a valid starus_id or None
        return "%s-%s" % (self.source or "", self.destination)
    
    def __cmp__(self, other):
        return cmp(self.order, other.order)

#

class StateController(object):
    
    zope.interface.implements(interfaces.IStateController)
    
    __slots__ = "context",
    
    def __init__(self, context):
        self.context = context
    
    def get_state(self):
        """Get the workflow.states.State instance for the context's status."""
        return get_object_state(self.context)
    
    def get_status(self):
        return self.context.status
    
    def set_status(self, status):
        source_status = self.get_status()
        if source_status != status:
            self.context.status = status
            # additional actions related to change of workflow status
            self.on_status_change(source_status, status)
        else:
            log.warn("Attempt to reset unchanged status [%s] on item [%s]" % (
                status, self.context))
    
    def on_status_change(self, source, destination):
        state = self.get_state()
        assert state is not None, "May not have a None state" # !+NEEDED?
        state.execute_actions(self.context)
    

def get_object_state(context):
    """Utility to look up the workflow.states.State singleton instance that 
    corresponds to the context's urrent status.
    
    Implemented as the IWorkflow adaptor for the context--but as may need to 
    be called numerous times per request, note that it is a lightweight and 
    performance-aware adapter -- there is no creation of any adapter instance, 
    just lookup of the object's Workflow instance off which to retrieve 
    existing State instances.
    """
    return interfaces.IWorkflow(context).get_state(context.status)

def get_object_state_rpm(context):
    """IRolePermissionMap(context) adapter factory. 
    
    Looks up the workflow.states.State singleton instance that is the current
    IRolePermissionMap responsible for the context.
    
    Lighweight and high-performance wrapper on get_object_state(context), 
    to *lookup* (note: no creation of any instance) the workflow.states.State 
    singleton instance.
    """
    state = get_object_state(context)
    if state.permissions_from_parent:
        # this state delegates permissions to parent, 
        # so just recurse passing parent item instead
        return get_object_state_rpm(context.item)
    return state

def get_object_version_state_rpm(version):
    """IRolePermissionMap(version) adapter factory.
    
    Lighweight and high-performance wrapper on get_object_state(context), 
    to *lookup* (note: no creation of any instance) the workflow.states.State 
    singleton instance for the version's context's status.
    
    Note that version insatnces are NOT workflowed.
    """
    # !+HEAD_DOCUMENT_ITEM(mr, sep-2011) standardize name, "head", "document" 
    # or "item"?
    return interfaces.IWorkflow(version.head).get_state(version.status)


class Workflow(object):
    """A Workflow instance for a specific document type, defining the possible 
    states a document may have and the allowed transitions between them.
    The initial state of the workflowed document is always None.
    """
    zope.interface.implements(interfaces.IWorkflow)
    
    initial_state = None
    
    def __init__(self, name, features, states, transitions, note=None):
        self.name = name
        self.features = features
        self.note = note
        self._states_by_id = {} # {id: State}
        self._transitions_by_id = {} # {id: Transition}
        self._transitions_by_source = {} # {source: [Transition]}
        self._transitions_by_destination = {} # {destination: [Transition]}
        self._transitions_by_grouping_unique_sources = {} # {grouping: [Transition]}
        self._permission_role_pairs = None # set([ (permission, role) ])
        self.refresh(states, transitions)
    
    def refresh(self, states, transitions):
        sbyid = self._states_by_id
        sbyid.clear()
        tbyid = self._transitions_by_id
        tbyid.clear()
        tbys = self._transitions_by_source
        tbys.clear()
        tbyd = self._transitions_by_destination
        tbyd.clear()
        tbygus = self._transitions_by_grouping_unique_sources
        tbygus.clear()
        # states
        tbys[self.initial_state] = [] # special case source: initial state
        for s in states:
            sbyid[s.id] = s
            tbys[s.id] = []
            tbyd[s.id] = []
        # transitions
        for t in transitions:
            tid = t.id
            assert tid not in tbyid, \
                "Workflow [%s] duplicates transition [%s]" % (self.name, tid)
            tbyid[tid] = t
            tbys[t.source].append(t)
            tbyd[t.destination].append(t)
            tbygus.setdefault(t.grouping_unique_sources, []).append(t)
        # integrity
        self.validate()
    
    @exceptions_as(interfaces.InvalidWorkflow, False)
    def validate(self):
        states = self._states_by_id.values()
        # at least one state
        assert len(states), "Workflow [%s] defines no states" % (self.name)
        # every state must explicitly set the same set of permissions
        # prs: set of all (permission, role) pairs assigned in a state
        self._permission_role_pairs = prs = set([ 
            (p[1], p[2]) for p in states[0].permissions ])
        num_prs = len(prs)
        for s in states:
            if s.permissions_from_parent:
                assert not len(s.permissions), "Workflow state [%s -> %s] " \
                    "with permissions_from_parent must not specify any own " \
                    "permissions" % (self.name, s.id)
                continue
            assert len(s.permissions) == num_prs, \
                "Workflow state [%s -> %s] does not explicitly set same " \
                "permissions used across other states... " \
                "\nTHIS:\n  %s\nOTHER:\n  %s" % (self.name, s.id, 
                    "\n  ".join([str(p) for p in s.permissions]),
                    "\n  ".join([str(p) for p in states[0].permissions])
                )
            for p in s.permissions:
                assert (p[1], p[2]) in prs, \
                    "Workflow state [%s -> %s] defines an unexpected " \
                    "permission: %s" % (self.name, s.id, p)
        # ensure that every active state is reachable, 
        # and that every obsolete state is NOT reachable
        tbyd = self._transitions_by_destination
        for dest_id, sources in tbyd.items():
            log.debug("Workflow [%s] sources %s -> destination [%s]" % (
                self.name, [t.source for t in sources], dest_id))
            if self.get_state(dest_id).obsolete:
                assert not sources, \
                    "Reachable obsolete state [%s] in Workflow [%s]" % (
                        dest_id, self.name)
            else:
                assert sources, \
                    "Unreachable state [%s] in Workflow [%s]" % (
                        dest_id, self.name)
        # inter-transition validation
        # grouping_unique_sources - used to semantically connect multiple 
        # transitions and constrain that accumulative sources are unique
        for grouping, ts in self._transitions_by_grouping_unique_sources.items():
            if grouping is not None:
                all_sources = [ t.source for t in ts ]
                assert len(all_sources)==len(set(all_sources)), "Duplicate " \
                    "sources in grouped transitions [%s] in workflow [%s]" % (
                        grouping, self.name)
    
    def has_feature(self, name):
        """Does this workflow enable the named feature?
        """
        for f in self.features:
            if f.name == name:
                return f.enabled
        return False
    
    @property
    def states(self):
        """ () -> { status: State } """
        log.warn("DEPRECATED [%s] Workflow.states, " \
            "use Workflow.get_state(status) instead" % (self.name))
        return self._states_by_id
    
    @exceptions_as(interfaces.InvalidStateError)
    def get_state(self, state_id):
        return self._states_by_id[state_id]
    
    @exceptions_as(interfaces.InvalidTransitionError)
    def get_transition(self, transition_id):
        return self._transitions_by_id[transition_id]
    
    # !+ get_transitions_to(destination) ? 
    @exceptions_as(interfaces.InvalidStateError)
    def get_transitions_from(self, source):
        return sorted(self._transitions_by_source[source])
    
    def __call__(self, context):
        """A Workflow instance is itself the "singleton factory" of itself.
        Called to adapt IWorkflow(context) -- the "adaptation" concept implied
        by this is simply a lookup, on the context's class/interface, for the 
        workflow instance that was registered for that class/interface.
        """
        return self


class WorkflowController(object):
    
    zope.interface.implements(interfaces.IWorkflowController)
        
    def __init__(self, context):
        # assume context is trusted... 
        # and unlitter all actions/conditions of calls to removeSecurityProxy
        self.context = removeSecurityProxy(context)
        self._state_controller = None # cache for state_controller instance
    
    @property
    def state_controller(self):
        if self._state_controller is None:
            self._state_controller = interfaces.IStateController(self.context)
        return self._state_controller
    
    @property
    def workflow(self):
        """ () -> bungeni.core.workflow.states.Workflow """
        return interfaces.IWorkflow(self.context)
    
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
                "transition: %s" % transition.id,
                transition.permission)
        # now make sure transition can still work in this context
        if not transition.condition(self.context):
            raise interfaces.ConditionFailedError
    
    # !+ RENAME
    def fireTransition(self, transition_id, comment=None, check_security=True):
        # !+fireTransitionParams(mr, mar-2011) needed?
        if not (comment is None and check_security is True):
            log.warn("%s.fireTransition(%s, comment=%s, check_security=%s)" % (
                self, transition_id, comment, check_security))
        # raises InvalidTransitionError if id is invalid for current state
        transition = self.workflow.get_transition(transition_id)
        # skip security check for transitions
        # !+CHECK_SECURITY(murithi, may-2011) some auto transitions have
        # sources - to either, fix zcml_regenerate or directive in xml
        if transition.trigger == interfaces.AUTOMATIC:
            check_security = False
        self._check(transition, check_security)
        # change status of context or new object
        self.state_controller.set_status(transition.destination)
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
                self.fireTransition(transition.id)
            except interfaces.ConditionFailedError:
                # fine, then we weren't ready to fire the transition as yet
                pass
            else:
                # if we actually managed to fire a transition, we're done
                return
    
    def getFireableTransitionIdsToward(self, state):
        workflow = self.workflow
        result = []
        for transition_id in self.getFireableTransitionIds():
            transition = workflow.get_transition(transition_id)
            if transition.destination == state:
                result.append(transition_id)
        return result
    
    def getFireableTransitionIds(self):
        return self.getManualTransitionIds() + self.getSystemTransitionIds()
    
    def getManualTransitionIds(self):
        checkPermission = self._get_checkPermission()
        return [ transition.id 
            for transition in self._get_transitions(interfaces.MANUAL, True)
            if checkPermission(transition.permission, self.context) ]
    
    def getSystemTransitionIds(self):
        # ignore permission checks
        return [ transition.id 
            for transition in self._get_transitions(interfaces.SYSTEM, False) ]
    # !+ /RENAME
    
    def _get_transitions(self, trigger_ifilter=None, conditional=False):
        """Retrieve all possible transitions from current status.
        If trigger_ifilter is not None, filter on trigger interface.
        If conditional, then only transitions that pass the condition.
        """
        transitions = self.workflow.get_transitions_from(
            self.state_controller.get_status())
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

