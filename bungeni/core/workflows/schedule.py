from bungeni.alchemist import Session
from zope.security.proxy import removeSecurityProxy
from bungeni.models import domain
from bungeni.ui.tagged import get_states
from bungeni.core.workflow.interfaces import IWorkflowController
from sqlalchemy.orm import eagerload

def handleSchedule(object, event):
    """ move scheduled items from to be scheduled state to schedule when draft 
    agenda is finalised and vice versa
    """
    session = Session()
    s = removeSecurityProxy(object)
    sitting = session.query(domain.GroupSitting
        ).options(eagerload("group_sitting_type"), eagerload("item_schedule")
        ).get(s.group_sitting_id)
    schedulings = map(removeSecurityProxy, sitting.item_schedule)
    if sitting.status == "draft_agenda":
        for sch in schedulings:
            if sch.item.type != "heading":
                wfc = IWorkflowController(sch.item)
                transitions = wfc.getSystemTransitionIds()
                state = wfc.state()
                wf = wfc.workflow()
                next_state = get_states(sch.item.type, tagged=["tobescheduled"])
                for transition_id in transitions:
                    t = wf.get_transition(state.getState(), transition_id)
                    if t.destination in next_state:
                        #TODO find out why firetransition fails for reschedule even 
                        #when the user has requisite permissions
                        wfc.fireTransition(transition_id, check_security=False)
                        break
    elif sitting.status == "published_agenda":
        for sch in schedulings:
            if sch.item.type != "heading":
                wfc = IWorkflowController(sch.item)
                transitions = wfc.getSystemTransitionIds()
                state = wfc.state()
                wf = wfc.workflow()
                next_state = get_states(sch.item.type, tagged=["scheduled"])
                for transition_id in transitions:
                    t = wf.get_transition(state.getState(), transition_id)
                    if t.destination in next_state:
                        wfc.fireTransition(transition_id, check_security=False)
                        break

