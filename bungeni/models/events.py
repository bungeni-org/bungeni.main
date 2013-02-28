# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Event handlers

Handlers for various domain objects after creation/change

$Id$
"""
log = __import__("logging").getLogger("bungeni.models.domain")

from zope.security.proxy import removeSecurityProxy
from zope.lifecycleevent.interfaces import IObjectCreatedEvent, \
    IObjectModifiedEvent
from sqlalchemy import sql, orm
import domain, utils, interfaces
from bungeni.core.interfaces import ISchedulingContext
from bungeni.utils import register

@register.handler(adapts=(interfaces.IAgendaItem, IObjectCreatedEvent))
@register.handler(adapts=(interfaces.ISession, IObjectCreatedEvent))
def set_parliament_id(context, event):
    """Set parliament_id when objects are added outside of parliament context
    """
    if context.parliament_id is None:
        if context.parliament_id is None:
            chamber = utils.get_chamber_for_group(context.group)
            context.parliament_id = chamber.group_id


@register.handler(adapts=(interfaces.ISitting, IObjectCreatedEvent))
@register.handler(adapts=(interfaces.ISitting, IObjectModifiedEvent))
def set_sitting_parent_ids(ob, event):
    """We add the group ID/sesssion id if adding a sitting in contexts
    not bound to groups in traversal hierarchy
    """
    scheduling_context = ISchedulingContext(ob.__parent__, None)
    if ob.group_id is None:
        if scheduling_context is not None:
            ob.group_id = removeSecurityProxy(scheduling_context).group_id
    if ob.session_id is None or IObjectModifiedEvent.providedBy(event):
        if scheduling_context is not None:
            group = scheduling_context.get_group()
            if interfaces.IParliament.providedBy(group):
                container = removeSecurityProxy(group).sessions
            else:
                return
        else:
            try:
                container = ob.group.sessions
            except AttributeError:
                return
        try:
            session_id = container._query.filter(
                sql.and_(
                    domain.Session.start_date < ob.start_date,
                    domain.Session.end_date > ob.end_date
                )
            ).one().session_id
            ob.session_id = session_id
        except (orm.exc.NoResultFound, orm.exc.MultipleResultsFound):
            log.error("Could not determine session for sitting %s", ob)

