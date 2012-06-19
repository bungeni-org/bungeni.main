# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Model Roles

$Id$
"""
log = __import__("logging").getLogger("bungeni.models.roles")

import zope.annotation
import zope.component
import zope.interface
from zope.securitypolicy.interfaces import IRole
from zope.securitypolicy.role import Role
from bungeni.models import interfaces
from bungeni.utils import register


@register.adapter(adapts=(IRole,))
@zope.annotation.factory
class SubRoleAnnotations(object):
    zope.interface.implements(interfaces.ISubRoleAnnotations)
    zope.component.adapts(IRole)  # zope.annotation.factory wants this here
    def __init__(self):
        self.sub_roles = []
        self.is_sub_role = False


def sub_role_configure(context, id, title, description, role):
    role_annt = interfaces.ISubRoleAnnotations(
        zope.component.getUtility(IRole, role))
    role_annt.sub_roles.append(id)
    sub_role = Role(id, title, description)
    sub_role_annt = interfaces.ISubRoleAnnotations(sub_role)
    sub_role_annt.is_sub_role = True
    gsm = zope.component.getGlobalSiteManager()
    gsm.registerUtility(sub_role, IRole, id)
    
    
def sub_role_handler(context, **kw):
    context.action(discriminator=('RegisterSubRoles', kw["id"], kw["role"]),
                   callable=sub_role_configure,
                   args = (context, kw["id"], kw["title"], getattr(kw, "description", None), kw["role"])
                   )
