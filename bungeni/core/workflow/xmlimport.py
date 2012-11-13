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
from bungeni.core.workflow import interfaces
from bungeni.core.workflow.states import GRANT, DENY
from bungeni.core.workflow.states import Feature, State, Transition, Workflow
from bungeni.core.workflow.states import assert_distinct_permission_scopes
from bungeni.utils.capi import capi, bungeni_custom_errors
from bungeni.utils import naming, misc

#

xas, xab = misc.xml_attr_str, misc.xml_attr_bool

ASSIGNMENTS = (GRANT, DENY)

ACTIONS_MODULE = resolve("._actions", "bungeni.core.workflows")

trigger_value_map = {
    "manual": interfaces.MANUAL,
    "automatic": interfaces.AUTOMATIC,
    "system": interfaces.SYSTEM
}

# only letters, numbers and "_" char i.e. no whitespace or "-"
ID_RE = re.compile("^[\w\d_]+$")

FEATURE_ATTRS = ("name", "enabled", "note")

STATE_ATTRS = ("id", "title", "version", "like_state", "tags", 
    "note", "permissions_from_parent", "obsolete")

TRANS_ATTRS_REQUIREDS = ("title", "source", "destination")
TRANS_ATTRS_OPTIONALS = ("grouping_unique_sources", "condition", "trigger", 
    "roles", "order", "require_confirmation", "note")
TRANS_ATTRS = TRANS_ATTRS_REQUIREDS + TRANS_ATTRS_OPTIONALS

#

ZCML_FILENAME = "permissions.zcml"
ZCML_WORKFLOWS_PROCESSED = set() # Process workflows once only
ZCML_LINES = [] # Accumulation of ZCML content
ZCML_INDENT = ""
#!+shared_workflow xmlns:meta="http://namespaces.zope.org/meta"
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

Defines a DEDICATED permission per workflow XML-TRANSITION, and grants it 
to the various Roles, as specified in same transition definition.

See the Bungeni Source Code Style Guide for further details. 

-->
%s

