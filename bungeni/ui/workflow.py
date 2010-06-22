
from zope.formlib import form
from zope.viewlet import viewlet
import zope.interface
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary
from zope.security.proxy import removeSecurityProxy
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.publisher.browser import BrowserView
from zope.app.schema.vocabulary import IVocabularyFactory
from zope.app.form.browser.textwidgets import TextAreaWidget
from zc.table import column

from sqlalchemy import orm
import sqlalchemy as rdb

from ore.workflow import interfaces
from ore.alchemist.interfaces import IAlchemistContainer
from ore.alchemist.interfaces import IAlchemistContent
from ore.alchemist import Session

from ore.workflow.interfaces import IWorkflowInfo
from bungeni.ui.forms.workflow import bindTransitions
from bungeni.ui.i18n import _
from bungeni.core import audit
from bungeni.ui.forms.common import BaseForm
from bungeni.ui.table import TableFormatter
from bungeni.ui.menu import get_actions
from bungeni.ui.utils import misc

from i18n import _

class WorkflowVocabulary(object):
    zope.interface.implements(IVocabularyFactory)

    def __call__(self, context):
        if IAlchemistContent.providedBy(context):
            ctx = context
        elif  IAlchemistContainer.providedBy(context):
            domain_model = removeSecurityProxy( context.domain_model )
            ctx = domain_model()
        wf = interfaces.IWorkflow(ctx)
        items=[]
        for state in wf.workflow.states.keys():
            items.append(SimpleTerm(wf.workflow.states[state].id,
                        wf.workflow.states[state].id,
                        _(wf.workflow.states[state].title)))
        return SimpleVocabulary(items)

workflow_vocabulary_factory = WorkflowVocabulary()


class WorkflowHistoryViewlet(viewlet.ViewletBase):
    """Implements the workflowHistoryviewlet this viewlet shows the
    current workflow state  and the workflow-history."""

    form_name = _(u"Workflow history")
    formatter_factory = TableFormatter
    
    def __init__( self,  context, request, view, manager ):
        self.context = context
        self.request = request
        self.__parent__= view
        self.manager = manager
        self.wf_status = u'new'
        self.has_status = False
        # table to display the workflow history
        self.columns = [
            column.GetterColumn( title=_(u"date"), getter=lambda i,f: i['date'].strftime('%Y-%m-%d %H:%M') ),
            column.GetterColumn( title=_(u"user"), getter=lambda i,f:i['user_id'] ),
            column.GetterColumn( title=_(u"description"), getter=lambda i,f:i['description'] ),
            ]
        
    def update(self):
        has_wfstate = False
        try:
            wf_state = interfaces.IWorkflowState( removeSecurityProxy(self.context) ).getState()
            has_wfstate = True
        except:
            wf_state = u'undefined'
        if wf_state is None:
           wf_state =u'undefined'
           has_wfstate = False
        self.wf_status = wf_state
        self.has_status = has_wfstate
        self.entries = self.getFeedEntries()
        
    def render( self ):
        columns = self.columns
        formatter = self.formatter_factory(
            self.context,
            self.request,
            self.entries,
            prefix="results",
            visible_column_names = [c.name for c in columns],
            columns = columns)
        formatter.cssClasses['table'] = 'listing',
        formatter.updateBatching()
        return formatter()

    @property
    def _log_table( self ):
        auditor = audit.getAuditor( self.context )
        if auditor is not None:
            return auditor.change_table

    def getFeedEntries( self ):
        instance = removeSecurityProxy( self.context )
        mapper = orm.object_mapper( instance )

        table = self._log_table
        if table is None:
            return ()
        
        query = table.select().where(
            rdb.and_(table.c.content_id == rdb.bindparam('content_id'),
            rdb.and_(table.c.action == 'workflow') )
            ).order_by(table.c.change_id.desc())

        content_id = mapper.primary_key_from_instance( instance )[0] 
        content_changes = query.execute( content_id = content_id )
        return map( dict, content_changes)


    
class WorkflowComment(object):
    note = u""
    
class WorkflowActionViewlet(BaseForm, viewlet.ViewletBase):
    """Display workflow status and actions."""

    class IWorkflowComment(zope.interface.Interface):
        note = zope.schema.Text(
            title=_("Comment on workflow change"), required=True )

    form_name = "Workflow"
    form_fields = form.Fields(IWorkflowComment)
    actions = ()
    
    render = ViewPageTemplateFile ('templates/viewlet.pt')
    
    def update(self, transition=None):
        self.adapters = {
            self.IWorkflowComment: WorkflowComment(),
            }

        wf = interfaces.IWorkflow(self.context) 
        
        if transition is not None:
            state_transition = wf.getTransitionById(transition)
            self.status = _(
                u"Confirmation required for workflow transition: '${title}'",
                mapping={'title': _(state_transition.title)})

        self.setupActions(transition)
        super(WorkflowActionViewlet, self).update()

        # after we transition we have different actions
        self.setupActions(transition)
        # only display the notes field to comment if there is an action
        # and a log table
        auditor = audit.getAuditor( self.context )
        if len(self.actions) == 0: 
            self.form_fields = self.form_fields.omit('note')
        elif auditor is None:
            self.form_fields = self.form_fields.omit('note')
        else:
            note_widget = TextAreaWidget
            note_widget.height = 1
            self.form_fields['note'].custom_widget = note_widget
                        
        self.setUpWidgets()

    def setupActions(self, transition):
        self.wf = interfaces.IWorkflowInfo( self.context )

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
            ignore_request = ignore_request )

class WorkflowView(BrowserView):
    template = ViewPageTemplateFile('templates/workflow.pt')

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

    def get_wf_state(self):
        # return human readable, and localized, workflow title
        return _(misc.get_wf_state(removeSecurityProxy(self.context)))
    
    def __call__(self):
        #session = Session()
        self.update()
        template = self.template()
        #session.close()
        return template
        
class WorkflowChangeStateView(WorkflowView):
    ajax_template = ViewPageTemplateFile('templates/workflow_ajax.pt')
    
    def __call__(self, headless=False, transition=None):
        method = self.request['REQUEST_METHOD']
        if transition:
            wf = interfaces.IWorkflow(self.context) 
            state_transition = wf.getTransitionById(transition)
            require_confirmation = getattr(
                state_transition, "require_confirmation", False)
            self.update(transition)
        else:
            self.update()
            
        if transition and require_confirmation is False and method == 'POST':
            actions = bindTransitions(
                self.action_viewlet, (transition,), None, 
                interfaces.IWorkflow(self.context))
            assert len(actions) == 1

            # execute action
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

