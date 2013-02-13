
from zope import component
from zope.lifecycleevent.interfaces import IObjectCreatedEvent

import domain, utils

@component.adapter(domain.AgendaItem, IObjectCreatedEvent)
def set_parliament_id(context, event):
    if context.parliament_id is None:
        chamber = utils.get_group_chamber(context.group)
        context.parliament_id = chamber.group_id

