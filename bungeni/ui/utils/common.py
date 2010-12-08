# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Misc utilities for the UI

recommended usage:
from bungeni.ui.utils import common

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.utils.common")

import zope
from zope.annotation.interfaces import IAnnotations
from zope.securitypolicy.interfaces import IPrincipalRoleMap

import bungeni

from ore.wsgiapp.interfaces import IApplication
def get_application():
    """Get the bungeni.core.app.BungeniApp instance."""
    return zope.component.getUtility(IApplication)
    # there is of course always ONE obvious way to do it ;-) :
    # return zope.app.component.hooks.getSite()


from zope.app.appsetup.appsetup import getConfigContext
def has_feature(feature_name):
    """Whether the application had been setup with the feature or not.
    
    (feature_name:str) -> bool
    """
    # via zope.configuration.config.ConfigurationMachine.hasFeature(name)
    return getConfigContext().hasFeature(feature_name)


def get_request():
    """ () -> either(IRequest, None)
    """
    interaction = zope.security.management.getInteraction()
    for participation in interaction.participations:
        if zope.publisher.interfaces.IRequest.providedBy(participation):
            return participation


def get_traversed_context(request=None, index=-1):
    """ (request:either(IRequest, None), indix:int) -> either(IRequest, None)
    
    Requires that the "contexts" list has been prepared on the request, see
    the event handler: bungeni.ui.publication.remember_traversed_context()

    As an optimization, if the caller already has a reference to the current 
    request, it may optionally be passed in as a parameter.

    By default, we pick off the last traversed (as per "index").
    """
    if request is None:
        request = get_request()
    if request is not None:
        return IAnnotations(request).get("contexts")[index]


def get_context_roles(context):
    """Get the list of current principal's roles for the specified context.
    
    return [ role_id for role_id, role 
             in zope.component.getUtilitiesFor(IRole, context) ]
    eeks we have to loop through all groups of the principal and all 
    PrincipalRoleMaps to get all roles

    Assumption: current principal is authenticated i.e. 
    zope.app.security.interfaces.IAuthenticatedPrincipal.providedBy(principal)
    
    """
    if context is None:
        log.warn(" [get_context_roles] CANNOT DETERMINE CONTEXT")
        return []
    
    prms = []
    def _build_principal_role_maps(ctx):
        if ctx is not None:
            if zope.component.queryAdapter(ctx, IPrincipalRoleMap):
                prms.append(IPrincipalRoleMap(ctx))
            _build_principal_role_maps(getattr(ctx, '__parent__', None))
    _build_principal_role_maps(context)
    prms.reverse()
    
    roles, message = [], []
    Allow = zope.securitypolicy.settings.Allow
    Deny = zope.securitypolicy.settings.Deny
    def add_roles(principal, prms):
        message.append("             principal: %s" % principal)
        for prm in prms:
            l_roles = prm.getRolesForPrincipal(principal)  # -> generator
            for role in l_roles:
                message.append("               role: %s" % str(role))
                if role[1] == Allow:
                    if not role[0] in roles:
                        roles.append(role[0])
                elif role[1] == Deny:
                    if role[0] in roles:
                        roles.remove(role[0])
    
    principal = bungeni.models.utils.get_principal()
    pg = principal.groups.keys()
    # ensure that the actual principal.id is included
    if not principal.id in pg:
        pg.append(principal.id)
    
    for principal_id in pg:
        add_roles(principal_id, prms)
    
    log.debug("get_context_roles: \n"
              "            principal: %s\n"
              "            groups %s ::\n%s\n"
              "            roles %s" % (
            principal.id, str(pg), "\n".join(message), roles))
    return roles

def is_admin(context):
    """Check if current interaction has admin privileges on specified context
    """
    return zope.security.management.getInteraction().checkPermission(
        "zope.ManageSite", context)


