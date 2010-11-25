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


import bungeni.models.utils
def get_context_roles(context):
    """Get the list of current user's roles for the specified context.
    
    A further optimization would be to simply cache the user's resulting roles 
    on a context -- but this seems to not be necessary as it seems this is 
    only called up to once per request.
    """
    if context is None:
        log.warn(" [get_context_roles] CANNOT DETERMINE CONTEXT")
        return []
    # assumption: current user is authenticated
    roles = bungeni.models.utils.get_roles(context)
    return roles


def is_admin(context):
    """Check if current interaction has admin privileges on specified context
    """
    return zope.security.management.getInteraction().checkPermission(
        "zope.ManageSite", context)


