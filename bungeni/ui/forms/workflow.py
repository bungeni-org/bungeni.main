# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Workflow Forms

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.forms.workflow")

from zope import component
from zope.formlib import form
from zope.security.proxy import removeSecurityProxy
from zope.annotation.interfaces import IAnnotations

from bungeni.core.interfaces import IVersioned
from bungeni.models.utils import get_principal_id
from bungeni.ui.i18n import _
from bungeni.core.workflow import interfaces
from bungeni.alchemist.ui import handle_edit_action

''' !+UNUSED(mr, mar-2011)
def createVersion(context, comment=""):
    """Create a new version of an object and return it.
    """
    instance = removeSecurityProxy(context)
    versions = IVersioned(instance)
    _comment = u"New version created upon edit."
    if comment:
       _comment = u"%s %s" % (_comment, comment)
    versions.create(_comment.strip())
'''

def bindTransitions(form_instance, transitions, wf_name=None, wf=None):
    """Bind workflow transitions into formlib actions.
    """
    if wf_name:
        success_factory = lambda tid: TransitionHandler(tid, wf_name)
    else:
        success_factory = TransitionHandler
    actions = []
    for tid in transitions:
        d = {}
        if success_factory:
            d["success"] = success_factory(tid)
        if wf is not None:
            title = _(unicode(wf.getTransitionById(tid).title))
            action = form.Action(title, **d)
        else:
            action = form.Action(tid, **d)
        action.form = form_instance
        action.__name__ = "%s.%s"%(form_instance.prefix, action.__name__)
        actions.append(action)
    return actions
    
class TransitionHandler(object):
    """Workflow transition 2 formlib action bindings.
    """
    
    def __init__(self, transition_id, wf_name=None):
        self.transition_id = transition_id
        self.wf_name = wf_name
        # !+ seems that on each manual transition selection in the UI,  
        # there are 3 instances of TransitionHandler initialized
    
    def __call__(self, form, action, data):
        """Save data, make version and fire transition.
        
        Redirects to the ``next_url`` location.
        """
        context = getattr(form.context, "_object", form.context)
        if self.wf_name:
            info = component.getAdapter(
                context, interfaces.IWorkflowController, self.wf_name)
        else:
            info = interfaces.IWorkflowController(context)
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
            data.setdefault("date_active", data.get("data_active", None))
            # and because WorkflowController API e.g. fireTransition(), ONLY 
            # foresees for a comment attribute as additional data, we bypass 
            # using that altogether, and pass it along downstream by stuffing 
            # onto the request
            IAnnotations(form.request)["change_data"] = data
            info.fireTransition(self.transition_id)
            next_url = form.next_url
            if next_url is None:
                next_url = form.request["HTTP_REFERER"]
                log.error(" TransitionHandler.__call__() => CANNOT redirect to "
                    "next_url [None]... will try instead to redirect to "
                    "HTTP_REFERER [%s]" % (next_url,))
            return form.request.response.redirect(next_url)

