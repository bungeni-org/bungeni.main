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
from zope.app.security.interfaces import IUnauthenticatedPrincipal
from zope.securitypolicy.interfaces import IPrincipalRoleMap
from zope.security import checkPermission, proxy

# !+bungeni.models(mr, apr-2011) gives error when executing localization.py
import bungeni
import bungeni.ui.interfaces

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


def request_cached(f):
    """Simple function decorator, for caching relatively expensive calls for 
    the duration of a request. Annotates the request.
    """
    fkey = id(f)  # f.__name__
    def request_cached_f(*args, **kws):
        key = "_rc-%s-%s-%s" % (fkey, id(args), hash(repr(kws)) if kws else "")
        aor = IAnnotations(get_request())  # annotations on request
        if not aor.has_key(key):
            #print "   REQUEST_CACHED...", key, f.__name__, args, kws
            aor[key] = f(*args, **kws)
        #print "***REQUEST_CACHED...", key, f.__name__, args, kws, "->", aor[key]
        return aor[key]
    return request_cached_f


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


def get_context_roles(context, principal):
    """Get the list of current principal's roles for the specified context.
    
    return [ role_id for role_id, role 
             in zope.component.getUtilitiesFor(IRole, context) ]
    eeks we have to loop through all groups of the principal and all 
    PrincipalRoleMaps to get all roles

    Assumption: current principal is authenticated i.e. 
    zope.app.security.interfaces.IAuthenticatedPrincipal.providedBy(principal)
    """
    assert context is not None, "Context may not be None."
    
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
    if not principal:
        return []
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


@request_cached
def get_workspace_roles(principal):
    """Returns all the roles that a user has that are relevant to the
       workspace configuration.
    """
    session = bungeni.alchemist.Session()
    roles = []
    for group_id in principal.groups.keys():
        result = session.query(bungeni.models.domain.Group).filter(
            bungeni.models.domain.Group.group_principal_id == group_id).first()
        if result:
            roles.extend(get_context_roles(
                    bungeni.core.workflows.utils.get_group_context(result), 
                    principal))
    return roles


def get_request_context_roles(request):
    """Get the list of user's roles (including whether admin or not) relevant 
    for this request layer.
    
    Wraps get_context_roles(context), with the following differences:
    - auto determines the context, a needed param for get_context_roles()
    - when within a public layer, always returns ["bungeni.Anonymous"]
    - handles case when user is not authenticated
    - handles case for when user is "admin"
    """
    request = request or get_request()
    if request is None:
        context = None
        principal = None
    else:
        context = get_traversed_context(request)
        principal = request.principal
    # within a public layer, just proceed as "bungeni.Anonymous"
    if is_public_layer(request):
        return ["bungeni.Anonymous"]
    # other layers
    if IUnauthenticatedPrincipal.providedBy(principal):
        roles = ["bungeni.Anonymous"]
    else: 
        roles = get_context_roles(context, principal)
        if is_admin(context):
            roles.append("bungeni.Admin")
    log.debug(""" [get_request_context_roles]
    PRINCIPAL: %s
    CONTEXT: %s
    ROLES: %s
    """ % (principal, context, roles))
    return roles


def is_public_layer(request):
    """Is this request within one of the "public" sections?
    """
    return bungeni.ui.interfaces.IAnonymousSectionLayer.providedBy(request)

    
def is_admin(context):
    """Check if current interaction has admin privileges on specified context
    """
    return zope.security.management.getInteraction().checkPermission(
        "zope.ManageSite", context)

def list_container_items(container, permission="zope.View"):
    """Generate list of container items with permission check
    """
    trusted = proxy.removeSecurityProxy(container)
    for contained in trusted.values():
        if checkPermission(permission, contained):
            yield contained
