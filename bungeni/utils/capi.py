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
            raise BungeniCustomError("%s: %s" % (e.__class__.__name__, e))
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
    def default_language(self):
        assert bc.default_language in self.zope_i18n_allowed_languages, \
            "Default language [%s] not in allowed languages [%s]" % (
                self.zope_i18n_allowed_languages,)
        return bc.default_language
    
    @bungeni_custom_errors
    def get_workflow_condition(self, condition):
        conds_module = resolve("._conditions", "bungeni_custom.workflows")
        return getattr(conds_module, condition) # raises AttributeError
    
    
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
    
    def put_env(self, key):
        """Set capi value for {key} as the environment variable {key}
        i.e. use to set os.environ[key].
        
        Wrapper on os.put_env(key, string_value) -- to take care of
        the value string-casting required by os.put_env while still 
        allowing the liberty of data-typing values of capi attributes 
        as needed.
        """
        try:
            os.environ[key] = getattr(self, key)
            # OK, value is a string... done.
        except TypeError:
            # putenv() argument 2 must be string, not ... 
            # i.e. value is NOT a string... then try repr'ing it to a string:
            os.environ[key] = repr(getattr(self, key))
            # ensure that the original object value defines a __repr__ 
            # that can correctly re-instantiate the original object
            assert eval(os.environ[key]) == getattr(self, key)

# we access all via the singleton instance
capi = CAPI()

