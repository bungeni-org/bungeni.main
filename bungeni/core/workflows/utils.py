# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Worklfow utilities

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflows.utils")

import sys

from zope.security.proxy import removeSecurityProxy
from zope.securitypolicy.interfaces import IPrincipalRoleMap
from bungeni.core.workflow.interfaces import IWorkflowController, \
    NoTransitionAvailableError, InvalidStateError

from bungeni.models import interfaces
from bungeni.models.utils import (
    get_chamber_for_group, 
    is_current_or_delegated_user, 
    get_user,
)
from bungeni.feature.interfaces import IFeatureSchedule

from bungeni.utils import common
from bungeni.ui.utils import debug
from bungeni.utils.misc import describe
from bungeni import _
#from bungeni.alchemist import Session

import re
import dbutils

from bungeni.capi import capi

from ConfigParser import ConfigParser, NoOptionError
import os


def formatted_user_email(user):
    return '"%s %s" <%s>' % (user.first_name, user.last_name, user.email)


def set_role(role_id, principal_name, context):
    """Add or activate implied role on this context, for implied principal.
    !+check if already defined and active, inactive?
    !+PrincipalRoleMapDynamic(mr, may-2012) infer role from context data
    """
    log.debug("Assigning role [%s] to principal [%s] on [%s]", 
        role_id, principal_name, context)
    # throws IntegrityError when principal_name is None
    IPrincipalRoleMap(context).assignRoleToPrincipal(role_id, principal_name)


def unset_role(role_id, principal_name, context):
    log.debug("Unsetting role [%s] for principal [%s] on [%s]", 
        role_id, principal_name, context)
    IPrincipalRoleMap(context).unsetRoleForPrincipal(role_id, principal_name)


def assign_ownership(context):
    """Assign editorial (all context types) and legal (only legal types)
    "ownership" roles.
    
    The actual (current) user creating the context is always granted the 
    "editorial ownership" for the item i.e. "bungeni.Drafter".
    
    If context is a "legal doc", then the user who would be the legal owner of
    the doc is determined and granted "legal ownership" i.e. "bungeni.Owner".
    """
    
    # bungeni.Drafter - all types
    current_user_login = common.get_request_login()
    log.debug("assign_ownership: role %r to user %r on [%s]" % (
        "bungeni.Drafter", current_user_login, context))
    set_role("bungeni.Drafter", current_user_login, context)
    
    # bungeni.Owner - selected types
    owner_login = None
    if interfaces.is_legal_doc(context):
        owner_login = _determine_related_user(context,user_attr_name="owner").login
    elif interfaces.IUser.providedBy(context):
        owner_login = context.login
    elif interfaces.IGroup.providedBy(context):
        owner_login = context.principal_name
    elif interfaces.ISignatory.providedBy(context):
        owner_login = _determine_related_user(context, user_attr_name="user").login
    if owner_login is not None:
        log.debug("assign_ownership: role %r to user %r on [%s]" % (
            "bungeni.Owner", owner_login, context))
        set_role("bungeni.Owner", owner_login, context)
    else:
        log.warn("assign_ownership: NO owner could be determined from [%s] - "
            "NOT assigning role %r to any user" % (context, "bungeni.Owner"))

def user_is_context_owner(context):
    """Test if current user is the context owner e.g. to check if someone 
    manipulating the context object is other than the owner of the object.
    
    Assumption: context is IOwned.
    
    A delegate is considered to be an owner of the object.
    """
    user = _determine_related_user(context, user_attr_name="owner")
    return is_current_or_delegated_user(user)

def _determine_related_user(context, user_attr_name="owner"):
    """Get the user instance that is the value of the {user_attr_name} attribute.
    
    The context may be newly created, not yet flushed to db (so may have 
    "owner_id" set but "owner" not yet updated).
    """
    user = getattr(context, user_attr_name)
    # context not yet flushed may have "X_id" set but "X" not yet updated
    if user is None:
        # !+ some contexts define an "X" but not an "X_id"!
        user_id_attr_name = "%s_id" % (user_attr_name)
        if hasattr(context, user_id_attr_name):
            user = get_user(getattr(context, user_id_attr_name))
    assert user, "User (as %r on %s) may not be None" % (user_attr_name, context)
    return user


@capi.bungeni_custom_errors
def get_mask(context):
    # assert IBungeniParliamentaryContent.providedBy(context)
    # !+IBungeniParliamentaryContent(mr, nov-2011) only context typed
    # interfaces.IBungeniParliamentaryContent should ever get here!
    # But for this case, all we need is that context defines a type:
    m = "PI context [%s] for get_mask must specify a type attr" % (context)
    assert hasattr(context, "type"), m
    path = capi.get_path_for("registry")
    config = ConfigParser()
    config.readfp(open(os.path.join(path, "config.ini")))
    try:
        return config.get("types", context.type)
    except NoOptionError:
        return None


