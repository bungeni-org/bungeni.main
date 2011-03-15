# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Workflow transition actions.

The name of all internal actions (bungeni private) here must follow:

    _{workflow_name}_{transition_name}
    
The name of all external actions (exposed to bungeni_custom for use per
site deployments) here must simply be:

    {transition_name}
    

Signature of all action utilities here: 

    (info:WorkflowInfo, context:Object) -> None

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflow._actions")

import zope.securitypolicy.interfaces
from bungeni.core.workflows import utils
from bungeni.core.workflows import dbutils
from bungeni.models import utils as model_utils


def create_version(info, context):
    utils.createVersion(info, context)


# address

def _address_create(info, context):
    # !+OWNER_ADDRESS(mr, mov-2010) is this logic correct, also for admin?
    try:
        user_id = dbutils.get_user_login(context.user_id)
    except AttributeError:
        # 'GroupAddress' object has no attribute 'user_id'
        user_id = model_utils.get_principal_id()
    if user_id:
        zope.securitypolicy.interfaces.IPrincipalRoleMap(
            context).assignRoleToPrincipal(u"bungeni.Owner", user_id) 


# agendaitem

def _agendaitem_create(info, context):
    utils.setParliamentId(info, context)
    utils.setBungeniOwner(context)
_agendaitem_create_on_behalf_of = _agendaitem_create

def _agendaitem_submit(info, context):
    utils.setRegistryNumber(info, context)
_agendaitem_resubmit = _agendaitem_submit


# bill

def _bill_create(info, context):
    utils.setParliamentId(info, context)
    user_id = model_utils.get_principal_id()
    if not user_id:
        user_id = "-"
    zope.securitypolicy.interfaces.IPrincipalRoleMap(context
                    ).assignRoleToPrincipal("bungeni.Owner", user_id)
    owner_id = utils.getOwnerId(context)
    if owner_id and (owner_id != user_id):
        zope.securitypolicy.interfaces.IPrincipalRoleMap(context 
            ).assignRoleToPrincipal("bungeni.Owner", owner_id)

def _bill_submit(info, context):
    utils.setBillPublicationDate(info, context)
    utils.setRegistryNumber(info, context)


# group

def _group_create(info, context):
    user_id = model_utils.get_principal_id()
    if user_id:
        zope.securitypolicy.interfaces.IPrincipalRoleMap( context 
            ).assignRoleToPrincipal( u'bungeni.Owner', user_id) 

def _group_activate(info, context):
    utils.set_group_local_role(context)

def _group_dissolve(info, context):
    """ when a group is dissolved all members of this 
    group get the end date of the group (if they do not
    have one yet) and there active_p status gets set to
    False"""
    dbutils.deactivateGroupMembers(context)
    groups = dbutils.endChildGroups(context)
    utils.dissolveChildGroups(groups, context)
    utils.unset_group_local_role(context)

def _group_deactivate(info, context):
    utils.unset_group_local_role(context)


# committee

_committee_create = _group_create
_committee_activate = _group_activate
_committee_dissolve = _group_dissolve
_committee_deactivate = _group_deactivate


# parliament

_parliament_create = _group_create
_parliament_activate = _group_activate
_parliament_dissolve = _group_dissolve
_parliament_deactivate = _group_deactivate


# groupsitting

def _groupsitting_allow_draft_minutes(info, context):
    dbutils.set_real_order(removeSecurityProxy(context))
        
def _groupsitting_publish_agenda(info, context):
    utils.schedule_sitting_items(info, context)


# motion

def _motion_create(info, context):
    utils.setParliamentId(info, context)
    utils.setBungeniOwner(context)
_motion_create_on_behalf_of = _motion_create

def _motion_submit(info, context):
    utils.setRegistryNumber(info, context)
_motion_resubmit = _motion_submit

def _motion_approve(info, context):
    dbutils.setMotionSerialNumber(context)


# question

def _question_create(info, context):
    """Create a question -> state.draft, grant all rights to owner
    deny right to add supplementary questions.
    """
    q = context # context is the newly created question
    log.debug("[QUESTION CREATE] [%s] [%s]" % (info, q))
    utils.setQuestionDefaults(info, q) # !+setQuestionDefaults
    utils.setBungeniOwner(q)
_question_create_on_behalf_of = _question_create

def _question_submit(info, context):
    """A question submitted to the clerks office, the owner cannot edit it 
    anymore the clerk has no edit rights until it is received.
    """
    utils.setRegistryNumber(info, context)
_question_resubmit = _question_submit

def _question_withdraw(info, context):
    """A question can be withdrawn by the owner, it is visible to ...
    and cannot be edited by anyone.
    """
    utils.setQuestionScheduleHistory(info, context)
_question_withdraw_public = _question_withdraw

def _question_allow_response(info, context):
    """A question sent to a ministry for a written answer, 
    it cannot be edited, the ministry can add a written response.
    """
    utils.setMinistrySubmissionDate(info, context)
_question_deferred_allow_response = _question_allow_response

def _question_approve(info, context):
    """The question is admissible and can be send to ministry,
    or is available for scheduling in a sitting.
    """
    dbutils.setQuestionSerialNumber(context)


# tableddocument

def _tableddocument_adjourn(info,context):
    utils.setTabledDocumentHistory(info, context)

def _tableddocument_create(info, context):
    utils.setParliamentId(info, context)
    utils.setBungeniOwner(context)
_tableddocument_create_on_behalf_of = _tableddocument_create

def _tableddocument_submit(info, context):
    utils.setRegistryNumber(info, context)
_tableddocument_resubmit = _tableddocument_submit

def _tableddocument_approve(info, context):
    dbutils.setTabledDocumentSerialNumber(context)


# user

def _user_create(info, context):
    zope.securitypolicy.interfaces.IPrincipalRoleMap(context
        ).assignRoleToPrincipal("bungeni.Owner", context.login)

def _user_resurrect(info, context):
    context.date_of_death = None


#

