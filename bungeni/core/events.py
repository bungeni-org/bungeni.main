# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

""" Event handlers for various changes to objects

note that other events are handled in workflows
audit and files!

$Id$
"""

import datetime

from zope.security.proxy import removeSecurityProxy

log = __import__("logging").getLogger("bungeni.core.events")

from zope.lifecycleevent import IObjectModifiedEvent, IObjectCreatedEvent

from bungeni.alchemist import Session
from bungeni.models import domain
from bungeni.models.interfaces import IBungeniGroup, \
    IBungeniGroupMembership, IBungeniParliamentaryContent
from bungeni.utils import register


@register.handler(adapts=(IBungeniGroupMembership, IObjectModifiedEvent))
def group_member_modified(ob, event):
    """when a group member gets inactivated (end date set)
    all his titles get deactivated for the same date (if they
    do not have an end date already
    """
    if ob.end_date:
        session = Session()
        trusted = removeSecurityProxy(ob)
        membership_id = trusted.membership_id
        titles = session.query(domain.MemberTitle).filter(
            domain.MemberTitle.membership_id == membership_id)
        for title in titles.all():
            if title.end_date == None:
                title.end_date = ob.end_date


# !+GROUP_PRINCIPAL_ID(ah, sep-2011) event to set group principal id
@register.handler(adapts=(IBungeniGroup, IObjectCreatedEvent))
def group_created(ob, event):
    """When a group is added, the value in group_principal_id is computed
    out of the group type and group id. This was a computed property in orm.py
    but has been moved here now - so it gets cached in the groups table.
    """
    assert ob.group_principal_id is None, \
        "group_principal_id [%s] is already set for group %s" % (
            ob.group_principal_id, ob.group_id)
    ob.group_principal_id = "group.%s.%s" % (ob.type, ob.group_id)
    log.debug("Setting group_principal_id for group %s to %s", 
        ob.group_id, ob.group_principal_id)


@register.handler(adapts=(IBungeniParliamentaryContent, IObjectModifiedEvent))
def timestamp(ob, event):
    """Set the timestamp for the item.
    """
    removeSecurityProxy(ob).timestamp = datetime.datetime.now()


