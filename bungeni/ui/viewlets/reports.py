#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Report viewlets

$Id$
"""

from zope.app.pagetemplate import ViewPageTemplateFile

class ReportPreview(object):
    """Report preview."""
    
    render = ViewPageTemplateFile("templates/report-preview.pt")
    
    def update(self):
        self.report_preview = self._parent.generated_content

    @property
    def available(self):
        return self._parent.show_preview    
