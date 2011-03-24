"""

# !+WHAT(mr, mar-2011) what was the idea behind this?

"""

from bungeni.core.workflow import interfaces as iworkflow
from bungeni.core.workflow import states as workflow

from bungeni.core.i18n import _

def states():
    return [
        workflow.State("new", _(u"visible"), [], []),
        workflow.State("pending", _(u"pending"), [], []),
        workflow.State("scheduled", _(u"scheduled"), [], []),
    ]

def transitions():
    return [
        workflow.Transition(
            transition_id="create",
            title="Create",
            trigger=iworkflow.AUTOMATIC,
            source=None,
            destination="new"
        ),
        workflow.Transition(
            transition_id="submit-clerk",
            title=_(u"Submit to Clerk"),
            source="new",
            destination="pending"
        ),
        workflow.Transition(
            transition_id="Schedule",
            title=_(u"Schedule"),
            source="pending",
            destination="scheduled"
        )
    ]

class SimpleWorkflow(workflow.Workflow):
    def __init__(self):
        super(SimpleWorkflow, self).__init__(states(), transitions())

simple_workflow = SimpleWorkflow()


if __name__ == "__main__":

    from bungeni.core.workflow import dot
    print dot.toDot(simple_workflow)
    
