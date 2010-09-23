# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist ui - [
    alchemist.ui
    alchemist.ui.core
    alchemist.ui.viewlet
    alchemist.ui.widgets
]

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")

from zope.formlib import form
from zope.formlib.namedtemplate import NamedTemplate

#

from alchemist.ui import widgets

from alchemist.ui.core import DynamicFields
from alchemist.ui.core import getSelected
from alchemist.ui.core import handle_edit_action
from alchemist.ui.core import null_validator
from alchemist.ui.core import setUpFields
from alchemist.ui.core import unique_columns

from alchemist.ui.viewlet import DisplayFormViewlet
from alchemist.ui.viewlet import EditFormViewlet


class BaseForm(form.FormBase):
    """Only used by: bungeni.ui.login.Login
    
    was: alchemist.ui.core.BaseForm
    """
    template = NamedTemplate("alchemist.form")
    
    def invariantErrors(self):
        errors = []
        for error in self.errors:
            if isinstance(error, interface.Invalid):
                errors.append(error)
        return errors

