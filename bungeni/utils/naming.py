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

import re
from zope.interface.interfaces import IInterface
from zope.dottedname.resolve import resolve


def polymorphic_identity(cls):
    """Formalize convention of determining the polymorphic discriminator value 
    for a domain type (a sub-type of models.domain.Entity) as a function of 
    the class name.
    
    The polymorphic_identity(domain_type) *is* the type_key for the domain_type.
    """
    #assert issubclass(cls, bungeni.models.domain.Entity)
    name = cls.__name__
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

def split_camel(name):
    """Split a CamelCase name into separate words.
    """
    s1 = un_camel.first_cap_re.sub(r"\1 \2", name)
    return un_camel.all_cap_re.sub(r"\1 \2", s1)


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
    "Address": "Addresses",
    "Ministry": "Ministries",
    "Signatory": "Signatories",
    "Country": "Countries",
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
    #module_path = getattr(obj, "__module__", None) or getattr(obj, "__name__")
    return resolve(dotted_relative, obj.__module__)

def qualname(obj):
    """Return qualified name for obj."""
    return "%s.%s" % (obj.__module__, obj.__name__)


# model, interfaces, descriptor, container

INTERFACE_PREFIX = "I"
TABLE_SCHEMA_POSTFIX = "TableSchema"
DESCRIPTOR_CLASSNAME_POSTFIX = "Descriptor"
CONTAINER_CLASSNAME_POSTFIX = "Container"

# !+ rename:
# model_name -> domain_model_name
# model_interface_name -> domain_interface_name

def model_name(type_key):
    return camel(type_key)

def model_interface_name(type_key):
    return "%s%s" % (INTERFACE_PREFIX, camel(type_key))
def _type_key_from_model_interface_name(model_interface_name):
    assert model_interface_name.startswith(INTERFACE_PREFIX)
    return un_camel(model_interface_name[len(INTERFACE_PREFIX):])

def table_schema_interface_name(type_key):
    return "%s%s%s" % (INTERFACE_PREFIX, camel(type_key), TABLE_SCHEMA_POSTFIX)
def _type_key_from_table_schema_interface_name(table_schema_interface_name):
    assert table_schema_interface_name.startswith(INTERFACE_PREFIX)
    assert table_schema_interface_name.endswith(TABLE_SCHEMA_POSTFIX)
    return un_camel(table_schema_interface_name[
            len(INTERFACE_PREFIX):-len(TABLE_SCHEMA_POSTFIX)])

def descriptor_class_name(type_key):
    cls_name = camel(type_key)
    return "%s%s" % (cls_name, DESCRIPTOR_CLASSNAME_POSTFIX)
def _type_key_from_descriptor_class_name(descriptor_cls_name):
    assert descriptor_cls_name.endswith(DESCRIPTOR_CLASSNAME_POSTFIX)
    return un_camel(descriptor_cls_name[0:-len(DESCRIPTOR_CLASSNAME_POSTFIX)])

def container_class_name(type_key):
    return "%sContainer" % model_name(type_key)

def container_interface_name(type_key):
    return "%s%s" % (INTERFACE_PREFIX, container_class_name(type_key))

# reverse conversions back to type_key
def type_key(name_type, name):
    return type_key.reverse_conversions[name_type](name)
type_key.reverse_conversions = {
    "model_name": un_camel, # for model cls, prefer polymorphic_identity(cls)
    # than type_key("model_name", cls.__name__)
    "model_interface_name": _type_key_from_model_interface_name,
    "table_schema_interface_name": _type_key_from_table_schema_interface_name,
    "descriptor_class_name": _type_key_from_descriptor_class_name,
}

# i18n msgids --
# set of message ids built dynamically, then dumped as needed for extractor

MSGIDS = set()

