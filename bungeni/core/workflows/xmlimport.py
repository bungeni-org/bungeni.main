"""
Support for xml defined workflows, and security manipulations by state.
"""
log = __import__("logging").getLogger("bungeni.core.workflows.xmlimport")

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

RESOLVE_BASEPATH = "bungeni.core.workflows"

trigger_value_map = {
    "manual": interfaces.MANUAL,
    "automatic": interfaces.AUTOMATIC,
    "system": interfaces.SYSTEM
}

# only letters, numbers and "_" char i.e. no whitespace or "-"
ID_RE = re.compile("^[\w\d_]+$")

TRANS_ATTRS_REQUIREDS = ("id", "title", "source", "destination")
TRANS_ATTRS_OPTIONALS = ("condition", "trigger", "roles", "permission", 
    "order", "event", "require_confirmation")
TRANS_ATTRS = TRANS_ATTRS_REQUIREDS + TRANS_ATTRS_OPTIONALS



''' !+NOT_WORKING... see: zope.security.permission
from zope.app.security.interfaces import IPermission
from zope.app import zapi
def assertRegisteredPermission(permission_id):
    assert zapi.queryUtility(IPermission, unicode(permission_id)), \
        'Permission "%s" has not been registered.' % (permission_id)
'''

#

ZCML_FILENAME = "permissions.zcml"
ZCML_MODULES_PROCESSED = set() # Process workflow modules once only
ZCML_LINES = [] # Accumulation of ZCML content
ZCML_INDENT = ""
ZCML_BOILERPLATE = """<?xml version="1.0"?>
<configure xmlns="http://namespaces.zope.org/zope"
    xmlns:i18n="http://namespaces.zope.org/i18n"
    i18n_domain="bungeni.core">
<!-- 

!! AUTO-GENERATED !! DO NOT MODIFY !!

This file is automatically [re-]generated on startup, after all the 
workflow XML files have been loaded, see: 
bungeni.core.workflows.xmlimport.zcml_check_regenerate()

It would need to be regenerated when any workflow transition is modified 
or added, a condition that is checked for and flagged automatically.

Defines a DEDICATED permission per workflow TRANSITION, and grants it to
the various Roles, as specified by each transition.

See the Bungeni Source Code Style Guide for further details. 

-->
%s

</configure>
"""

def zcml_check_regenerate():
    """Called after all XML workflows have been loaded (see adapers.py). 
    """
    __path__ = os.path.dirname(__file__)
    filepath = os.path.join(__path__, ZCML_FILENAME)
    persisted = open(filepath, "r").read()
    regenerated = ZCML_BOILERPLATE % ("\n".join(ZCML_LINES))
    if persisted != regenerated:
        log.warn("Stale workflows/%s file -- REWRITING: \n"
            "========== OLD CONTENTS:\n%s\n==========" % (
                ZCML_FILENAME, persisted))
        open(filepath, "w").write(regenerated)
        class ChangedWorkflowsPermissionsZCML(Exception): pass
        raise ChangedWorkflowsPermissionsZCML(
            "Must restart system with updated workflows/%s file" % (
                ZCML_FILENAME))

def is_zcml_permissionable(trans):
    # The "create" transitions should NOT have any permission assigned to them,
    # as the action of cretaing this object is controlled via an application
    # level bungeni.{type}.Add permission granted to the user in question. 
    #
    # The assumption here is that a "create" transition has a NULL source,
    # (by convention "" i.e. the empty string).
    return bool(trans.get("source"))

def zcml_transition_permission(pid, title, roles):
    ZCML_LINES.append(ZCML_INDENT)
    ZCML_LINES.append('%s<permission id="%s" title="%s" />' % (
        ZCML_INDENT, pid, title))
    for role in roles:
        ZCML_LINES.append(
            '%s<grant permission="%s" role="%s" />' % (ZCML_INDENT, pid, role))

#

def load(file_path):
    doc = etree.fromstring(open(file_path).read())
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    module = resolve(".%s" % module_name, RESOLVE_BASEPATH)
    actions = getattr(module, "actions")
    return _load(doc, module_name, actions)


