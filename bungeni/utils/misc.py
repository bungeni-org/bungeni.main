# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Misc utilities

recommended usage:
from bungeni.utils import misc

$Id$
"""
log = __import__("logging").getLogger("bungeni.utils.misc")

import sys
import os


# xml attr values

def xml_attr_bool(elem, attr_name, default=False):
    return as_bool(strip_none(elem.get(attr_name)) or str(default))

def xml_attr_int(elem, attr_name, default=None):
    value = strip_none(elem.get(attr_name)) or default
    if value is not None:
        value = int(value)
    return value

def xml_attr_str(elem, attr_name, default=None):
    return strip_none(elem.get(attr_name)) or default


# string / conversion / comparison

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

import difflib
def unified_diff(old_str, new_str, old_name="OLD", new_name="NEW"):
    """Return a unified diff of two strings.
    """
    return "".join(difflib.unified_diff(
                old_str.splitlines(1), 
                new_str.splitlines(1), 
                fromfile=old_name, 
                tofile=new_name))


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


# io

def read_file(file_path):
    return open(file_path, "r").read().decode("utf-8")

def check_overwrite_file(file_path, content):
    """Write content to file_path if necessary (that is if there are changes),
    creating it if does not exist. Log a "diff" to preceding content.
    """
    try:
        persisted = read_file(file_path)
        exists = True
    except IOError:
        persisted = '<NO-SUCH-FILE path="%s" />\n' % (file_path)
        exists = False
    if persisted != content:
        if exists:
            print "*** OVERWRITING file: %s" % (file_path)
        else:
            print "*** CREATING file: %s" % (file_path)
        print unified_diff(persisted, content, file_path, "NEW")            
        open(file_path, "w").write(content.encode("utf-8"))


# introspection

def get_caller_module_name(depth=1):
    """Get the global __name__ value at the given caller depth, by default
    the immediate caller's module.
    
    Calling with depth=0 is equivalent to __name__ (current module name).
    Calling with a depth greater than call stack will throw ValueError.
    """ 
    return sys._getframe(depth).f_globals["__name__"]


#

def describe(funcdesc):
    """
    The describe decorator is used add @describe annotations to 
    functions. This is used in conditions, validations etc to provide
    a extractable and i18n-able description of the function - as these 
    are provided in list boxes in the configuration UI
    """
    def decorate(func):
        setattr(func, "description", funcdesc)
        return func
    return decorate            


def put_env(key, value):
    """Set the the environment variable {key} to {value}
    i.e. use to set os.environ[key].
    
    Wrapper on os.put_env(key, string_value) -- to take care of
    the value string-casting required by os.put_env while still 
    allowing the liberty of data-typing values of capi attributes 
    as needed.
    """
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
            
            
def get_bungeni_installation_dir():
    """Get the path to the bungeni installation directory.
    """
    current_dir = __file__
    trailing_file_name = ""
    while trailing_file_name != "src":
        current_dir, trailing_file_name = os.path.split(current_dir)
    return current_dir

