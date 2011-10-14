# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Model Roles

$Id: __init__.py 8688 2011-10-14 14:22:07Z mario.ruggier $
"""
log = __import__("logging").getLogger("bungeni.models.roles")

from zope.securitypolicy.interfaces import IRole 
from zope.securitypolicy.role import Role 
from zope.component import getGlobalSiteManager
from zope import interface    
from bungeni.models import interfaces
from zope.component import getUtility
from bungeni.utils import register


@register.adapter(adapts=(IRole,))
class SubRoleAnnotations(object):
    interface.implements(interfaces.ISubRoleAnnotations)
    def __init__(self):
        self.sub_roles = []
        self.is_sub_role = False


def sub_role_configure(context, id, title, description, role):
    role_annt = interfaces.ISubRoleAnnotations(getUtility(IRole, role))
    role_annt.sub_roles.append(id)
    sub_role = Role(id, title, description)
    sub_role_annt = interfaces.ISubRoleAnnotations(sub_role)
    sub_role_annt.is_sub_role = True
    gsm = getGlobalSiteManager()
    gsm.registerUtility(sub_role, IRole, id)
    
    
def sub_role_handler(context, **kw):
    context.action(discriminator=('RegisterSubRoles', kw["id"], kw["role"]),
                   callable=sub_role_configure,
                   args = (context, kw["id"], kw["title"], getattr(kw, "description", None), kw["role"])
                   )
