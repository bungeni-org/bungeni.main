"""
Support for xml defined workflows, and security manipulations by state.
"""

import re
import os

from lxml import etree
from zope.dottedname.resolve import resolve
from zope.i18nmessageid import Message

from bungeni.core.workflows.states import GRANT
from bungeni.core.workflows.states import DENY
from bungeni.core.workflows.states import State
from bungeni.core.workflows.states import StateTransition
from bungeni.core.workflows.states import StateWorkflow

from ore.workflow import interfaces

ASSIGNMENTS = (GRANT, DENY)

trigger_value_map = {
    "manual": interfaces.MANUAL,
    "automatic": interfaces.AUTOMATIC,
    "system": interfaces.SYSTEM
}

# only letters, numbers and "_" char i.e. no whitespace or "-"
ID_RE = re.compile("^[\w\d_]+$")


''' !+NOT_WORKING... see: zope.security.permission
from zope.app.security.interfaces import IPermission
from zope.app import zapi
def assertRegisteredPermission(permission_id):
    assert zapi.queryUtility(IPermission, unicode(permission_id)), \
        'Permission "%s" has not been registered.' % (permission_id)
'''

def load(file_path):
    doc = etree.fromstring(open(file_path).read())
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    module = resolve(".%s" % module_name, "bungeni.core.workflows")
    actions = getattr(module, "actions")
    return _load(doc, actions)


def _load(workflow, actions):
    """ (workflow:etree_doc, actions:cls) -> StateWorkflow
    """
    transitions = []
    states = []
    domain = workflow.get("domain")
    _uids = set()
    wid = workflow.get("id")
    # bookkeeping of all (permission, role) pairs assigned in this workflow
    _all_prs = set()
    
    def validate_id(id, tag):
        """Assumption: id is not None."""
        m = 'Invalid <%s> id="%s" in workflow [%s]' % (tag, id, wid)
        assert ID_RE.match(id), '%s -- only letters, numbers, "_" allowed' % (m)
        assert id not in _uids, "%s -- id not unique in workflow document" % (m)
        _uids.add(id)
    # ID values should be unique within the same scope (the XML document)
    validate_id(wid, "workflow")
    
    def get_like_state(state_id):
        if state_id is None:
            return
        for state in states:
            if state.id == state_id:
                return state
        assert False, 'Invalid value: like_state="%s"' % (state_id)
    
    def check_add_permission(permissions, like_permissions, assignment, p, r):
        _all_prs.add((p, r))
        for perm in [(GRANT, p, r), (DENY, p, r)]:
            assert perm not in permissions, "Workflow [%s] state [%s] " \
                "conflicting state permission: (%s, %s, %s)" % (
                    wid, state_id, assignment, p, r)
            if perm in like_permissions:
                like_permissions.remove(perm)
        permissions.append((assignment, p, r))
    
    for s in workflow.iterchildren("state"):
        state_id = s.get("id")
        assert state_id, "Workflow State must define @id"
        validate_id(state_id, "state")
        permissions = [] # tuple(bool:int, permission:str, role:str) 
        # state.@like_state : to reduce repetition and enhance maintainibility
        # of workflow XML files, a state may specify a @like_state attribute to 
        # inherit all permissions defined by the specified like_state; further
        # permissions specific to this state may be added, but as these may 
        # also override inherited permissions we streamline those out so that 
        # downstream execution (a permission should be granted or denied only 
        # once per transition to a state).
        like_permissions = []
        like_state = get_like_state(s.get("like_state"))
        if like_state:
            like_permissions.extend(like_state.permissions)
        # (within same state) a deny is *always* executed after a *grant*
        for i, assign in enumerate(["grant", "deny"]):
            for p in s.iterchildren(assign):
                permission, role = p.get("permission"), p.get("role")
                #+!assertRegisteredPermission(permission)
                check_add_permission(permissions, like_permissions, 
                    ASSIGNMENTS[i], permission, role)
        # splice any remaining like_permissions at beginning of permissions
        if like_state:
            permissions[0:0] = like_permissions
        states.append(
            State(state_id, Message(s.get("title", domain)), permissions) 
        )
    
    transition_requireds = ("id", "title", "source", "destination")
    transition_optionals = ("condition", "trigger", "permission", "order", 
        "event", "require_confirmation")
    transition_all_attrs = transition_requireds + transition_optionals
    for t in workflow.iterchildren("transition"):
        for key in t.keys():
            assert key in transition_all_attrs, \
                "Unknown attribute %s in %s" % (key, etree.tostring(t))
        for key in transition_requireds:
            if t.get(key) is None:
                raise SyntaxError("%s not in %s" % (key, etree.tostring(t)))
        tid = t.get("id")
        validate_id(tid, "transition")
        # source = "" (empty string implies the None source)
        sources = t.get("source").split() or [None]
        for source in sources:
            if len(sources) > 1:
                disambiguated_tid = "%s-%s" % (tid, source)
            else:
                disambiguated_tid = tid
            args = (disambiguated_tid, 
                Message(t.get("title"), domain),
                source, 
                t.get("destination")
            )
            kw = {}
            
            # optionals
            for i in transition_optionals:
                val = t.get(i)
                if not val:
                    # we let setting of defaults be handled upstream
                    continue
                kw[i] = val
            # action - if this workflow's "actions" defines an action for
            # this transition (with same name as tranistion), then use it.
            if hasattr(actions, tid):
                kw["action"] = getattr(actions, tid)
            
            # data up-typing 
            if "trigger" in kw:
                kw["trigger"] = trigger_value_map[kw["trigger"]]
            # python resolvables
            for i in ("condition", "event"):
                if i in kw:
                    # raises importerror/nameerror
                    kw[i] = resolve(kw[i], "bungeni.core.workflows")
            # bool
            if "require_confirmation" in kw:
                if kw["require_confirmation"].lower() == "true":
                    kw["require_confirmation"] = True
            
            transitions.append(StateTransition(*args, **kw))
    
    return StateWorkflow(transitions, states)


