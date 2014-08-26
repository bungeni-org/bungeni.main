# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Common utilities oriented towards "usage of framework".

This module should NEVER import from any other bungeni sub-package
or even assume any knowledge of bungeni domain models.

$Id$
"""
log = __import__("logging").getLogger("bungeni.utils.common")

import zope.component
from zope.annotation.interfaces import IAnnotations
from zope.app.appsetup.appsetup import getConfigContext
from zope.publisher.interfaces import IRequest
from zope.security.management import getInteraction
from ore.wsgiapp.interfaces import IApplication


def get_application():
    """Get the bungeni.core.app.BungeniApp instance.
    """
    return zope.component.getUtility(IApplication)
    # return zope.app.component.hooks.getSite() '=?


def has_feature(feature_name):
    """Whether the application had been setup with the feature or not.
    
    (feature_name:str) -> bool
    """
    # via zope.configuration.config.ConfigurationMachine.hasFeature(name)
    return getConfigContext().hasFeature(feature_name)


def get_request():
    """ () -> either(IRequest, None)
    
    Raises zope.security.interfaces.NoInteraction if no interaction (and no 
    request).
    """
    # use queryInteraction() to raise 
    interaction = getInteraction()
    for participation in interaction.participations:
        if IRequest.providedBy(participation):
            return participation

def get_request_principal():
    """ () -> either(zope.security.interfaces.IGroupAwarePrincipal, None)
    """
    request = get_request()
    if request:
        return request.principal

def get_request_login():
    """ () -> either(str, None), login name of current principal, or None.
    """
    principal = get_request_principal()
    if principal is not None:
        return principal.id

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


# pick data

def getattr_ancestry(context, 
        name=None,
        parent_ref="__parent__",
        acceptable=lambda v: v is not None
    ):
    """Pick off the first acceptable value, starting from {context} and 
    traversing upwards, and testing for an cceptable value in the following 
    order:
    - the specified {context} itself
    - (if a horizontal attribute {name} is specified) the context's value for {name}
    - the parent of {context} via {parent_ref} that becomes the new {context}
    - (if a horizontal attribute {name} is specified) the context's value for {name}
    - and so on... until last parent. 
    Return None if no acceptable value found.
    """
    while context is not None:
        if acceptable(context):
            return context
        if name is not None:
            value = getattr(context, name, None)
            if acceptable(value):
                return value
        context = getattr(context, parent_ref, None)


