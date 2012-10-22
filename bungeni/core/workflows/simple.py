"""

    !+WHAT(mr, mar-2011) what was the idea behind this?

"""

from bungeni.core.workflow import interfaces as iworkflow
from bungeni.core.workflow import states as workflow

from bungeni.core.i18n import _

def states():
    return [
        workflow.State("new", _(u"visible"), None, [], [], []),
        workflow.State("pending", _(u"pending"), None, [], [], []),
        workflow.State("scheduled", _(u"scheduled"), None, [], [], []),
    ]

def transitions():
    return [
        workflow.Transition(
            title="Create",
            source=None,
            destination="new",
            trigger=iworkflow.AUTOMATIC,
        ),
        workflow.Transition(
            title=_(u"Submit to Clerk"),
            source="new",
            destination="pending"
        ),
        workflow.Transition(
            title=_(u"Schedule"),
            source="pending",
            destination="scheduled"
        )
    ]

class SimpleWorkflow(workflow.Workflow):
    def __init__(self):
        super(SimpleWorkflow, self).__init__("simple", states(), transitions())

simple_workflow = SimpleWorkflow()

import bungeni.models.interfaces
from bungeni.core.workflows.adapters import provideAdapterWorkflow
provideAdapterWorkflow(simple_workflow, 
    bungeni.models.interfaces.IBungeniContent)

if __name__ == "__main__":

    from bungeni.core.workflow import dot
    print dot.toDot(simple_workflow)
    
