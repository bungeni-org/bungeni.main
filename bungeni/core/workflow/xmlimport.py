# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Support for xml defined workflows, and security manipulations by state.

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflow.xmlimport")

import re
import os

from lxml import etree
from zope.dottedname.resolve import resolve
from zope.i18nmessageid import Message
from bungeni.core.workflow import interfaces
from bungeni.core.workflow.states import GRANT, DENY
from bungeni.core.workflow.states import State, Transition, Workflow
from bungeni.core.workflow.notification import Notification
from bungeni.utils.capi import capi, bungeni_custom_errors
from bungeni.ui.utils import debug

#

ASSIGNMENTS = (GRANT, DENY)

ACTIONS_MODULE = resolve("._actions", "bungeni.core.workflows")

trigger_value_map = {
    "manual": interfaces.MANUAL,
    "automatic": interfaces.AUTOMATIC,
    "system": interfaces.SYSTEM
}

# only letters, numbers and "_" char i.e. no whitespace or "-"
ID_RE = re.compile("^[\w\d_]+$")

STATE_ATTRS = ("id", "title", "version", "like_state", "note", "obsolete")

TRANS_ATTRS_REQUIREDS = ("title", "source", "destination")
TRANS_ATTRS_OPTIONALS = ("condition", "trigger", "roles", "order", 
    "require_confirmation", "note")
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
ZCML_WORKFLOWS_PROCESSED = set() # Process workflows once only
ZCML_LINES = [] # Accumulation of ZCML content
ZCML_INDENT = ""
ZCML_BOILERPLATE = """<?xml version="1.0"?>
<configure xmlns="http://namespaces.zope.org/zope"
    xmlns:i18n="http://namespaces.zope.org/i18n"
    i18n_domain="bungeni">
<!-- 

!! AUTO-GENERATED !! DO NOT MODIFY !!

This file is automatically [re-]generated on startup, after all the 
workflow XML files have been loaded, see: 
bungeni.core.workflow.xmlimport.zcml_check_regenerate()

It would need to be regenerated when any workflow transition is modified 
or added, a condition that is checked for and flagged automatically.

Defines a DEDICATED permission per workflow TRANSITION, and grants it to
the various Roles, as specified by each transition.

See the Bungeni Source Code Style Guide for further details. 

-->
%s

</configure>
"""

def strip_none(s):
    """Ensure non-empty whitespace-stripped string, else None."""
    if s is not None:
        return s.strip() or None
    return None

def as_bool(s):
    """ (s:str) -> bool
    """
    _s = s.lower()
    if _s == "true":
        return True
    elif _s == "false":
        return False
    raise TypeError("Invalid bool: %s" % s)

#

def zcml_check_regenerate():
    """Called after all XML workflows have been loaded (see adapers.py). 
    """
    # ZCML_FILENAME is under bungeni.core.workflows
    import bungeni.core.workflows
    __path__ = os.path.dirname(bungeni.core.workflows.__file__)
    filepath = os.path.join(__path__, ZCML_FILENAME)
    # read current file
    persisted = open(filepath, "r").read().decode("utf-8")
    # regenerate, compare, and re-write if needed
    regenerated = ZCML_BOILERPLATE % ("\n".join(ZCML_LINES))
    if persisted != regenerated:
        log.warn("CHANGES to file:\n%s" % (
            debug.unified_diff(persisted, regenerated, filepath, "NEW")))
        open(filepath, "w").write(regenerated.encode("utf-8"))
        class ChangedWorkflowsPermissionsZCML(Exception): pass
        raise ChangedWorkflowsPermissionsZCML(
            "Must restart system with updated file: %s" % (filepath))

def is_zcml_permissionable(trans_elem):
    # The "create" transitions should NOT have any permission assigned to them,
    # as the action of creating this object is controlled via an application
    # level bungeni.{type}.Add permission granted to the user in question. 
    #
    # The assumption here is that a "create" transition has a NULL source,
    # (by convention "" i.e. the empty string).
    return bool(strip_none(trans_elem.get("source")))

def zcml_transition_permission(pid, title, roles):
    ZCML_LINES.append(ZCML_INDENT)
    ZCML_LINES.append('%s<permission id="%s" title="%s" />' % (
        ZCML_INDENT, pid, title))
    for role in roles:
        ZCML_LINES.append(
            '%s<grant permission="%s" role="%s" />' % (ZCML_INDENT, pid, role))

