# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Localization of Form Schema Descriptors

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.descriptor.localization")

from time import time
import elementtree.ElementTree
from zope.component import getUtilitiesFor
from zope.securitypolicy.interfaces import IRole
from zope.configuration import xmlconfig

from bungeni.alchemist.model import (
    #ModelDescriptor, 
    IModelDescriptor,
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
    """Called once_per_request on IBeforeTraverseEvent events (ui.publication)."""
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
    descriptor_cls_name = naming.descriptor_cls_name_from_type_key(type_key)
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
            # !+decl label description required value_type render_type vocabulary
            
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
                    f.validate_localizable()
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
# Generation of the default localization file -- this code executes only 
# when this module is run as a standalone process.

def get_defined_roles():
    zcml_slug = """<configure xmlns="http://namespaces.zope.org/zope">
        <include package="zope.component" file="meta.zcml" />
        <includeOverrides package="repoze.whooze" file="overrides.zcml" />
        <include package="zope.app.security" />
        <include package="bungeni.server" />
        <include package="bungeni" file="security.zcml"/>
    </configure>
    """
    xmlconfig.string(zcml_slug)
    system_roles = ["zope.Manager"]
    return [ name for name, role in getUtilitiesFor(IRole)
        if name not in system_roles ]

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
            else: # should all be str
                attr_strs.append(attr_tmpl % (name, value))
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

def serialize_cls(cls, depth=1):
    """(cls:ModelDescriptor) -> [str]
    
    Assumption: cls (subclass of ModelDescriptor) is localizable.
    """
    type_key = naming.type_key_from_descriptor_cls_name(cls.__name__)
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
    roles = " ".join(get_defined_roles())
    if _acc:
        acc.append('%s<ui roles="%s">' % (ind, roles))
        acc.extend(_acc)
        acc.append("")
        acc.append("%s</ui>" % (ind))
    else:
        acc.append('%s<ui roles="%s" />' % (ind, roles))
    acc.append("") # blank line at end of file
    acc.append("")
    return acc


def dump_i18n_message_ids():
    """Dump msgids from Descriptor Field labels and descriptions
    for internationalization.
    """
    from os import path
    msgids_py_source_file_path = path.join(
        path.dirname(path.abspath(__file__)), "_dumped_msgids.py")
    msgids_py_source_preamble = [
        "# automatically generated: dump_i18n_message_ids",
        "from bungeni.ui.i18n import _", 
        ""]
    msgids_py_source = "\n".join(msgids_py_source_preamble + [
            "_(%r)" % msgid for msgid in sorted(naming.MSGIDS) ])
    open(msgids_py_source_file_path, "w").write(msgids_py_source.encode("utf-8"))
    print "Descriptor Field message IDs:", msgids_py_source_file_path
    print msgids_py_source


if __name__ == "__main__":
    
    print "Processing localization file: %s" % (CUSTOM_PATH)
    persisted = read_custom()
    regenerated = "\n".join(serialize_module(DESCRIPTOR_MODULE))
    if persisted != regenerated:
        write_custom(persisted, regenerated)
    dump_i18n_message_ids()

