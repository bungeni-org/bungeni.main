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
log = __import__("logging").getLogger("bungeni.core.workflows._actions")

from bungeni.core.workflows import utils
from bungeni.core.workflows import dbutils
from bungeni.models import utils as model_utils

#

create_version = utils.create_version

#

def _pi_create(info, context):
    #!+utils.setParliamentId(info, context)
    utils.assign_owner_role_pi(context)

def _pi_submit(info, context):
    utils.set_pi_registry_number(info, context)


# address

def _address_create(info, context):
    # !+OWNER_ADDRESS(mr, mov-2010) is this logic correct, also for admin?
    try:
        user_login = dbutils.get_user_login(context.user_id)
    except AttributeError:
        # 'GroupAddress' object has no attribute 'user_id'
        user_login = model_utils.get_principal_id()
    if user_login:
        utils.assign_owner_role(context, user_login)


# agendaitem

_agendaitem_create = _pi_create
_agendaitem_create_on_behalf_of = _pi_create

_agendaitem_submit = _pi_submit
_agendaitem_resubmit = _pi_submit


# bill

_bill_create = _pi_create

def _bill_submit(info, context):
    utils.setBillPublicationDate(info, context)
    utils.set_pi_registry_number(info, context)


# group

def _group_create(info, context):
    user_login = model_utils.get_principal_id()
    if user_login:
        utils.assign_owner_role(context, user_login)

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

_motion_create = _pi_create
_motion_create_on_behalf_of = _pi_create

_motion_submit = _pi_submit
_motion_resubmit = _pi_submit

def _motion_approve(info, context):
    dbutils.setMotionSerialNumber(context)


# question

_question_create = _pi_create
_question_create_on_behalf_of = _pi_create

_question_submit = _pi_submit
_question_resubmit = _pi_submit

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

_tableddocument_create = _pi_create
_tableddocument_create_on_behalf_of = _pi_create

_tableddocument_submit = _pi_submit
_tableddocument_resubmit = _pi_submit

def _tableddocument_approve(info, context):
    dbutils.setTabledDocumentSerialNumber(context)


# user

def _user_create(info, context):
    utils.assign_owner_role(context, context.login)

def _user_resurrect(info, context):
    context.date_of_death = None


#

