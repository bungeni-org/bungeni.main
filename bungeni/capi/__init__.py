# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Accessor API for Bungeni Custom parameters.

Provides uniform access and validation layer, plus related utilities, 
for using bungeni_custom parameters.

All access to bungeni_custom parameters should go through this module. 

Usage:
from bungeni.capi import capi
    # parameter name properties
    capi.default_language
    ...
    # utility methods
    capi.get_root_path()
    capi.get_type_info(type_key) 
    ...
    # decorator
    capi.bungeni_custom_errors
    
    # schema
    capi.schema.validate_file_rng()
    ...

$Id$
"""
log = __import__("logging").getLogger("bungeni.capi")

__all__ = ["capi"]

import _capi, _schema


# we access all via the singleton instance
capi = _capi.CAPI()

# additional conveniences for simpler and more uniform usage

# attach _bungeni_custom_errors decorator onto capi singleton
capi.bungeni_custom_errors = _capi.bungeni_custom_errors

# attach _schema sub-package onto capi singleton
capi.schema = _schema

# 

