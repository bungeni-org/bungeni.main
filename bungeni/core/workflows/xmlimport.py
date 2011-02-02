"""
Support for xml defined workflows, and security manipulations by state.
"""

import re

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
    return _load(doc)


def _load(workflow):
    """ (workflow:etree_doc) -> StateWorkflow
    """
    transitions = []
    states = []
    domain = workflow.get("domain")
    wid = workflow.get("id")
    _uids = set()
    _uids.add(wid)
    
    def validate_id(id, tag):
        """Assumption: id is not None."""
        m = 'Invalid <%s> id="%s" in workflow [%s]' % (tag, id, wid)
        assert ID_RE.match(id), '%s -- only letters, numbers, "_" allowed' % (m)
        assert id not in _uids, "%s -- id not unique in workflow document" % (m)
        _uids.add(id)

    def get_like_state(state_id):
        if state_id is None:
            return
        for state in states:
            if state.id == state_id:
                return state
        assert False, 'Invalid value: like_state="%s"' % (state_id)
    
    def check_add_permission(permissions, like_permissions, assignment, p, r):
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
    
    for t in workflow.iterchildren("transition"):
    
        for key in ("source", "destination", "id", "title"):
            if t.get(key) is None:
                raise SyntaxError("%s not in %s"%(key, etree.tostring(t)))
        validate_id(t.get("id"), "transition")
        # source="" (empty string implies the None source
        sources = t.get("source").split() or [None]
        for source in sources:
            if len(sources) > 1:
                tid = "%s-%s" % (t.get("id"), source)
            else:
                tid = t.get("id")
            args = (tid, Message(t.get("title"), domain),
                    source, t.get("destination"))
            kw = {}
            
            # optionals
            for i in ("trigger", "order", "permission"):
                val = t.get(i)
                if not val:
                    continue
                kw[i] = val
            
            require_confirmation = getattr(t, "require_confirmation", "")
            if require_confirmation.lower() == "true":
                kw["require_confirmation"] = True
            
            if "trigger" in kw:
                k = kw["trigger"]
                v = trigger_value_map[k]
                kw["trigger"] = v
            
            # optional python resolvables
            for i in("condition", "action", "event"):
                val = t.get(i)
                if not val:
                    continue
                # raises importerror/nameerror
                val = resolve(val, "bungeni.core.workflows")
                kw[i] = val
            transitions.append(StateTransition(*args, **kw))
    
    return StateWorkflow(transitions, states)
