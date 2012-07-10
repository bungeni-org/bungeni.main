# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Localization of Form Schema Descriptors

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.descriptor.localization")

from time import time
import elementtree.ElementTree

from bungeni.alchemist.model import (
    #ModelDescriptor, 
    IModelDescriptor,
    #queryModelDescriptor,
    Field,
    show, hide,
    norm_sorted, 
)
from bungeni.utils.capi import capi, bungeni_custom_errors
from bungeni.ui.utils import debug
from bungeni.utils import naming
from bungeni.utils.misc import xml_attr_str

# constants 

from bungeni.ui.descriptor import descriptor as DESCRIPTOR_MODULE

CUSTOM_PATH = capi.get_path_for("forms", "ui.xml")
DESCRIPTOR_CLASSNAME_POSTFIX = "Descriptor"

ROLES_DEFAULT = " ".join(Field._roles)
INDENT = " " * 4

# utils

def read_custom():
    try:
        return open(CUSTOM_PATH, "r").read().decode("utf-8")
    except IOError:
        return '<NO-SUCH-FILE path="%s" />' % (CUSTOM_PATH)

def write_custom(old_content, content):
    print "*** OVERWRITING localization file: %s" % (CUSTOM_PATH)
    print debug.unified_diff(old_content, content, CUSTOM_PATH, "NEW")
    open(CUSTOM_PATH, "w").write(content.encode("utf-8"))

def check_reload_localization(event):
    if capi.is_modified_since(CUSTOM_PATH):
        localize_descriptors()

def is_descriptor(cls):
    try:
        return IModelDescriptor.implementedBy(cls)
    except (TypeError, AttributeError):
        return False
    '''
    try:
        return issubclass(cls, ModelDescriptor):
    except TypeError:
        return False
    '''

def localizable_descriptor_classes(module):
    """A generator of localizable descriptor classes contained in module.
    """
    for key in dir(module): # alphabetic key order
        cls = getattr(module, key)
        if is_descriptor(cls):
            if cls.localizable:
                yield cls


####
# Localize descriptors from {bungeni_custom}/forms/ui.xml.

def get_localizable_descriptor_class(module, type_key):
    cls_name = naming.camel(type_key)
    descriptor_cls_name = "%s%s" % (cls_name, DESCRIPTOR_CLASSNAME_POSTFIX)
    assert hasattr(module, descriptor_cls_name), \
        "Unknown descriptor [%s]" % (descriptor_cls_name)
    cls = getattr(module, descriptor_cls_name) # raises AttributeError
    assert is_descriptor(cls), \
        "Invalid descriptor [%s]" % (descriptor_cls_name)
    assert cls.localizable, \
        "May not localize a non-localizable descriptor [%s]" % (
            descriptor_cls_name)
    return cls

def reorder_fields(cls, ordered_field_names, field_by_name):
    """Reorder descriptor class fields.
    """
    log.debug("reorder_fields [%s] %s" % (cls.__name__, ordered_field_names))
    # validate
    assert len(cls.fields) == len(ordered_field_names), \
        "Localization of [%s]: Field list does not match:\nB: %s\nC: %s" % (
            cls.__name__, [ f.name for f in cls.fields ], ordered_field_names )
    for f in cls.fields:
        assert f.name in ordered_field_names, \
            "Localization of [%s]: Unspecified order for field [%s]" % (
                cls.__name__, f.name)
        field_by_name[f.name] = f
    # reorder (retaining same list instance as class attribute)
    cls.fields[:] = [ field_by_name[name] for name in ordered_field_names ]

def is_stale_info(bval, cval, message):
    if not bval == cval:
        log.warn(message)
        return True
    return False

@bungeni_custom_errors
def localize_descriptors():
    """Localizes descriptors from {bungeni_custom}/forms/ui.xml.
    """
    start_time = time()
    #for d in localizable_descriptor_classes(descriptor_module): ...
    xml = elementtree.ElementTree.fromstring(read_custom())
    # make the value of <ui.@roles> as *the* bungeni default list of roles
    global ROLES_DEFAULT
    Field._roles[:] = xml.get("roles", ROLES_DEFAULT).split()
    # and reset global "constant"
    ROLES_DEFAULT = " ".join(Field._roles)
    
    STALE_INFO = False
    for edescriptor in xml.findall("descriptor"):
        type_key = xml_attr_str(edescriptor, "name")
        order = xml_attr_str(edescriptor, "order")
        cls = get_localizable_descriptor_class(DESCRIPTOR_MODULE, type_key)
        if order is not None:
            cls.order = int(order)
        field_elems = edescriptor.findall("field")
        field_by_name = {}
        reorder_fields(cls, 
            [ fe.get("name") for fe in field_elems ], 
            field_by_name)
        for f_elem in field_elems:
            fname = xml_attr_str(f_elem, "name")
            f = field_by_name[fname]
            # check if info-only field attributes are out of sync with bungeni
            # @displayable, from f.modes:tuple
            c_displayable_modes = f_elem.get("displayable").split()
            if is_stale_info(set(f.modes), set(c_displayable_modes),
                "STALE INFO ATTR [%s.%s.modes]\n B: %s\n C: %s" % (
                    type_key, fname, f.modes, c_displayable_modes)):
                f._SERIALIZE_modes = f.modes[:]
                STALE_INFO = True
            # @localizable, from f._localizable_modes:set
            c_localizable_modes = set(f_elem.get("localizable", "").split())
            if is_stale_info(f._localizable_modes, c_localizable_modes,
                "STALE INFO ATTR [%s.%s.localizable]\n B: %s\n C: %s" % (
                    type_key, fname, f._localizable_modes, c_localizable_modes)):
                f._SERIALIZE_localizable_modes = list(f._localizable_modes)
                STALE_INFO = True
            
            clocs = [] # custom_localizable_directives
            for cloc_elem in f_elem.getchildren():
                modes = xml_attr_str(cloc_elem, "modes")
                roles = xml_attr_str(cloc_elem, "roles") # ROLES_DEFAULT
                if cloc_elem.tag == "show":
                    clocs.append(show(modes=modes, roles=roles))
                elif cloc_elem.tag == "hide":
                    clocs.append(hide(modes=modes, roles=roles))
                else:
                    assert False, "Unknown directive [%s/%s] %s" % (
                        type_key, fname, cloc_elem.tag)
            if clocs:
                f.localizable[:] = clocs
                try: 
                    f.validate_localizable(
                        reference_localizable_modes=list(c_localizable_modes))
                except Exception, e:
                    # make error message more useful
                    raise e.__class__("Descriptor [%s] %s" % (type_key, e.message))
    
    if STALE_INFO:
        # Re-sync info-only attributes, by re-serializing AFTER that all 
        # descriptor classes have been localized
        write_custom(read_custom(),
            "\n".join(serialize_module(DESCRIPTOR_MODULE)))
        # re-localize, to ensure consistency
        localize_descriptors()
    
    log.warn("LOCALIZING DESCRIPTORS...\n           ...DONE [in %s seconds]" % (
        time()-start_time))


