#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Workspace viewlets

$Id$
"""

from zope.app.component.hooks import getSite
from ploned.ui.viewlet import StructureAwareViewlet
from zope.app.pagetemplate import ViewPageTemplateFile

from bungeni.ui.i18n import _
from bungeni.ui.utils import url
from bungeni.models.interfaces import ISignatoriesValidator


class WorkspaceContextNavigation(StructureAwareViewlet):

    render = ViewPageTemplateFile("templates/workspace.pt")

    def update(self):
        self.tabs = []
        app = getSite()
        keys = app["workspace"]["documents"].keys()
        for key in keys:
            tab_url = url.absoluteURL(app["workspace"]["documents"][key],
                self.request
            )
            tab = {}
            tab["title"] = key
            tab["url"] = tab_url
            tab["active"] = self.request.getURL().startswith(tab_url)
            tab["count"] = app["workspace"]["documents"][key].count()
            self.tabs.append(tab)


class SignatoriesStatus(object):
    """Shows the signature status of a document - e.g. number required
    """
    available = True

    render = ViewPageTemplateFile("templates/signatories-status.pt")

    def update(self):
        self.signature_status = self.getMessage()
        if self.signature_status.get("message_text") == u"":
            self.available = False

    def getMessage(self):
        """Check signatories validator and generate status message
        of the form {"level": <level> , "message_text": "<i18n_message>"}
        """
        message = {"level": "info", "message_text": u""}
        validator = ISignatoriesValidator(self.context, None)
        if validator is None:
            return message
        if validator.requireSignatures():
            if validator.validateConsentedSignatories():
                message["message_text"] = _("signature_requirement_met",
                    default=(u"This document has the required number of "
                        u"signatories. ${signed_members} member(s) have signed"
                        u". ${required_members} signature(s) required."
                    ),
                    mapping = {
                        "signed_members": validator.consented_signatories,
                        "required_members": validator.min_signatories
                    }
                )
            else:
                message["level"] = "warning"
                message["message_text"] = _("signature_requirements_not_met",
                        default=(u"This document does not have the required "
                            u"number of signatories. Requires "
                            u"${required_members} signature(s). " 
                            u"${signed_members} member(s) have signed."
                        ),
                        mapping={
                            "required_members": validator.min_signatories,
                            "signed_members": validator.consented_signatories
                        }
                )
        return message