# !+REGISTRY(mr, apr-2012) this utility MUST ALWAYS be executed whenever a doc 
# reaches a state that semantically implies "receive" !!
@describe(_("Sets the document's registry number"))
def set_doc_registry_number(doc):
    """A doc's registry_number should be set on the item being 
    submitted to parliament.
    """
    # never overwrite a previously set registry_number
    if doc.registry_number is not None:
        log.warn("Ignoring attempt to reset doc [%s] registry_number [%s]" % (
            doc, doc.registry_number))
        return
    
    mask = get_mask(doc)
    if mask == "manual" or mask is None:
        return
    
    # ensure that sequences are updated -- independently of whether these are 
    # used by the mask string templates!
    #registry_number_general = dbutils.get_next_reg() # all docs
    #registry_number_specific = dbutils.get_next_prog(doc) # per doc type
    registry_count_general, registry_count_specific = \
        dbutils.get_registry_counts(doc.__class__)
    registry_number_general = 1 + registry_count_general
    registry_number_specific = 1 + registry_count_specific
    type_key = doc.type
    
    # !+ why not just use string.Template ?!
    items = re.findall(r"\{(\w+)\}", mask)
    for name in items:
        if name == "registry_number":
            mask = mask.replace("{%s}" % name, str(registry_number_general))
        if name == "progressive_number":
            mask = mask.replace("{%s}" % name, str(registry_number_specific))
        if name == "type":
            mask = mask.replace("{%s}" % name, type_key)
    
    doc.registry_number = mask

@describe(_(u"Sets the serial number of the document in the order of approval"))
def set_doc_type_number(doc):
    """Sets the number that indicates the order in which docs of this type
    have been approved by the Speaker to be the current maximum + 1.
    
    The number is reset at the start of each new parliamentary session with the 
    first doc of this type being assigned the number 1.
    """
    doc.type_number = dbutils.get_max_type_number(doc.__class__) + 1


is_pi_scheduled = dbutils.is_pi_scheduled

unschedule_doc = dbutils.unschedule_doc


# groups
# !+PrincipalRoleMapDynamic(mr, may-2012) infer role from context data

def get_group_privilege_extent_context(group):
    privilege_extent = removeSecurityProxy(group.__class__).privilege_extent
    if privilege_extent == "group":
        return group
    elif privilege_extent == "chamber":
        return get_chamber_for_group(group)
    elif privilege_extent == "legislature":
        return common.get_application()
    raise ValueError(group)

def set_group_local_role(group):
    set_role(group.group_role, group.principal_name, 
        get_group_privilege_extent_context(group))

def unset_group_local_role(group):
    unset_role(group.group_role, group.principal_name, 
        get_group_privilege_extent_context(group))


def dissolveChildGroups(groups, context):
    for group in groups:
        # !+group_dissolve(mr, may-2012) assumes that workflow of EVERY group
        # type has a state "active" AND a state "dissolved" AND a transition
        # from first to second AND that the semantic meaning of state 
        # "dissolved" is indeed dissolution of the group... should probably 
        # be replaced by a GroupType.dissolve() method that knows how to 
        # dissolve itself.
        IWorkflowController(group).fireTransition("active-dissolved", 
            check_security=False)

# sitting
@describe(_(u"Schedules the items on a sitting"))
def schedule_sitting_items(context):
    
    # !+fireTransitionToward(mr, dec-2010) sequence of fireTransitionToward 
    # calls was introduced in r5818, 28-jan-2010 -- here the code is reworked
    # to be somewhat more sane, and added logging of both SUCCESS and of 
    # FAILURE of each call to fireTransitionToward().
    #
    # The check/logging should be removed once it is understood whether
    # NoTransitionAvailableError is *always* raised (i.e. fireTransitionToward is
    # broken) or it is indeed raised correctly when it should be.
    def fireTransitionScheduled(item, wfc, toward):
        try:
            wfc.fireTransitionToward(toward, check_security=True)
            raise RuntimeWarning(
                "It has WORKED !!! fireTransitionToward(%r)" % (toward))
        except (NoTransitionAvailableError, RuntimeWarning):
            debug.log_exc_info(sys.exc_info(), log.error)
    
    for schedule in context.items.values():
        if not IFeatureSchedule.providedBy(schedule.item):
            continue
        wfc = IWorkflowController(schedule.item)
        wf = wfc.workflow
        schedule_feature = wf.get_feature("schedule")
        scheduled_states = schedule_feature.p.scheduled_states
        schedulable_states = schedule_feature.p.schedulable_states
        try:
            for target_state in scheduled_states:
                if wf.get_state(target_state):
                    fireTransitionScheduled(schedule.item, wfc, target_state)
        except InvalidStateError:
            # try to fire to next logical scheduled state
            if schedule.item.status in schedulable_states: # !+is_schedulable
                transition_ids = wfc.getFireableTransitionIds()
                for transition_id in transition_ids:
                    transition = wf.get_transition(transition_id)
                    if transition.destination in scheduled_states: 
                        fireTransitionScheduled(schedule.item, wfc,
                            toward=transition.destination)
                        break

def check_agenda_finalized(context):
    def check_finalized(schedule):
        wfc = IWorkflowController(schedule.item, None)
        if wfc is None:
            return True
        #!+TYPES(mb, march-2012) There might be a more elegant approach here
        # to filter out 'text records' from the schedule
        if interfaces.IBungeniParliamentaryContent.providedBy(schedule.item):
            schedule_feature = wfc.wf.get_feature("schedule")
            return (wfc.state_controller.get_status() not in 
                schedule_feature.p.scheduled_states
            )
        else:
            return True
    check_list = map(check_finalized, context.items.values())
    return  (False not in check_list)


def view_permission(item):
    ti = capi.get_type_info(item)
    return "bungeni.%s.View" % (ti.permission_type_key)


