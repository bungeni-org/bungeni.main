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
#from bungeni.models import domain
from bungeni.core.workflow.states import get_object_state
from bungeni.core.workflows import utils
from bungeni import _
from bungeni.utils import naming
from bungeni.utils.misc import describe


# utils

def child(context, type_key):
    """Get the child document of the specified type. 
    
    !+ assumes only one; if more than one, glazes over the issue and just takes 
    the "latest", approximately; if None returns None.
    """
    container_property_name = naming.plural(type_key)
    container = getattr(context, container_property_name)
    try:
        return sorted(container.values())[-1]
    except IndexError:
        return None

def in_state(context, *state_ids):
    """Is context status one of the ones in state_ids?
    """
    return bool(context) and context.status in state_ids

def child_in_state(context, type_key, *state_ids):
    """Is the context child document, identified by type_key, in one of the 
    specified state_ids?
    """
    return in_state(child(context, type_key), *state_ids)


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
    return utils.is_doc_scheduled(doc)


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
    return len(context.items) > 0

@describe(_(u"sitting: Require agenda to be finalized"))
def agenda_finalized(context):
    return utils.check_agenda_finalized(context)

@describe(_(u"sitting: dummy ?"))
def sitting_dummy(context):
    return context.recurring_type == "none"


# user

@describe(_(u"user: Require date of death to be set"))
def has_date_of_death(context):
    return context.date_of_death is not None

@describe(_(u"user: Require date of death to be not set"))
def not_has_date_of_death(context):
    return context.date_of_death is None


# child items

@describe(_(u"subtype: Require parent document to be in draft state"))
def context_parent_is_draft(context):
    """Is parent context in a draft state?
    A doc is a draft iff its current current state is tagged with "draft".
    """
    parent_state = get_object_state(context.head)
    return "draft" in parent_state.tags

@describe(_(u"subtype: Require parent document not to be in draft state"))
def context_parent_is_not_draft(context):
    return not context_parent_is_draft(context)

@describe(_(u"subtype: Require parent document to be visible to the public"))
def context_parent_is_public(context):
    """Is the parent context public i.e. can Anonymous see it?
    """
    return context_is_public(context.head)
    
@describe(_(u"subtype: Require parent document not to be visible to the public"))
def context_parent_is_not_public(context):
    return not context_is_public(context.head)

@describe(_(u"subtype: Require parent document to be editable by the user"))
def user_may_edit_context_parent(context):
    """Does user have edit permission on the context's parent?
    For a context that is a workflowed sub-object, such as an Attachment or 
    an Event.
    """
    parent = context.head
    permission = "bungeni.%s.Edit" % (naming.polymorphic_identity(type(parent)))
    return checkPermission(permission, parent)

@describe(_(u"subtype: Require the signatory to be the owner of the parent document"))
def signatory_is_parent_document_owner(context):
    return context.user.login == context.head.owner.login

@describe(_(u"subtype: Require the signatory not to be the owner of the parent document"))
def signatory_is_not_parent_document_owner(context):
    return not signatory_is_parent_document_owner(context)


# signatory

@describe(_(u"signatory: Require the owner to be the signatory. Auto-signs the document"))
def signatory_auto_sign(signatory):
    """Determines whether signature is automatically signed when a signatory
    is added.
    
    Whenever the signature is that of the document owner, we auto sign.
    Also, signature is signed if parent document is created on behalf of a 
    member. The assumption is that the user has provided a list of consented
    signatories to the document.
    """
    #if user_is_parent_document_owner(signatory):
    # !+ called before signatory is created! Owner role not yet set...
    if signatory.user_id == signatory.head.owner_id:
        return True
    # if user adding signatory is not parent document owner, then auto sign
    #!+SIGNATORIES(mb, aug-2011) this could be tricky versus checking if parent
    # document is in a 'working_draft' state
    head = signatory.head
    if not utils.user_is_context_owner(head):
        return True
    return head.signatory_feature.auto_sign(head)

@describe(_(u"signatory: Require the signatory to manually sign the document"))
def signatory_manual_sign(signatory):
    return not signatory_auto_sign(signatory)

@describe(_(u"signatory: Require signature period to have expired"))
def signatory_period_elapsed(signatory):
    """The document has been submitted"""
    head = signatory.head
    signatory_feature = head.signatory_feature
    return signatory_feature and signatory_feature.elapse_signatures(head)

@describe(_(u"signatory: Require the signature to have been withdrawn"))
def signatory_allows_unsign(signatory):
    return (doc_is_draft(signatory.head) and 
        signatory_is_not_parent_document_owner(signatory))

@describe(_(u"signatory: Require the signatory be allowed to sign"))
def signatory_allowed_sign(signatory):
    signatory_feature = signatory.head.signatory_feature
    return (signatory_feature and 
            utils.user_is_context_owner(signatory) and 
            signatory_feature.allow_signature(signatory.head))

@describe(_(u"signatory: Require the signatory to be allowed to withdraw or reject"))
def signatory_allowed_actions(signatory):
    """allow/disallow other signature actions => such as withdraw and reject
    """
    signatory_feature = signatory.head.signatory_feature
    return (signatory_feature and 
            utils.user_is_context_owner(signatory) and 
            (signatory_feature.document_submitted(signatory.head) or 
                signatory_feature.auto_sign(signatory.head)) and
            signatory_is_not_parent_document_owner(signatory))


@describe(_(u"doc: Require signatories"))
def doc_has_signatories(doc):
    signatory_feature = doc.signatory_feature
    if signatory_feature:
        return signatory_feature.has_signatories(doc)
    return True

@describe(_(u"doc: Check consented signatories"))
def doc_valid_num_consented_signatories(doc):
    signatory_feature = doc.signatory_feature
    if signatory_feature:
        return signatory_feature.valid_num_consented_signatories(doc)
    return True

def doc_is_draft(doc):
    """Parent document has been redrafted"""
    signatory_feature = doc.signatory_feature
    return signatory_feature and signatory_feature.document_is_draft(doc)



