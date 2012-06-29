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
from zope.interface.interfaces import IInterface
from zope.dottedname.resolve import resolve


def polymorphic_identity(cls):
    """Formalize convention of determining the polymorphic discriminator value 
    for a domain class as a function of the class name.
    
    For convenience, the cls parameter may be a normal type or
    a zope.interface.Iterface, that is specially handled.
    """
    name = cls.__name__
    if IInterface.providedBy(cls):
        assert name.startswith("I"), \
            'InterfaceClass %s name does not start with "I"' % (cls)
        name = name[1:]
    return un_camel(name)


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


def is_valid_identifier(name):
    """Is name a valid identifier ::=  (letter|"_") (letter | digit | "_")*
    """
    return is_valid_identifier.RE.match(name)
is_valid_identifier.RE = re.compile("^[\w_][\w\d_]+$")
def as_identifier(name):
    """Ensure name is a valid idenifier (for python, js, etc)... replace any
    whitespace, "-" and "." with "_".
    """
    if not is_valid_identifier(name):
        name = name.strip(" -."
            ).replace(" ", "_").replace("-", "_").replace(".", "_")
    assert is_valid_identifier(name), \
        '%s ::= (letter|"_") (letter | digit | "_")*' % (name)
    return name


def resolve_relative(dotted_relative, obj):
    """Normalize the relative python path with obj.__module__ or with 
    obj.__name__, and resolve.
    
    Parameters:
        dotted_relative:str e.g. "..interfaces"
        obj:either(instance, type, module)
    
    Raises AttributeError if obj does not define a __module__ or __name__ attr.
    """
    # (instance, type) or (module)
    module_path = getattr(obj, "__module__", None) or getattr(obj, "__name__")
    return resolve(dotted_relative, obj.__module__)

