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

def __create(context):
    # !+utils.setParliamentId(context)
    # !+OWNERSHIP(mr, may-2012) should not this be part of the actual 
    # *creation* logic of the item?
    utils.assign_role_owner_to_login(context)


# !+NUMBER_GENERATION(ah, nov-2011) - used for parliamentary item transitions
# to recieved state
def __pi_received(context):
    utils.set_doc_registry_number(context)

# sub-item types

_event_draft = __create
_attachment_draft = __create
_address_private = __create


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

_agendaitem_draft = _agendaitem_working_draft = __create


# bill

_bill_draft = _bill_working_draft = __create


# group

def _group_draft(context):
    utils.assign_role_owner_to_login(context)
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

_motion_draft = _motion_working_draft = __create

def _motion_admissible(motion):
    dbutils.set_doc_type_number(motion)


# question

def __question_create(context):
    __create(context)
    utils.assign_role_minister_question(context)
    
_question_draft = _question_working_draft = __question_create


# !+unschedule(mr, may-2012) why does unscheduling only apply to:
# a) only transitions to withdrawn?
# b) only to questions?
def _question_withdrawn(context):
    """A question can be withdrawn by the owner, it is visible to ...
    and cannot be edited by anyone.
    """
    utils.unschedule_doc(context)
_question_withdrawn_public = _question_withdrawn

def _question_admissible(question):
    """The question is admissible and can be send to ministry,
    or is available for scheduling in a sitting.
    """
    dbutils.set_doc_type_number(question)


# tableddocument

_tableddocument_draft = _tableddocument_working_draft = __create

def _tableddocument_adjourned(context):
    utils.setTabledDocumentHistory(context)

def _tableddocument_admissible(tabled_document):
    dbutils.set_doc_type_number(tabled_document)

# user

def _user_A(context):
    utils.assign_role("bungeni.Owner", context.login, context)
    context.date_of_death = None


