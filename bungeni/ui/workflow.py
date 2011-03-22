
from datetime import datetime, timedelta

from zope.formlib import form
from zope.viewlet import viewlet
import zope.interface
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary
from zope.security.proxy import removeSecurityProxy
from zope.app.schema.vocabulary import IVocabularyFactory
from zope.app.form.browser.textwidgets import TextAreaWidget
from zc.table import column

from bungeni.core.workflow import interfaces

from bungeni.alchemist.interfaces import IAlchemistContainer
from bungeni.alchemist.interfaces import IAlchemistContent
from bungeni.core import audit
from bungeni.core import globalsettings
from bungeni.ui.forms.workflow import bindTransitions
from bungeni.ui.forms.common import BaseForm
from bungeni.ui.widgets import TextDateTimeWidget
from bungeni.ui.table import TableFormatter
from bungeni.ui.menu import get_actions
from bungeni.ui.utils import date
from bungeni.ui import browser
from bungeni.ui import z3evoque
from zope.dublincore.interfaces import IDCDescriptiveProperties
from bungeni.core.interfaces import IAuditable
#from zope.app.pagetemplate import ViewPageTemplateFile

from bungeni.ui.i18n import _
from bungeni.core.i18n import _ as _bc
from zope.i18n import translate


class WorkflowVocabulary(object):
    zope.interface.implements(IVocabularyFactory)

    def __call__(self, context):
        if IAlchemistContent.providedBy(context):
            ctx = context
        elif  IAlchemistContainer.providedBy(context):
            domain_model = removeSecurityProxy(context.domain_model)
            ctx = domain_model()
        wf = interfaces.IWorkflow(ctx)
        items = []
        for state in wf.workflow.states.keys():
            items.append(SimpleTerm(wf.workflow.states[state].id,
                        wf.workflow.states[state].id,
                        _(wf.workflow.states[state].title)))
        return SimpleVocabulary(items)
workflow_vocabulary_factory = WorkflowVocabulary()


