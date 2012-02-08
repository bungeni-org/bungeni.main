# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist security - [
    alchemist.security
    alchemist.security.auth
    alchemist.security.schema
    alchemist.security.role
    alchemist.security.permission
]

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


# used directly in bungeni
__all__ = [
    "schema",                   # alias -> alchemist.security
    "metadata",                 # alias -> alchemist.security.schema
    "GlobalPrincipalRoleMap",   # alias -> alchemist.security.role
    "LocalPrincipalRoleMap",    # alias -> alchemist.security.role
    "GlobalRolePermissionMap",  # alias -> alchemist.security.permission
    "LocalRolePermissionMap",   # alias -> alchemist.security.permission
    "AuthenticatedPrincipalFactory",    # alias -> alchemist.security.auth
]


from alchemist.security import schema

from alchemist.security.auth import AuthenticatedPrincipalFactory

from alchemist.security.schema import metadata

from alchemist.security.role import GlobalPrincipalRoleMap
from alchemist.security.role import LocalPrincipalRoleMap

from alchemist.security.permission import GlobalRolePermissionMap
from alchemist.security.permission import LocalRolePermissionMap

