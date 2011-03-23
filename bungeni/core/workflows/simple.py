"""

# !+WHAT(mr, mae-2011) what was the idea behind this?

"""

from ore.workflow import interfaces as iworkflow
from ore.workflow import workflow

from bungeni.core.i18n import _

class states:
    new = _(u"visible")
    pending = _(u"pending")
    scheduled = _(u"scheduled")

def create_simple_workflow( ):
    transitions = []
    add = transitions.append
    
    add( workflow.Transition(
        transition_id = 'create',
        title='Create',
        trigger = iworkflow.AUTOMATIC,
        source = None,
        destination = states.new
        ) )

    add( workflow.Transition(
        transition_id = 'submit-clerk',
        title=_(u'Submit to Clerk'),
        source = states.new,
        destination = states.pending
        ) )

    add( workflow.Transition(
        transition_id = 'Schedule',
        title=_(u'Schedule'),
        source = states.pending,
        destination = states.scheduled
        ) )

    return transitions

class SimpleWorkflow( workflow.Workflow ):

    def __init__( self ):
        super( SimpleWorkflow, self).__init__( create_simple_workflow() )

SimpleWorkflowAdapter = workflow.AdaptedWorkflow( SimpleWorkflow() )

if __name__ == '__main__':
    wf = SimpleWorkflow()
    print wf.toDot()


    
