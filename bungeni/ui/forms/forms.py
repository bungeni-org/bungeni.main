# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Specific forms for Bungeni user interface

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.forms.forms")

from zope.formlib import namedtemplate
from zope import interface
from zope.app.pagetemplate import ViewPageTemplateFile

from bungeni.ui.forms.common import DisplayForm

FormTemplate = namedtemplate.NamedTemplateImplementation(
    ViewPageTemplateFile("templates/form.pt")
)
SubFormTemplate = namedtemplate.NamedTemplateImplementation(
    ViewPageTemplateFile("templates/subform.pt")
)
ContentTemplate = namedtemplate.NamedTemplateImplementation(
    ViewPageTemplateFile("templates/content.pt")
)

def set_widget_errors(widgets, errors):
    """Display invariant errors / custom validation errors in the
    context of the field."""

    for widget in widgets:
        name = widget.context.getName()
        for error in errors:
            if isinstance(error, interface.Invalid) and name in error.args[1:]:
                if widget._error is None:
                    widget._error = error


class UserAddressDisplayForm(DisplayForm):
    
    @property
    def page_title(self):
        return "%s address" % self.context.logical_address_type.title()
