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

import time
import os
from zope.dottedname.resolve import resolve
from bungeni.utils import error
from bungeni.core import type_info
import bungeni_custom as bc


def bungeni_custom_errors(f):
    """Decorator to intercept any error raised by function f and re-raise it
    as a BungeniCustomError. To be used to decorate any function involved 
    in reading/validating/processing any bungeni_custom parameters. 
    """
    class BungeniCustomError(Exception):
        """A Localization Error.
        """
    return error.exceptions_as(BungeniCustomError, True)(f)


class CAPI(object):
    """Accessor class for Bungeni Custom parameters.
    """
    
    def __init__(self):
        self.validate_properties()
    
    def validate_properties(self):
        """Validate this capi instance.
        Ensure valid setup of properties at instantiation of CAPI instance
        """
        self.default_language
        self.right_to_left_languages
    
    # bungeni_custom parameter properties
    
    @property
    @bungeni_custom_errors
    def zope_i18n_allowed_languages(self):
        # NOTE: zope.i18n.config.ALLOWED_LANGUAGES expects the value of the 
        # env variable for this to be a COMMA or SPACE separated STRING
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
                bc.default_language, self.zope_i18n_allowed_languages,)
        return bc.default_language
        
    @property
    @bungeni_custom_errors
    def right_to_left_languages(self):
        rtl_langs = tuple(bc.right_to_left_languages.split())
        assert set(rtl_langs).issubset(set(self.zope_i18n_allowed_languages)),\
            "Right to left languages [%s] not in allowed languages [%s]" % (
                bc.right_to_left_languages, self.zope_i18n_allowed_languages)
        return rtl_langs
    
    @property
    @bungeni_custom_errors
    def check_auto_reload_localization(self):
        """ () -> int
        minimum number of seconds to wait between checks for whether a 
        localization file needs reloading; 0 means never check (deployment)
        """
        int(bc.check_auto_reload_localization) # TypeError if not an int
        return bc.check_auto_reload_localization
    
    @bungeni_custom_errors
    def get_workflow_condition(self, condition):
        conds_module = resolve("._conditions", "bungeni_custom.workflows")
        return getattr(conds_module, condition) # raises AttributeError
    
    @property
    @bungeni_custom_errors
    def default_number_of_listing_items(self):
        """This is the max number of items that are displayed in a listing by
        default. Returns an integer
        """
        return int(bc.default_number_of_listing_items)
    
    @property
    @bungeni_custom_errors
    def long_text_column_listings_truncate_at(self):
        """When listing text columns, only display first so many characters."""
        return int(bc.long_text_column_listings_truncate_at)
    
    @property
    @bungeni_custom_errors
    def workspace_tab_count_cache_refresh_time(self):
        """The duration in seconds between tab count refresh operations"""
        return int(bc.workspace_tab_count_cache_refresh_time)
    
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
        value = getattr(self, key)
        try:
            os.environ[key] = value
            # OK, value is a string... done.
        except TypeError:
            # putenv() argument 2 must be string, not <...>
            # i.e. value is NOT a string... try string-casting:
            try:
                # some zope code expects sequences to be specified as a 
                # COMMA or SPACE separated STRING, so we first try the value 
                # as a sequence, and serialize it to an environment variable 
                # value as expected by zope
                os.environ[key] = " ".join(value)
            except TypeError:
                # not a sequence, just fallback on repr(value)
                os.environ[key] = repr(value)
                # ensure that the original object value defines a __repr__ 
                # that can correctly re-instantiate the original object
                assert eval(os.environ[key]) == value
    
    _is_modified_since_last_times = {} # {path: (last_checked, last_modified)}
    def is_modified_since(self, abspath, modified_on_first_check=True):
        """ (abspath:str, modified_on_first_check:bool) -> bool
        Checks file path st_mtime to see if file has been modified since last 
        check. Updates entry per path, with last (check, modified) times.
        """
        check_auto_reload_localization = self.check_auto_reload_localization
        now = time.time()
        last_checked, old_last_modified = \
            self._is_modified_since_last_times.get(abspath) or (0, 0)
        if not check_auto_reload_localization:
            # 0 =>> never check (unless this is the first check...)
            if last_checked or not modified_on_first_check:
                return False
        if not now-last_checked > check_auto_reload_localization:
            # last check too recent, avoid doing os.stat
            return False
        last_modified = os.stat(abspath).st_mtime
        self._is_modified_since_last_times[abspath] = (now, last_modified)
        if not last_checked:
            # last_checked==0, this is the first check
            return modified_on_first_check
        return (old_last_modified < last_modified)
    
    # type registry
    
    def get_type_info(self, discriminator):
        """Get the TypeInfo instance for discriminator (see core.type_info). 
        
        The discriminator may be any of:
            type_key: str (the lowercase underscore-separated of domain cls name)
            workflow: an instance of Workflow, provides IWorkflow
            interface: provides IInterface
            domain model: provides IBungeniContent
            domain model instance: type provides IBungeniContent
            descriptor: provides IModelDescriptor
        
        Raise KeyError if no entry matched.
        """
        return type_info._get(discriminator)
    
    def iter_type_info(self):
        """Return iterator on all registered (key, TypeInfo) entries.
        """
        for type_key, ti in type_info._iter():
            yield type_key, ti


# we access all via the singleton instance
capi = CAPI()

