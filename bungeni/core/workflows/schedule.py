from ore.alchemist import Session
from zope.security.proxy import removeSecurityProxy
from bungeni.models import domain
from bungeni.ui.tagged import get_states
from ore.workflow.interfaces import IWorkflowInfo
from sqlalchemy.orm import eagerload, object_mapper
from bungeni.core import audit
import sqlalchemy as rdb
def handleSchedule( object, event):
    """ move scheduled items from to be scheduled state to schedule when draft agenda is finalised and vice versa"""
    session = Session()
    s = removeSecurityProxy(object)
    sitting = session.query(domain.GroupSitting).options(
                        eagerload('sitting_type'),
                        eagerload('item_schedule')).get(s.sitting_id)
    schedulings = map( removeSecurityProxy, sitting.item_schedule)
    
    if sitting.status == "draft_agenda":
        for sch in schedulings:
            if sch.item.type != "heading":
                wf_info = IWorkflowInfo(sch.item)
                transitions = wf_info.getManualTransitionIds()
                state = wf_info.state()
                wf = wf_info.workflow()
                next_state = get_states(sch.item.type, tagged=["tobescheduled"])
                for transition_id in transitions:
                    t = wf.getTransition(state.getState(), transition_id)
                    if t.destination in next_state:
                        wf_info.fireTransition(transition_id)
                        break
                        
    elif sitting.status == "published_agenda":
        for sch in schedulings:
            if sch.item.type != "heading":
                wf_info = IWorkflowInfo(sch.item)
                transitions = wf_info.getManualTransitionIds()
                state = wf_info.state()
                wf = wf_info.workflow()
                next_state = get_states(sch.item.type, tagged=["scheduled"])
                for transition_id in transitions:
                    t = wf.getTransition(state.getState(), transition_id)
                    if t.destination in next_state:
                        wf_info.fireTransition(transition_id)
                        break
