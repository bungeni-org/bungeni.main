# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist security

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


# used directly in bungeni
__all__ = [
    "schema",                   # redefn -> alchemist.security
    "metadata",                 # redefn -> alchemist.security.schema
    "GlobalPrincipalRoleMap",   # redefn -> alchemist.security.role
    "LocalPrincipalRoleMap",    # redefn -> alchemist.security.role
    #"GlobalRolePermissionMap",  # alias -> alchemist.security.permission
    #"LocalRolePermissionMap",   # alias -> alchemist.security.permission
    "AuthenticatedPrincipalFactory", # redefn -> alchemist.security.auth
]


# !+RolePermissionMap
#from alchemist.security.permission import GlobalRolePermissionMap
#from alchemist.security.permission import LocalRolePermissionMap

from zope import interface
from zope.securitypolicy.interfaces import IPrincipalRoleMap 
from zope.securitypolicy.interfaces import Allow, Deny, Unset
from zope.app.authentication import interfaces, principalfolder
import zope.security.proxy
import sqlalchemy as rdb
import bungeni.alchemist
from bungeni.utils import naming

# role

BooleanAsSetting = {True: Allow, False: Deny, None: Unset}

class LocalPrincipalRoleMap(object):
    interface.implements(IPrincipalRoleMap)
    
    def __init__(self, context):
        #self.context = context
        context = zope.security.proxy.removeSecurityProxy(context)
        # !+ASSUMPTION_SINGLE_COLUMN_PK(mr, may-2012)
        self.oid = rdb.orm.object_mapper(
            context).primary_key_from_instance(context)[0]
        self.object_type = naming.polymorphic_identity(type(context))
    
    def getPrincipalsForRole(self, role_id):
        """Get the principals that have been granted a role.
        
        Return the list of (principal id, setting) who have been assigned or
        removed from a role.
        
        If no principals have been assigned this role,
        then the empty list is returned.
        """
        prm = schema.principal_role_map
        s = rdb.select(
                [prm.c.principal_id, prm.c.setting],
                rdb.and_(
                    prm.c.role_id == role_id,
                    prm.c.object_type == self.object_type,
                    prm.c.object_id == self.oid))
        for o in s.execute():
            yield o[0], BooleanAsSetting[o[1]]
    
    def getRolesForPrincipal(self, principal_id):
        """Generator of (role, setting) grants to a principal.
        """
        #included_roles = set()
        prm = schema.principal_role_map
        s = rdb.select(
                [prm.c.role_id, prm.c.setting],
                rdb.and_(
                    prm.c.principal_id == principal_id,
                    prm.c.object_type == self.object_type,
                    prm.c.object_id == self.oid))
        for o in s.execute():
            #included_roles.add(role)
            #yield role, setting
            yield o[0], BooleanAsSetting[o[1]]
        # !+PrincipalRoleMapDynamic(mr, may-2012) infer all local roles from 
        # context data:
        # - may have a simple logic, made explicit as a callable, per role, to 
        #   determine dynamically if a principal has the role on a context...
        # - included_roles, consider a hybrid system with existing db table
        #   and infer dynamically only for certain subset of roles ?!?
        # - add an "owner" attribute to group? Or, alternatively, move out 
        #   all "owner" attributes from other types to this db table??
        # - there should not be any need for global roles? ..., parliament, app.
    
    def getSetting(self, role_id, principal_id):
        """Return the setting for this principal, role combination
        """
        prm = schema.principal_role_map
        s = rdb.select(
                [prm.c.setting],
                rdb.and_(
                    prm.c.principal_id == principal_id,
                    prm.c.role_id == role_id, 
                    prm.c.object_type == self.object_type,
                    prm.c.object_id == self.oid))
        results = s.execute().fetchone()
        if not results:
            return Unset
        return BooleanAsSetting[results[0]]
    
    def getPrincipalsAndRoles(self):
        """Get all settings.
        
        Return all the principal/role combinations along with the
        setting for each combination as a sequence of tuples with the
        role id, principal id, and setting, in that order.
        """
        prm = schema.principal_role_map
        s = rdb.select(
                [prm.c.role_id, prm.c.principal_id, prm.c.setting ],
                rdb.and_(
                    prm.c.object_type == self.object_type,
                    prm.c.object_id == self.oid))
        for role_id, principal_id, setting in s.execute():
            yield role_id, principal_id, BooleanAsSetting[setting]
    
    def assignRoleToPrincipal(self, role_id, principal_id):
        prm = schema.principal_role_map
        s = rdb.select(
                [prm.c.role_id, prm.c.setting],
                rdb.and_(
                    prm.c.principal_id == principal_id,
                    prm.c.object_type == self.object_type,
                    prm.c.role_id == role_id, 
                    prm.c.object_id == self.oid))
        if s.execute().fetchone():
            self.unsetRoleForPrincipal(role_id, principal_id)        
        prm.insert(
            values=dict(
                role_id=role_id, 
                principal_id=principal_id,
                object_id=self.oid,
                object_type=self.object_type)).execute()
    
    def removeRoleFromPrincipal(self, role_id, principal_id):
        prm = schema.principal_role_map
        s = rdb.select(
                [prm.c.role_id, prm.c.setting],
                rdb.and_(
                    prm.c.principal_id == principal_id,
                    prm.c.object_type == self.object_type,
                    prm.c.role_id == role_id, 
                    prm.c.object_id == self.oid))
        if s.execute().fetchone():
            self.unsetRoleForPrincipal(role_id, principal_id)
        prm.insert(
            values=dict(
                role_id=role_id, 
                principal_id=principal_id,
                setting=False,
                object_id=self.oid,
                object_type=self.object_type)).execute()    
    
    def unsetRoleForPrincipal(self, role_id, principal_id):
        prm = schema.principal_role_map
        prm.delete(
            rdb.and_(
                prm.c.role_id == role_id,
                prm.c.principal_id == principal_id,
                prm.c.object_type == self.object_type,
                prm.c.object_id == self.oid)).execute()

