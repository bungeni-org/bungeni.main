# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Workflow transition actions.

All actions with names starting with a "_" may NOT be referenced from the 
workflow XML definitions i.e. they are internal actions, private to bungeni.
They are AUTOMATICALLY associated with the name of a workflow state, via the
following simple naming convention:

    _{workflow_name}_{state_name}

Signature of all (both private and public) action callables:

    (context:Object) -> None

!+ All actions with names that start with a letter are actions that may be 
liberally used from within workflow XML definitions.


$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflows._actions")


import zope.event
import zope.lifecycleevent

from bungeni.alchemist import Session
from bungeni.core.workflows import utils
from bungeni.core.workflows import dbutils


# specially handled actions - executed on transition to a given state (set 
# when workflow is loaded) 

# make a new version of a document
# not tied to a state name, but to <state> @version bool attribute
create_version = utils.create_version

# publish document to xml
# not tied to a state name, but to <state> @publish bool attribute
from bungeni.core.serialize import publish_to_xml

# /specially handled actions


# parliamentary item, utils

def __pi_create(context):
    #!+utils.setParliamentId(context)
    utils.assign_owner_role_pi(context)

def __pi_submit(context):
    if len(context.signatories) > 0:
        __make_owner_signatory(context)
    utils.pi_update_signatories(context)
    utils.pi_unset_signatory_roles(context)

# !+NUMBER_GENERATION(ah, nov-2011) - used for parliamentary item transitions
# to recieved state
def __pi_received(context):
    utils.set_doc_registry_number(context)

def __pi_redraft(context):
    """Signatory operations on redraft - Unsetting signatures e.t.c
    """
    utils.pi_update_signatories(context)
    utils.pi_unset_signatory_roles(context, all=True)

# address

def _address_private(context):
    # !+OWNER_ADDRESS(mr, mov-2010) is this logic correct, also for admin?
    try:
        user_login = dbutils.get_user(context.user_id).login
    except AttributeError:
        # 'GroupAddress' object has no attribute 'user_id'
        user_login = utils.get_principal_id()
    if user_login:
        utils.assign_owner_role(context, user_login)

''' !+XML 
def _address_attached(context):
    # !+XML this is anyway incorrect, what about useraddress (uses same workflow)
    publish_to_xml(context, type="groupaddress", include=[])
'''

# !+NUMBER_GENERATION (ah,nov-2011) - generate the number on receiving an item
_question_received = __pi_received
_bill_received = __pi_received
_motion_received = __pi_received
_agendaitem_received = __pi_received
_tableddocument_received = __pi_received


# agendaitem

_agendaitem_draft = _agendaitem_working_draft = __pi_create
_agendaitem_submitted = __pi_submit
_agendaitem_redraft = __pi_redraft


# bill

_bill_draft = _bill_working_draft = __pi_create
_bill_redraft = __pi_redraft
_bill_submitted = __pi_submit


# group

def _group_draft(context):
    user_login = utils.get_principal_id()
    if user_login:
        utils.assign_owner_role(context, user_login)
    def _deactivate(context):
        utils.unset_group_local_role(context)
    _deactivate(context)

def _group_active(context):
    utils.set_group_local_role(context)

def _group_dissolved(context):
    """ when a group is dissolved all members of this 
    group get the end date of the group (if they do not
    have one yet) and there active_p status gets set to
    False"""
    dbutils.deactivateGroupMembers(context)
    groups = dbutils.endChildGroups(context)
    utils.dissolveChildGroups(groups, context)
    utils.unset_group_local_role(context)



# committee

_committee_draft = _group_draft
_committee_active = _group_active
_committee_dissolved = _group_dissolved


# parliament

_parliament_draft = _group_draft
_parliament_active = _group_active
_parliament_dissolved = _group_dissolved


# sitting

def _sitting_draft_agenda(context):
    dbutils.set_real_order(context)
        
def _sitting_published_agenda(context):
    utils.schedule_sitting_items(context)


# motion

_motion_draft = _motion_working_draft = __pi_create
_motion_submitted = __pi_submit
_motion_redraft = __pi_redraft

def _motion_admissible(motion):
    dbutils.set_doc_type_number(motion)


# question

def __question_create(context):
    __pi_create(context)
    utils.assign_question_minister_role(context)
    
_question_draft = _question_working_draft = __question_create
_question_submitted = __pi_submit
_question_redraft = __pi_redraft

def _question_withdrawn(context):
    """A question can be withdrawn by the owner, it is visible to ...
    and cannot be edited by anyone.
    """
    utils.setQuestionScheduleHistory(context)
_question_withdrawn_public = _question_withdrawn

def _question_response_pending(context):
    """A question sent to a ministry for a written answer, 
    it cannot be edited, the ministry can add a written response.
    """
    utils.setMinistrySubmissionDate(context)

def _question_admissible(question):
    """The question is admissible and can be send to ministry,
    or is available for scheduling in a sitting.
    """
    dbutils.set_doc_type_number(question)


# tableddocument

_tableddocument_draft = _tableddocument_working_draft = __pi_create
_tableddocument_submitted = __pi_submit
_tableddocument_redraft = __pi_redraft

def _tableddocument_adjourned(context):
    utils.setTabledDocumentHistory(context)

def _tableddocument_admissible(tabled_document):
    dbutils.set_doc_type_number(tabled_document)

# user

def _user_A(context):
    utils.assign_owner_role(context, context.login)
    context.date_of_death = None

#


# signatories

def __make_owner_signatory(context):
    """Make document owner a default signatory when document is submited to
    signatories for consent.
    """
    signatories = context.signatories
    if context.owner_id not in [sgn.user_id for sgn in signatories._query]:
        session = Session()
        signatory = signatories._class()
        signatory.user_id = context.owner_id
        signatory.head_id = context.doc_id
        session.add(signatory)
        session.flush()
        zope.event.notify(zope.lifecycleevent.ObjectCreatedEvent(signatory))

def __pi_submitted_signatories(context):
    __make_owner_signatory(context)
    for signatory in context.signatories.values():
        owner_login = utils.get_owner_login_pi(signatory)
        utils.assign_owner_role(signatory, owner_login)
        utils.assign_signatory_role(context, owner_login)
    utils.pi_update_signatories(context)


_question_submitted_signatories = __pi_submitted_signatories
_motion_submitted_signatories = __pi_submitted_signatories
_bill_submitted_signatories = __pi_submitted_signatories
_agendaitem_submitted_signatories = __pi_submitted_signatories
_tableddocument_submitted_signatories = __pi_submitted_signatories

def _signatory_awaiting_consent(context):
    """Done when parent object is already in submitted_signatories stage.
    Otherwise roles assignment is handled by `__pi_assign_signatory_roles`
    """
    if context.head.status == u"submitted_signatories":
        owner_login = utils.get_owner_login_pi(context)
        utils.assign_owner_role(context, owner_login)
        utils.assign_signatory_role(context.head, owner_login)

def _signatory_rejected(context):
    #!+SIGNATORIES(mb, aug-2011) Unsetting of roles now handled when
    # document is submitted or redrafted. Deprecate this action if not needed.
    #owner_login = utils.get_owner_login_pi(context)
    #utils.assign_signatory_role(context.head, owner_login, unset=True)
    return

_signatory_withdrawn = _signatory_rejected

# events
def _event_private(context):
    """
    Assigns owner role to event creator - Limit viewing to owner
    """
    login = utils.get_principal_id()
    if login is not None:
        utils.assign_owner_role(context, login)


