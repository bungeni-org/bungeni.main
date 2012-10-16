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
from bungeni.models.interfaces import ISignatoryManager
#from bungeni.models import domain
from bungeni.models import utils as model_utils
from bungeni.core.workflow.states import get_object_state
from bungeni.core.workflows import utils
from bungeni.ui.interfaces import IFormEditLayer
from bungeni.ui.utils import common
from bungeni.utils import naming

# common

# the condition for the transition from "" (None) to either "draft" or to 
# "working_draft" seems to need the explicit condition (and negation of 
# condition) on each of the two transition options 
def user_is_not_context_owner(context):
    return not user_is_context_owner(context)

def user_is_context_owner(context):
    """Test if current user is the context owner e.g. to check if someone 
    manipulating the context object is other than the owner of the object.
    
    Assimption: context is IOwned.
    
    A delegate is considered to be an owner of the object.
    """
    return model_utils.is_current_or_delegated_user(context.owner)

def context_is_public(context):
    """Is the context public i.e. can Anonymous see it?
    """
    state = get_object_state(context)
    # also return False for None (Unset)
    return bool(state.getSetting("zope.View", "bungeni.Anonymous"))


# parliamentary items

def is_scheduled(doc):
    """Is doc scheduled?
    """
    return utils.is_pi_scheduled(doc.doc_id)


# group

def has_end_date(context):
    """A group can only be dissolved if an end date is set.
    """
    return context.end_date != None


# sitting

def has_venue(context):
    return context.venue is not None

def has_agenda(context):
    return len(context.items)>0

def agenda_finalized(context):
    return utils.check_agenda_finalized(context)

def sitting_dummy(context):
    return context.recurring_type == 'none'

# question

def is_written_response(context):
    return (context.ministry_id is not None and 
        context.response_type == "written"
    )

def is_oral_response(context):
    return context.response_type == "oral"

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


# child items

def context_parent_is_draft(context):
    """Is parent context in a draft state?
    A doc is a draft iff its current current state is tagged with "draft".
    """
    parent_state = get_object_state(context.head)
    return "draft" in parent_state.tags
def context_parent_is_not_draft(context):
    return not context_parent_is_draft(context)

def context_parent_is_public(context):
    """Is the parent context public i.e. can Anonymous see it?
    """
    return context_is_public(context.head)
def context_parent_is_not_public(context):
    return not context_is_public(context.head)

def user_may_edit_context_parent(context):
    """Does user have edit permission on the context's parent?
    For a context that is a workflowed sub-object, such as an Attachment or 
    an Event.
    """
    parent = context.head
    permission = "bungeni.%s.Edit" % (naming.polymorphic_identity(type(parent)))
    return checkPermission(permission, parent)


# signatory

def user_is_parent_document_owner(context):
    return context.owner.login == context.head.owner.login

def signatory_auto_sign(context):
    """Determines whether signature is automatically signed when a signatory
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
    if user_is_not_context_owner(context.head):
        return True
    #!+(mb, Jul-2012) move all signatory logic to signatory manager
    if ISignatoryManager(context.head).autoSign():
        return True
    return False

def signatory_manual_sign(context):
    return not signatory_auto_sign(context)

def user_is_not_parent_document_owner(context):
    return not user_is_parent_document_owner(context)

def pi_has_signatories(context):
    manager = ISignatoryManager(context, None)
    if manager is not None:
        return manager.validateSignatories()
    return True

def pi_signatories_check(context):
    manager = ISignatoryManager(context, None)
    if manager is not None:
        return manager.validateConsentedSignatories()
    return True

def pi_signature_period_expired(context):
    """The document has been submitted"""
    manager = ISignatoryManager(context.head, None)
    if manager is not None:
        return manager.expireSignatures()
    return False

def pi_document_redrafted(context):
    """Parent document has been redrafted"""
    manager = ISignatoryManager(context.head, None)
    return manager and manager.documentInDraft()

def pi_unsign_signature(context):
    manager = ISignatoryManager(context.head, None)
    if manager:
        return ((pi_document_redrafted(context) and 
            user_is_not_parent_document_owner(context))
        )
    return False

def pi_allow_signature(context):
    manager = ISignatoryManager(context.head, None)
    if manager is not None:
        return user_is_context_owner(context) and manager.allowSignature()
    return False

def pi_allow_signature_actions(context):
    """allow/disallow other signature actions => such as withdraw and reject
    """
    manager = ISignatoryManager(context.head, None)
    if manager is not None:
        return (user_is_context_owner(context) and
            (manager.documentSubmitted() or manager.autoSign()) and
            user_is_not_parent_document_owner(context)) 
    return False


# auditables

''' !+AUDITABLES_UNUSED(mr, apr-2012)
from bungeni.models.interfaces import IFeatureAudit
def user_is_state_creator(context):
    """Did the current user create current state - based on workflow log?
    """
    is_state_creator = False
    if IFeatureAudit.providedBy(context):
        current_user = model_utils.get_db_user()
        if current_user:
            for _object_change in reversed(
                    domain.get_changes(context.changes, "workflow")
                ):
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
'''