#####
# Generation of the default localization file

def serialize_loc(loc, depth=3, localizable_modes=[]):
    """(loc:show/hide directive) -> [str]
    """
    map = loc._repr_map()
    localizable_modes.extend(map["modes"])
    tag = map["tag"]
    modes = " ".join(map["modes"])
    roles = " ".join(map["roles"])
    ind = INDENT * depth
    acc = []
    if roles == ROLES_DEFAULT:
        # ALL targetted roles, no need to write them out, implied by no roles
        acc.append("""%s<%s modes="%s" />""" % (ind, tag, modes))
    else:
        acc.append("""%s<%s modes="%s" roles="%s" />""" % (
            ind, tag, modes, roles))
    return acc

def serialize_field(f, depth=2):
    """(f:Field) -> [str]
    """
    _acc = []
    field_localizable_modes = []
    
    # @modes
    display_modes = " ".join(f.modes)
    if hasattr(f, "_SERIALIZE_modes"):
        display_modes = " ".join(f._SERIALIZE_modes)
        del f._SERIALIZE_modes
    
    # @localizable
    for loc in f.localizable:
        _acc.extend(serialize_loc(loc, depth+1, field_localizable_modes))
    localizable_modes = " ".join(
        norm_sorted(field_localizable_modes, Field._modes))
    if hasattr(f, "_SERIALIZE_localizable_modes"):
        localizable_modes = " ".join(
            norm_sorted(f._SERIALIZE_localizable_modes, Field._modes))
        del f._SERIALIZE_localizable_modes
    
    acc = []
    ind = INDENT * depth
    if _acc:
        if localizable_modes:
            acc.append('%s<field name="%s" displayable="%s" localizable="%s">' % (
                ind, f.name, display_modes, localizable_modes))
        else:
            acc.append('%s<field name="%s" displayable="%s">' % (
                ind, f.name, display_modes))
        acc.extend(_acc)
        acc.append('%s</field>' % (ind))
    else:
        if localizable_modes:
            acc.append('%s<field name="%s" displayable="%s" localizable="%s" />' % (
                ind, f.name, display_modes, localizable_modes))
        else:
            acc.append('%s<field name="%s" displayable="%s" />' % (
                ind, f.name, display_modes))
    return acc

def serialize_cls(cls, depth=1):
    """(cls:ModelDescriptor) -> [str]
    
    Assumption: cls (subclass of ModelDescriptor) is localizable.
    """
    assert cls.__name__.endswith(DESCRIPTOR_CLASSNAME_POSTFIX)
    type_key = naming.un_camel(cls.__name__[0:-len(DESCRIPTOR_CLASSNAME_POSTFIX)])
    order = cls.order
    
    _acc = []
    for f in cls.fields:
        _acc.extend(serialize_field(f, depth+1))
    
    acc = []
    ind = INDENT * depth
    acc.append("")
    if _acc:
        if order != 999: # default "not ordered":
            acc.append('%s<descriptor name="%s" order="%s">' % (
                    ind, type_key, order))
        else:
            acc.append('%s<descriptor name="%s">' % (ind, type_key))
        acc.extend(_acc)
        acc.append('%s</descriptor>' % (ind))
    else:
        acc.append('%s<descriptor name="%s" />' % (ind, type_key))
    return acc

def serialize_module(module, depth=0):
    """Return a list of serialization strings, for localizable descriptor 
    classes in module.
    """
    _acc = []
    for dcls in localizable_descriptor_classes(module):
        _acc.extend(serialize_cls(dcls, depth=1))
    
    acc = []
    ind = INDENT * depth
    if _acc:
        acc.append('%s<ui roles="%s">' % (ind, ROLES_DEFAULT))
        acc.extend(_acc)
        acc.append("")
        acc.append("%s</ui>" % (ind))
    else:
        acc.append('%s<ui roles="%s" />' % (ind, ROLES_DEFAULT))
    acc.append("") # blank line at end of file
    acc.append("")
    return acc


if __name__ == "__main__":
    
    print "Processing localization file: %s" % (CUSTOM_PATH)
    persisted = read_custom()
    regenerated = "\n".join(serialize_module(DESCRIPTOR_MODULE))
    if persisted != regenerated:
        write_custom(persisted, regenerated)
    

