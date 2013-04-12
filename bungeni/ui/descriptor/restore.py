# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Restore the default forms localization file -- 
utility module, intended to be executed as a standalone process.

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.descriptor.localization")

from bungeni.utils import naming, misc
from bungeni.ui.descriptor import localization

INDENT = " " * 4


def serialize_roles(roles):
    """(roles:[qualified_role_id] -> space-separated-str of names
    Reduce each "bungeni.Role" or ".Role" to "Role".
    """
    names = []
    for name in roles:
        if name.startswith("bungeni."):
            name = name[8:]
        elif name.startswith("."):
            name = name[1:]
        names.append(name)
    return " ".join(names)


def localizable_descriptor_classes(module):
    """A generator of localizable descriptor classes contained in module.
    """
    for key in dir(module): # alphabetic key order
        cls = getattr(module, key)
        if localization.is_descriptor(cls):
            if cls.localizable:
                yield cls

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
    if roles == localization.ROLES_DEFAULT:
        # ALL targetted roles, no need to write them out, implied by no roles
        acc.append("""%s<%s modes="%s" />""" % (ind, tag, modes))
    else:
        acc.append("""%s<%s modes="%s" roles="%s" />""" % (
            ind, tag, modes, serialize_roles(roles.split())))
    return acc

def serialize_field(f, depth=2):
    """(f:Field) -> [str]
    """
    _acc = []
    field_localizable_modes = []
        
    # @localizable
    for loc in f.localizable:
        _acc.extend(serialize_loc(loc, depth+1, field_localizable_modes))
    
    # serialize decl attrs
    attr_strs = []
    attr_tmpl = '%s="%s"'
    for name, value in f._decl:
        if value is not None:
            if isinstance(value, bool):
                attr_strs.append(attr_tmpl % (name, str(value).lower()))
            elif isinstance(value, basestring):
                attr_strs.append(attr_tmpl % (name, value))
            else:
                raise ValueError("Field [name=%s] _decl attribute [%s] "
                    "is NOT serialized as an XML attribute" % (
                        f.name, attr_tmpl % (name, value)))
    decl_attrs = " ".join(attr_strs)
    
    acc = []
    ind = INDENT * depth
    if _acc:
        acc.append('%s<field %s>' % (ind, decl_attrs))
        acc.extend(_acc)
        acc.append('%s</field>' % (ind))
    else:
        acc.append('%s<field %s />' % (ind, decl_attrs))
    return acc

def serialize_integrity(schema_invariants, custom_validators, depth=2):
    acc = []
    ind = INDENT * depth
    attr_strs = []
    attr_tmpl = '%s="%s"'
    if schema_invariants:
        attr_strs.append(attr_tmpl % ("constraints", 
                " ".join([c.__name__ for c in schema_invariants ])))
    if custom_validators:
        attr_strs.append(attr_tmpl % ("validations",
                " ".join([c.__name__ for c in custom_validators ])))
    if attr_strs:
        acc.append("%s<integrity %s />" % (ind, " ".join(attr_strs)))
    return acc

def serialize_cls(cls, depth=1):
    """(cls:ModelDescriptor) -> [str]
    
    Assumption: cls (subclass of ModelDescriptor) is localizable.
    """
    type_key = naming.type_key("descriptor_class_name", cls.__name__)
    _acc = []
    for f in cls.fields:
        _acc.extend(serialize_field(f, depth+1))
    _acc.extend(serialize_integrity(
            cls.schema_invariants, cls.custom_validators, depth+1))
    
    acc = []
    ind = INDENT * depth
    acc.append(ind)
    if _acc:
        if cls.order != 999: # default "not ordered":
            acc.append('%s<descriptor name="%s" order="%s">' % (
                    ind, type_key, cls.order))
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
        # only serialize non-custom descriptors
        if dcls.scope in ("system", "archetype"):
            _acc.extend(serialize_cls(dcls, depth=1))
    
    acc = []
    ind = INDENT * depth
    if _acc:
        acc.append('%s<?xml version="1.0"?>' % (ind))
        acc.append("%s<ui>" % (ind))
        acc.extend(_acc)
        acc.append(ind)
        acc.append("%s</ui>" % (ind))
    else:
        acc.append("%s<ui />" % (ind))
    acc.append(ind) # blank line at end of file
    acc.append(ind)
    return acc


def reset_localization_system_descriptors():
    print
    print "Processing localization file: %s" % (localization.PATH_UI_FORMS_SYSTEM)
    regenerated = "\n".join(serialize_module(localization.DESCRIPTOR_MODULE))
    misc.check_overwrite_file(localization.PATH_UI_FORMS_SYSTEM, regenerated)


def dump_i18n_message_ids():
    """Dump msgids from Descriptor Field labels and descriptions
    for internationalization.
    """
    # ensure localization files are loaded (and naming.MSGIDS correctly primed)
    from bungeni.ui import feature
    feature.setup_customization_ui()
    #localization.check_reload_localization(None) #!+ AssertionError from custom roles...
    from os import path
    import bungeni.ui # !+ simply using __file__ gives erroneous abspath!
    msgids_py_source_file_path = path.join(
        path.dirname(path.abspath(bungeni.ui.__file__)), "descriptor", "_dumped_msgids.py")
    
    print
    print "Processing UI Field i18n MSGID file: %s" % (msgids_py_source_file_path)
    msgids_py_source_preamble = [
        "# automatically generated: dump_i18n_message_ids",
        "from bungeni.ui.i18n import _", 
        ""]
    msgids_py_source = "\n".join(msgids_py_source_preamble + [
            "_(%r)" % msgid for msgid in sorted(naming.MSGIDS) ])
    misc.check_overwrite_file(msgids_py_source_file_path, msgids_py_source)


if __name__ == "__main__":    
    reset_localization_system_descriptors()
    dump_i18n_message_ids()

