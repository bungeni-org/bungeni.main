#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Workspace viewlets

$Id$
"""

from zope.security.proxy import removeSecurityProxy
from zope.app.component.hooks import getSite
from ploned.ui.viewlet import StructureAwareViewlet
from zope.app.pagetemplate import ViewPageTemplateFile

from bungeni.ui.utils import url
from bungeni.core.interfaces import IWorkspaceDocuments
from bungeni.core import translation
from bungeni.capi import capi
from bungeni import _, translate


class WorkspaceContextNavigation(StructureAwareViewlet):

    render = ViewPageTemplateFile("templates/workspace.pt")
    folder = "my-documents"
    css_class = "workpace-listing"

    def update(self):
        self.tabs = []
        directory = getSite()["workspace"][self.folder]
        for key in directory.keys():
            tab_url = url.absoluteURL(directory[key], self.request)
            tab = {}
            if IWorkspaceDocuments.providedBy(directory):
                tab["title"] = translate("section_workspace_%s" % key)
            else:
                tab["title"] = directory[key].title
            tab["tab_type"] = directory[key].__name__
            tab["url"] = tab_url
            tab["active"] = self.request.getURL().startswith(tab_url)
            self.tabs.append(tab)


class WorkspaceDocumentNavigation(WorkspaceContextNavigation):
    css_class = "workspace-documents"

class WorkspaceDocMarker(StructureAwareViewlet):
    """Adds a hidden div in the doc view that marks
    that the workspace count should be loaded
    """
    render = ViewPageTemplateFile("templates/workspace-doc-marker.pt")


class WorkspaceUnderConsiderationNavigation(WorkspaceContextNavigation):
   
    render = ViewPageTemplateFile("templates/workspace-under-consideration.pt")
    folder = "under-consideration"
    css_class = "workspace-under-consideration"


class MessageViewlet(object):
    """display a message with optional level info
    """
    available = True

    render = ViewPageTemplateFile("templates/messages.pt")

    def update(self):
        self.messages = self.getMessages()
        if not len(self.messages):
            self.available = False

    def getMessages(self):
        """Return a list of messages of the form
        of the form {"level": <level> , "header": "<i18n_message>",
        "text": "<i18n_message>"}
        """
        raise NotImplementedError("Child class must implement this")


class SignatoriesStatus(MessageViewlet):
    """Display a message on signatories status (if threshold is met or otherwise)
    """
    def getMessages(self):
        messages = []
        message = {"level": "info", "header": _("Signatories"), "text": u""}
        context = removeSecurityProxy(self.context)
        signatory_feature = context.signatory_feature
        if signatory_feature and signatory_feature.needs_signatures():
            if signatory_feature.valid_num_consented_signatories(context):
                message["text"] = _("signature_requirement_met",
                    default=(u"This document has the required number of "
                        u"signatories. ${signed_members} member(s) have signed"
                        u". ${required_members} signature(s) required."
                    ),
                    mapping = {
                        "signed_members": signatory_feature.num_consented_signatories(context),
                        "required_members": signatory_feature.p.min_signatories
                    }
                )
            else:
                message["level"] = "warning"
                message["text"] = _("signature_requirements_not_met",
                        default=(u"This document does not have the required "
                            u"number of signatories. Requires "
                            u"${required_members} signature(s). " 
                            u"${signed_members} member(s) have signed."
                        ),
                        mapping={
                            "required_members": signatory_feature.p.min_signatories,
                            "signed_members": signatory_feature.num_consented_signatories(context)
                        }
                )
            messages.append(message)
        return messages


class TranslationStatus(MessageViewlet):
    def getMessages(self):
        """display a message indicating that a doc needs translation to pivot"""
        messages = []
        if capi.pivot_languages:
            is_translated = False
            context_lang = self.context.language
            for lang in capi.pivot_languages:
                if lang == context_lang:
                    is_translated = True
                    break
                trans = translation.get_field_translations(self.context, lang)
                if trans:
                    is_translated = True
                    break
            if not is_translated:
                messages.append(
                    {"level": "warning", "header": _("Pivot Translation"), 
                        "text": u"This document has no pivot translation."}
                )
        return messages


