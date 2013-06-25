# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Signatories validation machinery for parliamentary documents

$Id$
"""
log = __import__("logging").getLogger("bungeni.feature.signatory")

import zope.component
import zope.interface
import zope.event
import zope.lifecycleevent
from zope.security.proxy import removeSecurityProxy

from bungeni.alchemist import Session
from bungeni.models import domain, interfaces as model_ifaces
from bungeni.models.utils import get_login_user
from bungeni.feature import feature
from bungeni.feature import interfaces
from bungeni.utils import register
from bungeni.core.workflow.interfaces import IWorkflowController, IWorkflowTransitionEvent
from bungeni.core.workflows import utils


# meta data on signatory workflow states
SIGNATORY_CONSENTED_STATES = ["consented"]
SIGNATORY_CONSENTED_STATE = SIGNATORY_CONSENTED_STATES[0]


@register.handler(adapts=(interfaces.IFeatureSignatory, IWorkflowTransitionEvent))
def on_signatory_doc_workflow_transition(ob, event):
    ob.signatory_feature.on_signatory_doc_workflow_transition(ob)


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


class Signatory(feature.Feature):
    """Support for the "signatory" feature. For Doc types.
    """
    feature_interface = interfaces.IFeatureSignatory
    feature_parameters = {    
        "min_signatories": dict(type="integer", default=0,
            doc="minimum consented signatories"),
        "max_signatories": dict(type="integer", default=0,
            doc="maximum consented signatories"),
        "submitted_states": dict(type="space_separated_state_ids", default="submitted_signatories"),
        "draft_states": dict(type="space_separated_state_ids", default="draft redraft"),
        "elapse_states": dict(type="space_separated_state_ids", default="submitted"),
        "open_states": dict(type="space_separated_state_ids", default=None),
    }
    subordinate_interface = model_ifaces.ISignatory
    
    def validate_parameters(self):
        assert not set.intersection(
                set(self.p.submitted_states), 
                set(self.p.draft_states), 
                set(self.p.elapse_states)), \
                    "draft, submitted and expired states must be distinct lists"
    
    def decorate_model(self, model):
        sf = self # signatory feature (this instance)
        def allow_sign_document(context):
            """Check if doc is open for signatures and current user is allowed to 
            sign. Used in bungeni/ui/menu.zcml to filter out "sign document action".
            """
            assert sf is context.signatory_feature, (sf.name, context, sf)
            return ((sf.can_sign(context) and sf.allow_signature(context)) or 
                (sf.is_signatory(context) and not sf.is_consented_signatory(context)))
        def allow_withdraw_signature(context):
            """Check if current user is a signatory and that the doc allows signature
            actions. Used in bungeni/ui/menu.zcml to filter out "review signature" action.
            """
            assert sf is context.signatory_feature, (sf.name, context, sf)
            return ((sf.document_submitted(context) or sf.auto_sign(context)) and
                sf.is_consented_signatory(context) and not sf.is_owner(context))
        model.allow_sign_document = property(allow_sign_document)
        model.allow_withdraw_signature = property(allow_withdraw_signature)
    
    def decorate_ui(self, model):
        feature.add_info_container_to_descriptor(model, "signatories", "signatory", "head_id")
    
    
    # feature class utilities
    
    def needs_signatures(self):
        """Does the document or object require signatures?
        """
        return self.p.min_signatories > 0
    
    
    # contextual
    
    def has_signatories(self, context):
        return bool(len(context.sa_signatories))
    
    def num_consented_signatories(self, context):
        return len([ 
                cs for cs in removeSecurityProxy(context).sa_signatories 
                if cs.status in SIGNATORY_CONSENTED_STATES ])
    
    def validate_consented_signatories(self, context):
        """Validate number of consented signatories against min and max.
        """
        return (
            (self.num_consented_signatories(context) >= self.p.min_signatories) and
            ((not self.p.max_signatories) or 
                (self.num_consented_signatories(context) <= self.p.max_signatories)
            )
        )
    
    def allow_signature(self, context):
        """Check that the current user has the right to consent on document.
        """
        return (not self.p.max_signatories or 
            (self.num_consented_signatories(context) < self.p.max_signatories)
        ) and (self.document_submitted(context) or self.auto_sign(context))
    
    def auto_sign(self, context):
        return context.status in self.p.open_states
    
    def elapse_signatures(self, context):
        """Should pending signatures be archived.
        """
        return context.status in self.p.elapse_states
    
    def document_submitted(self, context):
        """Check that the document has been submitted.
        """
        return context.status in self.p.submitted_states
    
    def document_is_draft(self, context):
        """Check that a document is being redrafted.
        """
        return context.status in self.p.draft_states
    
    def on_signatory_doc_workflow_transition(self, context):
        """Perform any workflow related actions on signatories and/or parent.
        """
        # make (head)context owner a default signatory when doc is submitted to 
        # signatories for consent
        if self.document_submitted(context):
            if not self.is_signatory(context, user=context.owner):
                new_signatory(context.owner_id, context.doc_id)
        # setup roles
        for signatory in context.sa_signatories:
            login = signatory.user.login
            if self.document_submitted(context):
                utils.set_role("bungeni.Signatory", login, context)
                utils.set_role("bungeni.Owner", login, signatory)
            elif self.document_is_draft(context):
                utils.unset_role("bungeni.Signatory", login, context)
            elif self.elapse_signatures(context):
                if signatory.status not in SIGNATORY_CONSENTED_STATES:
                    utils.unset_role("bungeni.Signatory", login, context)
        # update signatories
        for signatory in context.sa_signatories:
            wfc = IWorkflowController(signatory)
            wfc.fireAutomatic()
    
    
    # contextual and on current user 
    
    def is_owner(self, context):
        return get_login_user() == context.owner
    
    def is_signatory(self, context, user=None):
        user = user or get_login_user()
        for sgn in context.sa_signatories:
            if sgn.user_id == user.user_id:
                return True
        return False
    
    def is_consented_signatory(self, context, user=None):
        user = user or get_login_user()
        if user:
            for cs in context.sa_signatories:
                if cs.status in SIGNATORY_CONSENTED_STATES:
                    return True
        return False
    
    def can_sign(self, context):
        """Check if the current user can sign a document.
        """
        return (self.auto_sign(context) and 
            not self.is_owner(context) and 
            not self.is_signatory(context))
    
    def sign_document(self, context):
        """Sign context for current user if they have not already signed.
        Called from ui.forms.common.SignOpenDocumentForm.handle_sign_document().
        """
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


