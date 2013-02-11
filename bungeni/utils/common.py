# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Application-wide common utilities.

$Id$
"""
log = __import__("logging").getLogger("bungeni.utils.common")

import zope.component
from zope.app.appsetup.appsetup import getConfigContext
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

