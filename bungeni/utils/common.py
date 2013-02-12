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


def get_request_principal():
    """ () -> either(zope.security.interfaces.IGroupAwarePrincipal, None)
    """
    interaction = getInteraction()
    for participation in interaction.participations:
        if IRequest.providedBy(participation):
            return participation.principal

def get_request_login():
    """ () -> either(str, None), login name of current principal, or None.
    """
    principal = get_request_principal()
    if principal is not None:
        return principal.id



# pick data

def getattr_ancestry(context, name, 
        parent_ref="__parent__",
        acceptable=lambda v: v is not None
    ):
    """Get the first encountered acceptable value for attribute {name}, 
    cascading upwards to parent via {parent_ref}.
    If no attribute name is specifed, as value use the context.
    """
    while context is not None:
        if name is not None:
            value = getattr(context, name, None)
        else:
            value = context
        if acceptable(value):
            return value
        context = getattr(context, parent_ref, None)

