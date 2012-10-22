# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Worklfow utilities

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflows.utils")

import sys

from zope.securitypolicy.interfaces import IPrincipalRoleMap
from zope.app.component.hooks import getSite
from bungeni.core.workflow.interfaces import IWorkflowController
from bungeni.core.workflow.interfaces import (NoTransitionAvailableError, 
    InvalidStateError
)

import bungeni.models.interfaces as interfaces
#import bungeni.models.domain as domain
from bungeni.models.utils import get_principal_id
import bungeni.core.version
#import bungeni.core.globalsettings as prefs
from bungeni.ui.utils import debug

import re
import dbutils

from bungeni.utils.capi import capi, bungeni_custom_errors

from ConfigParser import ConfigParser, NoOptionError
import os


''' !+UNUSED(mr, mar-2011)
def get_parliament(context):
    """go up until we find a parliament """
    parent = context.__parent__
    while parent:
        if  interfaces.IParliament.providedBy(parent):
            return parent
        else:
            try:
                parent = parent.__parent__
            except:
                parent = None
    if not parent:
        parliament_id = context.parliament_id
        session = Session()
        parliament = session.query(domain.Parliament).get(parliament_id)
        return parliament
'''


def formatted_user_email(user):
    return '"%s %s" <%s>' % (user.first_name, user.last_name, user.email)

# parliamentary item

def assign_role(role_id, principal_id, context):
    """Add or activate implied role on this context, for implied principal.
    !+check if already defined and active, inactive?
    !+PrincipalRoleMapDynamic(mr, may-2012) infer role from context data
    """
    log.debug("Assigning role [%s] to principal [%s] on [%s]", 
        role_id, principal_id, context)
    # throws IntegrityError when principal_id is None
    IPrincipalRoleMap(context).assignRoleToPrincipal(role_id, principal_id)
def unset_role(role_id, principal_id, context):
    log.debug("Unsetting role [%s] for principal [%s] on [%s]", 
        role_id, principal_id, context)
    IPrincipalRoleMap(context).unsetRoleForPrincipal(role_id, principal_id)

def assign_role_owner_to_login(context):
    """Assign bungeni.Owner role on context to the currently logged in user.
    """
    current_user_login = get_principal_id()
    log.debug("assign_role_owner_to_login [%s] user:%s" % (
        context, current_user_login))
    assign_role("bungeni.Owner", current_user_login, context)
    # "owner" from direct user/owner field !+why is this needed here?
    # !+ owner may still be None for types with no such direct field
    #owner = context.owner
    #if owner and (owner.login != current_user_login):
    #    assign_role("bungeni.Owner", owner.login, context)

def create_version(context):
    """Create a new version of an object and return it.
    Note: context.status is already updated to destination state.
    """
    return bungeni.core.version.create_version(context)
    # !+capi.template_message_version_transition
    #message_template = "New version on workflow transition to: %(status)s"
    #message = message_template % context.__dict__


@bungeni_custom_errors
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
    


is_pi_scheduled = dbutils.is_pi_scheduled


# question
# !+PrincipalRoleMapDynamic(mr, may-2012) infer role from context data
def assign_role_minister_question(context):
    assert interfaces.IQuestion.providedBy(context), \
        "Not a Question: %s" % (context)
    if context.ministry is not None:
        ministry_login_id = context.ministry.group_principal_id
        if ministry_login_id:
            assign_role("bungeni.Minister", ministry_login_id, context)

unschedule_doc = dbutils.unschedule_doc

''' !+UNUSUED (and incorrect) :
def getQuestionSchedule(context):
    question_id = context.question_id
    return dbutils.is_pi_scheduled(question_id)

def getMotionSchedule(context):
    motion_id = context.motion_id
    return dbutils.is_pi_scheduled(motion_id)

def getQuestionSubmissionAllowed(context):
    return prefs.getQuestionSubmissionAllowed()
'''

'''
# question, motion, bill, agenda_item, tabled_document
# !+setParliamentId(mr, mar-2011) this is used in "create" transitions... 
def setParliamentId(context):
    if not context.parliament_id:
         context.parliament_id = prefs.getCurrentParliamentId()
'''

