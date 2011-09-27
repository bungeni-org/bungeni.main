# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Workflow Forms

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.forms.workflow")

from zope import component
from zope.formlib import form
from zope.annotation.interfaces import IAnnotations

from bungeni.models.utils import get_principal_id
from bungeni.ui.i18n import _
from bungeni.core.workflow import interfaces
from bungeni.alchemist.ui import handle_edit_action


def bindTransitions(form_instance, transitions, wf):
    """Bind workflow transitions into formlib actions.
    """
    actions = []
    for tid in transitions:
        action = form.Action(
            _(unicode(wf.get_transition(tid).title)), 
            success=TransitionHandler(tid)
        )
        action.form = form_instance
        action.__name__ = "%s.%s" % (form_instance.prefix, action.__name__)
        actions.append(action)
    return actions
    
class TransitionHandler(object):
    """Workflow transition to formlib action binding.
    """
    
    def __init__(self, transition_id, wf_name=None):
        self.transition_id = transition_id
        self.wf_name = wf_name
    
    def __call__(self, form, action, data):
        """Save data, make version and fire transition.
        
        Redirects to the ``next_url`` location.
        """
        context = getattr(form.context, "_object", form.context)
        if self.wf_name:
            wfc = component.getAdapter(
                context, interfaces.IWorkflowController, self.wf_name)
        else:
            wfc = interfaces.IWorkflowController(context)
        result = handle_edit_action(form, action, data)
        #
        if form.errors: 
            return result
        else:
            # NOTE: for some reason form.next_url is (always?) None --
            # for when it is None, we redirect to HTTP_REFERER instead.
            log.debug(""" TransitionHandler.__call__()
        form=%s 
        action=(name=%s, label=%s)
        data=%s
        principal_id=%s
        context=%s
        transition_id=%s
        result=%s
        next_url=%s 
        current_url=%s """ % (form, action.label, action.name, data, 
                get_principal_id(), context, self.transition_id, 
                result, form.next_url, form.request.getURL()))
            # dress-up transition data object
            data.setdefault("note", data.get("note", ""))
            data.setdefault("date_active", data.get("date_active", None))
            # and because WorkflowController API e.g. fireTransition(), ONLY 
            # foresees for a comment attribute as additional data, we bypass 
            # using that altogether, and pass it along downstream by stuffing 
            # onto the request
            IAnnotations(form.request)["change_data"] = data
            wfc.fireTransition(self.transition_id)
            next_url = form.next_url
            if next_url is None:
                next_url = form.request["HTTP_REFERER"]
                log.error(" TransitionHandler.__call__() => CANNOT redirect to "
                    "next_url [None]... will try instead to redirect to "
                    "HTTP_REFERER [%s]" % (next_url,))
            return form.request.response.redirect(next_url)

