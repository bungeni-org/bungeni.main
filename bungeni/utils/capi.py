# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Accessor API for Bungeni Custom parameters.

Provides uniform access and validation layer, plus related utilities, 
for using bungeni_custom parameters.

All access to bungeni_custom parameters should go through this module. 

Usage:
from bungeni.utils.capi import capi
    ... capi.NAME ...

$Id$
"""
__all__ = ["capi", "bungeni_custom_errors"]

log = __import__("logging").getLogger("bungeni.utils.capi")

import os
from zope.dottedname.resolve import resolve
import bungeni_custom as bc


def bungeni_custom_errors(f):
    """Decorator to intercept any error raised by function f and re-raise it
    as a BungeniCustomError. To be used to decorate any function involved 
    in reading/validating/processing any bungeni_custom parameters. 
    """
    class BungeniCustomError(Exception):
        """A Localization Error.
        """
    def _errorable(*args, **kw):
        try: 
            return f(*args, **kw)
        except Exception, e: 
            raise BungeniCustomError("%s: %s" % (e.__class__.name, e))
    return _errorable


class CAPI(object):
    """Accessor class for Bungeni Custom parameters.
    """
    
    # bungeni_custom parameter properties
    
    @property
    @bungeni_custom_errors
    def zope_i18n_allowed_languages(self):
        return tuple(bc.zope_i18n_allowed_languages.split())
    
    @property
    @bungeni_custom_errors
    def zope_i18n_compile_mo_files(self):
        return bool(
            bc.zope_i18n_compile_mo_files is True or 
            bc.zope_i18n_compile_mo_files == "1"
        )
    
    @property
    @bungeni_custom_errors
    def application_language(self):
        return bc.default_language
    
    @bungeni_custom_errors
    def get_workflow_condition(self, condition):
        conds_module = resolve("._conditions", "bungeni_custom.workflows")
        assert hasattr(conds_module, condition), \
            "No such custom condition: %s" % (condition)
        return getattr(conds_module, condition)
    
    
    # utility methods
    
    def get_root_path(self):
        """Get absolute physical path location for currently active 
        bungeni_custom package folder.
        """
        return os.path.dirname(os.path.abspath(bc.__file__)) 
    
    def get_path_for(self, *path_components):
        """Get absolute path, under bungeni_custom, for path_components.
        """
        return os.path.join(*(self.get_root_path(),)+path_components)

# we access all via the singleton instance
capi = CAPI()


