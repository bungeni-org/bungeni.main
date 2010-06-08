from zope import component
from zope.formlib import form
from zope.security.proxy import removeSecurityProxy
from bungeni.core.interfaces import IVersioned
from bungeni.ui.i18n import _
from ore.workflow import interfaces
from alchemist.ui.core import handle_edit_action

def createVersion(context, comment=""):
    """Create a new version of an object and return it."""
    instance = removeSecurityProxy(context)

    versions = IVersioned(instance)
    if not comment:
       comment =''
    versions.create(u'New version created upon edit.' + comment)

def bindTransitions( form_instance, transitions, wf_name=None, wf=None):
    """ bind workflow transitions into formlib actions """

    if wf_name:
        success_factory = lambda tid: TransitionHandler( tid, wf_name )
    else:
        success_factory = TransitionHandler

    actions = []
    for tid in transitions:
        d = {}
        if success_factory:
            d['success'] = success_factory( tid )
        if wf is not None:
            title = _(unicode(wf.getTransitionById( tid ).title))
            action = form.Action(title, **d)
        else:
            action = form.Action( tid, **d)
        action.form = form_instance
        action.__name__ = "%s.%s"%(form_instance.prefix, action.__name__)
        
        actions.append( action )
    return actions
    
class TransitionHandler( object ):
    """Workflow transition 2 formlib action bindings."""

    def __init__( self, transition_id, wf_name=None):
        self.transition_id = transition_id
        self.wf_name = wf_name

    def __call__( self, form, action, data ):
        """Save data, make version and fire transition.

        Redirects to the ``next_url`` location.
        """
        
        context = getattr( form.context, '_object', form.context )
        notes = None
        if self.wf_name:
            info = component.getAdapter(
                context, interfaces.IWorkflowInfo, self.wf_name)
        else:
            info = interfaces.IWorkflowInfo( context ) 
        if data.has_key('note'):
            notes = data['note']
        else:
            notes=''
        result = handle_edit_action( form, action, data )
        if form.errors: 
            return result
        else:
            info.fireTransition( self.transition_id, notes )
            return form.request.response.redirect(form.next_url)