class WorkflowHistoryViewlet(viewlet.ViewletBase):
    """Implements the workflowHistoryviewlet this viewlet shows the
    current workflow state  and the workflow-history.
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
            wf_state = interfaces.IStateController(
                removeSecurityProxy(self.context)).getState()
            has_wfstate = True
        except:
            wf_state = u"undefined"
        if wf_state is None:
            wf_state = u"undefined"
            has_wfstate = False
        self.wf_status = wf_state
        self.has_status = has_wfstate
        self.entries = self.getFeedEntries()
    
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
    
    @property
    def _change_object(self):
        auditor = audit.getAuditor(self.context)
        return auditor.change_object
    
    def getFeedEntries(self):
        instance = removeSecurityProxy(self.context)
        return [ change for change in instance.changes 
                if change.action == "workflow" ]
        

class WorkflowActionViewlet(browser.BungeniBrowserView, 
        BaseForm, viewlet.ViewletBase):
    """Display workflow status and actions."""
    
    # evoque
    render = z3evoque.ViewTemplateFile("form.html#form")
    
    # zpt
    #render = ViewPageTemplateFile("templates/viewlet.pt")
    
    class IWorkflowForm(zope.interface.Interface):
        note = zope.schema.Text(
            title=_("Comment on workflow change"), required=False)
        date_active = zope.schema.Datetime(
            title=_("Active Date"), required=True)
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
        min_date_active = None
        if IAuditable.providedBy(self.context):
            instance = removeSecurityProxy(self.context)
            changes = [ change for change in instance.changes 
                        if change.action == "workflow" ]
            if changes:
 	            # then use the "date_active" of the most recent entry
                min_date_active = changes[-1].date_active
        if not min_date_active: 
            # then fallback to the current parliament's atart_date
            min_date_active = globalsettings.get_current_parliament().start_date
        # As the precision of the UI-submitted datetime is only to the minute, 
        # we adjust min_date_time by a margin of 59 secs earlier to avoid 
        # issues of doing 2 transitions in quick succession (within same minute) 
        # the 2nd of which could be taken to be too old...
        return min_date_active - timedelta(seconds=59)
    
    def validate(self, action, data):
        # submitted data is actually updated in following call to super.validate
        errors = super(WorkflowActionViewlet, self).validate(action, data)
        if "date_active" in data.keys():
            min_date_active = self.get_min_date_active()
            if data.get("date_active") < min_date_active:
                errors.append(zope.interface.Invalid(
                    _("Active Date is too old.")))
            elif data.get("date_active") > datetime.now():
                errors.append(zope.interface.Invalid(
                    _("Active Date is in the future.")))
        return errors
    
    def setUpWidgets(self, ignore_request=False):
        class WorkflowForm:
            note = None
            date_active = None
        self.adapters = {
            self.IWorkflowForm: WorkflowForm,
        }
        self.widgets = form.setUpDataWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            ignore_request = ignore_request)
    
    def update(self, transition=None):
        wf = interfaces.IWorkflow(self.context) 
        if transition is not None:
            state_transition = wf.getTransitionById(transition)
            # !- workflow state title translations are in bungeni.core
            # use the right factory here to get translation
            state_title = translate(_bc(state_transition.title),
                                context=self.request)
            self.status = translate(_(
                u"Confirmation required for workflow transition: '${title}'",
                mapping={"title": state_title}), context = self.request)
        self.setupActions(transition)
        if not self.actions: 
            self.form_fields = self.form_fields.omit("note", "date_active")
        elif not IAuditable.providedBy(self.context):
            self.form_fields = self.form_fields.omit("note", "date_active")
        super(WorkflowActionViewlet, self).update()
    
    def setupActions(self, transition):
        self.wf = interfaces.IWorkflowController(self.context)
        if transition is None:
            transitions = self.wf.getManualTransitionIds()
        else:
            transitions = (transition,)
        self.actions = bindTransitions(
            self, transitions, None, interfaces.IWorkflow(self.context))


class WorkflowView(browser.BungeniBrowserView):
    """This view is linked to by the "workflow" context action and dislays the 
    workflow history and the action viewlet with all possible transitions
    """
    # evoque
    template = z3evoque.PageViewTemplateFile("workflow.html#main")
    
    # zpt
    #template = ViewPageTemplateFile("templates/workflow.pt")
    
    _page_title = "Workflow"
    
    def update(self, transition=None):
        # set up viewlets; the view is rendered from viewlets for
        # historic reasons; this may be refactored anytime.
        if IAuditable.providedBy(self.context):
            self.history_viewlet = WorkflowHistoryViewlet(
                self.context, self.request, self, None)
            self.history_viewlet.update()
        self.action_viewlet = WorkflowActionViewlet(
            self.context, self.request, self, None)
        self.action_viewlet.update(transition=transition)
    
    def __call__(self):
        self.update()
        template = self.template()
        return template


class WorkflowChangeStateView(WorkflowView):
    """This gets called on selection of a transition from the menu i.e. NOT
    when clicking on one of the trasition buttons in the workflow form.
    """
    
    # evoque
    ajax_template = z3evoque.PageViewTemplateFile("workflow.html#ajax")
    
    # zpt
    #ajax_template = ViewPageTemplateFile("templates/workflow_ajax.pt")
    
    def __call__(self, headless=False, transition=None):
        method = self.request["REQUEST_METHOD"]
        if transition:
            wf = interfaces.IWorkflow(self.context) 
            state_transition = wf.getTransitionById(transition)
            require_confirmation = getattr(
                state_transition, "require_confirmation", False)
            self.update(transition)
        else:
            self.update()
        
        if transition and require_confirmation is False and method == "POST":
            actions = bindTransitions(
                self.action_viewlet, (transition,), None, 
                interfaces.IWorkflow(self.context))
            assert len(actions) == 1
            # execute action
            # !+ should pass self.request.form as data? e.g. value is:
            # {u"next_url": u"...", u"transition": u"submit_response"}
            result = actions[0].success({})
        
        if headless is True:
            actions = get_actions("context_workflow", self.context, self.request)
            state_title = interfaces.IWorkflowController(self.context
                ).workflow().workflow.states[self.context.status].title
            result = self.ajax_template(actions=actions, state_title=state_title)
            
            if require_confirmation is True:
                self.request.response.setStatus(403)
            else:
                self.request.response.setStatus(200)
                self.request.response.setResult(result)
                self.request.response.setHeader("Content-Type", "text/xml")
            
            return result
            
        template = self.template()
        return template

