# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Localization of Form Schema Descriptors

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.descriptor.localization")

#from lxml import etree
from bungeni import alchemist
from bungeni.alchemist.descriptor import (
    #ModelDescriptor,
    IModelDescriptor,
    Field,
    show, hide,
    #norm_sorted,
)
from bungeni.models import roles
from bungeni.ui.descriptor import field
from bungeni.capi import capi
from bungeni.utils import naming, misc

xas, xab, xai = misc.xml_attr_str, misc.xml_attr_bool, misc.xml_attr_int

# constants 

from bungeni.ui.descriptor import descriptor as DESCRIPTOR_MODULE

PATH_UI_FORMS_SYSTEM = capi.get_path_for("forms", "ui.xml")
ROLES_DEFAULT = " ".join(Field._roles)


####
# Load and apply forms localization --
# Localize descriptors from {bungeni_custom}/forms/.

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

def get_localizable_descriptor_class(module, type_key):
    """Retrieve an existing localizable descriptor class from module.
    AttributeError -> not existing, descriptor to be created.
    AssertionError -> exists but either not a descriptor cls or not localizable.
    """
    descriptor_cls_name = naming.descriptor_class_name(type_key)
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


@capi.bungeni_custom_errors
def check_reload_localization(event):
    """Called once on IWSGIApplicationCreatedEvent and (if in DEVMODE)
    once_per_request on IBeforeTraverseEvent events (ui.publication).
    """
    is_init = (event is None)
    if capi.is_modified_since(PATH_UI_FORMS_SYSTEM):
        localize_descriptors(PATH_UI_FORMS_SYSTEM, is_init)
    for type_key, ti in capi.iter_type_info(scope="custom"):
        check_reload_descriptor_file(type_key, is_init)


def check_reload_descriptor_file(type_key, is_init):
    """Check if a singel file has been modified and needs reloading.
    """
    #!+get_descriptor_elem
    file_path = capi.get_path_for("forms", "%s.xml" % (type_key))
    if capi.is_modified_since(file_path):
        descriptor_doc = capi.schema.validate_file_rng("descriptor", file_path)
        assert xas(descriptor_doc, "name") == type_key, type_key
        descriptor_cls = localize_descriptor(descriptor_doc, is_init, scope="custom")

def localize_descriptors(file_path, is_init):
    """Localizes descriptors from {file_path} [{bungeni_custom}/forms/..].
    """
    descriptor_doc = capi.schema.validate_file_rng("descriptor", file_path)
    # make the value of <ui.@roles> as *the* bungeni default list of roles
    global ROLES_DEFAULT
    #!+ROLES Field._roles[:] = capi.schema.qualified_roles(descriptor_doc.get("roles", ROLES_DEFAULT))
    Field._roles[:] = roles.SYSTEM_ROLES + roles.CUSTOM_ROLES
    # and reset global "constant" !+DECL ui.@roles must be set only once!
    ROLES_DEFAULT = " ".join(Field._roles)
    for edescriptor in descriptor_doc.findall("descriptor"):
        descriptor_cls = localize_descriptor(edescriptor, is_init)


