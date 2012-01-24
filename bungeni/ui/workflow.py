# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Workflow UI

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.workflow")


import datetime

from zope.formlib import form
from zope.viewlet import viewlet
import zope.interface
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary
from zope.security.proxy import removeSecurityProxy
from zope.app.schema.vocabulary import IVocabularyFactory
from zope.formlib.widgets import TextAreaWidget
from zc.table import column
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.i18n import translate

from bungeni.alchemist import Session
from bungeni.alchemist.interfaces import IAlchemistContainer
from bungeni.alchemist.interfaces import IAlchemistContent
from bungeni.core import globalsettings
from bungeni.core.workflow import interfaces
from bungeni.core.workflows.utils import get_mask
from bungeni.models.interfaces import IAuditable, IWorkspaceContainer, \
    IBungeniParliamentaryContent
from bungeni.models.domain import ParliamentaryItem, get_changes
from bungeni.ui.forms.workflow import bindTransitions
from bungeni.ui.forms.common import BaseForm
from bungeni.ui.widgets import TextDateTimeWidget
from bungeni.ui.table import TableFormatter
from bungeni.ui.menu import get_actions
from bungeni.ui.utils import date
from bungeni.ui import browser
from bungeni.ui import z3evoque
from bungeni.ui.utils.url import absoluteURL
#from zope.app.pagetemplate import ViewPageTemplateFile
from bungeni.ui.i18n import _
from bungeni.ui.absoluteurl import WorkspaceAbsoluteURLView

from bungeni.utils import register


class WorkflowVocabulary(object):
    zope.interface.implements(IVocabularyFactory)

    def __call__(self, context):
        if IAlchemistContent.providedBy(context):
            ctx = context
        elif  IAlchemistContainer.providedBy(context):
            domain_model = removeSecurityProxy(context.domain_model)
            ctx = domain_model()
        workflow = interfaces.IWorkflow(ctx)
        items = []
        for status in workflow.states.keys():
            items.append(SimpleTerm(status, status, 
                _(workflow.get_state(status).title)))
        return SimpleVocabulary(items)
workflow_vocabulary_factory = WorkflowVocabulary()


class WorkflowHistoryViewlet(viewlet.ViewletBase):
    """Show the current workflow state and the workflow-history.
    """
    form_name = _(u"Workflow history")
    formatter_factory = TableFormatter
    
    def __init__(self,  context, request, view, manager):
        self.context = context
        self.request = request
        self.__parent__ = view
        self.manager = manager
        self.wf_status = "new"
        self.has_status = False
        # table to display the workflow history
        formatter = date.getLocaleFormatter(self.request, "dateTime", "short")
        # !+ note this breaks the previous sort-dates-as-strings-hack of 
        # formatting dates as date.strftime("%Y-%m-%d %H:%M") -- when sorted
        # as a string -- gives correct results (for all locales).
        self.columns = [
            column.GetterColumn(title=_(u"date"), 
                getter=lambda i,f:formatter.format(i.date_active)),
            column.GetterColumn(title=_(u"user"), 
                getter=lambda i,f:IDCDescriptiveProperties(i.user).title),
            column.GetterColumn(title=_(u"description"), 
                getter=lambda i,f:i.description),
        ]
    
    def update(self):
        has_wfstate = False
        try:
            sc = interfaces.IStateController(
                removeSecurityProxy(self.context)).get_status()
            has_wfstate = True
        except:
            sc = "undefined"
        if sc is None:
            sc = "undefined"
            has_wfstate = False
        self.wf_status = sc
        self.has_status = has_wfstate
        self.entries = self.get_feed_entries()
    
    def render(self):
        columns = self.columns
        formatter = self.formatter_factory(
            self.context,
            self.request,
            self.entries,
            prefix="results",
            visible_column_names=[c.name for c in columns],
            columns=columns)
        formatter.cssClasses["table"] = "listing",
        formatter.updateBatching()
        return formatter()
    
    def get_feed_entries(self):
        return get_changes(removeSecurityProxy(self.context), "workflow")