#

@bungeni_custom_errors
def load(path_custom_workflows, name):
    """ (path_custom_workflows:str, name:str) -> Workflow
    
    Loads the workflow XML definition file, returning the correspondingly setup 
    Workflow instance. Called by workflows.adapters.load_workflow.
    """
    file_path = os.path.join(path_custom_workflows, "%s.xml" % (name))
    return _load(etree.fromstring(open(file_path).read()), name)

def _load(workflow, name):
    """ (workflow:etree_doc, name:str) -> Workflow
    """
    transitions = []
    states = []
    domain = strip_none(workflow.get("domain"))
    wuids = set() # unique IDs in this XML workflow file
    note = strip_none(workflow.get("note"))
    # initial_state, must be ""
    assert workflow.get("initial_state") == "", "Workflow [%s] initial_state " \
        "attribute must be empty string, not [%s]" % (
            name, workflow.get("initial_state"))
    initial_state = None
    
    ZCML_PROCESSED = bool(name in ZCML_WORKFLOWS_PROCESSED)
    if not ZCML_PROCESSED:
        ZCML_WORKFLOWS_PROCESSED.add(name)
        ZCML_LINES.append(ZCML_INDENT)
        ZCML_LINES.append(ZCML_INDENT)
        ZCML_LINES.append("%s<!-- %s -->" % (ZCML_INDENT, name))
    
    def validate_id(id, tag):
        """Ensure that ID values are unique within the same XML doc scope.
        """
        m = 'Invalid <%s> id="%s" in workflow [%s]' % (tag, id, name)
        assert id is not None, "%s -- id may not be None" % (m)
        assert ID_RE.match(id), '%s -- only letters, numbers, "_" allowed' % (m)
        assert id not in wuids, "%s -- id not unique in workflow document" % (m)
        wuids.add(id)
    
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
                    name, state_id, assignment, p, r)
            if perm in like_permissions:
                like_permissions.remove(perm)
        permissions.append((assignment, p, r))
    
    def assert_valid_attr_names(e, allowed_attr_names):
        for key in e.keys():
            assert key in allowed_attr_names, \
                "Workflow [%s]: unknown attribute %s in %s" % (
                    name, key, etree.tostring(e))
    
    # top-level child ordering
    grouping, allowed_child_ordering = 0, ("grant", "state", "transition")
    for child in workflow.iterchildren():
        if not isinstance(child.tag, basestring):
            # ignore comments
            continue
        while child.tag != allowed_child_ordering[grouping]:
            grouping += 1
            assert grouping < 3, "Workflow [%s] element <%s> %s not allowed " \
                "here -- element order must respect: %s" % (
                    name, child.tag, child.items(), allowed_child_ordering)
    
    # global grants
    for p in workflow.iterchildren("grant"):
        pid = strip_none(p.get("permission"))
        role = strip_none(p.get("role"))
        #+!assertRegisteredPermission(permission)
        ZCML_LINES.append(
            '%s<grant permission="%s" role="%s" />' % (ZCML_INDENT, pid, role))
    
    # states
    for s in workflow.iterchildren("state"):
        assert_valid_attr_names(s, STATE_ATTRS)
        # @id
        state_id = strip_none(s.get("id"))
        assert state_id, "Workflow State must define @id"
        validate_id(state_id, "state")
        # actions
        actions = []
        # version
        if strip_none(s.get("version")) is not None:
            make_version = as_bool(strip_none(s.get("version")))
            if make_version is None:
                raise ValueError("Invalid state value "
                    '[version="%s"]' % s.get("version"))
            if make_version:
                actions.append(ACTIONS_MODULE.create_version)
        
        # state-id-inferred action - if "actions" module defines an action for
        # this state (associated via a naming convention), then use it.
        # !+ tmp, until actions are user-exposed as part of <state>
        action_name = "_%s_%s" % (name, state_id)
        if hasattr(ACTIONS_MODULE, action_name):
            actions.append(getattr(ACTIONS_MODULE, action_name))
        # @like_state, permissions
        permissions = [] # [ tuple(bool:int, permission:str, role:str) ]
        # state.@like_state : to reduce repetition and enhance maintainibility
        # of workflow XML files, a state may specify a @like_state attribute to 
        # inherit all permissions defined by the specified like_state; further
        # permissions specific to this state may be added, but as these may 
        # also override inherited permissions we streamline those out so that 
        # downstream execution (a permission should be granted or denied only 
        # once per transition to a state).
        like_permissions = []
        like_state = get_like_state(strip_none(s.get("like_state")))
        if like_state:
            like_permissions.extend(like_state.permissions)
        # (within same state) a deny is *always* executed after a *grant*
        for i, assign in enumerate(["grant", "deny"]):
            for p in s.iterchildren(assign):
                permission = strip_none(p.get("permission"))
                role = strip_none(p.get("role"))
                #+!assertRegisteredPermission(permission)
                check_add_permission(permissions, like_permissions, 
                    ASSIGNMENTS[i], permission, role)
        if like_state:
            # splice any remaining like_permissions at beginning of permissions
            permissions[0:0] = like_permissions
        # notifications
        notifications = [] # [ notification.Notification ]
        for n in s.iterchildren("notification"):
            notifications.append(
                Notification(
                    strip_none(n.get("condition")), # python resolvable
                    strip_none(n.get("subject")), # template source, i18n
                    strip_none(n.get("from")), # template source
                    strip_none(n.get("to")), # template source
                    strip_none(n.get("body")), # template source, i18n
                    strip_none(n.get("note")), # documentational note
                )
            )
        # states
        states.append(
            State(state_id, Message(s.get("title", domain)), 
                strip_none(s.get("note")),
                actions, permissions, notifications,
                as_bool(strip_none(s.get("obsolete") or "false")))
        )
    
    STATE_IDS = [ s.id for s in states ]
    
    # transitions
    for t in workflow.iterchildren("transition"):
        assert_valid_attr_names(t, TRANS_ATTRS)
        for key in TRANS_ATTRS_REQUIREDS:
            if key == "source" and t.get(key) == "":
                # initial_state, an explicit empty string
                continue
            elif strip_none(t.get(key)) is None:
                raise SyntaxError('No required "%s" attribute in %s' % (
                    key, etree.tostring(t)))
        
        # sources, empty string -> initial_state
        sources = t.get("source").split() or [initial_state]
        assert len(sources) == len(set(sources)), \
            "Transition contains duplicate sources [%s]" % (sources)
        for source in sources:
            if source is not initial_state:
                assert source in STATE_IDS, \
                    "Unknown transition source state [%s]" % (source)
        # destination must be a valid state
        destination = t.get("destination")
        assert destination in STATE_IDS, \
            "Unknown transition destination state [%s]" % (destination)
        # update ZCML for dedicated permission for (XML multi-source) transition
        tid = "%s.%s" % (
            ".".join([ source or "" for source in sources ]),
            destination)
        pid = "bungeni.%s.wf.%s" % (name, tid)
        if not ZCML_PROCESSED:
            if is_zcml_permissionable(t):
                zcml_transition_permission(pid, t.get("title"), 
                    t.get("roles", "bungeni.Clerk").split())
        
        kw = {}
        # optionals -- only set on kw IFF explicitly defined
        for i in TRANS_ATTRS_OPTIONALS:
            val = t.get(i)
            if not val:
                # we let setting of defaults be handled upstream
                continue
            kw[i] = val
        
        # data up-typing
        #
        # trigger
        if "trigger" in kw:
            kw["trigger"] = trigger_value_map[kw["trigger"]]
        # permission - one-to-one per transition, may only be {pid} or None
        if is_zcml_permissionable(t):
            kw["permission"] = pid
        else:
            assert kw.get("permission") is None, "Not allowed to set a " \
                "permission on (creation) transition: %s" % (tid)
        # python resolvables
        if "condition" in kw:
            kw["condition"] = capi.get_workflow_condition(kw["condition"])
        # numeric
        if "order" in kw:
            kw["order"] = float(kw["order"]) # ValueError if not numeric
        # bool
        if "require_confirmation" in kw:
            try:
                kw["require_confirmation"] = as_bool(kw["require_confirmation"])
                assert kw["require_confirmation"] is not None
            except:
                raise ValueError("Invalid transition value "
                    '[require_confirmation="%s"]' % (
                        t.get("require_confirmation")))
        # multiple-source transitions are really multiple "transition paths"
        for source in sources:
            args = (Message(t.get("title"), domain), source, destination)
            transitions.append(Transition(*args, **kw))
            log.debug("[%s] adding transition [%s-%s] [%s]" % (
                name, source or "", destination, kw))
    
    return Workflow(name, states, transitions, note)

