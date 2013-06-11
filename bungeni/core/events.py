# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

""" Event handlers for various changes to objects

note that other events are handled in workflows
audit and files!

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.events")


import datetime

from zope.security.proxy import removeSecurityProxy
from zope.lifecycleevent import (
    IObjectCreatedEvent,
    IObjectModifiedEvent, 
    IObjectRemovedEvent,
)

from bungeni.alchemist import Session
from bungeni.core.workflows.utils import (
    get_group_privilege_extent_context,
    set_role,
    unset_role
)
from bungeni.models import domain
from bungeni.models.interfaces import (
    IGroupMember, 
    IMemberRole,
    IBungeniParliamentaryContent,
)
from bungeni.utils import register


@register.handler(adapts=(IGroupMember, IObjectModifiedEvent))
def group_member_modified(ob, event):
    """when a group member gets inactivated (end date set)
    all his titles get deactivated for the same date (if they
    do not have an end date already
    """
    if ob.end_date:
        session = Session()
        trusted = removeSecurityProxy(ob)
        member_id = trusted.member_id
        titles = session.query(domain.MemberTitle).filter(
            domain.MemberTitle.member_id == member_id)
        for title in titles.all():
            if title.end_date == None:
                title.end_date = ob.end_date


@register.handler(adapts=(IBungeniParliamentaryContent, IObjectModifiedEvent))
def timestamp(ob, event):
    """Set the timestamp for the item.
    """
    # !+ADD_SUB_OBJECT_MODIFIES_HEAD(mr, oct-2012) adding an event/attachment 
    # causes an ObjectMofiedEvent on head doc to be caught here... thus
    # updating its timestamp. Is this the desired behaviour?
    removeSecurityProxy(ob).timestamp = datetime.datetime.now()


# !+ these should NOT be event-driven !
@register.handler(adapts=(IMemberRole, IObjectCreatedEvent))
def member_role_added(member_role, event):
    if member_role.is_global:
        set_role(member_role.role_id, member_role.member.user.login, 
            get_group_privilege_extent_context(member_role.member.group))

@register.handler(adapts=(IMemberRole, IObjectRemovedEvent))
def member_role_deleted(member_role, event):
    if member_role.is_global:
        unset_role(member_role.role_id, member_role.member.user.login, 
            get_group_privilege_extent_context(member_role.member.group))