class WorkflowActionViewlet(browser.BungeniBrowserView, 
        BaseForm, viewlet.ViewletBase
    ):
    """Display workflow status and actions.
    """
    # stores old_url of object before transition change
    # we could use HTTP_REFERER but that would mean relying on client input
    _old_url = None
    
    # evoque
    render = z3evoque.ViewTemplateFile("form.html#form")
    
    # zpt
    #render = ViewPageTemplateFile("templates/viewlet.pt")
    
    class IWorkflowForm(zope.interface.Interface):
        note = zope.schema.Text(
            title=_("Comment on workflow change"), required=False)
        date_active = zope.schema.Datetime(
            title=_("Active Date"), required=True)
        registry_number = zope.schema.TextLine(
            title=_("Registry number"), required=False)
    form_name = "Workflow"
    form_fields = form.Fields(IWorkflowForm)
    note_widget = TextAreaWidget
    note_widget.height = 1
    form_fields["note"].custom_widget = note_widget
    form_fields["date_active"].custom_widget = TextDateTimeWidget
    actions = ()
    
    def get_min_date_active(self):
        """Determine the min_date_active to validate against.
        """
        
        def is_workflowed_and_draft(instance):
            """is item workflowed, and if so is it in a logical draft state?
            """
            if interfaces.IWorkflowed.providedBy(instance):
                wf = interfaces.IWorkflow(instance)
                return instance.status in wf.get_state_ids(tagged=["draft"],
                    restrict=False)
            return False
        
        min_date_active = None
        if IAuditable.providedBy(self.context):
            instance = removeSecurityProxy(self.context)
            # !+PASTDATAENTRY(mr, jun-2011) offers a way to enter past data 
            # for workflowed items via the UI -- note, ideally we should be 
            # able to also control the item's creation active_date.
            #
            # If a workflowed item is in draft state, we do NOT take the 
            # date_active of its last change as the min_date_active, but
            # let that min fallback to parliament's creation date...
            if not is_workflowed_and_draft(instance):
                changes = get_changes(instance, "workflow")
                if changes:
     	            # then use the "date_active" of the most recent entry
                    min_date_active = changes[-1].date_active
        if not min_date_active:
            # fallback to current parliament's start_date (cast to a datetime)
            min_date_active = datetime.datetime.combine(
                globalsettings.get_current_parliament().start_date,
                datetime.time())
        # As the precision of the UI-submitted datetime is only to the minute, 
        # we adjust min_date_active by a margin of 59 secs earlier to avoid 
        # issues of doing 2 transitions in quick succession (within same minute) 
        # the 2nd of which could be taken to be too old...
        return min_date_active - datetime.timedelta(seconds=59)
    
    def validate(self, action, data):
        # submitted data is actually updated in following call to super.validate
        # !+PASTDATAENTRY(mr, jun-2011) enhancement? see Issue 612 Comment 6:
        # unrequire, allow active_date=None, 
        # get_effective_active_date -> last workflow non-None active_date
        errors = super(WorkflowActionViewlet, self).validate(action, data)
        if "date_active" in data.keys():
            min_date_active = self.get_min_date_active()
            if data.get("date_active") < min_date_active:
                errors.append(zope.interface.Invalid(
                        _("Active Date is in the past.")))
            elif data.get("date_active") > datetime.datetime.now():
                errors.append(zope.interface.Invalid(
                        _("Active Date is in the future.")))
        if "registry_number" in data.keys():
            reg_number = data.get("registry_number")
            if reg_number:
                session = Session()
                num = session.query(ParliamentaryItem
                    ).filter(ParliamentaryItem.registry_number==reg_number
                    ).count()
                if num != 0:
                    errors.append(zope.interface.Invalid(
                        "This registry number is already taken."))
        return errors
    
    def setUpWidgets(self, ignore_request=False):
        class WorkflowForm:
            note = None
            date_active = None
            registry_number = None
        self.adapters = {
            self.IWorkflowForm: WorkflowForm,
        }
        self.widgets = form.setUpDataWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            ignore_request=ignore_request)
    
    def update(self, transition_id=None):
        if IWorkspaceContainer.providedBy(self.context.__parent__):
            self._old_url = WorkspaceAbsoluteURLView(
                self.context, self.request)()
        workflow = interfaces.IWorkflow(self.context)
        if transition_id:
            transition = workflow.get_transition(transition_id)
            title = translate(_(transition.title), context=self.request)
            self.status = translate(
                _(u"Confirmation required for workflow transition: '${title}'",
                    mapping={"title": title}
                ), 
                context=self.request)
        self.setupActions(transition_id)
        
        if (IBungeniParliamentaryContent.providedBy(self.context) and
                get_mask(self.context) == "manual" and 
                not self.context.registry_number
            ):
            self.form_fields = self.form_fields.omit("note", "date_active")
        else:
            self.form_fields = self.form_fields.omit("registry_number")
        
        if not self.actions: 
            self.form_fields = self.form_fields.omit("note", "date_active")
        elif not IAuditable.providedBy(self.context):
            self.form_fields = self.form_fields.omit("note", "date_active")
        # !+SUPERFLUOUS_ObejctModifiedEvent(mr, nov-2011) the following update()
        # is causing a ModifiedEvent to be fired, causing a modify change to be 
        # logged (while this workflow change should be just that).
        super(WorkflowActionViewlet, self).update()
    
    @property
    def next_url(self):
        if IWorkspaceContainer.providedBy(self.context.__parent__):
            # check if the object is in the same tab as before.
            # if it is redirect to the object, if not redirect to the listing
            if (WorkspaceAbsoluteURLView(self.context, self.request)() == 
                self._old_url):
                self._next_url = self._old_url
            else:
                self._next_url = absoluteURL(
                    self.context.__parent__, self.request)
        return self._next_url
        
    def setupActions(self, transition_id):
        # !+RENAME(mr, apr-2011) should be transition_id
        wfc = interfaces.IWorkflowController(self.context)
        if transition_id is None:
            transition_ids = wfc.getManualTransitionIds()
        else:
            transition_ids = (transition_id,)
        self.actions = bindTransitions(self, transition_ids, wfc.workflow)


