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
    #norm_sorted,
)
from bungeni.ui.descriptor import field
from bungeni.utils.capi import capi, bungeni_custom_errors
from bungeni.utils import naming, misc

# constants 

from bungeni.ui.descriptor import descriptor as DESCRIPTOR_MODULE

PATH_UI_FORMS_SYSTEM = capi.get_path_for("forms", "ui.xml")

ROLES_DEFAULT = " ".join(Field._roles)
INDENT = " " * 4


# utils

def check_reload_localization(event):
    """Called once_per_request on IBeforeTraverseEvent events (ui.publication)."""
    if capi.is_modified_since(PATH_UI_FORMS_SYSTEM):
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
    descriptor_cls_name = naming.descriptor_class_name(type_key)
    assert hasattr(module, descriptor_cls_name), \
        "Unknown descriptor [%s]" % (descriptor_cls_name)
    cls = getattr(module, descriptor_cls_name) # raises AttributeError
    assert is_descriptor(cls), \
        "Invalid descriptor [%s]" % (descriptor_cls_name)
    assert cls.localizable, \
        "May not localize a non-localizable descriptor [%s]" % (
            descriptor_cls_name)
    return cls

''' !+UNUSED
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
'''

@bungeni_custom_errors
def localize_descriptors():
    """Localizes descriptors from {bungeni_custom}/forms/ui.xml.
    
    Called by check_reload_localization() (that is routinely called by
    request event handling).
    """
    start_time = time()
    #for d in localizable_descriptor_classes(descriptor_module): ...
    xml = elementtree.ElementTree.fromstring(misc.read_file(PATH_UI_FORMS_SYSTEM))
    # make the value of <ui.@roles> as *the* bungeni default list of roles
    global ROLES_DEFAULT
    Field._roles[:] = xml.get("roles", ROLES_DEFAULT).split()
    # and reset global "constant"
    ROLES_DEFAULT = " ".join(Field._roles)
    
    import bungeni.alchemist
    import ore.alchemist.sa2zs
    def reset_zope_schema_properties_on_model_interface(descriptor_cls):
        __module__ = "bungeni.models.interfaces"
        type_key = naming.type_key("descriptor_class_name", descriptor_cls.__name__)
        ti = capi.get_type_info(type_key)
        domain_model = ti.domain_model
        sast = ore.alchemist.sa2zs.SQLAlchemySchemaTranslator()
        domain_table = bungeni.alchemist.utils.get_local_table(domain_model)
        # zope.schema field property map
        zsfp_map = sast.generateFields(domain_table, descriptor_cls)
        # apply manually overridden field properties
        sast.applyProperties(zsfp_map, descriptor_cls)
        # stuff back onto derived_table_schema
        derived_table_schema = ti.derived_table_schema
        assert len(derived_table_schema.names(all=False)) == len(zsfp_map)
        for name in derived_table_schema.names(all=False):
            assert name in zsfp_map
            # !+ zsfp == descriptor_cls.fields_by_name[name].property
            zsfp = zsfp_map[name]
            # !+property.__name__ needed downstream by 
            # zope.formlib.form.FormField __init__() does assert name !?!
            zsfp.__name__ = name
            # !+ cannot simply set the property directly on derived_table_schema:
            #   derived_table_schema[f.name] = zsfp
            # as this gives: 
            #   *** TypeError: 'InterfaceClass' object does not support item assignment
            # So we have to do workaround it !!
            derived_table_schema._InterfaceClass__attrs[name] = zsfp 
            derived_table_schema.changed(name)
    '''!+ reset_zope_schema_properties_on_model_interface
    Initially field.property IS derived_table_schema[f.name], and so if field config
    changes then the derived_table_schema has to be "kept ijn sync". 
    
    Above does it the "alchemist" way, but it could certainly be a lot simpler 
    and faster, at least for "repeat" syncing with changed fields. Examples:
    
    a) (if we ignore the issue of not being able to directly set property on 
    derived_table_schema) this could simply be done with something like:
    
        for f in cls.fields:
            if f.property is not None:
                derived_table_schema[f.name] = f.property
    
    b) it may (should!) be possible to make this completely dynamic... that is 
    to give the IIModelInterface interfaces the intelligence to always 
    dynamically pull the field.property directly!
    '''
    for edescriptor in xml.findall("descriptor"):
        type_key = misc.xml_attr_str(edescriptor, "name")
        order = misc.xml_attr_str(edescriptor, "order")
        # !+capi.get_type_info(type_key).descriptor_model
        cls = get_localizable_descriptor_class(DESCRIPTOR_MODULE, type_key)
        if order is not None:
            cls.order = int(order)
        
        # rebuild (in desired order) all fields from newly loaded configuration
        # !+ what about "removed" fields from a sys-descriptor config?
        fields = []
        for f_elem in edescriptor.findall("field"):
            # custom_localizable_directives
            clocs = []
            for cloc_elem in f_elem.getchildren():
                modes = misc.xml_attr_str(cloc_elem, "modes")
                roles = misc.xml_attr_str(cloc_elem, "roles") # ROLES_DEFAULT
                if cloc_elem.tag == "show":
                    clocs.append(show(modes=modes, roles=roles))
                elif cloc_elem.tag == "hide":
                    clocs.append(hide(modes=modes, roles=roles))
                else:
                    assert False, "Unknown directive [%s/%s] %s" % (
                        type_key, misc.xml_attr_str(f_elem, "name"), cloc_elem.tag)
            
            fields.append(field.F(
                    name=misc.xml_attr_str(f_elem, "name"),
                    label=misc.xml_attr_str(f_elem, "label"),
                    description=misc.xml_attr_str(f_elem, "description"),
                    required=misc.xml_attr_bool(f_elem, "required"),
                    localizable=clocs,
                    value_type=misc.xml_attr_str(f_elem, "value_type"),
                    render_type=misc.xml_attr_str(f_elem, "render_type"),
                    vocabulary=misc.xml_attr_str(f_elem, "vocabulary")
                ))
        
        # replace contents of descriptor cls fields list, retaining list instance
        cls.fields[:] = fields
        # validate/update descriptor model
        cls.sanity_check_fields()
        # push back on alchemist model interface
        reset_zope_schema_properties_on_model_interface(cls)
    
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

def serialize_cls(cls, depth=1):
    """(cls:ModelDescriptor) -> [str]
    
    Assumption: cls (subclass of ModelDescriptor) is localizable.
    """
    type_key = naming.type_key("descriptor_class_name", cls.__name__)
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
    print "Processing UI Field i18n MSGID file: %s" % (msgids_py_source_file_path)
    msgids_py_source_preamble = [
        "# automatically generated: dump_i18n_message_ids",
        "from bungeni.ui.i18n import _", 
        ""]
    msgids_py_source = "\n".join(msgids_py_source_preamble + [
            "_(%r)" % msgid for msgid in sorted(naming.MSGIDS) ])
    misc.check_overwrite_file(msgids_py_source_file_path, msgids_py_source)


if __name__ == "__main__":
    
    print "Processing localization file: %s" % (PATH_UI_FORMS_SYSTEM)
    regenerated = "\n".join(serialize_module(DESCRIPTOR_MODULE))
    misc.check_overwrite_file(PATH_UI_FORMS_SYSTEM, regenerated)
    dump_i18n_message_ids()

