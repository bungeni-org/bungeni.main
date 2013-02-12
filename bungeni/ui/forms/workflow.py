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
from zope.security.proxy import removeSecurityProxy

from bungeni.ui.i18n import _
from bungeni.core.workflow import interfaces
from bungeni.utils import common


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
    def __init__(self, transition_id):
        self.transition_id = transition_id
    
    def __call__(self, form, action, data):
        """Stuff additional form transition field values onto the request, and
        fire transition (context.status will be modified as a result of that).
        
        Redirects to the ``next_url`` location.
        """
        context = getattr(form.context, "_object", form.context)
        log.debug(""" TransitionHandler.__call__()
            form=%s 
            action=(name=%s, label=%s)
            data=%s
            principal_id=%s
            context=%s
            transition_id=%s
            next_url=%s 
            current_url=%s """ % (form, action.label, action.name, data, 
                common.get_request_login(), context, self.transition_id, 
                form.next_url, form.request.getURL())
        )
        
        # dress-up transition data object
        data.setdefault("note", data.get("note", ""))
        data.setdefault("date_active", data.get("date_active", None))
        data.setdefault("registry_number", data.get("registry_number", ""))
        
        # !+registry_number(mr, feb-2012) should be within a workflow action?
        reg_number = data.get("registry_number", "")
        if reg_number:
            unproxied_context = removeSecurityProxy(context)
            unproxied_context.registry_number = reg_number
        
        # !+ because WorkflowController API e.g. fireTransition(), ONLY 
        # foresees for a comment attribute as additional data, we bypass 
        # using that altogether, and pass it along downstream by stuffing 
        # onto the request
        IAnnotations(form.request)["change_data"] = data
        
        interfaces.IWorkflowController(context).fireTransition(
            self.transition_id)
        
        # NOTE: for some reason form.next_url is (always?) None --
        # in which case we redirect to HTTP_REFERER instead.
        next_url = form.next_url
        if next_url is None:
            next_url = form.request["HTTP_REFERER"]
            log.error(" TransitionHandler.__call__() => CANNOT redirect to "
                "next_url [None]... will try instead to redirect to "
                "HTTP_REFERER [%s]" % (next_url,))
        return form.request.response.redirect(next_url)

