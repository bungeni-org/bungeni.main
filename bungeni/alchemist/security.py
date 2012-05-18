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
    "GlobalPrincipalRoleMap",   # redefn -> alchemist.security.role
    "LocalPrincipalRoleMap",    # redefn -> alchemist.security.role
    #"GlobalRolePermissionMap",  # alias -> alchemist.security.permission
    #"LocalRolePermissionMap",   # alias -> alchemist.security.permission
    "AuthenticatedPrincipalFactory",    # alias -> alchemist.security.auth
]


from alchemist.security import schema

from alchemist.security.auth import AuthenticatedPrincipalFactory

from alchemist.security.schema import metadata

# !+RolePermissionMap
#from alchemist.security.permission import GlobalRolePermissionMap
#from alchemist.security.permission import LocalRolePermissionMap


import zope.security.proxy
import sqlalchemy.orm
import alchemist.security.role
from bungeni.utils import naming

class LocalPrincipalRoleMap(alchemist.security.role.LocalPrincipalRoleMap):
    
    def __init__(self, context):
        #self.context = context
        context = zope.security.proxy.removeSecurityProxy(context)
        # !+ASSUMPTION_SINGLE_COLUMN_PK(mr, may-2012)
        self.oid = sqlalchemy.orm.object_mapper(
            context).primary_key_from_instance(context)[0]
        self.object_type = naming.polymorphic_identity(type(context))
    
    def getRolesForPrincipal(self, principal_id):
        """Generator of (role, setting) grants to a principal.
        """
        #included_roles = set()
        for role, setting in super(LocalPrincipalRoleMap, self
                ).getRolesForPrincipal(principal_id):
            #included_roles.add(role)
            yield role, setting
        # !+PrincipalRoleMapDynamic(mr, may-2012) infer all local roles from 
        # context data:
        # - may have a simple logic, made explicit as a callable, per role, to 
        #   determine dynamically if a principal has the role on a context...
        # - included_roles, consider a hybrid system with existing db table
        #   and infer dynamically only for certain subset of roles ?!?
        # - add an "owner" attribute to group? Or, alternatively, move out 
        #   all "owner" attributes from other types to this db table??
        # - there should not be any need for global roles? ..., parliament, app.
        
    # !+getPrincipalsForRole


class GlobalPrincipalRoleMap(LocalPrincipalRoleMap):
    
    def __init__(self, context):
        #self.context = context
        self.object_type = None
        self.oid = None

