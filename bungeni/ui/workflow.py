
from datetime import datetime, timedelta

from zope.formlib import form
from zope.viewlet import viewlet
import zope.interface
from zope.annotation.interfaces import IAnnotations
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary
from zope.security.proxy import removeSecurityProxy
from zope.publisher.browser import BrowserView
from zope.app.schema.vocabulary import IVocabularyFactory
from zope.app.form.browser.textwidgets import TextAreaWidget
from zc.table import column

from sqlalchemy import orm
import sqlalchemy as rdb

from ore.workflow import interfaces
from ore.alchemist.interfaces import IAlchemistContainer
from ore.alchemist.interfaces import IAlchemistContent

from ore.workflow.interfaces import IWorkflowInfo
from bungeni.core import audit
from bungeni.core import globalsettings
from bungeni.ui.forms.workflow import bindTransitions
from bungeni.ui.forms.common import BaseForm
from bungeni.ui.widgets import TextDateTimeWidget
from bungeni.ui.table import TableFormatter
from bungeni.ui.menu import get_actions
from bungeni.ui.utils import date, common
from bungeni.ui import browser
from bungeni.ui import z3evoque
from zope.app.pagetemplate import ViewPageTemplateFile

from bungeni.ui.i18n import _


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
                getter=lambda i,f:formatter.format(i["date_active"])),
            column.GetterColumn(title=_(u"user"), 
                getter=lambda i,f:i["user_id"]),
            column.GetterColumn(title=_(u"description"), 
                getter=lambda i,f:i["description"]),
        ]
        
    def update(self):
        has_wfstate = False
        try:
            wf_state = interfaces.IWorkflowState(
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
        # min_date_active
        if len(self.entries):
            # then use the "date_active" of the most recent entry
            min_date_active = self.entries[0]["date_active"]
        else:
            # then use the current parliament's atart_date
            min_date_active = globalsettings.get_current_parliament().start_date
        # remember "min_date_active" on the request
        IAnnotations(self.request)["min_date_active"] = min_date_active
    
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
    def _log_table(self):
        auditor = audit.getAuditor(self.context)
        if auditor is not None:
            return auditor.change_table

    def getFeedEntries(self):
        instance = removeSecurityProxy(self.context)
        mapper = orm.object_mapper(instance)
        
        table = self._log_table
        if table is None:
            return ()
        
        query = table.select().where(
            rdb.and_(table.c.content_id==rdb.bindparam("content_id"),
            rdb.and_(table.c.action=="workflow"))
            ).order_by(table.c.change_id.desc())
        
        content_id = mapper.primary_key_from_instance(instance)[0] 
        content_changes = query.execute(content_id=content_id)
        return map(dict, content_changes)


class WorkflowActionViewlet(BaseForm, viewlet.ViewletBase):
    """Display workflow status and actions."""
    
    class IWorkflowComment(zope.interface.Interface):
        note = zope.schema.Text(
            title=_("Comment on workflow change"), required=True)
        date_active = zope.schema.Datetime(
            title=_("Active Date"), required=True)
        
        @zope.interface.invariant
        def valid_date_active(comment):
            request = common.get_request()
            # recover min_date_active, and adjust it to be 59 secs earlier to
            # avoid issues of doing 2 transitions in quick succession (within 
            # the same minute) the 2nd of which could be taken to be too old...
            min_date_active = (IAnnotations(request)["min_date_active"] - 
                                                        timedelta(seconds=59))
            if not hasattr(comment, "date_active"):
                # !+ because of a BUG in the datetime widget (probably) :
                # after a server restart, resubmitting a previously loaded 
                # form -- that displays valid data_active value results in a
                # form.NoDataInput("date_active") error... thus causing:
                # (comment.date_active<min_date_active) to be False !
                raise zope.interface.Invalid(_("NoDataInput for Active Date."))
            elif comment.date_active < min_date_active:
                raise zope.interface.Invalid(_("Active Date is too old."))
            elif comment.date_active > datetime.now():
                raise zope.interface.Invalid(_("Active Date is in the future."))
    
    class WorkflowComment(object):
        note = u""
        date_active = None
    
    form_name = "Workflow"
    form_fields = form.Fields(IWorkflowComment)  # [form.FormField]
    actions = ()
    
    # !+ metal:use-macro="context/@@standard_macros/form" ?
    render = ViewPageTemplateFile("templates/viewlet.pt")
    
    def update(self, transition=None):
        self.adapters = {
            self.IWorkflowComment: self.WorkflowComment(),
        }
        wf = interfaces.IWorkflow(self.context) 
        
        if transition is not None:
            state_transition = wf.getTransitionById(transition)
            self.status = _(
                u"Confirmation required for workflow transition: '${title}'",
                mapping={"title": _(state_transition.title)})
        
        self.setupActions(transition)
        super(WorkflowActionViewlet, self).update()
        
        # after we transition we have different actions
        self.setupActions(transition)
        # only display the notes field to comment if there is an action
        # and a log table
        auditor = audit.getAuditor(self.context)
        if len(self.actions)==0: 
            self.form_fields = self.form_fields.omit("note", "date_active")
        elif auditor is None:
            self.form_fields = self.form_fields.omit("note", "date_active")
        else:
            # note widget
            note_widget = TextAreaWidget
            note_widget.height = 1
            self.form_fields["note"].custom_widget = note_widget
            # date_active widget
            self.form_fields["date_active"].custom_widget = TextDateTimeWidget
            # !+ for "past data entry" mode, the default "date_active" value
            # should be gotten from a "pseudo_current_date" service utility
        self.setUpWidgets()
        # update form status in case of any errors
        # !+ follow the "bungeni descriptor schema_invariants" way of doing 
        # this, i.e. displaying widget-specific errors next to each widget
        if self.errors:
            if self.status is None: 
                self.status = _("Errors")
            self.status = "%s: %s " % (self.status, 
                            " / ".join([ e.message #or e.__class__.__name__ 
                                         for e in self.errors ]))
    
    def setupActions(self, transition):
        self.wf = interfaces.IWorkflowInfo(self.context)
        if transition is None:
            transitions = self.wf.getManualTransitionIds()
        else:
            transitions = (transition,)
        self.actions = bindTransitions(
            self, transitions, None, interfaces.IWorkflow(self.context))
    
    def setUpWidgets(self, ignore_request=False):
        # setup widgets in data entry mode not bound to context
        self.widgets = form.setUpDataWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            ignore_request = ignore_request)
    