@register.view(interfaces.IWorkflowed, name="workflow")
class WorkflowView(browser.BungeniBrowserView):
    """This view is linked to by the "workflow" context action and dislays the 
    workflow history and the action viewlet with all possible transitions
    """
    # evoque
    template = z3evoque.PageViewTemplateFile("workflow.html#main")
    
    # zpt
    #template = ViewPageTemplateFile("templates/workflow.pt")
    
    _page_title = "Workflow"
    
    def update(self, transition_id=None):
        # set up viewlets; the view is rendered from viewlets for
        # historic reasons; this may be refactored anytime.
        if IAuditable.providedBy(self.context):
            self.history_viewlet = WorkflowHistoryViewlet(
                self.context, self.request, self, None)
            self.history_viewlet.update()
        self.action_viewlet = WorkflowActionViewlet(
            self.context, self.request, self, None)
        self.action_viewlet.update(transition_id=transition_id)
    
    def __call__(self):
        self.update()
        template = self.template()
        return template


@register.view(interfaces.IWorkflowed, name="change_workflow_state")
class WorkflowChangeStateView(WorkflowView):
    """This gets called on selection of a transition from the menu i.e. NOT:
    a) when clicking on one of the transition buttons in the workflow form.
    b) when clicking Add of an object (automatic transitions).
    """
    
    # evoque
    ajax_template = z3evoque.PageViewTemplateFile("workflow.html#ajax")
    
    # zpt
    #ajax_template = ViewPageTemplateFile("templates/workflow_ajax.pt")
    
    def __call__(self, transition_id=None, headless=False):
        # parameters coming in via URL querystring or post vars !
        method = self.request["REQUEST_METHOD"]
        # !+ALWAYS_POST(mr, sep-2011) requests coming from link clicks (GETs) 
        # from the bungeni Web UI seem to always be intercepted and switched 
        # into POSTs.
        workflow = interfaces.IWorkflow(self.context)
        
        require_confirmation = True
        if transition_id is not None: 
            self.update(transition_id)
            require_confirmation = workflow.get_transition(transition_id
                ).require_confirmation
        else:
            self.update()
        
        if (IBungeniParliamentaryContent.providedBy(self.context) and
                get_mask(self.context) == "manual" and 
                not self.context.registry_number
            ):
            require_confirmation = True
        
        if (not require_confirmation and method == "POST"):
            actions = bindTransitions(
                self.action_viewlet, (transition_id,), workflow)
            assert len(actions) == 1
            # execute action
            # !+ should pass self.request.form as data? e.g. value is:
            # {u"next_url": u"...", u"transition": u"submit_response"}
            result = actions[0].success({})
            # !+UNUSED(mr, jun-2011) this result is never used!
        
        if headless:
            actions = get_actions("context_workflow", self.context, self.request)
            state_title = workflow.get_state(self.context.status).title
            result = self.ajax_template(actions=actions, state_title=state_title)
            if require_confirmation:
                self.request.response.setStatus(403)
            else:
                self.request.response.setStatus(200)
                self.request.response.setResult(result)
                self.request.response.setHeader("Content-Type", "text/xml")
            return result
            
        template = self.template()
        return template

