# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Loading and processing of Workflow configuration files.

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflow.xmlimport")

import os

from zope.dottedname.resolve import resolve
from zope.component import provideUtility
from zope.security.interfaces import IPermission
from zope.security.permission import Permission
from zope.securitypolicy.rolepermission import rolePermissionManager as rpm
from bungeni.core.workflow import interfaces
from bungeni.core.workflow.states import GRANT, DENY
from bungeni.core.workflow.states import Facet, Feature, State, Transition, Workflow
from bungeni.core.workflow.states import assert_distinct_permission_scopes
from bungeni.capi import capi
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

This file is automatically [re-]generated on startup after all the 
workflow XML files have been loaded, see: 
bungeni.core.workflow.xmlimport.zcml_check_regenerate()

It is regenerated when any workflow transition is modified or added, 
a condition that is checked for and flagged automatically.

Note, since r10609, this is written out to disk for DEBUGGING PURPOSES ONLY,
as all directives here are executed directly on loading workflows.

See Bungeni Custom documentation (and workflows/README.txt) for further details.

-->
%s

</configure>
"""


def zcml_check_regenerate():
    """Called after all XML workflows have been loaded (see adapers.py).
    """
    #!+permissions.zcml(mr, aug-2011) bypass writing to disk?
    filepath = capi.get_path_for(os.path.join("workflows/.auto/", ZCML_FILENAME))
    # read current file
    try:
        persisted = open(filepath, "r").read().decode("utf-8")
    except IOError:
        persisted = u""
    # regenerate, compare, and re-write if needed
    regenerated = ZCML_BOILERPLATE % ("\n".join(ZCML_LINES))
    if persisted != regenerated:
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))
        log.warn("CHANGES to file:\n%s", 
            misc.unified_diff(persisted, regenerated, filepath, "NEW"))
        open(filepath, "w").write(regenerated.encode("utf-8"))

def is_zcml_permissionable(trans_elem):
    # Automatically triggered transitions may not be permissioned.
    return not xas(trans_elem, "trigger") == "automatic"

def zcml_transition_permission(pid, title, roles):
    ZCML_LINES.append(ZCML_INDENT)
    ZCML_LINES.append('%s<permission id="%s" title="%s" />' % (
        ZCML_INDENT, pid, title))
    provideUtility(Permission(pid), IPermission, pid)
    for role in roles:
        ZCML_LINES.append(
            '%s<grant permission="%s" role="%s" />' % (ZCML_INDENT, pid, role))
        rpm.grantPermissionToRole(pid, role, check=False)

#

def get_named(name, seq):
    for s in seq:
        if s.name == name:
            return s

def get_default_facet(facet_seq):
    for facet in facet_seq:
        if facet.default:
            return facet

def get_loaded_workflow(workflow_name):
    """Retrieve the previously loaded named workflow.
    """
    try:
        return Workflow.get_singleton(workflow_name)
    except KeyError:
        return None # no such workflow (or workflow not yet loaded)


def load_features(workflow_name, workflow_elem):
    # all workflow features (enabled AND disabled)
    workflow_features = []
    for f in workflow_elem.iterchildren("feature"):
        feature_name = xas(f, "name")
        feature_enabled = xab(f, "enabled")
        
        # !+FEATURE_DEPENDENCIES archetype/feature inter-dep; should be part of feature descriptor
        if feature_enabled and feature_name == "version":
            assert "audit" in [ fe.name for fe in workflow_features if fe.enabled ], \
                "Workflow [%s] has version but no audit feature" % (workflow_name)
        # feature.parameter !+constraints, in models.feature_* ?
        params = []
        for param in f.iterchildren("parameter"):
            name_value = param.get("name"), param.get("value")
            assert name_value[0] and name_value[1], (workflow_name, feature_name, name_value) #!+RNC
            params.append(name_value)
        num_params, params = len(params), dict(params)
        assert num_params == len(params), \
            "Repeated parameters in feature %r" % (feature_name)
        
        workflow_features.append(Feature(feature_name, 
                enabled=feature_enabled,
                note=xas(f, "note"), 
                **params))
    return workflow_features


def load_facets(workflow_name, workflow_elem):
    facets = []
    for facet in workflow_elem.iterchildren("facet"):
        facet_name = xas(facet, "name")
        assert facet_name, \
            "Workflow %r facet must define a name" % (workflow_name) #!+RNC
        assert get_named(facet_name, facets) is None, \
            "Duplicate workflow %r facet %r" % (workflow_name, facet_name)
        facet_is_default = xab(facet, "default", False)
        facet_note = xas(facet, "note")
        facet_perms = get_permissions_from_allows(workflow_name, facet)
        facets.append(
            Facet(facet_name, facet_note, facet_perms, default=facet_is_default))
    return facets


def get_permissions_from_allows(workflow_name, elem):
    def gen_allow_permissions(allow_elem):
        pid = capi.schema.qualified_pid(workflow_name, xas(allow_elem, "permission"))
        for role in capi.schema.qualified_roles(xas(allow_elem, "roles")):
            yield (GRANT, pid, role)
    perms = []
    for allow in elem.iterchildren("allow"):
        for allow_perm in gen_allow_permissions(allow):
            check_add_assign_permission(workflow_name, perms, allow_perm)
    return perms


def resolve_state_facets(workflow_name, workflow_facets, 
        enabled_feature_names, state_elem
    ):
    """Resolve referenced state facets by feature 
        -> {enabled_feature_name: either(facet, None)}
    """
    state_id = xas(state_elem, "id")
    
    def parse_facet_ref(state_facet_elem):
        """(elem) -> (feature_name, qtk, facet_name)
        Parse ref into feature_name, qualifier_type_key (qtk), facet_name
        """
        ref = xas(state_facet_elem, "ref")
        qualified_feature_name, facet_name = ref.split(".", 1)
        if "#" not in qualified_feature_name:
            qualified_feature_name = qualified_feature_name + "#"
        feature_name, qtk = qualified_feature_name.split("#", 1)
        # normalize feature_name, empty strings become None
        feature_name = feature_name if feature_name else None
        # normalize qtk, empty strings become value of feature_name
        qtk = qtk if qtk else feature_name
        if feature_name is None:
            assert qtk is None, \
                "Must specify feature name in facet '#%s' in state %r" % (
                    qtk, state_id)
        assert facet_name, \
            "Facet %r in state %r must specify a valid facet name" % (
                facet_name, state_id) #!+RNC
        # !+FEATURE_DEPENDENCIES ensure that qtk does correspond to a "valid feature type"?
        return feature_name, qtk, facet_name
    
    def get_facet_seq(feature_name, qtk):
        if feature_name is None:
            return workflow_facets
        feature_wf = get_loaded_workflow(qtk)
        if feature_wf:
            return feature_wf.facets
        return []
    
    def is_facet_ref(state_facet_elem):
        """Return True if facet is a ref, False for an anonymous facet.
        """
        return bool(xas(state_facet_elem, "ref"))
    
    # first, specified facets by feature
    used_facets_fq = {} # used facets by (feature, qualifier)
    for state_facet_elem in state_elem.iterchildren("facet"):
        if is_facet_ref(state_facet_elem):
            # facet ref
            feature_name, qtk, facet_name = parse_facet_ref(state_facet_elem)
            # enabled features (for enabled types) only
            if feature_name not in enabled_feature_names:
                log.warn("State %r specifies facet %r ref '%s#%s' but feature is disabled", 
                    state_id, facet_name, feature_name, qtk)
                continue
            if qtk and get_loaded_workflow(qtk) is None:
                log.warn("State %r specifies facet %r ref '%s#%s' but type is disabled", 
                    state_id, facet_name, feature_name, qtk)
                continue
            facet_seq = get_facet_seq(feature_name, qtk)
            facet = get_named(facet_name, facet_seq)
            assert facet is not None, \
                "No facet %r found (workflow %r state %r, for feature '%s#%s')" % (
                    facet_name, workflow_name, state_id, feature_name, qtk)
        else:
            # anonymous facet
            feature_name, qtk = None, None
            facet_name = "_ANONYMOUS_"
            facet_note = xas(state_facet_elem, "note")
            facet_perms = get_permissions_from_allows(workflow_name, state_facet_elem)
            facet = Facet(facet_name, facet_note, facet_perms, default=False)
        # add to state facets, ensuring only one facet per (feature_name, qtk)
        # feature_name is None implies facets of this "workflow"
        assert (feature_name, qtk) not in used_facets_fq, \
            "Duplicate facet %r for feature '%s#%s' in state %r" % (
                facet_name, feature_name, qtk, state_id)
        used_facets_fq[(feature_name, qtk)] = facet
    
    # second, any remaining enabled features
    seen_feature_names = [ feature_name 
        for (feature_name, qtk) in used_facets_fq ]
    unseen_feature_names = [ feature_name 
        for feature_name in enabled_feature_names 
        if feature_name not in seen_feature_names  ]
    for unseen_fn in unseen_feature_names:
        facet_seq = get_facet_seq(unseen_fn, unseen_fn)
        used_facets_fq[(unseen_fn, unseen_fn)] = get_default_facet(facet_seq)
    return used_facets_fq


def check_add_assign_permission(workflow_name, permissions, (setting, p, r)):
    """Check that permission (setting==GRANT) may be added to list of 
    permissions (assignments) -- a permission assignment should not be 
    duplicated i.e. may be granted or denied ONCE, and adher to permission 
    mixing constraints. A permission assignment may be both global or local.
    """
    # we only "allow" permissions
    assert setting == GRANT, (setting, p, r)
    # check that current permissions list do not GRANT/DENY same pid->role.
    for perm in [(GRANT, p, r), (DENY, p, r)]:
        assert perm not in permissions, "Workflow [%s] " \
            "duplicated or conflicting state permission: (%s, %s, %s)" % (
                workflow_name, setting, p, r)
    permissions.append((setting, p, r))

#

@capi.bungeni_custom_errors
def load(file_key, workflow_name,
        path_custom_workflows=capi.get_path_for("workflows")
    ):
    """ (type_key:str, file_key:str, workflow_name:str,
            path_custom_workflows:str) -> Workflow
    
    Loads the workflow XML definition file, returning the correspondingly setup 
    Workflow instance. Called by workflows.adapters.load_workflow.
    """
    file_path = os.path.join(path_custom_workflows, "%s.xml" % (file_key))
    workflow_doc = capi.schema.validate_file_rng("workflow", file_path)
    return _load(workflow_name, workflow_doc)

def _load(workflow_name, workflow):
    """ (workflow_name:str, workflow:etree_doc) -> Workflow
    """
    workflow_title = xas(workflow, "title")
    naming.MSGIDS.add(workflow_title)
    workflow_description = xas(workflow, "description")
    naming.MSGIDS.add(workflow_description)
    transitions = []
    states = []
    note = xas(workflow, "note")
    
    # initial_state, in XML indicated with a transition.@source=""
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
        m = "Invalid element <%s> id=%r in workflow %r" % (tag, id, workflow_name)
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
    for (key, permission_action) in capi.schema.qualified_permission_actions(
            workflow_name, xas(workflow, "permission_actions", "").split()
        ):
        pid = "bungeni.%s.%s" % (key, permission_action)
        title = "%s %s" % (
            permission_action, naming.split_camel(naming.model_name(key)))
        # !+ add to a Workflow.defines_permissions list
        ZCML_LINES.append(
            '%s<permission id="%s" title="%s" />' % (ZCML_INDENT, pid, title))
        provideUtility(Permission(pid), IPermission, pid)
    
    # global grants
    global_pid_roles = {} # {pid: [role]}
    global_grants = get_permissions_from_allows(workflow_name, workflow)
    for (setting, pid, role) in global_grants:
        # for each global permission, build list of roles it is set to
        global_pid_roles.setdefault(pid, []).append(role)
        assert setting and pid and role, \
            "Global grant must specify valid permission/role" #!+RNC
        # !+ add to a Workflow.global_grants list
        ZCML_LINES.append(
            '%s<grant permission="%s" role="%s" />' % (ZCML_INDENT, pid, role))
        # no real need to check that the permission and role of a global grant 
        # are properly registered in the system -- an error should be raised 
        # by the zcml if either is not defined.
        rpm.grantPermissionToRole(pid, role, check=False)

    for perm, roles in global_pid_roles.items():
        # assert roles mix limitations for state permissions
        assert_distinct_permission_scopes(perm, roles, workflow_name, "global grants")
    
    # all workflow features (enabled AND disabled)
    workflow_features = load_features(workflow_name, workflow)
    enabled_feature_names = [None] + [ 
        f.name for f in workflow_features if f.enabled ]
    # !+EVENT_FEATURE_TYPES add each as enabled_feature_names, or extend the 
    # facet quailifer by feature_name(sub_type_key).facet_ref?
    # workflow facets
    workflow_facets = load_facets(workflow_name, workflow)
    
    # states
    for s in workflow.iterchildren("state"):
        # @id
        state_id = xas(s, "id")
        assert state_id, "Workflow State must define @id" #!+RNC
        validate_id(state_id, "state")
        
        # @actions - transition-to-state actions
        state_actions = []
        for action_name in xas(s, "actions", "").split():
            state_actions.append(capi.get_workflow_action(action_name))
        
        # @permissions_from_state
        permissions = [] # [ tuple(bool:int, permission:str, role:str) ]
        # state.@permissions_from_state : to reduce repetition and enhance 
        # maintainibility of workflow XML files, a state may inherit ALL 
        # permissions defined by the specified state. NO other permissions 
        # may be specified by this state. 
        from_state = get_from_state(xas(s, "permissions_from_state"))
        parent_permissions = xab(s, "parent_permissions")
        if parent_permissions:
            pass # no own permission definitions allowed
        elif from_state:
            # assimilate (no more no less) the state's permissions !+tuple, use same?
            permissions[:] = from_state.permissions
        else:
            used_facets_fq = resolve_state_facets(
                workflow_name, workflow_facets, enabled_feature_names, s)
            # assimilate permissions from facets from None and all enabled features
            def add_facet_permissions(facet):
                for perm in facet.permissions:
                    check_add_assign_permission(workflow_name, permissions, perm)
                    check_not_global_grant(perm[1], perm[2])
            for (feature_name, qtk) in used_facets_fq:
                # debug check that feature is enabled
                assert feature_name in enabled_feature_names
                facet = used_facets_fq[(feature_name, qtk)]
                if facet is not None:
                    add_facet_permissions(facet)
        
        # states
        state_title = xas(s, "title")
        naming.MSGIDS.add(state_title)
        states.append(
            State(state_id, state_title,
                xas(s, "note"),
                state_actions, permissions,
                parent_permissions,
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
        roles = capi.schema.qualified_roles(kw.pop("roles", ""))
        if not is_zcml_permissionable(t):
            assert not roles, "Workflow [%s] - non-permissionable transition " \
                "does not allow @roles [%s]." % (workflow_name, roles) #!+RNC
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
                assert kw["require_confirmation"] is not None #!+RNC
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
    
    return Workflow(workflow_name,
        workflow_features, workflow_facets, states, transitions, global_grants,
        workflow_title, workflow_description, note)

