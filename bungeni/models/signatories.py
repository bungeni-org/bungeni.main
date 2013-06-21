# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Signatories validation machinery for parliamentary documents

$Id$
"""
log = __import__("logging").getLogger("bungeni.models.signatories")

import zope.component
import zope.interface
import zope.event
import zope.lifecycleevent
from zope.security.proxy import removeSecurityProxy
from zope.component import getGlobalSiteManager

from bungeni.alchemist import Session
from bungeni.models import domain
from bungeni.models.utils import get_login_user
from bungeni.feature import interfaces
from bungeni.utils import register
from bungeni.capi import capi
# !+MODEL_DEPENDENCY_CORE
from bungeni.core.workflow.interfaces import IWorkflowController, IWorkflowTransitionEvent
from bungeni.core.workflows import utils


# meta data on signatory workflow states
SIGNATORY_CONSENTED_STATES = ["consented"]
SIGNATORY_CONSENTED_STATE = SIGNATORY_CONSENTED_STATES[0]


@register.handler(adapts=(interfaces.IFeatureSignatory, IWorkflowTransitionEvent))
def on_signatory_doc_workflow_transition(ob, event):
    ob.signatory_manager.on_signatory_doc_workflow_transition()


def new_signatory(user_id, head_id):
    """Create a new signatory instance for user on doc.
    """
    session = Session()
    sgn = domain.Signatory()
    sgn.user_id = user_id
    sgn.head_id = head_id
    session.add(sgn)
    session.flush()
    sgn.on_create()
    zope.event.notify(zope.lifecycleevent.ObjectCreatedEvent(sgn))
    return sgn


class SignatoryManager(object):
    zope.interface.implements(interfaces.ISignatoryManager)
    
    feature = None
    
    # !+ use feature.params[name] directly !
    max_signatories = 0
    min_signatories = 0
    submitted_states = ("submitted_signatories",)
    draft_states = ("draft", "redraft",)
    elapse_states = ("submitted",)
    open_states = ()
    
    def __init__(self, context):
        self.context = removeSecurityProxy(context)
    
    # feature methods
    
    def require_signatures(self):
        return self.min_signatories > 0
    
    
    # context-dependent methods (head doc)
    
    @property
    def signatories(self):
        return self.context.sa_signatories
    
    @property
    def signatories_count(self):
        return len(self.signatories)
    
    def validate_signatories(self):
        return self.signatories_count > 0
    
    @property
    def consented_signatories(self):
        return len(filter(
                lambda cs:cs.status in SIGNATORY_CONSENTED_STATES, 
                self.signatories))
    
    def validate_consented_signatories(self):
        return (
            (self.consented_signatories >= self.min_signatories) and
            ((not self.max_signatories) or 
                (self.consented_signatories <= self.max_signatories)
            )
        )
    
    def allow_signature(self):
        return (not self.max_signatories or 
            (self.consented_signatories < self.max_signatories)
        ) and (self.document_submitted() or self.auto_sign())
    
    def auto_sign(self):
        return self.context.status in self.open_states

    def elapse_signatures(self):
        return self.context.status in self.elapse_states

    def document_submitted(self):
        return self.context.status in self.submitted_states
    
    def document_is_draft(self):
        """Check that a document is being redrafted
        """
        return self.context.status in self.draft_states
    
    def allow_sign_document(self):
        """Check if doc is open for signatures and current user is allowed to 
        sign. Used in bungeni/ui/menu.zcml to filter out "sign document action".
        """
        return (
            (self.can_sign() and self.allow_signature()) or 
            (self.is_signatory() and not self.is_consented_signatory())
        )
    def allow_withdraw_signature(self):
        """Check if current user is a signatory and that the doc allows signature
        actions. Used in bungeni/ui/menu.zcml to filter out "review signature" action.
        """
        return ((self.document_submitted() or self.auto_sign()) and
            self.is_consented_signatory() and not self.is_owner())
    
    def on_signatory_doc_workflow_transition(self):
        """Perform any workflow related actions on signatories and/or parent
        """
        head = self.context
        # make head owner a default signatory when doc is submitted to 
        # signatories for consent
        if self.document_submitted():
            if not self.is_signatory(head.owner):
                new_signatory(head.owner_id, head.doc_id)
        # setup roles
        for signatory in self.signatories:
            login = signatory.user.login
            if self.document_submitted():
                utils.set_role("bungeni.Signatory", login, head)
                utils.set_role("bungeni.Owner", login, signatory)
            elif self.document_is_draft():
                utils.unset_role("bungeni.Signatory", login, head)
            elif self.elapse_signatures():
                if signatory.status not in SIGNATORY_CONSENTED_STATES:
                    utils.unset_role("bungeni.Signatory", login, head)
        # update signatories
        for signatory in self.signatories:
            wfc = IWorkflowController(signatory)
            wfc.fireAutomatic()
    
    
    # methods on current user 
    
    def is_owner(self):
        return get_login_user() == self.context.owner
    
    def is_signatory(self, user=None):
        user = user or get_login_user()
        for sgn in self.signatories:
            if sgn.user_id == user.user_id:
                return True
        return False
    
    def is_consented_signatory(self, user=None):
        user = user or get_login_user()
        if user:
            return user.user_id in [ 
                    sgn.user_id for sgn in filter(
                            lambda cs:cs.status in SIGNATORY_CONSENTED_STATES, 
                            self.signatories) ]
        return False
    
    def can_sign(self):
        """Check if the current user can sign a document.
        """
        return (self.auto_sign() and not self.is_owner() 
            and not self.is_signatory())
    
    def sign_document(self):
        """Sign context for current user if they have not already signed.
        Called from ui.forms.common.SignOpenDocumentForm.handle_sign_document().
        """
        context = self.context
        user = get_login_user()
        signatory = None
        for sgn in context.sa_signatories:
            if sgn.user_id == user.user_id:
                signatory = removeSecurityProxy(sgn)
                break
        if not signatory:
            signatory = new_signatory(user.user_id, context.doc_id)
        else:
            if not signatory.status == SIGNATORY_CONSENTED_STATE:
                wfc = IWorkflowController(signatory)
                wfc.state_controller.set_status(SIGNATORY_CONSENTED_STATE)
        return signatory


