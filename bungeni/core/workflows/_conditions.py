# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Workflow transition (bungeni) conditions.

Signature of all utilities here: 

    (context:Object) -> bool

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflows._conditions")

from zope.security import checkPermission
from bungeni.ui.interfaces import IFormEditLayer
from bungeni.ui.utils import common
from bungeni.core import globalsettings as prefs
from bungeni.core.workflows import utils
from bungeni.models.interfaces import IAuditable, ISignatoriesValidator
from bungeni.models import domain
from bungeni.alchemist import Session
from bungeni.models import utils as model_utils

# common

# the condition for the transition from "" (None) to either "draft" or to 
# "working_draft" seems to need the explicit condition (and negation of 
# condition) on each of the two transition options 
def user_is_not_context_owner(context):
    return not user_is_context_owner(context)

def user_is_context_owner(context):
    """Test if current user is the context owner e.g. to check if someone 
        manipulating the context object is other than the owner of the object.
        
        A delegate is considered to be an owner of the object
    """
    user = model_utils.get_db_user()
    owner_login = utils.get_owner_login_pi(context)
    session = Session()
    delegations = session.query(domain.User) \
                    .join((domain.UserDelegation, domain.User.user_id
                                        ==domain.UserDelegation.user_id)) \
                    .filter(domain.UserDelegation.delegation_id == user.user_id) \
                    .all()
    users = [delegate.login for delegate in delegations]
    users.append(owner_login) 
    return user.login in users

def user_may_edit_context_parent(context):
    """Does user have edit permission on the context's parent?
    For a context that is a workflowed sub-object, such as an Attachment or 
    an Event; context must define an "item" proeprty that returns the parent.
    """
    parent = context.item
    permission = "bungeni.%s.Edit" % (parent.__class__.__name__.lower())
    return checkPermission(permission, parent)


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

def signatory_auto_sign(context):
    """ Determines whether signature is automatically signed when a signatory
        is added.
    
    Whenever the signature is that of the document owner, we auto sign.
    Also, signature is signed if parent document is created on behalf of a 
    member. The assumption is that the user has provided a list of consented
    signatories to the document.
    """
    if user_is_parent_document_owner(context):
        return True
    # if user adding signatory is not parent document owner, then auto sign
    #!+SIGNATORIES(mb, aug-2011) this could be tricky versus checking if parent
    # document is in a 'working_draft' state
    if user_is_not_context_owner(context.item):
        return True
    return False

def user_is_not_parent_document_owner(context):
    return not user_is_parent_document_owner(context)

def pi_has_signatories(context):
    validator = ISignatoriesValidator(context, None)
    if validator is not None:
        return validator.validateSignatories()
    return False

def pi_signatories_check(context):
    validator = ISignatoriesValidator(context, None)
    if validator is not None:
        return validator.validateConsentedSignatories()
    return False

def pi_signature_period_expired(context):
    """The document has been submitted"""
    validator = ISignatoriesValidator(context.item, None)
    if validator is not None:
        return validator.expireSignatures()
    return False

def pi_document_redrafted(context):
    """Parent document has been redrafted"""
    validator = ISignatoriesValidator(context.item, None)
    return validator and validator.documentInDraft()

def pi_unsign_signature(context):
    return (pi_document_redrafted(context) and 
        user_is_not_parent_document_owner(context)
    )

def pi_allow_signature(context):
    validator = ISignatoriesValidator(context.item, None)
    if validator is not None:
        return user_is_context_owner(context) and validator.allowSignature()
    return False

def pi_allow_signature_actions(context):
    """allow/disallow other signature actions => such as withdraw and reject
    """
    validator = ISignatoriesValidator(context.item, None)
    if validator is not None:
        return (user_is_context_owner(context) and
            validator.documentSubmitted() and
            user_is_not_parent_document_owner(context))
    return False

# auditables

def user_is_state_creator(context):
    """Did the current user create current state - based on workflow log?
    """
    is_state_creator = False
    if IAuditable.providedBy(context):
        current_user = model_utils.get_db_user()
        if current_user:
            for _object_change in reversed(context.changes):
                if _object_change.action == "workflow":
                    extras = _object_change.extras
                    if extras and (extras.get("destination") == context.status):
                        if _object_change.user.login == current_user.login:
                            is_state_creator = True
                    break
    return is_state_creator

def user_is_state_creator_and_owner(context):
    return user_is_state_creator(context) and user_is_context_owner(context)

def user_is_state_creator_not_owner(context):
    return user_is_state_creator(context) and user_is_not_context_owner(context)

