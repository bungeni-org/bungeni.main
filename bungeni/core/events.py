#
# note that other events are handled in workflows
# audit and files!

import datetime

from zope.security.proxy import removeSecurityProxy

from ore.alchemist import Session
from bungeni.models import domain
from bungeni.core import audit



def consignatory_added(ob, event): 
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

    
def consignatory_modified(ob, event):
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

def group_member_modified(ob, event):
    """when a group member gets inactivated (end date set)
    all his titles get deactivated for the same date (if they
    do not have an end date already
    """
    if ob.end_date:
        session = Session()
        trusted = removeSecurityProxy(ob)
        membership_id = trusted.membership_id
        titles = session.query(domain.MemberRoleTitle).filter(
            domain.MemberRoleTitle.membership_id == membership_id)
        for title in titles.all():
            if title.end_date == None:
                title.end_date = ob.end_date
        



            
