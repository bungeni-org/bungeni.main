# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Security Policy 

$Id$
"""
log = __import__("logging").getLogger("bungeni")

import zope.interface
from zope.security.interfaces import ISecurityPolicy
import zope.securitypolicy.zopepolicy

from zope.securitypolicy.rolepermission import rolePermissionManager
globalRolesForPermission = rolePermissionManager.getRolesForPermission

from zope.securitypolicy.principalrole import principalRoleManager
globalRolesForPrincipal = principalRoleManager.getRolesForPrincipal

from zope.security.proxy import removeSecurityProxy
from zope.securitypolicy.interfaces import Allow #, Deny, Unset
from zope.securitypolicy.interfaces import IRolePermissionMap

from bungeni.core.workflow.interfaces import IWorkflow


def cache_item(mapping, key, value):
    """Utility to set (key, value) item on mapping, and return the value.
    """
    mapping[key] = value
    return value


class BungeniSecurityPolicy(zope.securitypolicy.zopepolicy.ZopeSecurityPolicy):
    """Custom Security Policy for Bungeni.
    
    Given the Bungeni convention that permissions are only assigned to roles,
    we optimize security checking by never checking permission directly on
    a principal or on a group. 
    
    For workflowed objects, we infer the permission setting from the permission
    declarations of each workflow state.
    """
    zope.interface.classProvides(ISecurityPolicy)
    
    #def checkPermission(self, permission, object):
    #    return super(BungeniSecurityPolicy, self
    #        ).checkPermission(permission, object)
    
    def cached_decision(self, object, principal, groups, permission):
        """Get (cached, set if needed) the decision for a principal and 
        a permission. Called from checkPermission.
        """
        cache = self.cache(object)
        try:
            cache_decision = cache.decision
        except AttributeError:
            cache_decision = cache.decision = {}
        # cache_decision_prin[permission] is the cached decision for 
        # a principal and permission on object.
        cache_decision_prin = cache_decision.get(principal)
        if not cache_decision_prin:
            cache_decision_prin = cache_decision[principal] = {}
        try:
            return cache_decision_prin[permission]
        except KeyError:
            return cache_item(cache_decision_prin, permission,
                self._get_decision(object, principal, groups, permission))
    
    def _get_decision(self, object, principal, groups, permission):
        """Get the decision for a principal and a permission on object.
        """
        # Given that bungeni categorically grants/denies permissions only 
        # to *roles* i.e. never directly to a principal/group, there is no 
        # need to check permissions for these i.e. to ever call:
        #
        #   self.cached_prinper( ... )
        #   self._group_based_cashed_prinper( ... )
        #
        # as the decision will categorically always be None.
        #
        #decision = self.cached_prinper(object, principal, groups, permission)
        #if (decision is None) and groups:
        #    decision = self._group_based_cashed_prinper(
        #        object, principal, groups, permission)
        #assert decision is None, "#### ZOPEPOLICY #### %s" % (vars())
        
        roles = self.cached_roles(object, permission)
        if roles:
            # get decision from: zope_principal_role_map
            prin_roles = self.cached_principal_roles(object, principal)
            if groups:
                prin_roles = self.cached_principal_roles_w_groups(
                    object, principal, groups, prin_roles)
            for role, setting in prin_roles.items():
                if setting and (role in roles):
                    return True
        return False
    
    def cached_roles(self, object, permission):
        """Get roles for permission on object.
        
        If object is workflowed get from the workflow state definition,
        else from zope_role_permission_map.
        """
        cache = self.cache(object)
        try:
            cache_roles = cache.roles
        except AttributeError:
            cache_roles = cache.roles = {}
        try:
            return cache_roles[permission]
        except KeyError:
            pass
        
        if object is None:
            roles = dict([ (role, 1)
                    for (role, setting) in globalRolesForPermission(permission)
                    if setting is Allow ])
            return cache_item(cache_roles, permission, roles)
        
        # recurse on parent
        roles = self.cached_roles(
            removeSecurityProxy(getattr(object, '__parent__', None)),
            permission)
        
        getRolesForPermission = None
        # ASSUMPTION: if an object is workflowed, then ALL local role 
        # permissions are specified by its current workflow state.
        try:
            # get the workflow instance for object
            workflow = IWorkflow(object)
            # !+status = StateController.get_status(object)
            getRolesForPermission = workflow.get_state(object.status
                ).getRolesForPermission
        except TypeError, e: # could not adapt
            # None is default value for when IRolePermissionMap(object) fails
            roleper = IRolePermissionMap(object, None)
            # !+RolePermissionMap(mr, apr-2011) should categorically always be
            # None? if so, clean-out all ZCA regs on IRolePermissionMap, and 
            # rpm-related code). (Temporary) Assertion of this:
            assert roleper is None, \
                "[%s] !+RolePermissionMap [%s] for OBJECT [%s] not None" % (
                    e, roleper, object)
            log.warn("BungeniSecurityPolicy: object [%s] is NOT workflowed. "
                "Temporarily trying anyway to determine local role permissions "
                "via IRolePermissionMap(object) [%s] i.e. via "
                "zope_role_permission_map--that in future will be EMPTY)." % (
                    object, roleper))
            if roleper is not None:
                getRolesForPermission = roleper.getRolesForPermission
        
        if getRolesForPermission is not None:
            roles = roles.copy()
            for role, setting in getRolesForPermission(permission):
                #if workflow: assert (permission, role) in workflow._permission_role_pairs
                if setting is Allow:
                    roles[role] = 1
                    #if workflow: assert (1, permission, role) in state.permissions
                elif role in roles:
                    del roles[role]
                    #if workflow: assert (0, permission, role) in state.permissions
        return cache_item(cache_roles, permission, roles)


