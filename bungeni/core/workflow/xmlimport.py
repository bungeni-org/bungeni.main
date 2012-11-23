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
from bungeni.core.workflow.states import Facet, Feature, State, Transition, Workflow
from bungeni.core.workflow.states import assert_distinct_permission_scopes
from bungeni.utils.capi import capi, bungeni_custom_errors
from bungeni.schema import WORKFLOW_SCHEMA
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

TRANS_ATTRS_REQUIREDS = ("title", "source", "destination")
TRANS_ATTRS_OPTIONALS = ("grouping_unique_sources", "condition", "trigger", 
    "roles", "order", "require_confirmation", "note")
TRANS_ATTRS = TRANS_ATTRS_REQUIREDS + TRANS_ATTRS_OPTIONALS

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

See Bungeni Custom documentation (and workflows/README.txt) for further details.

-->
%s

</configure>
"""


class ChangedWorkflowsPermissionsZCML(Exception): pass
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

def get_named(name, seq):
    for s in seq:
        if s.name == name:
            return s

def qualified_permission_actions(permission_type_key, permission_actions):
    """[space-separated-str] -> [(permission_type_key, permission_action)]
    """
    return [ qualified_permission_action(permission_type_key, pa) 
        for pa in permission_actions ]

def qualified_permission_action(permission_type_key, pa):
    """str -> (permission_type_key, permission_action)
    where string may be: ".Action" or "type_key.Action"
    """
    # !+do not allow a preceeding "bungeni."?
    if pa.startswith("bungeni."):
        pa = pa[len("bungeni."):]
    qpa = pa.split(".", 1)
    assert len(qpa) == 2, \
        "No dot in workflow %r permission action %r" % (permission_type_key, pa)
    return (qpa[0] or permission_type_key, qpa[1])

def qualified_pid(permission_type_key, pa):
    return "bungeni.%s.%s" % qualified_permission_action(permission_type_key, pa)


def qualified_roles(roles):
    """space-separated-str -> [role_id]
    Parse space separated string into a list of qualified role ids where 
    each role word-str may be: "Role" or ".Role" or "bungeni.Role"
    """
    qrs = []
    for r in roles.split():
        if r.startswith("bungeni."):
            qrs.append(r)
        elif r.startswith("."):
            qrs.append("bungeni%s" % (r))
        else:
            qrs.append("bungeni.%s" % (r))
    # !+alchemist.model.validated_set
    # !+alchemist.model.norm_sorted
    return sorted(qrs)


def get_facets(workflow_name, feature_name, elem):
    facets = []
    for facet in elem.iterchildren("facet"):
        facet_name = xas(facet, "name")
        assert facet_name, \
            "Workflow %r [%s] facet must define a name" % (workflow_name, feature_name)
        assert get_named(facet_name, facets) is None, \
            "Duplicate feature %r facet %r" % (feature_name, facet_name)
        facet_is_default = xab(facet, "default", False)
        facet_note = xas(facet, "note")
        facet_perms = get_permissions_from_allows(workflow_name, facet)
        facets.append(
            Facet(facet_name, facet_note, facet_perms, default=facet_is_default))
    return facets

def get_permissions_from_allows(workflow_name, elem):
    def gen_allow_permissions(allow_elem):
        pid = qualified_pid(workflow_name, xas(allow_elem, "permission"))
        for role in qualified_roles(xas(allow_elem, "roles")):
            yield (GRANT, pid, role)
    perms = []
    for allow in elem.iterchildren("allow"):
        for allow_perm in gen_allow_permissions(allow):
            check_add_assign_permission(workflow_name, perms, allow_perm)
    return perms

def check_add_assign_permission(workflow_name, permissions, (assignment, p, r)):
    """Check that permission (assignment==GRANT) may be added to list of 
    permissions (assignments) -- a permission assignment should not be 
    duplicated i.e. may be granted or denied ONCE, and adher to permission 
    mixing constraints. A permission assignment may be both global or local.
    """
    # we only "allow" permissions
    assert assignment == GRANT, (assignment, p, r)
    # check that current permissions list do not GRANT/DENY same pid->role.
    for perm in [(GRANT, p, r), (DENY, p, r)]:
        assert perm not in permissions, "Workflow [%s] state [%s] " \
            "duplicated or conflicting state permission: (%s, %s, %s)" % (
                workflow_name, state_id, assignment, p, r)
    permissions.append((assignment, p, r))

#

@bungeni_custom_errors
def load(file_key, workflow_name,
        path_custom_workflows=capi.get_path_for("workflows")
    ):
    """ (type_key:str, file_key:str, workflow_name:str, 
            path_custom_workflows:str) -> Workflow
    
    Loads the workflow XML definition file, returning the correspondingly setup 
    Workflow instance. Called by workflows.adapters.load_workflow.
    """
    file_path = os.path.join(path_custom_workflows, "%s.xml" % (file_key))
    workflow_doc = etree.fromstring(open(file_path).read())
    WORKFLOW_SCHEMA.assertValid(workflow_doc) # raises etree.DocumentInvalid
    return _load(workflow_name, workflow_doc)

def _load(workflow_name, workflow):
    """ (workflow_name:str, workflow:etree_doc) -> Workflow
    """
    # !+ @title, @description
    transitions = []
    states = []
    note = xas(workflow, "note")
    allowed_tags = xas(workflow, "tags", "").split()
    
    # initial_state, in XML indicated a transition source=""
    initial_state = None
    
    ZCML_PROCESSED = bool(workflow_name in ZCML_WORKFLOWS_PROCESSED)
    if not ZCML_PROCESSED:
        ZCML_WORKFLOWS_PROCESSED.add(workflow_name)
        ZCML_LINES.append(ZCML_INDENT)
        ZCML_LINES.append(ZCML_INDENT)
        ZCML_LINES.append("%s<!-- %s -->" % (ZCML_INDENT, workflow_name))
    
    def validate_id(id, tag):
        """Ensure that ID values are unique within the same XML doc scope.
        """
        m = 'Invalid <%s> id="%s" in workflow [%s]' % (tag, id, workflow_name)
        assert id not in validate_id.wuids, "%s -- id not unique in workflow document" % (m)
        validate_id.wuids.add(id)
    validate_id.wuids = set() # unique IDs in this XML workflow file
    
    def get_from_state(state_id):
        if state_id is None:
            return
        for state in states:
            if state.id == state_id:
                return state
        raise ValueError("Invalid value: permissions_from_state=%r" % (state_id))
    
    def check_not_global_grant(pid, role):
        # ensure global and local assignments are distinct
        # (global: global_pid_roles, workflow_name)
        global_proles = global_pid_roles.get(pid, "")
        assert role not in global_proles, ("Workflow [%s] may not mix "
            "global and local granting of a same permission [%s] to a "
            "same role [%s].") % (workflow_name, pid, role)
    
    # permission_actions -> permissions for this type
    for (key, permission_action) in qualified_permission_actions(
            workflow_name, xas(workflow, "permission_actions", "").split()
        ):
        pid = "bungeni.%s.%s" % (key, permission_action)
        title = "%s %s" % (
            permission_action, naming.split_camel(naming.model_name(key)))
        # !+ add to a Workflow.defines_permissions list
        ZCML_LINES.append(
            '%s<permission id="%s" title="%s" />' % (ZCML_INDENT, pid, title))
    
    # global grants
    global_pid_roles = {} # {pid: [role]}
    global_grants = get_permissions_from_allows(workflow_name, workflow)
    for (setting, pid, role) in global_grants:
        # for each global permission, build list of roles it is set to
        global_pid_roles.setdefault(pid, []).append(role)
        assert setting and pid and role, \
            "Global grant must specify valid permission/role"
        # !+ add to a Workflow.global_grants list
        ZCML_LINES.append(
            '%s<grant permission="%s" role="%s" />' % (ZCML_INDENT, pid, role))
        # no real need to check that the permission and role of a global grant 
        # are properly registered in the system -- an error should be raised 
        # by the zcml if either is not defined. 
    for perm, roles in global_pid_roles.items():
        # assert roles mix limitations for state permissions
        assert_distinct_permission_scopes(perm, roles, workflow_name, "global grants")
    
    
    # features
    features = []
    for f in workflow.iterchildren("feature"):
        # @name
        feature_name = xas(f, "name")
        assert feature_name, "Workflow %r feature must define @name" % (workflow_name)
        # @enabled
        feature_enabled = xab(f, "enabled")
        # !+ archetype/feature inter-dep; should be part of feature descriptor
        if feature_enabled and feature_name == "version":
            assert "audit" in [ fe.name for fe in features if fe.enabled ], \
                "Workflow [%s] has version but no audit feature" % (workflow_name)
        # feature.parameter !+constraints, in models.feature_* ?
        params = []
        for param in f.iterchildren("parameter"):
            name_value = param.get("name"), param.get("value")
            assert name_value[0] and name_value[1], (workflow_name, feature_name, name_value)
            params.append(name_value)
        num_params, params = len(params), dict(params)
        assert num_params == len(params), \
            "Repeated parameters in feature %r" % (feature_name)
        # feature.facet
        facets = get_facets(workflow_name, feature_name, f)
        features.append(Feature(feature_name, 
                enabled=feature_enabled,
                note=xas(f, "note"), 
                facets=facets,
                **params))
    # top level (workflow, feature_name==None) facets
    workflow_facets = get_facets(workflow_name, None, workflow)
    none_feature = Feature(None, enabled=True, facets=workflow_facets)
    
    # states
    for s in workflow.iterchildren("state"):
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
                raise ValueError("Invalid state value [version=%r]" % (
                    s.get("version")))
            if make_version:
                state_actions.append(ACTIONS_MODULE.create_version)
        # state-id-inferred action - if "actions" module defines an action for
        # this state (associated via a naming convention), then use it.
        # !+ tmp, until state_actions are user-exposed as part of <state>
        action_name = "_%s_%s" % (workflow_name, state_id)
        if hasattr(ACTIONS_MODULE, action_name):
            state_actions.append(getattr(ACTIONS_MODULE, action_name))
        
        # @tags
        tags = xas(s, "tags", "").split()
        # @permissions_from_state
        permissions = [] # [ tuple(bool:int, permission:str, role:str) ]
        # state.@permissions_from_state : to reduce repetition and enhance 
        # maintainibility of workflow XML files, a state may inherit ALL 
        # permissions defined by the specified state. NO other permissions 
        # may be specified by this state. 
        from_state = get_from_state(xas(s, "permissions_from_state"))
        if from_state:
            permissions.extend(from_state.permissions)
        else:
            # use permissions from facets
            used_facets_by_feature = {}
            for facet in s.iterchildren("facet"):
                ref = xas(facet, "ref")
                assert ref is not None, "State %r facet must specify a ref" % (state_id)
                feature_name, facet_name = ref.split(".", 1)
                feature_name = feature_name if feature_name else None # "" -> None
                # feature_name is None -> "workflow" facets
                assert feature_name not in used_facets_by_feature, \
                    "Duplicate facet %r for feature %r in state %r" % (facet_name, feature_name, state_id)
                assert facet_name, \
                    "Facet %r in state %r must specify a valid facet name" % (facet_name, state_id)
                if feature_name is None:
                    facet_seq = workflow_facets
                else:
                    facet_seq = get_named(feature_name, features).facets
                used_facets_by_feature[feature_name] = get_named(facet_name, facet_seq)
                assert used_facets_by_feature[feature_name] is not None, \
                    "No facet %r found (used in state %r)" % (facet_name, state_id)
            
            def add_facet_permissions(used_facets_by_feature, feature):
                if feature.name in used_facets_by_feature:
                    facet = used_facets_by_feature[feature.name]
                    perms_to_add = facet.permissions
                else:
                    default_facet = feature.get_default_facet()
                    perms_to_add = []
                    if default_facet is not None:
                        perms_to_add = default_facet.permissions
                for perm in perms_to_add:
                    check_add_assign_permission(workflow_name, permissions, perm)
                    check_not_global_grant(perm[1], perm[2])
            
            # first, assimilate permissions from workflow-level facets (the None feature)
            add_facet_permissions(used_facets_by_feature, none_feature)
            # then from facets from all enabled features
            for feature in features:
                if feature.enabled:
                    add_facet_permissions(used_facets_by_feature, feature)
                else:
                    if feature.name in used_facets_by_feature:
                        log.warn("State %r specifies facet for disabled feature %r", 
                            state_id, feature.name)
        
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
        roles = qualified_roles(kw.pop("roles", ""))
        if not is_zcml_permissionable(t):
            assert not roles, "Workflow [%s] - non-permissionable transition " \
                "does not allow @roles [%s]." % (workflow_name, roles)
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
        #    kw["permission"] = "bungeni.%s.Edit" % (workflow_name) # fallback permission
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
            pid = "bungeni.%s.wf.%s" % (workflow_name, tid)
            if not ZCML_PROCESSED:
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
                workflow_name, source or "", destination, kw))
    
    return Workflow(workflow_name, features, allowed_tags, states, transitions, note)

