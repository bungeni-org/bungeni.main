# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Model Roles

$Id$
"""
log = __import__("logging").getLogger("bungeni.models.roles")

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
ROLES_DIRECTLY_DEFINED_ON_OBJECTS = [
    "bungeni.Drafter", # all types, editorial owner, all types
    "bungeni.Owner", # legal owner, parliamentary documents
    "bungeni.Signatory",
]

# Default list of roles that are guaranteed to always be there in Bungeni 
SYSTEM_ROLES = [
    "bungeni.Admin", # parliament, has all privileges
    "bungeni.Authenticated", # authenticated user
    "bungeni.Anonymous", # unauthenticated user, anonymous
] + ROLES_DIRECTLY_DEFINED_ON_OBJECTS

# The IDs of all custom roles, populated in load_custom_roles()
CUSTOM_ROLES = []


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
def load_custom_roles():
    file_path = capi.get_path_for("roles.xml")
    roles_config = capi.schema.validate_file_rng("roles", file_path)
    gsm = zope.component.getGlobalSiteManager()
    custom_roles = []
    for role_config in roles_config.iterchildren(tag="role"):
        role_id = "bungeni.%s" % (role_config.get("id"))
        custom_roles.append(role_id)
        role = Role(role_id, role_config.get("title"))
        role_annt = interfaces.ISubRoleAnnotations(role)
        gsm.registerUtility(role, IRole, role_id)
        for sub_role_config in role_config.iterchildren(tag="subrole"):
            sub_role_id = "bungeni.%s" % (sub_role_config.get("id"))
            custom_roles.append(sub_role_id)
            sub_role = Role(sub_role_id, sub_role_config.get("title"))
            sub_role_annt = interfaces.ISubRoleAnnotations(sub_role)
            sub_role_annt.is_sub_role = True
            sub_role_annt.parent = role
            role_annt.sub_roles.append(sub_role_id)
            gsm.registerUtility(sub_role, IRole, sub_role_id)
    CUSTOM_ROLES[:] = sorted(custom_roles)


''' !+
from zope.component import getUtilitiesFor
from zope.configuration import xmlconfig
def get_defined_roles():
    zcml_slug = """<configure xmlns="http://namespaces.zope.org/zope">
        <include package="zope.component" file="meta.zcml" />
        <includeOverrides package="repoze.whooze" file="overrides.zcml" />
        <include package="zope.app.security" />
        <include package="bungeni.server" />
        <include package="bungeni" file="security.zcml"/>
    </configure>
    """
    xmlconfig.string(zcml_slug)
    system_roles = ["zope.Manager"]
    return sorted([ name for name, role in getUtilitiesFor(IRole)
        if name not in system_roles ])
'''