# tabled_document
def setTabledDocumentHistory(context):
    pass

def get_group_local_role(group):
    if interfaces.IParliament.providedBy(group):
        return "bungeni.MP"
    elif interfaces.IMinistry.providedBy(group):
        return "bungeni.Minister"
    elif interfaces.ICommittee.providedBy(group): 
        return "bungeni.CommitteeMember"
    elif interfaces.IPoliticalGroup.providedBy(group):
        return "bungeni.PoliticalGroupMember"
    elif interfaces.IGovernment.providedBy(group):
        return "bungeni.Government"
    elif interfaces.IOffice.providedBy(group):
        return group.office_role
    else:
        # fallback to a generic (but unregistered) group membership role
        return "bungeni.GroupMember"

def get_group_context(context):
    if interfaces.IOffice.providedBy(context):
        return getSite() #get_parliament(context)
    else:
        return context

# groups
# !+PrincipalRoleMapDynamic(mr, may-2012) infer role from context data
def _set_group_local_role(context, unset=False):
    group = context
    role = get_group_local_role(group)
    prm = IPrincipalRoleMap(get_group_context(group))
    if not unset:
        prm.assignRoleToPrincipal(role, group.group_principal_id)
    else:
        prm.unsetRoleForPrincipal(role, group.group_principal_id)

def set_group_local_role(context):
    _set_group_local_role(context, unset=False)

def unset_group_local_role(context):
    _set_group_local_role(context, unset=True)

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
SCHEDULED = "scheduled"
PENDING = "tobescheduled"
def schedule_sitting_items(context):
    
    # !+fireTransitionToward(mr, dec-2010) sequence of fireTransitionToward 
    # calls was introduced in r5818, 28-jan-2010 -- here the code is reworked
    # to be somewhat more sane, and added logging of both SUCCESS and of 
    # FAILURE of each call to fireTransitionToward().
    #
    # The check/logging should be removed once it is understood whether
    # NoTransitionAvailableError is *always* raised (i.e. fireTransitionToward is
    # broken) or it is indeed raised correctly when it should be.
    def fireTransitionScheduled(item, wfc, check_security=False, 
        toward=SCHEDULED):
        try:
            wfc.fireTransitionToward(toward, check_security=check_security)
            raise RuntimeWarning(
                """It has WORKED !!! fireTransitionToward("scheduled")""")
        except (NoTransitionAvailableError, RuntimeWarning):
            debug.log_exc_info(sys.exc_info(), log.error)
    
    for schedule in context.item_schedule:
        wfc = IWorkflowController(schedule.item, None)
        if wfc is None:
            continue
        wf = wfc.workflow
        try:
            if wf.get_state(SCHEDULED):
                fireTransitionScheduled(schedule.item, wfc)
        except InvalidStateError:
            #try to fire to next logical scheduled state
            if (wfc.state_controller.get_status() in
                wfc.workflow.get_state_ids(tagged=[PENDING], 
                    restrict=False
                )
            ):
                transition_ids = wfc.getFireableTransitionIds()
                for transition_id in transition_ids:
                    transition = wf.get_transition(transition_id)
                    if (transition.destination in 
                        wfc.workflow.get_state_ids(tagged=[SCHEDULED], 
                            restrict=False)
                        ):
                        fireTransitionScheduled(schedule.item, wfc,
                            toward=transition.destination
                        )
                        break

def check_agenda_finalized(context):
    unfinalized_tags = [SCHEDULED]
    def check_finalized(schedule):
        wfc = IWorkflowController(schedule.item, None)
        if wfc is None:
            return True
        #!+TYPES(mb, march-2012) There might be a more elegant approach here
        # to filter out 'text records' from the schedule
        if interfaces.IBungeniParliamentaryContent.providedBy(schedule.item):
            return (wfc.state_controller.get_status() in 
                wfc.workflow.get_state_ids(not_tagged=unfinalized_tags,
                    restrict=False
                )
            )
        else:
            return True
    check_list = map(check_finalized, context.items.values())
    return  (False not in check_list)

