# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Localization of Form Schema Descriptors

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.descriptor.localization")

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

def write_custom(content):
    open(CUSTOM_PATH, "w").write(content.encode("utf-8"))

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
    """A generator of localizable descriptor classes conatined in module.
    """
    for key in dir(module):
        cls = getattr(module, key)
        if is_descriptor(cls):
            if cls.localizable:
                yield cls


####
# Localize descriptors from {bungeni_custom}/forms/ui.xml.

def get_localizable_descriptor_class(module, name):
    descriptor_cls_name = "%s%s" % (name, DESCRIPTOR_CLASSNAME_POSTFIX)
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


@bungeni_custom_errors
def localize_descriptors():
    """Localizes descriptors from {bungeni_custom}/forms/ui.xml.
    Called when .localize is imported.
    """
    #for d in localizable_descriptor_classes(descriptor_module): ...
    xml = elementtree.ElementTree.fromstring(read_custom())
    # make the value of <ui.@roles> as *the* bungeni default list of roles
    Field._roles[:] = xml.get("roles", ROLES_DEFAULT).split()
    for descriptor_elem in xml.findall("descriptor"):
        dname = descriptor_elem.get("name")
        cls = get_localizable_descriptor_class(DESCRIPTOR_MODULE, dname)
        field_elems = descriptor_elem.findall("field")
        field_by_name = {}
        reorder_fields(cls, [f.get("name") for f in field_elems], field_by_name)
        for f_elem in field_elems:
            fname = f_elem.get("name")
            f = field_by_name[fname]
            # assert that info-only field attributes have not been changed:
            cval = f_elem.get("modes").split()
            assert set(f.modes) == set(cval), (
                "Field [%s] modifies information-only attribute [modes]: "
                "\n B: %s\n C: %s" % (fname, f.modes, cval))
            cval = set(f_elem.get("localizable", "").split())
            assert f._localizable_modes == cval, (
                "Field [%s] modifies information-only attribute [localizable]: "
                "\n B: %s\n C: %s" % (fname, f._localizable_modes, cval))
            bungeni_localizable_modes = [ blm for blm in f._localizable_modes ]
            clocs = []
            for cloc_elem in f_elem.getchildren():
                modes = cloc_elem.get("modes", None)
                roles = cloc_elem.get("roles", None) # ROLES_DEFAULT
                if cloc_elem.tag == "show":
                    clocs.append(show(modes=modes, roles=roles))
                elif cloc_elem.tag == "hide":
                    clocs.append(hide(modes=modes, roles=roles))
                else:
                    assert False, "Unknown directive [%s/%s] %s" % (
                        dname, fname, cloc_elem.tag)
            if clocs:
                f.localizable[:] = clocs
                f.validate_localizable(
                    reference_localizable_modes=bungeni_localizable_modes)


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
    for loc in f.localizable:
        _acc.extend(serialize_loc(loc, depth+1, field_localizable_modes))
    localizable_modes = " ".join(
        norm_sorted(field_localizable_modes, Field._modes))
    display_modes = " ".join(f.modes)
    
    acc = []
    ind = INDENT * depth
    if _acc:
        if localizable_modes:
            acc.append('%s<field name="%s" modes="%s" localizable="%s">' % (
                ind, f.name, display_modes, localizable_modes))
        else:
            acc.append('%s<field name="%s" modes="%s">' % (
                ind, f.name, display_modes))
        acc.extend(_acc)
        acc.append('%s</field>' % (ind))
    else:
        if localizable_modes:
            acc.append('%s<field name="%s" modes="%s" localizable="%s" />' % (
                ind, f.name, display_modes, localizable_modes))
        else:
            acc.append('%s<field name="%s" modes="%s" />' % (
                ind, f.name, display_modes))
    return acc

def serialize_cls(cls, depth=1):
    """(cls:ModelDescriptor) -> [str]
    
    Assumption: cls (subclass of ModelDescriptor) is localizable.
    """
    assert cls.__name__.endswith(DESCRIPTOR_CLASSNAME_POSTFIX)
    name = cls.__name__[0:-len(DESCRIPTOR_CLASSNAME_POSTFIX)]
    
    _acc = []
    for f in cls.fields:
        _acc.extend(serialize_field(f, depth+1))
    
    acc = []
    ind = INDENT * depth
    acc.append("")
    if _acc:
        acc.append('%s<descriptor name="%s">' % (ind, name))
        acc.extend(_acc)
        acc.append('%s</descriptor>' % (ind))
    else:
        acc.append('%s<descriptor name="%s" />' % (ind, name))
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
    
    from bungeni.ui.utils import debug
    print "Processing localization file: %s" % (CUSTOM_PATH)
    persisted = read_custom()
    regenerated = "\n".join(serialize_module(DESCRIPTOR_MODULE))
    if persisted != regenerated:
        print "*** OVERWRITING:"
        print debug.unified_diff(persisted, regenerated, CUSTOM_PATH, "NEW")
        write_custom(regenerated)
    