def _load(workflow, module_name, actions):
    """ (workflow:etree_doc, actions:cls) -> StateWorkflow
    """
    transitions = []
    states = []
    domain = workflow.get("domain")
    wuids = set() # unique IDs in this XML workflow file
    wid = workflow.get("id") # workflow XML id
    # accumulation of ALL (permission, role) pairs assigned in ANY of the 
    # states within this workflow (for consistency checking)
    states_permissions_roles = set()
    
    ZCML_PROCESSED = bool(module_name in ZCML_MODULES_PROCESSED)
    if not ZCML_PROCESSED:
        ZCML_MODULES_PROCESSED.add(module_name)
        ZCML_LINES.append(ZCML_INDENT)
        ZCML_LINES.append(ZCML_INDENT)
        ZCML_LINES.append("%s<!-- %s -->" % (ZCML_INDENT, module_name))
    
    def validate_id(id, tag):
        """Assumption: id is not None."""
        m = 'Invalid <%s> id="%s" in workflow [%s]' % (tag, id, wid)
        assert ID_RE.match(id), '%s -- only letters, numbers, "_" allowed' % (m)
        assert id not in wuids, "%s -- id not unique in workflow document" % (m)
        wuids.add(id)
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
        states_permissions_roles.add((p, r))
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
        if like_state:
            # splice any remaining like_permissions at beginning of permissions
            permissions[0:0] = like_permissions
        states.append(
            State(state_id, Message(s.get("title", domain)), permissions) 
        )
    
    for s in states:
        # check that every state explictly sets the same set of permissions 
        assert len(s.permissions) == len(states_permissions_roles), \
            "Workflow state [%s -> %s] does not explictly set all permissions " \
            "used across other states... accumulated set is:\n  %s" % (
                wid, s.id, 
                "\n  ".join([str(p) for p in states_permissions_roles]) 
            )
    
    STATE_IDS = [ s.id for s in states ]
    
    for t in workflow.iterchildren("transition"):
        for key in t.keys():
            assert key in TRANS_ATTRS, \
                "Unknown attribute %s in %s" % (key, etree.tostring(t))
        for key in TRANS_ATTRS_REQUIREDS:
            if t.get(key) is None:
                raise SyntaxError("%s not in %s" % (key, etree.tostring(t)))
        tid = t.get("id")
        validate_id(tid, "transition")
        
        # update ZCML for dedicated permission
        pid = "bungeni.%s.wf.%s" % (module_name, tid)
        if not ZCML_PROCESSED:
            if is_zcml_permissionable(t):
                zcml_transition_permission(pid, t.get("title"), 
                    t.get("roles", "bungeni.Clerk").split())
        
        # source = "" (empty string -> None source)
        sources = t.get("source").split() or [None]
        destination = t.get("destination")
        assert destination in STATE_IDS, \
            "Unknown transition destination state [%s]" % (destination)
        
        kw = {}
        # optionals
        for i in TRANS_ATTRS_OPTIONALS:
            val = t.get(i)
            if not val:
                # we let setting of defaults be handled upstream
                continue
            kw[i] = val
        
        # data up-typing
        #
        # action - if this workflow's "actions" defines an action for
        # this transition (with same name as tranistion), then use it.
        if hasattr(actions, tid):
            kw["action"] = getattr(actions, tid)
        # trigger
        if "trigger" in kw:
            kw["trigger"] = trigger_value_map[kw["trigger"]]
        # permission - one-to-one per transition, if set may only be {pid}
        if is_zcml_permissionable(t):
            if "permission" in kw:
                assert kw["permission"] == pid, \
                    "Inconsistent transition permission: %s -> %s" % (tid, pid)
            else:
                kw["permission"] = pid
        else:
            assert kw.get("permission") is None, "Not allowed to set a " \
                "permission on (creation) transition: %s" % (tid)
        # python resolvables
        for i in ("condition", "event"):
            if i in kw:
                # raises importerror/nameerror
                kw[i] = resolve(kw[i], RESOLVE_BASEPATH)
        # bool
        if "require_confirmation" in kw:
            if kw["require_confirmation"].lower() == "true":
                kw["require_confirmation"] = True

        # multiple-source transitions are really multiple "transition paths"
        for source in sources:
            if source is not None:
                assert source in STATE_IDS, \
                    "Unknown transition source state [%s]" % (source)
            # !+TRANSITION_ID(mr, feb-2010) always use normalized transition ID, 
            # "%s-%s" % (tid, source), even for single-source transitions?
            # !+TRANSITION_ID(mr, feb-2010) adopt more predictable scheme, 
            # "%s-%s" % (source, destination), but leaving pid scheme unchanged?
            if len(sources) > 1:
                disambiguated_tid = "%s-%s" % (tid, source)
            else:
                disambiguated_tid = tid
            
            args = (disambiguated_tid, 
                Message(t.get("title"), domain),
                source, 
                destination
            )
            transitions.append(StateTransition(*args, **kw))
    
    return StateWorkflow(transitions, states)



