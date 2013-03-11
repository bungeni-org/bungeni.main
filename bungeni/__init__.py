# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Security Policy

$Id$
"""
log = __import__("logging").getLogger("bungeni")

import zope.interface
from zope.security.interfaces import ISecurityPolicy
from zope.security.proxy import removeSecurityProxy
from zope.securitypolicy import zopepolicy
from zope.securitypolicy.interfaces import IPrincipalRoleMap


def cache_item(mapping, key, value):
    """Utility to set (key, value) item on mapping, and return the value.
    """
    mapping[key] = value
    return value


class BungeniSecurityPolicy(zopepolicy.ZopeSecurityPolicy):
    """Custom Security Policy for Bungeni.
    
    Given the Bungeni convention that permissions are only assigned to roles,
    we optimize security checking by never checking permission directly on
    a principal or on a group. 
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

    def cached_principal_roles(self, parent, principal):
        cache = self.cache(parent)
        try:
            cache_principal_roles = cache.principal_roles
        except AttributeError:
            cache_principal_roles = cache.principal_roles = {}
        try:
            return cache_principal_roles[principal]
        except KeyError:
            pass

        if parent is None:
            roles = dict(
                [(role, zopepolicy.SettingAsBoolean[setting])
                 for (role, setting) in
                 zopepolicy.globalRolesForPrincipal(principal)])
            roles['zope.Anonymous'] = True  # Everybody has Anonymous
            cache_principal_roles[principal] = roles
            return roles

        roles = self.cached_principal_roles(
            removeSecurityProxy(getattr(parent, '__parent__', None)),
            principal)

        prinrole = IPrincipalRoleMap(parent, None)
        if prinrole:
            roles = roles.copy()
            for role, setting in prinrole.getRolesForPrincipal(principal):
                roles[role] = zopepolicy.SettingAsBoolean[setting]
        # The lines below include the group that a document has been assigned
        # to into the lookup hierarchy.
        group_assignments = getattr(parent, "group_assignment", list())
        for group_assignment in group_assignments:
            assigned_group_prinrole = IPrincipalRoleMap(
                group_assignment.group, None)
            if assigned_group_prinrole:
                roles = roles.copy()
                role_settings = assigned_group_prinrole.getRolesForPrincipal(
                    principal)
                for role, setting in role_settings:
                    roles[role] = zopepolicy.SettingAsBoolean[setting]
        cache_principal_roles[principal] = roles
        return roles