def localize_descriptor(descriptor_elem, is_init, scope="system"):
    """Localize descriptor from descriptor XML element.
    Return the created/modified descriptor class.
    """
    type_key = xas(descriptor_elem, "name")
    ti = capi.get_type_info(type_key)
    
    # !+ ensure domain_model has already been set
    assert ti.domain_model, type_key
    
    order = xai(descriptor_elem, "order")
    fields = new_descriptor_fields(descriptor_elem)
    
    info_containers = [ parse_container(c_elem) 
        for c_elem in descriptor_elem.findall("container") ]
    
    integrity = descriptor_elem.find("integrity")
    if integrity is not None:
        constraints = [ capi.get_form_constraint(c) for c in
            xas(integrity, "constraints", "").split() ]
        validations = [ capi.get_form_validator(v) for v in 
            xas(integrity, "validations", "").split() ]
    else:
        constraints, validations = (), ()
    
    domain_model = ti.domain_model
    if scope=="custom":
        try:
            cls = update_descriptor_cls(type_key, order, 
                fields, info_containers, constraints, validations)
        except AttributeError:
            # first time around, no such descriptor - so create a new custom descriptor
            archetype_key = naming.polymorphic_identity(ti.archetype)
            cls = new_descriptor_cls(type_key, archetype_key, order, 
                fields, info_containers, constraints, validations)
            # only "push" onto cls (hiding same-named properties or overriding 
            # inherited setting) if set in the descriptor AND only on cls creation:
            if xas(descriptor_elem, "label"):
                cls.display_name = xas(descriptor_elem, "label")
            if xas(descriptor_elem, "container_label"):
                cls.container_name = xas(descriptor_elem, "container_label")
            if xas(descriptor_elem, "sort_on"):
                cls.sort_on = xas(descriptor_elem, "sort_on").split()
                # !+ assert each name is a field in the descriptor
            if xas(descriptor_elem, "sort_dir"): # default cls.sort_dir: "desc"
                cls.sort_dir = xas(descriptor_elem, "sort_dir")
            naming.MSGIDS.add(cls.display_name)
            naming.MSGIDS.add(cls.container_name)
            # this is guarenteed to execute maximum once per type_key
            alchemist.model.localize_domain_model_from_descriptor_class(domain_model, cls)
            #!+CATALYSE_SYSTEM_DESCRIPTORS -- all custom types are catalysed here!
            alchemist.catalyst.catalyse(ti)
    else:
        # non-custom
        cls = update_descriptor_cls(type_key, order, 
            fields, info_containers, constraints, validations)
        # ensures that this executes a maximum once per type_key
        if type_key in alchemist.model.localize_domain_model_from_descriptor_class.DONE:
            log.warn("Ignoring attempt to re-localize model [scope=%r] "
                "from descriptor for type %r", scope, type_key)
        else:
            alchemist.model.localize_domain_model_from_descriptor_class(domain_model, cls)
            #!+CATALYSE_SYSTEM_DESCRIPTORS -- all non-custom types have already 
            # catalysed on import of ui.descriptor, and may not "catalyse twice"
            # so just working around it by "calling" less of alchemist.catalyst.catalyse(ti)
            # Make ui.descriptor.catalyse_system_descriptors to be more selective,
            # and then catalyse remaining support types here?
            #alchemist.catalyst.catalyse(ti)
            #!+re-apply_security breaks edit event view (fields shown in view mode!)
            #alchemist.catalyst.apply_security(ti)
            alchemist.catalyst.generate_collection_traversal(ti)
    log.debug("Localized [init=%s] descriptor [%s] %s", is_init, type_key, ti)
    return cls


def parse_container(container_elem):
    target_type_key, rel_attr_name = xas(container_elem, "match").split(".", 1)
    return (
        xas(container_elem, "name") or naming.plural(target_type_key), 
        target_type_key, 
        rel_attr_name, 
        xas(container_elem, "indirect_key")
    )

def new_descriptor_fields(edescriptor):
    """(Re-)build (in desired order) all fields from newly loaded 
    descriptor configuration.
    # !+ what about "removed" fields from a sys-descriptor config?
    """
    type_key = xas(edescriptor, "name")
    fields = []
    for f_elem in edescriptor.findall("field"):
        name = xas(f_elem, "name")
        # custom_localizable_directives
        clocs = []
        for cloc_elem in f_elem.getchildren():
            modes = xas(cloc_elem, "modes")
            roles = capi.schema.qualified_roles(xas(cloc_elem, "roles", ROLES_DEFAULT))
            tag = cloc_elem.tag
            if tag == "show":
                clocs.append(show(modes=modes, roles=roles))
            elif tag == "hide":
                clocs.append(hide(modes=modes, roles=roles))
            elif isinstance(tag, basestring):
                raise ValueError(
                    "Unknown directive %r in field %r in descriptor %r" % (
                        cloc_elem.tag, name, type_key))
            else:
                pass # xml comment, ...
        
        fields.append(field.F(
                name=name,
                label=xas(f_elem, "label"),
                description=xas(f_elem, "description"),
                required=xab(f_elem, "required"),
                localizable=clocs,
                value_type=xas(f_elem, "value_type"),
                render_type=xas(f_elem, "render_type"),
                vocabulary=xas(f_elem, "vocabulary"),
                extended=xas(f_elem, "extended"),
                derived=xas(f_elem, "derived"),
            ))
    return fields

