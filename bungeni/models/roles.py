# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Model Roles

$Id$
"""
log = __import__("logging").getLogger("bungeni.models.roles")
import os

import zope.annotation
from zope.component import adapts
from zope import interface
from zope.securitypolicy.interfaces import IRole
from zope.securitypolicy.role import Role
from bungeni.models import interfaces
from bungeni.capi import capi

# Roles can be divided into two, roles that a principal gets by virtue
# of his membership to a group and roles that are defined on objects
# eg. bungeni.Owner and bungeni.Signatory
# These are defined here for use in the workspace, notifications
# or any other code that needs to compute the principals/permissions on objects
ROLES_DIRECTLY_DEFINED_ON_OBJECTS = ["bungeni.Owner", "bungeni.Signatory"]


@zope.annotation.factory
class SubRoleAnnotations(object):
    interface.implements(interfaces.ISubRoleAnnotations)
    adapts(IRole)

    def __init__(self):
        self.sub_roles = []
        self.is_sub_role = False
        self.parent = None


class IDummyRoleConfig(interface.Interface):
    """Dummy interface"""


@capi.bungeni_custom_errors
def load_roles():
    path = capi.get_path_for("sys", "acl")
    file_path = os.path.join(path, "roles.xml")
    roles_config = capi.schema.validate_file_rng("roles", file_path)
    gsm = zope.component.getGlobalSiteManager()
    for role_config in roles_config.iterchildren(tag="role"):
        role = Role("bungeni."+role_config.get("id"), role_config.get("title"))
        role_annt = interfaces.ISubRoleAnnotations(role)
        gsm.registerUtility(role, IRole, "bungeni."+role_config.get("id"))
        for sub_role_config in role_config.iterchildren(tag="subrole"):
            sub_role = Role("bungeni."+sub_role_config.get("id"),
                sub_role_config.get("title"))
            sub_role_annt = interfaces.ISubRoleAnnotations(sub_role)
            sub_role_annt.is_sub_role = True
            sub_role_annt.parent = role
            role_annt.sub_roles.append("bungeni."+sub_role_config.get("id"))
            gsm.registerUtility(sub_role, IRole,
                "bungeni."+sub_role_config.get("id"))
    return None
