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
from bungeni.core.workflow.states import get_object_state
from bungeni.core.workflows import utils
from bungeni.ui.interfaces import IFormEditLayer
from bungeni.ui.i18n import _
from bungeni.ui.utils import common
from bungeni.utils import naming
from bungeni.utils.misc import describe


# common


def context_is_public(context):
    """Is the context public i.e. can Anonymous see it?
    !+ logic here is now incorrect !!!
    """
    state = get_object_state(context)
    # also return False for None (Unset)
    return bool(state.getSetting("zope.View", "bungeni.Anonymous"))


# doc

@describe(_(u"Require document to be scheduled"))
def is_scheduled(doc):
    """Is doc scheduled?
    """
    return utils.is_pi_scheduled(doc)


# group
@describe(_(u"group: Require end date to be set for the group"))
def has_end_date(context):
    """A group can only be dissolved if an end date is set.
    """
    return context.end_date != None


# sitting

@describe(_(u"sitting: Require a venue set in the current context"))
def has_venue(context):
    return context.venue is not None

@describe(_(u"sitting: Require agenda in the current context"))
def has_agenda(context):
    return len(context.items)>0

@describe(_(u"sitting: Require agenda to be finalized"))
def agenda_finalized(context):
    return utils.check_agenda_finalized(context)

@describe(_(u"sitting: dummy ?"))
def sitting_dummy(context):
    return context.recurring_type == 'none'


# question

#!+NECESSARY?
@describe(_(u"question: Require a written response"))
def is_written_response(question):
    return question.group_id is not None and question.response_type == "written"

@describe(_(u"question: Require an oral response"))
def is_oral_response(question):
    return question.response_type == "oral"

@describe(_(u"question: Require the response to be submitted in the current context"))
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

@describe(_(u"user: Require date of death to be set"))
def has_date_of_death(context):
    return context.date_of_death is not None

@describe(_(u"user: Require date of death to be not set"))
def not_has_date_of_death(context):
    return context.date_of_death is None


# child items

@describe(_(u"attachments, events etc: Require parent document to be in draft state"))
def context_parent_is_draft(context):
    """Is parent context in a draft state?
    A doc is a draft iff its current current state is tagged with "draft".
    """
    parent_state = get_object_state(context.head)
    return "draft" in parent_state.tags

@describe(_(u"attachments, events etc: Require parent document not to be in draft state"))
def context_parent_is_not_draft(context):
    return not context_parent_is_draft(context)

@describe(_(u"attachments, events etc: Require parent document to be visible to the public"))
def context_parent_is_public(context):
    """Is the parent context public i.e. can Anonymous see it?
    """
    return context_is_public(context.head)
    
@describe(_(u"attachments, events etc: Require parent document not to be visible to the public"))
def context_parent_is_not_public(context):
    return not context_is_public(context.head)

@describe(_(u"attachments, events etc: Require parent document to be editable by the user"))
def user_may_edit_context_parent(context):
    """Does user have edit permission on the context's parent?
    For a context that is a workflowed sub-object, such as an Attachment or 
    an Event.
    """
    parent = context.head
    permission = "bungeni.%s.Edit" % (naming.polymorphic_identity(type(parent)))
    return checkPermission(permission, parent)


# signatory

#!+INCORRENTLY named... only checks that owner of child is same as of parent!
@describe(_(u"signatory: Require the user to be the owner of the parent document"))
def user_is_parent_document_owner(context):
    return context.owner.login == context.head.owner.login

@describe(_(u"signatory: Require the user not to be the owner of the parent document"))
def user_is_not_parent_document_owner(context):
    return not user_is_parent_document_owner(context)



@describe(_(u"signatory: Require the owner to be the signatory. Auto-signs the document"))
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
    if not utils.user_is_context_owner(context.head):
        return True
    #!+(mb, Jul-2012) move all signatory logic to signatory manager
    if ISignatoryManager(context.head).auto_sign():
        return True
    return False

@describe(_(u"signatory: Require the signatory to manually sign the document"))
def signatory_manual_sign(context):
    return not signatory_auto_sign(context)

@describe(_(u"signatory: Require signatories"))
def pi_has_signatories(context):
    manager = ISignatoryManager(context, None)
    if manager is not None:
        return manager.validate_signatories()
    return True

@describe(_(u"signatory: Require consented signatories"))
def pi_signatories_check(context):
    manager = ISignatoryManager(context, None)
    if manager is not None:
        return manager.validate_consented_signatories()
    return True

@describe(_(u"signatory: Require signature period to have expired"))
def pi_signature_period_expired(context):
    """The document has been submitted"""
    manager = ISignatoryManager(context.head, None)
    if manager is not None:
        return manager.expire_signatures()
    return False

@describe(_(u"signatory: Require parent document to have been redrafted"))
def pi_document_redrafted(context):
    """Parent document has been redrafted"""
    manager = ISignatoryManager(context.head, None)
    return manager and manager.document_is_draft()

@describe(_(u"signatory: Require the signature to have been withdrawn"))
def pi_unsign_signature(context):
    manager = ISignatoryManager(context.head, None)
    if manager:
        return ((pi_document_redrafted(context) and 
            user_is_not_parent_document_owner(context))
        )
    return False

@describe(_(u"signatory: Require the signatory be allowed to sign"))
def pi_allow_signature(context):
    manager = ISignatoryManager(context.head, None)
    if manager is not None:
        return utils.user_is_context_owner(context) and manager.allow_signature()
    return False

@describe(_(u"signatory: Require the signatory to be allowed to withdraw or reject"))
def pi_allow_signature_actions(context):
    """allow/disallow other signature actions => such as withdraw and reject
    """
    manager = ISignatoryManager(context.head, None)
    if manager is not None:
        return (utils.user_is_context_owner(context) and 
            (manager.document_submitted() or manager.auto_sign()) and
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
        current_user = model_utils.get_login_user()
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
    return user_is_state_creator(context) and utils.user_is_context_owner(context)

def user_is_state_creator_not_owner(context):
    return user_is_state_creator(context) and not utils.user_is_context_owner(context)
'''