def new_descriptor_cls(type_key, archetype_key, order, 
        fields, info_containers, constraints, validations
    ):
    """Generate and setup new custom descriptor from configuration.
    """
    assert archetype_key, \
        "Custom descriptor %r does not specify an archetype" % (type_key)
    archetype = get_localizable_descriptor_class(DESCRIPTOR_MODULE, archetype_key)
    assert archetype.scope in ("archetype", "custom"), \
        "Custom descriptor %r specifies an invalid archetype %r" % (
            type_key, archetype_key)
    descriptor_cls_name = naming.descriptor_class_name(type_key)
    cls = type(descriptor_cls_name, (archetype,), {
            "scope": "custom",
            "__module__": DESCRIPTOR_MODULE.__name__,
            "order": order,
            "fields": fields,
            "info_containers": info_containers,
            "schema_invariants": constraints,
            "custom_validators": validations,
            "default_field_order": [ f.name for f in fields ],
        })
    # set on DESCRIPTOR_MODULE, register as the ti.descriptor_model
    setattr(DESCRIPTOR_MODULE, descriptor_cls_name, cls)
    ti = capi.get_type_info(type_key)
    ti.descriptor_model = cls
    log.info("generated descriptor [type=%s] %s.%s" % (
            type_key, DESCRIPTOR_MODULE.__name__, descriptor_cls_name))
    return cls

def update_descriptor_cls(type_key, order, 
        fields, info_containers, constraints, validations
    ):
    cls = get_localizable_descriptor_class(DESCRIPTOR_MODULE, type_key)
    if order is not None:
        cls.order = order
    # replace contents of descriptor cls fields list (retaining list 
    # instance) and validate/update descriptor model
    cls.fields[:] = fields
    cls.sanity_check_fields()
    cls.info_containers = info_containers
    cls.schema_invariants = constraints
    cls.custom_validators = validations
    # push back on alchemist model interface !+
    reset_zope_schema_properties_on_model_interface(cls)
    return cls

def reset_zope_schema_properties_on_model_interface(descriptor_cls):
    type_key = naming.type_key("descriptor_class_name", descriptor_cls.__name__)
    ti = capi.get_type_info(type_key)
    domain_model = ti.domain_model
    sast = alchemist.sa2zs.SQLAlchemySchemaTranslator()
    domain_table = alchemist.utils.get_local_table(domain_model)
    # zope.schema field property map
    zsfp_map = sast.generate_fields(domain_table, descriptor_cls)
    # apply manually overridden field properties
    sast.apply_properties(zsfp_map, descriptor_cls)
    # stuff back onto derived_table_schema
    derived_table_schema = ti.derived_table_schema
    assert set(derived_table_schema.names(all=False)) == set(zsfp_map), \
        "Incosistency in descriptor %r field lists:\n old:%s\n new:%s" % (
            type_key, 
            sorted(set(derived_table_schema.names(all=False))), 
            sorted(set(zsfp_map)))
    for name in derived_table_schema.names(all=False):
        # !+ zsfp == descriptor_cls.fields_by_name[name].property
        zsfp = zsfp_map[name]
        # !+property.__name__ needed downstream by 
        # zope.formlib.form.FormField __init__() does assert name !?!
        zsfp.__name__ = name
        # !+ cannot simply set the property directly on derived_table_schema:
        #   derived_table_schema[f.name] = zsfp
        # as this gives: 
        #   *** TypeError: 'InterfaceClass' object does not support item assignment
        # So we have to workaround it !!
        derived_table_schema._InterfaceClass__attrs[name] = zsfp
    # and we need to notify (only once) that the schema has changed 
    derived_table_schema.changed("localize_descriptors")
'''!+ reset_zope_schema_properties_on_model_interface
Initially field.property IS derived_table_schema[f.name], and so if field config
changes then the derived_table_schema has to be "kept in sync". 

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

