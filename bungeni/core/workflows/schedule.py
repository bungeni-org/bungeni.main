from bungeni.alchemist import Session
from zope.security.proxy import removeSecurityProxy
from bungeni.models import domain
from bungeni.core.workflow.interfaces import IWorkflowController
from sqlalchemy.orm import eagerload

from bungeni.utils import register
from bungeni.models.interfaces import ISitting
from zope.lifecycleevent import IObjectModifiedEvent

@register.handler(adapts=(ISitting, IObjectModifiedEvent))
def handle_schedule(object, event):
    """ move scheduled items from to be scheduled state to schedule when draft 
    agenda is finalised and vice versa
    """
    session = Session()
    s = removeSecurityProxy(object)
    sitting = session.query(domain.Sitting
        ).options(eagerload("item_schedule")
        ).get(s.sitting_id)
    schedulings = map(removeSecurityProxy, sitting.item_schedule)
    if sitting.status == "draft_agenda":
        for sch in schedulings:
            if sch.item.type != "heading":
                wfc = IWorkflowController(sch.item)
                wf = wfc.workflow
                next_state = wf.get_state_ids(tagged=["tobescheduled"])
                for transition_id in wfc.getSystemTransitionIds():
                    t = wf.get_transition(transition_id)
                    if t.destination in next_state:
                        #TODO find out why firetransition fails for reschedule even 
                        #when the user has requisite permissions
                        wfc.fireTransition(transition_id, check_security=False)
                        break
    elif sitting.status == "published_agenda":
        for sch in schedulings:
            if sch.item.type != "heading":
                wfc = IWorkflowController(sch.item)
                wf = wfc.workflow
                next_state = wf.get_state_ids(tagged=["scheduled"])
                for transition_id in wfc.getSystemTransitionIds():
                    t = wf.get_transition(transition_id)
                    if t.destination in next_state:
                        wfc.fireTransition(transition_id, check_security=False)
                        break

