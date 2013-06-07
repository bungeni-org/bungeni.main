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

import bungeni.ui.descriptor.descriptor as DESCRIPTOR_MODULE
import bungeni.ui.forms.viewlets as VIEWLET_MODULE


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

def get_localizable_descriptor_class(module, descriptor_key):
    """Retrieve an existing localizable descriptor class from module.
    AttributeError -> not existing, descriptor to be created.
    AssertionError -> exists but either not a descriptor cls or not localizable.
    """
    descriptor_cls_name = naming.descriptor_class_name(descriptor_key)
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


def update_new_descriptor_cls_from_ti(ti):
    # only "push" label/container_label onto descriptor cls (hiding 
    # same-named properties or overriding inherited setting) if set 
    # on type info AND only on cls creation:
    cls = ti.descriptor_model
    # display_name
    if ti.label is not None:
        cls.display_name = ti.label
        # register i18n msgid for descriptor display_name
        naming.MSGIDS.add(cls.display_name)
    else:
        # !+TypeError: 'dictproxy' object does not support item deletion
        assert "display_name" not in cls.__dict__, \
            "Type %r re-use of descriptor must re-set @label" % (ti.type_key)
        # clear any "cloned over' customization of this
        if cls.__dict__.has_key("display_name"):
            del cls.__dict__["display_name"]
    # container_name
    if ti.container_label is not None:
        cls.container_name = ti.container_label
        # register i18n msgid for descriptor container_name
        naming.MSGIDS.add(cls.container_name)
    else:
        # !+TypeError
        assert "container_name" not in cls.__dict__, \
            "Type %r re-use of descriptor must re-set @container_label" % (ti.type_key)


def forms_localization_init():
    """Called once on IWSGIApplicationCreatedEvent.
    """
    # first create / update descriptor classes as per config
    forms_localization_check_reload(None)
    
    # then, do the once-only update of each domain model
    for type_key, ti in capi.iter_type_info(scope="system"):
        alchemist.model.localize_domain_model_from_descriptor_class(
            ti.domain_model, ti.descriptor_model)
        #!+CATALYSE_SYSTEM_DESCRIPTORS -- all non-custom types have already 
        # catalysed on import of ui.descriptor, and may not "catalyse twice"
        # so just working around it by "calling" less of alchemist.catalyst.catalyse(ti)
        # Make ui.descriptor.catalyse_system_descriptors to be more selective,
        # and then catalyse remaining support types here?
        #alchemist.catalyst.catalyse(ti)
        #!+re-apply_security breaks edit event view (fields shown in view mode!)
        #alchemist.catalyst.apply_security(ti)
        alchemist.catalyst.generate_collection_traversal(ti)
    
    for type_key, ti in capi.iter_type_info(scope="custom"):
        alchemist.model.localize_domain_model_from_descriptor_class(
            ti.domain_model, ti.descriptor_model)
        alchemist.catalyst.catalyse(ti)


@capi.bungeni_custom_errors
def forms_localization_check_reload(event):
    """Called once from forms_localization_init() and (if in DEVMODE)
    once_per_request on IBeforeTraverseEvent events (ui.publication).
    !+ note: switching descriptor on a type config requires restart!
    """
    # a cache of descriptor elems, to be able to update "re-used" descriptors
    DESC_ELEMS_MODIFIED_SINCE = {}
    # "sys" descriptors, if PATH_UI_FORMS_SYSTEM is modified (or not yet loaded)
    if capi.is_modified_since(PATH_UI_FORMS_SYSTEM):
        descriptor_doc = capi.schema.validate_file_rng("descriptor", PATH_UI_FORMS_SYSTEM)
        Field._roles[:] = roles.SYSTEM_ROLES + roles.CUSTOM_ROLES
        # reset global "constant" ROLES_DEFAULT
        global ROLES_DEFAULT
        ROLES_DEFAULT = " ".join(Field._roles)
        for edescriptor in descriptor_doc.findall("descriptor"):
            type_key = xas(edescriptor, "name")
            descriptor_cls = localize_descriptor(type_key, edescriptor)
            DESC_ELEMS_MODIFIED_SINCE[type_key] = edescriptor
    
    for type_key, ti in capi.iter_type_info(scope="custom"):
        # only check "dedicated" descriptor files
        if ti.descriptor_key == type_key:
            # ok, check if dedicated descriptor file has been modified (or not yet loaded)
            #!+get_descriptor_elem
            file_path = capi.get_path_for("forms", "%s.xml" % (type_key))
            if capi.is_modified_since(file_path):
                descriptor_elem = capi.schema.validate_file_rng("descriptor", file_path)
                descriptor_cls = localize_descriptor(type_key, descriptor_elem, scope="custom")
                DESC_ELEMS_MODIFIED_SINCE[type_key] = descriptor_elem
        else:
            # re-using another descriptor...
            if ti.descriptor_key in DESC_ELEMS_MODIFIED_SINCE:
                descriptor_elem = DESC_ELEMS_MODIFIED_SINCE[ti.descriptor_key]
                descriptor_cls = localize_descriptor(type_key, descriptor_elem, scope="custom")
    
    DESC_ELEMS_MODIFIED_SINCE.clear()


