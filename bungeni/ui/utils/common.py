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
import sqlalchemy.sql.expression as sql

# !+bungeni.models(mr, apr-2011) gives error when executing localization.py
import bungeni
import bungeni.ui.interfaces
import bungeni.alchemist
from bungeni.capi import capi
from bungeni.utils import common


# !+ move to utils.common


def get_request():
    """ () -> either(IRequest, None)
    
    Raises zope.security.interfaces.NoInteraction if no interaction (and no 
    request).
    """
    # use queryInteraction() to raise 
    interaction = zope.security.management.getInteraction()
    for participation in interaction.participations:
        if zope.publisher.interfaces.IRequest.providedBy(participation):
            return participation

''' !+REQUEST_CACHED(mr, sep-2011) experimetally replacing with a different 
    implementation that does not require that the request be already 
    initialized.

def request_cached(f):
    """Simple function decorator, for caching relatively expensive calls for 
    the duration of a request. Annotates the request.
    
    Assumes request is not None.
    """
    fkey = id(f)  # f.__name__
    def request_cached_f(*args, **kws):
        key = "-rc-%s-%s-%s" % (fkey, id(args), hash(repr(kws)) if kws else "")
        # ok, via annotated request as cache
        aor = IAnnotations(get_request())  # annotations on request
        if not aor.has_key(key):
            #print "   REQUEST_CACHED...", key, f.__name__, args, kws
            aor[key] = f(*args, **kws)
        #print "***REQUEST_CACHED...", key, f.__name__, args, kws, "->", aor[key]
        return aor[key]
    return request_cached_f
'''

thread_local = __import__("threading").local()
def request_cached(f):
    """Simple function decorator, for caching relatively expensive calls until 
    *end* of the current request. May be used for calls executing prior to
    initialization of the request instance i.e. get_request() raises error.
    
    Stores on a mapping on threading.local(), and so requires explicit clearing 
    at end of request (in ui.publication).
    """
    fkey = id(f)  # f.__name__
    def request_cached_f(*args, **kws):
        key = "-rc-%s-%s-%s" % (fkey, id(args), hash(repr(kws)) if kws else "")
        rc = getattr(thread_local, "_request_cache", None)
        if rc is None:
            rc = thread_local._request_cache = {}
        if not rc.has_key(key):
             #print "   REQUEST_CACHED...", key, f.__name__, args, kws
             rc[key] = f(*args, **kws)
        #print "***REQUEST_CACHED...", key, f.__name__, args, kws, "->", rc[key]
        return rc[key]
    return request_cached_f
def _clear_request_cache():
    """Called on IEndRequestEvent, via handler ui.publication.on_end_request().
    """
    rc = getattr(thread_local, "_request_cache", None)
    if rc is not None:
        rc.clear()


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
            prm = zope.component.queryAdapter(
                ctx, IPrincipalRoleMap, default=None)
            if prm:
                prms.append(prm)
            group_assignment = getattr(ctx, "group_assignment", list())
            trusted_ga = proxy.removeSecurityProxy(group_assignment)
            for ga in trusted_ga:
                gprm = zope.component.queryAdapter(
                    ga.group, IPrincipalRoleMap, default=None)
                if gprm:
                    prms.append(gprm)
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
def get_workspace_roles():
    """Returns all the roles that the current principal has that are 
    relevant to the workspace configuration.
    """
    principal = common.get_request_principal()
    session = bungeni.alchemist.Session()
    roles = set()
    user = bungeni.models.utils.get_login_user()
    groups = session.query(bungeni.models.domain.Group).filter(
        bungeni.models.domain.Group.principal_name.in_(
            principal.groups.keys())).all()
    principal_groups = [
        delegate.login for delegate in
        bungeni.models.delegation.get_user_delegations(user)] + [principal.id]
    pg = []
    Allow = zope.securitypolicy.settings.Allow
    for group in groups:
        context = bungeni.core.workflows.utils.get_group_context(group)
        prm = zope.component.queryAdapter(
            context, IPrincipalRoleMap, default=None)
        if prm:
            pg = principal_groups + [group.principal_name]
            for principal_id in pg:
                l_roles = prm.getRolesForPrincipal(principal_id)
                for role in l_roles:
                    if role[1] == Allow:
                        roles.add(role[0])
    group_memberships = session.query(
        bungeni.models.domain.GroupMembership).filter(
        bungeni.models.domain.GroupMembership.user_id == user.user_id).all()
    group_membership_roles = []
    for group_membership in group_memberships:
        for sub_role in group_membership.sub_roles:
            group_membership_roles.append(sub_role.role_id)
    for group_membership_role in group_membership_roles:
        roles.add(group_membership_role)
    return list(roles)


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
        roles.append("bungeni.Authenticated")
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

sort_dir_funcs = dict(asc=sql.asc, desc=sql.desc)
def list_container_items(container_instance, permission=None):
    """Generate list of container items with permission check
    Note that we first try to generate the permission name or fall
    back to zope.View
    """
    sort_fields = []
    from bungeni.core.workflows.utils import view_permission
    trusted = proxy.removeSecurityProxy(container_instance)
    domain_model = trusted._class
    type_info = capi.get_type_info(domain_model)
    descriptor = type_info.descriptor_model
    if descriptor.sort_on:
        order_func = sort_dir_funcs.get(descriptor.sort_dir, sql.desc)
        for field in descriptor.sort_on:
            sort_fields.append(
                order_func(getattr(domain_model, field)) 
            )
    if not permission:
        permission = view_permission(domain_model)
    for item in trusted.batch(limit=None, order_by=tuple(sort_fields)):
        if checkPermission(permission, item):
            yield item

def get_users(role_id):
    session = bungeni.alchemist.Session()
    gmrs = session.query(bungeni.models.domain.GroupMembershipRole).filter(
        sql.and_(
            bungeni.models.domain.GroupMembershipRole.role_id == role_id,
            bungeni.models.domain.GroupMembershipRole.is_global == False)).all()
    return [gmr.member.user for gmr in gmrs]

