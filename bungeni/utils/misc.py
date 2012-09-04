# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Misc utilities

recommended usage:
from bungeni.utils import misc

$Id$
"""
log = __import__("logging").getLogger("bungeni.utils.misc")


# xml attr values

def xml_attr_bool(elem, attr_name, default=False):
    return as_bool(strip_none(elem.get(attr_name)) or str(default))

def xml_attr_str(elem, attr_name, default=None):
    return strip_none(elem.get(attr_name)) or default


# string / conversion

def strip_none(s):
    """Ensure non-empty whitespace-stripped string, else None.
    """
    if s is not None:
        return s.strip() or None
    return None

def as_bool(s):
    """(s:str) -> bool 
    Cast case-insensitive & stripped strings "true" or "false" to boolean.
    Other string variations give TypeError.
    """
    _s = s.strip().lower()
    if _s == "true":
        return True
    elif _s == "false":
        return False
    raise TypeError("Invalid bool: %s" % s)


# list

def get_keyed_item(seq, value, key="name"):
    """Get the first item in the sequence that has a {key} entry set to {value}.
    """
    for s in seq:
        if s[key] == value:
            return s
        
def replace_keyed_item(seq, replacement_item, key="name"):
    """Replace the first item in the sequence whose {key} value is same as 
    replacement_item[{key}].
    """
    for s in seq:
        if s[key] == replacement_item[key]:
            seq[seq.index(s)] = replacement_item
            return
    raise LookupError("No matching item [%s=%r] found in seq: %s" % (
        key, replacement_item[key], seq))

