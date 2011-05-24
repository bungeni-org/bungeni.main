"""
Signatories validation machinery

$Id:$
"""

import zope.component
import zope.interface

from bungeni.models.interfaces import (IBill, IMotion, IQuestion,
    IAgendaItem, ITabledDocument, ISignatoriesValidator
)
from bungeni.models.settings import BungeniSettings
from bungeni.core.app import BungeniApp
from bungeni.core.workflow.interfaces import IWorkflow

app = BungeniApp()

class SignatoryValidator(object):
    zope.interface.implements(ISignatoriesValidator)
    
    def __init__(self, pi_instance):
        self.pi_instance = pi_instance
        self.object_type = pi_instance.type
    
    @property
    def settings(self):
        return BungeniSettings(app)

    @property
    def signatories(self):
        return self.pi_instance.signatories.values()

    @property
    def signatories_count(self):
        return len(list(self.signatories))

    @property
    def min_signatories(self):
        setting_id = "%s_signatories_min" %(self.object_type)
        return getattr(self.settings, setting_id, 0)

    @property
    def max_signatories(self):
        setting_id = "%s_signatories_max" %(self.object_type)
        return getattr(self.settings, setting_id, 0)

    @property
    def consented_signatories(self):
        return self.consentedSignatories()

    def consentedSignatories(self, status=u"consented"):
        return len(filter(
                    lambda cs:cs.status==u"consented", self.signatories
        ))
    
    def validateSignatories(self):
        return self.signatories_count > 0

    def validateConsentedSignatories(self):
        return ( (self.consented_signatories >= self.min_signatories) and
            ((not self.max_signatories) or 
                (self.consented_signatories <= self.max_signatories)
            )
        )

    def allowSignature(self):
        return (not self.max_signatories or 
            (self.consented_signatories < self.max_signatories)
        ) and self.documentSubmitted()

    def expireSignatures(self):
        return unicode(self.pi_instance.status) == u"submitted"

    def documentSubmitted(self):
        return unicode(self.pi_instance.status) == u"submitted_signatories"

    def documentInDraft(self):
        """Assume destinations of transitions with no sources are draft
        """
        wf = IWorkflow(self.pi_instance, None)
        if wf:
            return (self.pi_instance.status in 
                [tr.destination for tr in wf.get_transitions_from(None)]
            )
        return False

class BillSignatoryValidator(SignatoryValidator):
    zope.component.adapts(IBill)

    def expireSignatures(self):
        return unicode(self.pi_instance.status) == u"gazetted"


class MotionSignatoryValidator(SignatoryValidator):
    zope.component.adapts(IMotion)

class QuestionSignatoryValidator(SignatoryValidator):
    zope.component.adapts(IQuestion)

class AgendaItemSignatoryValidator(SignatoryValidator):
    zope.component.adapts(IAgendaItem)

class TabledDocumentSignatoryValidator(SignatoryValidator):
    zope.component.adapts(ITabledDocument)
