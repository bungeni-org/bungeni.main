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

# /specially handled actions


# !+NUMBER_GENERATION(ah, nov-2011) - used for parliamentary item transitions
# to recieved state
def __pi_received(context):
    utils.set_doc_registry_number(context)


# !+NUMBER_GENERATION (ah,nov-2011) - generate the number on receiving an item
_question_received = __pi_received
_bill_received = __pi_received
_motion_received = __pi_received
_agenda_item_received = __pi_received
_tabled_document_received = __pi_received


# group

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

# office
_office_active = _group_active


# committee

_committee_active = _group_active
_committee_dissolved = _group_dissolved


# parliament

_parliament_active = _group_active
_parliament_dissolved = _group_dissolved


# sitting

def _sitting_draft_agenda(context):
    dbutils.set_real_order(context)
        
def _sitting_published_agenda(context):
    utils.schedule_sitting_items(context)


# motion

def _motion_admissible(motion):
    dbutils.set_doc_type_number(motion)


# question

def __question_create(context):
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


# tabled_document

def _tabled_document_adjourned(context):
    utils.setTabledDocumentHistory(context)

def _tabled_document_admissible(tabled_document):
    dbutils.set_doc_type_number(tabled_document)

# user

def _user_A(context):
    utils.assign_role("bungeni.Owner", context.login, context)
    context.date_of_death = None


