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