class WorkflowView(browser.BungeniBrowserView):
    
    # evoque
    template = z3evoque.PageViewTemplateFile("workflow.html#main")
    
    # zpt
    #template = ViewPageTemplateFile("templates/workflow.pt")
    
    _page_title = "Workflow"
    
    def update(self, transition=None):
        # set up viewlets; the view is rendered from viewlets for
        # historic reasons; this may be refactored anytime.
        self.history_viewlet = WorkflowHistoryViewlet(
            self.context, self.request, self, None)
        self.action_viewlet = WorkflowActionViewlet(
            self.context, self.request, self, None)
        # update viewlets
        self.history_viewlet.update()
        self.action_viewlet.update(transition=transition)
    
    def __call__(self):
        self.update()
        # NOTE: the success_handler for the parent form is at:
        #   bungeni.ui.forms.workflow.TransitionHandler
        # To get the form data:
        #   av = self.action_viewlet
        #   data = {}
        #   form.getWidgetsData(av.widgets, av.prefix, data)
        template = self.template()
        return template
        
class WorkflowChangeStateView(WorkflowView):
    """This gets called on selection of a transition from the menu i.e. NOT
    when clicking on one of the trasition buttons in the workflow form.
    """
    
    # evoque
    #ajax_template = z3evoque.PageViewTemplateFile("workflow.html#ajax")
    
    # zpt
    ajax_template = ViewPageTemplateFile("templates/workflow_ajax.pt")
    
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
        
        if transition and require_confirmation is False and method=="POST":
            actions = bindTransitions(
                self.action_viewlet, (transition,), None, 
                interfaces.IWorkflow(self.context))
            assert len(actions)==1
            # execute action
            # !+ should pass self.request.form as data? e.g. value is:
            # {u'next_url': u'...', u'transition': u'submit_response'}
            result = actions[0].success({})
        
        if headless is True:
            actions = get_actions("context_workflow", self.context, self.request)
            state_title = IWorkflowInfo(self.context).workflow().workflow.states[
                self.context.status].title
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

