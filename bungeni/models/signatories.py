# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Signatories validation machinery for parliamentary documents

$Id$
"""

import zope.component
import zope.interface

from bungeni.models.interfaces import (IBill, IMotion, IQuestion,
    IAgendaItem, ITabledDocument, ISignatoriesValidator
)
from bungeni.models.settings import BungeniSettings
from bungeni.core.app import BungeniApp

log = __import__("logging").getLogger("bungeni.models.signatories")

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
        #!_VERSIONS(mb, aug-2011) automatic transitions firing for versions?
        # as at r8488 - check whether the context actually has signatories
        if hasattr(self.pi_instance, "signatories"):
            return self.pi_instance.signatories.values()
        else:
            log.warning("The object  %s has no signatories. Returning empty"
                " list of signatories.", 
                self.pi_instance.__str__()
            )
            return []

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
        """Check that a document is being redrafted
        """
        return unicode(self.pi_instance.status) == u"redraft"

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