</configure>
"""


def zcml_check_regenerate():
    """Called after all XML workflows have been loaded (see adapers.py).
    """
    #!+permissions.zcml(mr, aug-2011) bypass writing to disk?
    def get_filepath():
        # ZCML_FILENAME is under bungeni.core.workflows
        import bungeni.core.workflows
        __path__ = os.path.dirname(bungeni.core.workflows.__file__)
        return os.path.join(__path__, ZCML_FILENAME)
    filepath = get_filepath()
    # read current file
    persisted = open(filepath, "r").read().decode("utf-8")
    # regenerate, compare, and re-write if needed
    regenerated = ZCML_BOILERPLATE % ("\n".join(ZCML_LINES))
    if persisted != regenerated:
        log.warn("CHANGES to file:\n%s" % (
            misc.unified_diff(persisted, regenerated, filepath, "NEW")))
        open(filepath, "w").write(regenerated.encode("utf-8"))
        class ChangedWorkflowsPermissionsZCML(Exception): pass
        raise ChangedWorkflowsPermissionsZCML(
            "Must restart system with updated file: %s" % (filepath))

def is_zcml_permissionable(trans_elem):
    # Automatically triggered transitions may not be permissioned.
    return not xas(trans_elem, "trigger") == "automatic"

def zcml_transition_permission(pid, title, roles):
    ZCML_LINES.append(ZCML_INDENT)
    ZCML_LINES.append('%s<permission id="%s" title="%s" />' % (
        ZCML_INDENT, pid, title))
    for role in roles:
        ZCML_LINES.append(
            '%s<grant permission="%s" role="%s" />' % (ZCML_INDENT, pid, role))

#

@bungeni_custom_errors
def load(type_key, name, path_custom_workflows):
    """ (type_key:str, name:str, path_custom_workflows:str) -> Workflow
    
    Loads the workflow XML definition file, returning the correspondingly setup 
    Workflow instance. Called by workflows.adapters.load_workflow.
    """
    file_path = os.path.join(path_custom_workflows, "%s.xml" % (name))
    return _load(type_key, name, etree.fromstring(open(file_path).read()))

def _load(type_key, name, workflow):
    """ (type_key:str, name:str, workflow:etree_doc) -> Workflow
    """    
    # !+ @title, @description
    transitions = []
    states = []
    wuids = set() # unique IDs in this XML workflow file
    note = xas(workflow, "note")
    allowed_tags = xas(workflow, "tags", "").split()
    
    # initial_state, in XML indicated a transition source=""
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
        raise ValueError('Invalid value: like_state="%s"' % (state_id))
    
    def check_add_permission(permissions, like_permissions, assignment, p, r):
        for perm in [(GRANT, p, r), (DENY, p, r)]:
            assert perm not in permissions, "Workflow [%s] state [%s] " \
                "duplicated or conflicting state permission: (%s, %s, %s)" % (
                    name, state_id, assignment, p, r)
            if perm in like_permissions:
                like_permissions.remove(perm)
        permissions.append((assignment, p, r))
    def assert_valid_attr_names(elem, allowed_attr_names):
        for key in elem.keys():
            assert key in allowed_attr_names, \
                "Workflow [%s]: unknown attribute %s in %s" % (
                    name, key, etree.tostring(elem))
    
    def qualified_permission_actions(type_key, permission_actions):
        """[str] -> [(type_key, permission_action)]
        where string may be: ".Action" or "type_key.Action"
        """
        qpas = []
        for pa in permission_actions:
            qpa = pa.split(".", 1)
            assert len(qpa) == 2, \
                "No dot in workflow %r permission action %r" % (name, pa)
            qpas.append( (qpa[0] or type_key, qpa[1]) )
        return qpas
    
    # top-level child ordering
    grouping, allowed_child_ordering = 0, (
        "feature", "grant", "state", "transition")
    for child in workflow.iterchildren():
        if not isinstance(child.tag, basestring):
            # ignore comments
            continue
        while child.tag != allowed_child_ordering[grouping]:
            grouping += 1
            assert grouping < len(allowed_child_ordering), \
                "Workflow [%s] element <%s> %s not allowed " \
                "here -- element order must respect: %s" % (
                    name, child.tag, child.items(), allowed_child_ordering)
    
    # features
    features = []
    for f in workflow.iterchildren("feature"):
        assert_valid_attr_names(f, FEATURE_ATTRS)
        # @name
        feature_name = xas(f, "name")
        assert feature_name, "Workflow Feature must define @name"
        # !+ archetype/feature inter-dep; should be part of feature descriptor
        feature_enabled = xab(f, "enabled", True)
        if feature_enabled and feature_name == "version": 
            assert "audit" in [ fe.name for fe in features if fe.enabled ], \
                "Workflow [%s] has version but no audit feature" % (name)
        config = [ cfg for cfg in f.iterchildren("config") ]
        params = dict([ (param.get("name"), param.get("value")) for param in 
            f.iterchildren("parameter")
        ])
        features.append(Feature(feature_name, enabled=feature_enabled, 
                note=xas(f, "note"), **params
        ))
    
    # permission_actions -> permissions for this type
    for (key, permission_action) in qualified_permission_actions(
            type_key, xas(workflow, "permission_actions", "").split()
        ):
        pid = "bungeni.%s.%s" % (key, permission_action)
        title = "%s %s" % (
            permission_action, naming.split_camel(naming.model_name(key)))
        ZCML_LINES.append(
            '%s<permission id="%s" title="%s" />' % (ZCML_INDENT, pid, title))
        # !+shared_workflow tmp for types "sharing" a workflow...
        #if permission_action == "View" and not key == type_key:
        #    ZCML_LINES.append(
        #        '%s<meta:redefinePermission from="%s" to="bungeni.%s.View" />' % (
        #            ZCML_INDENT, pid, type_key))
    
    # global grants
    _global_permission_role_mixes = {} # {pid: [role]}
    for p in workflow.iterchildren("grant"):
        pid = xas(p, "permission")
        role = xas(p, "role")
        # for each global permission, build list of roles it is set to
        _global_permission_role_mixes.setdefault(pid, []).append(role)
        assert pid and role, "Global grant must specify valid permission/role" 
        ZCML_LINES.append(
            '%s<grant permission="%s" role="%s" />' % (ZCML_INDENT, pid, role))
        # no real need to check that the permission and role of a global grant 
        # are properly registered in the system -- an error should be raised 
        # by the zcml if either is not defined. 
    for perm, roles in _global_permission_role_mixes.items():
        # assert roles mix limitations for state permissions
        assert_distinct_permission_scopes(perm, roles, name, "global grants")
    
    # states
    for s in workflow.iterchildren("state"):
        assert_valid_attr_names(s, STATE_ATTRS)
        # @id
        state_id = xas(s, "id")
        assert state_id, "Workflow State must define @id"
        validate_id(state_id, "state")
        # state actions
        state_actions = []
        # version (prior to any custom actions)
        if xas(s, "version") is not None:
            make_version = xab(s, "version")
            if make_version is None:
                raise ValueError('Invalid state value [version="%s"]' % (
                        s.get("version")))
            if make_version:
                state_actions.append(ACTIONS_MODULE.create_version)
        # state-id-inferred action - if "actions" module defines an action for
        # this state (associated via a naming convention), then use it.
        # !+ tmp, until state_actions are user-exposed as part of <state>
        action_name = "_%s_%s" % (name, state_id)
        if hasattr(ACTIONS_MODULE, action_name):
            state_actions.append(getattr(ACTIONS_MODULE, action_name))

        # @tags
        tags = xas(s, "tags", "").split()
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
        like_state = get_like_state(xas(s, "like_state"))
        if like_state:
            like_permissions.extend(like_state.permissions)
        # (within same state) a deny is *always* executed after a *grant*
        for i, assign in enumerate(["grant", "deny"]):
            for p in s.iterchildren(assign):
                permission = xas(p, "permission")
                role = xas(p, "role")
                check_add_permission(permissions, like_permissions, 
                    ASSIGNMENTS[i], permission, role)
                # ensure global and local assignments are distinct
                global_proles = _global_permission_role_mixes.get(permission, "")
                assert role not in global_proles, ("Workflow [%s] may not mix "
                    "global and local granting of a same permission [%s] to a "
                    "same role [%s].") % (name, permission, role)
        if like_state:
            # splice any remaining like_permissions at beginning of permissions
            permissions[0:0] = like_permissions
        # states
        state_title = xas(s, "title")
        naming.MSGIDS.add(state_title)
        states.append(
            State(state_id, state_title,
                xas(s, "note"),
                state_actions, permissions, tags,
                xab(s, "permissions_from_parent"),
                xab(s, "obsolete"),
            )
        )
    
    
    STATE_IDS = [ s.id for s in states ]
    
    # transitions
    for t in workflow.iterchildren("transition"):
        assert_valid_attr_names(t, TRANS_ATTRS)
        for key in TRANS_ATTRS_REQUIREDS:
            if key == "source" and t.get(key) == "":
                # initial_state, an explicit empty string
                continue
            elif xas(t, key) is None:
                raise SyntaxError('No required "%s" attribute in %s' % (
                    key, etree.tostring(t)))
        
        # title
        title = xas(t, "title")
        naming.MSGIDS.add(title)
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
        
        # optionals -- only set on kw IFF explicitly defined
        kw = {}
        for i in TRANS_ATTRS_OPTIONALS:
            val = xas(t, i)
            if not val:
                # we let setting of defaults be handled downstream
                continue
            kw[i] = val
        
        # data up-typing
        #
        # trigger
        if "trigger" in kw:
            kw["trigger"] = trigger_value_map[kw["trigger"]]
        # roles -> permission - one-to-one per transition
        roles = kw.pop("roles", None) # space separated str
        if not is_zcml_permissionable(t):
            assert not roles, "Workflow [%s] - non-permissionable transition " \
                "does not allow @roles [%s]." % (name, roles)
            kw["permission"] = None # None -> CheckerPublic
        # !+CAN_EDIT_AS_DEFAULT_TRANSITION_PERMISSION(mr, oct-2011) this feature
        # is functional (uncomment following elif clause) but as yet not enabled. 
        #
        # Advantage would be that it would be easier to keep transitions 
        # permissions in sync with object permissions (set in state) as the 
        # majority of transition require exactly this as privilege; for the 
        # occassional transition needing a different privilege, the current 
        # transition.@roles mechanism may be used to make this explicit. 
        #
        # Need to consider implications further; the zope_principal_role_map db 
        # table, that caches contextual roles for principals, should probably 
        # first be reworked to be db-less (as for zope_role_permission_map).
        #
        #elif not roles:
        #    # then as fallback transition permission use can modify object
        #    kw["permission"] = "bungeni.%s.Edit" % (name) # fallback permission
        else:
            # Dedicated permission for XML multi-source transition.
            # Given that, irrespective of how sources are grouped into 
            # multi-source XML <transition> elements, there may be only *one* 
            # path from any given *source* to any given *destination* state, 
            # it suffices to use only the first source element + the destination 
            # to guarantee a unique identifier for an XML transition element.
            #
            # Note: the "-" char is not allowed within a permission id 
            # (so we use "." also here).
            #
            tid = "%s.%s" % (sources[0] or "", destination)
            pid = "bungeni.%s.wf.%s" % (name, tid)
            if not ZCML_PROCESSED:
                roles = roles.split()
                zcml_transition_permission(pid, title, roles)
                # remember list of roles from xml
                kw["_roles"] = roles
            kw["permission"] = pid
        # python resolvables
        if "condition" in kw:
            kw["condition"] = capi.get_workflow_condition(kw["condition"])
        # numeric
        if "order" in kw:
            kw["order"] = float(kw["order"]) # ValueError if not numeric
        # bool
        if "require_confirmation" in kw:
            try:
                kw["require_confirmation"] = misc.as_bool(kw["require_confirmation"])
                assert kw["require_confirmation"] is not None
            except:
                raise ValueError("Invalid transition value "
                    '[require_confirmation="%s"]' % (
                        t.get("require_confirmation")))
        # multiple-source transitions are really multiple "transition paths"
        for source in sources:
            args = (title, source, destination)
            transitions.append(Transition(*args, **kw))
            log.debug("[%s] adding transition [%s-%s] [%s]" % (
                name, source or "", destination, kw))
    
    return Workflow(name, features, allowed_tags, states, transitions, note)

