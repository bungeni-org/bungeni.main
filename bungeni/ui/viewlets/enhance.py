#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Additional UI enhancement viewlets

$Id$
"""

from zope.app.pagetemplate import ViewPageTemplateFile
from zc.resourcelibrary import need


class ProcessingViewlet(object):
    """Blocked UI processing message."""
    
    render = ViewPageTemplateFile("templates/processing.pt")

    def update(self):
        need("bungeni-form-block-ui")