def localize_descriptor(type_key, descriptor_elem, scope="system"):
    """Localize descriptor from descriptor XML element.
    Return the created/modified descriptor class.
    """
    ti = capi.get_type_info(type_key)
    # !+ ensure domain_model has already been set
    assert ti.domain_model, type_key
    
    order = xai(descriptor_elem, "order")
    fields = new_descriptor_fields(descriptor_elem)
    
    _info_containers = [ 
        new_info_container(seq + 1, c_elem)
        for (seq, c_elem) in enumerate(descriptor_elem.findall("container")) ]
    info_containers = [ 
        ic for ic in _info_containers
        if capi.has_type_info(ic.target_type_key) ]
    for ic in _info_containers:
        if ic not in info_containers:
            # target type not enabled
            log.warn("Ignoring %r container property %r to disabled type: %s.%s", 
                type_key, ic.container_attr_name, ic.target_type_key, ic.rel_attr_name)
    
    integrity = descriptor_elem.find("integrity")
    if integrity is not None:
        constraints = [ capi.get_form_constraint(c) for c in
            xas(integrity, "constraints", "").split() ]
        validations = [ capi.get_form_validator(v) for v in 
            xas(integrity, "validations", "").split() ]
    else:
        constraints, validations = (), ()
    
    if scope=="custom":
        try:
            cls = update_descriptor_cls(type_key, order, 
                fields, info_containers, constraints, validations)
        except AttributeError:
            # first time around, no such descriptor - so create a new custom descriptor
            archetype_key = naming.polymorphic_identity(ti.archetype)
            cls = new_descriptor_cls(type_key, archetype_key, order, 
                fields, info_containers, constraints, validations)
            if xas(descriptor_elem, "sort_on"):
                cls.sort_on = xas(descriptor_elem, "sort_on").split()
                # !+ assert each name is a field in the descriptor
            if xas(descriptor_elem, "sort_dir"): # default cls.sort_dir: "desc"
                cls.sort_dir = xas(descriptor_elem, "sort_dir")
            update_new_descriptor_cls_from_ti(ti)
        
        # finish model/descriptor setup from feature configuration
        for feature in ti.workflow.features:
            feature.setup_ui(ti.domain_model)
        # custom container viewlets
        for i, ic in enumerate(ti.descriptor_model.info_containers):
            if ic.viewlet:
                sfv_cls = new_container_sub_form_viewlet_cls(ti.type_key, ic)
    
    else:
        # non-custom
        cls = update_descriptor_cls(type_key, order, 
            fields, info_containers, constraints, validations)
    log.debug("Localized descriptor [%s] %s", type_key, ti)
    return cls


class InfoContainer(object):
    def __init__(self, container_attr_name, target_type_key, rel_attr_name, 
            indirect_key, seq, _origin, viewlet=True,
        ):
        self.container_attr_name = container_attr_name
        self.target_type_key = target_type_key
        self.rel_attr_name = rel_attr_name
        self.indirect_key = indirect_key
        self.seq = seq
        self.viewlet = viewlet # bool
        self.viewlet_name = None # set on viewlet cls creation
        self._origin = _origin # "feature" | "container"
    def __str__(self):
        return misc.named_repr(self, self.container_attr_name)
    __repr__ = __str__

def new_info_container(seq, container_elem):
    # !+ @view_title:i18n_key, @view_id:token, @weight:int ?
    target_type_key, rel_attr_name = xas(container_elem, "match").split(".", 1)
    return InfoContainer(
        xas(container_elem, "name") or naming.plural(target_type_key), 
        target_type_key, 
        rel_attr_name,
        xas(container_elem, "indirect_key"),
        seq * 100, # !+INFO_CONTAINER_SEQ a "largish" seq for "container" containers
        "container",
        viewlet=xab(container_elem, "viewlet", False),
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
            roles = capi.schema.qualified_roles(xas(cloc_elem, "roles", ROLES_DEFAULT).split())
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
    archetype_ti = capi.get_type_info(archetype_key)
    archetype_descriptor_key = archetype_ti.descriptor_key or archetype_ti.type_key
    descriptor_archetype = \
        get_localizable_descriptor_class(DESCRIPTOR_MODULE, archetype_descriptor_key)
    assert descriptor_archetype.scope in ("archetype", "custom"), \
        "Custom descriptor %r specifies an invalid archetype %r" % (
            type_key, archetype_key)
    descriptor_cls_name = naming.descriptor_class_name(type_key)
    cls = type(descriptor_cls_name, (descriptor_archetype,), {
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


def new_container_sub_form_viewlet_cls(type_key, info_container):
    """Generate a new viewlet class for this custom container attribute.
    """
    info_container.viewlet_name = \
        container_sub_form_viewlet_cls_name(type_key, info_container)
    cls = type(info_container.viewlet_name, (VIEWLET_MODULE.SubformViewlet,), {
        "sub_attr_name": info_container.container_attr_name,
        "weight": (1 + info_container.seq) * 10,
    })
    # set on VIEWLET_MODULE
    setattr(VIEWLET_MODULE, info_container.viewlet_name, cls)
    return cls

def container_sub_form_viewlet_cls_name(type_key, info_container):
    return "_".join(["SFV", type_key, info_container.container_attr_name])


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