class GlobalPrincipalRoleMap(LocalPrincipalRoleMap):
    
    def __init__(self, context):
        #self.context = context
        self.object_type = None
        self.oid = None


# schema

metadata = rdb.MetaData()
def schema():
    '''!+
    role_permission_map = rdb.Table("zope_role_permission_map", metadata,
       rdb.Column("role_id", rdb.Unicode(50)),
       rdb.Column("permission_id", rdb.Unicode(50)),
       rdb.Column("setting", rdb.Boolean, default=True, nullable=False),
       rdb.Column("object_type", rdb.String(100),),
       rdb.Column("object_id", rdb.Integer),
    )
    rdb.Index("rpm_oid_idx",
        role_permission_map.c["object_id"],
        role_permission_map.c["object_type"]
    )
    '''
    principal_role_map = rdb.Table("zope_principal_role_map", metadata,
       rdb.Column("principal_id", rdb.Unicode(50), index=True, nullable=False),
       rdb.Column("role_id", rdb.Unicode(50), nullable=False),
       rdb.Column("setting", rdb.Boolean, default=True, nullable=False),
       rdb.Column("object_type", rdb.String(100)),
       rdb.Column("object_id", rdb.Integer),
    )
    schema.principal_role_map = principal_role_map
    rdb.Index("prm_oid_idx",
        principal_role_map.c["object_id"],
        principal_role_map.c["object_type"]
    )
schema.principal_role_map = None
schema()

# auth

class AuthenticatedPrincipalFactory(principalfolder.AuthenticatedPrincipalFactory):
    """We enable returning an orm user object back for use as a principal. 
    The only constraint is attributes of a user object must not be orm mapped, 
    as we overwrite them with standard bookkeeping information as per the 
    IPrincipal interface.

    This enables interesting behavior for adaptation as we can use orm mapped
    hierarchies to always return the most suitable class for an object.
    """
    interface.implements(interfaces.IAuthenticatedPrincipalFactory)
    
    def __call__(self, authentication):
        User = bungeni.alchemist.interfaces.IAlchemistUser(self)
        results = bungeni.alchemist.Session().query(
                    User).filter_by(login=self.info.id).all()
        
        # delegate back if we can't find the user in the database
        if len(results) != 1:
            return super(AuthenticatedPrincipalFactory, self).__call__(authentication)
        user = results[0]
        user.id = self.info.id
        user.title = self.info.title
        user.description = self.info.description
        user.groups = []
        return user


