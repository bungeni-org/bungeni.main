from zope import component
from zope.lifecycleevent.interfaces import IObjectCreatedEvent

import domain, utils

@component.adapter(domain.ItemSchedule, IObjectCreatedEvent)
def create_discussion_for_item_scheduling(context, event):
    context.discussion = domain.ItemScheduleDiscussion()
    
@component.adapter(domain.AgendaItem, IObjectCreatedEvent)
def set_parliament_id(context, event):
    parliament =  utils.get_parliament_for_group_id(context.group_id)
    context.parliament_id = parliament.group_id
