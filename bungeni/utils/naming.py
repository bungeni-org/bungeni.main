# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Support for naming conventions and mappings.

Generic utilities, no bungeni.* dependencies allowed, 
may be imported from anywhere and at anytime.

Usage:
from bungeni.utils import naming

$Id$
"""
log = __import__("logging").getLogger("bungeni.utils")

__all__ = ["polymorphic_identity", "camel", "un_camel", "singular", "plural"]

import re


def polymorphic_identity(cls):
    """Formalize convention of determining the polymorphic discriminator value 
    for a domain class as a function of the class name.
    """
    return un_camel(cls.__name__)


def camel(name):
    """Convert an underscore-separated word to CamelCase.
    """
    return "".join([ s.capitalize() for s in name.split("_") ])

def un_camel(name):
    """Convert a CamelCase name to lowercase underscore-separated.
    """
    s1 = un_camel.first_cap_re.sub(r"\1_\2", name)
    return un_camel.all_cap_re.sub(r"\1_\2", s1).lower()
un_camel.first_cap_re = re.compile("(.)([A-Z][a-z]+)")
un_camel.all_cap_re = re.compile("([a-z0-9])([A-Z])")


# !+should become not needed
def singular(pname):
    """Get the english singular of (plural) name.
    """
    for sname in plural.custom:
        if plural.custom[sname] == pname:
            return sname
    if pname.endswith("s"):
        return pname[:-1]
    return pname

def plural(sname):
    """Get the english plural of (singular) name.
    """
    return plural.custom.get(sname, None) or "%ss" % (sname)
plural.custom = {
    "user_address": "user_addresses",
    "group_address": "group_addresses",
}


