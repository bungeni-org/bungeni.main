# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Workflow transition (bungeni) conditions.

Signature of all utilities here: 

    (context:Object) -> bool

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflows._conditions")

from bungeni.ui.interfaces import IFormEditLayer
from bungeni.ui.utils import common
from bungeni.core import globalsettings as prefs
from bungeni.core.workflows import utils
from bungeni.models.interfaces import ISignatoriesValidator


# common

# the condition for the transition from "" (None) to either "draft" or to 
# "working_draft" seems to need the explicit condition (and negation of 
# condition) on each of the two transition options 
def user_is_not_context_owner(context):
    return not user_is_context_owner(context)

def user_is_context_owner(context):
    def user_is_context_owner(context):
        """Test if current user is the context owner e.g. to check if someone 
        manipulating the context object is other than the owner of the object.
        """
        user_login = utils.get_principal_id()
        owner_login = utils.get_owner_login_pi(context)
        return user_login == owner_login
    return user_is_context_owner(context)

def clerk_receive_notification(context):
    return prefs.getClerksOfficeReceiveNotification()

def owner_receive_notification(context):
    return context.receive_notification

def ministry_receive_notification(context):
    return prefs.getMinistriesReceiveNotification() and context.ministry_id


# parliamentary items

def is_scheduled(context):
    """Is Parliamentary Item scheduled.
    """
    return utils.is_pi_scheduled(context.parliamentary_item_id)


# group

def has_end_date(context):
    """A group can only be dissolved if an end date is set.
    """
    return context.end_date != None


# groupsitting

def has_venue(context):
    return context.venue is not None


# question

def is_written_response(context):
    return (context.ministry_id is not None and 
        context.response_type.response_type_name == u"Written"
    )

def is_oral_response(context):
    return context.response_type.response_type_name == u"Oral"

def response_allow_submit(context):
    # The "submit_response" workflow transition should NOT be displayed when 
    # the UI is displaying the question in "edit" mode (as this transition
    # will cause deny of bungeni.Question.Edit to the Minister).
    request = common.get_request()
    if IFormEditLayer.providedBy(request):
        return False
    if context.response_text is None:
        return False
    else:
        return True

# user

def has_date_of_death(context):
    return context.date_of_death is not None

def not_has_date_of_death(context):
    return context.date_of_death is None


# signatory conditions
def user_is_parent_document_owner(context):
    return (
        utils.get_owner_login_pi(context) ==
        utils.get_owner_login_pi(context.item)
    )
def pi_has_signatories(context):
    validator = ISignatoriesValidator(context)
    return validator.validateSignatories()

def pi_signatories_check(context):
    validator = ISignatoriesValidator(context)
    return validator.validateConsentedSignatories()

def pi_allow_signature(context):
    validator = ISignatoriesValidator(context.item)
    return user_is_context_owner(context) and validator.allowSignature()
