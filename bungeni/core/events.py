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

from bungeni.alchemist import Session
from bungeni.models import domain
from bungeni.core import audit
from bungeni.core.workflows.utils import (
    assign_signatory_role, get_owner_login_pi
)

def signatory_added(ob, event): 
    session = Session()
    ob = removeSecurityProxy(ob)
    if ob.user:
        title=  "%s %s %s" % (ob.user.titles,
                ob.user.first_name,
                ob.user.last_name)
    else:
        title = ""
    event.cls =  ob.__class__.__name__
    event.description = u" %s: %s added" % (
            ob.__class__.__name__ , 
            title)
    if ob.item:
        audit.objectContained( ob.item, event)

    
def signatory_modified(ob, event):
    session = Session()
    ob = removeSecurityProxy(ob)
    if ob.user:
        title=  "%s %s %s" % (ob.user.titles,
                ob.user.first_name,
                ob.user.last_name)
    else:
        title = ""
    event.cls =  ob.__class__.__name__
    event.description = u" %s: %s modified" % (
            ob.__class__.__name__ , 
            title)
    if ob.item:
        audit.objectContained( ob.item, event)

def signatory_deleted(ob, event):
    """Clear signatory role for a deleted signatory
    """
    session = Session()
    ob = removeSecurityProxy(ob)
    if ob.user:
        owner_login = get_owner_login_pi(ob)
        assign_signatory_role(ob.item, owner_login, unset=True)
    else:
        log.warning("Signatory object %s has no user set."
            " Skipping unsetting of role", ob.__str__()
        )

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
                
def timestamp(object, event):
        object.timestamp = datetime.datetime.now()
