# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist catalyst

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


# List everything from this module intended for package-external use.
__all__ = [
    "catalyse_system_descriptors"
]

# from bungeni.alchemist, used only here

from bungeni.alchemist.interfaces import (
    IAlchemistContent,
    IAlchemistContainer,
    IManagedContainer,
    IIModelInterface,
)
from bungeni.alchemist.container import AlchemistContainer
from bungeni.alchemist.traversal import CollectionTraverser, ManagedContainerDescriptor
from bungeni.alchemist.sa2zs import transmute
from bungeni.alchemist import utils

#

from zope import interface, component
from zope.app.security.protectclass import (
        protectName, # !+remove
        protectSetAttribute, 
        protectLikeUnto
)
from zope.publisher.interfaces import IPublisherRequest, IPublishTraverse
from z3c.traverser.interfaces import ITraverserPlugin
from z3c.traverser.traverser import PluggableTraverser

from sqlalchemy import orm
from bungeni.utils import naming
# target modules
import bungeni.models.interfaces as INTERFACE_MODULE
import bungeni.models.domain as MODEL_MODULE
import bungeni.models.domain as CONTAINER_MODULE
#import bungeni.ui.content as UI_MODULE


def validate_required_fields(ti):
    """Raise a ValueError if a field is not required in ui but required in db.
    """
    mapper = orm.class_mapper(ti.domain_model)
    if not mapper: 
        return
    type_name = ti.workflow_key or naming.polymorphic_identity(ti.domain_model)
    for field_name, field in ti.descriptor_model.fields_by_name.iteritems():
        if field.property and not field.property.required:
            column = mapper.columns.get(field_name)
            if column is not None:
                if column.nullable == False:
                    raise ValueError("Descriptor %r field %r is required in "
                        "the db. Must set to be required." % (
                            type_name, field_name))


def catalyse_system_descriptors(module):
    """Catalyze system descriptor classes (with by-name-convention associated 
    model class) in specified module.
    
    Called when ui.descriptor is initially imported, so before descriptors for 
    custom types have been created (that happens on first call to 
    localization.localize_descriptors on application created event).
    
    !+CATALYSE_SYSTEM_DESCRIPTORS(mr, feb-2013) drop this, reworking it into
    catalysing on first time to localize each descriptor.
    """
    import sys
    import inspect
    from bungeni.alchemist.descriptor import IModelDescriptor
    from bungeni.capi import capi
    from bungeni.ui.utils import debug
    
    def descriptor_classes():
        """A generator of descriptor classes in this module, preserving the
        order of definition.
        """
        # dir() returns names in alphabetical order
        decorated = []
        for key in dir(module):
            cls = getattr(module, key)
            try:
                assert IModelDescriptor.implementedBy(cls)
                # we decorate with the source code line number for the cls
                decorated.append((inspect.getsourcelines(cls)[1], cls))
            except (TypeError, AttributeError, AssertionError):
                debug.log_exc(sys.exc_info(), log_handler=log.debug)
        # we yield each cls in order of definition
        for cls in [ cls for (line_num, cls) in sorted(decorated) ]:
            yield cls
    
    def is_model_mapped(domain_model):
        # try get mapper to force UnmappedClassError
        try:
            orm.class_mapper(domain_model)
            return True
        except orm.exc.UnmappedClassError:
            # unmapped class e.g. Version
            return False
    
    for descriptor_model in descriptor_classes():
        descriptor_name = descriptor_model.__name__
        type_key = naming.type_key("descriptor_class_name", descriptor_name)
        # Associate each descriptor to the dedicated domain type via naming 
        # convention, and only catalyse (descriptor, model) pairs 
        # for which the domain type is mapped. Otherwise, ignore.
        domain_model = getattr(MODEL_MODULE, naming.model_name(type_key), None)
        if not (domain_model and is_model_mapped(domain_model)):
            log.warn("Not catalysing: %s", descriptor_name)
            continue
        # type_info, register descriptor_model, domain_model
        ti = capi.get_type_info(type_key)
        utils.inisetattr(ti, "domain_model", domain_model)
        utils.inisetattr(ti, "descriptor_model", descriptor_model)
        # catalyse each (domain_model, descriptor_model) pair
        catalyse(ti)
    
    # !+remove?
    m = "\n\nDone all setup of system types... running with:\n\n%s\n\n" % (
            "\n\n".join(sorted(
                [ "%s: %s" % (key, ti) for key, ti in capi.iter_type_info() ])
            ))
    log.debug(m)


def catalyse(ti):
    """Called from catalyse_system_descriptors here (for system descriptors) 
    AND from ui.descriptor.localization.new_descriptor_cls for custom types.
    """
    type_key = naming.polymorphic_identity(ti.domain_model)
    log.info(" ----- CATALYSE: %s -----", type_key) 
    log.debug("ti = %s", ti)
    validate_required_fields(ti)
    generate_table_schema_interface(ti)
    apply_security(ti)
    generate_container_class(ti)
    generate_collection_traversal(ti)
    return ti


def generate_table_schema_interface(ti):
    '''!+DO_NOT_REORDER_USER_APPLIED_INTERFACES
    def get_domain_interfaces(domain_model):
        """Return the domain bases for an interface as well as a filtered 
        implements only list (base interfaces removed).
        
        Note that for 2nd level (mapped) domain classes i.e. those that inherit
        from another domain class e.g. Event(Doc), Office(Group), 
        OfficeMember(GroupMembership), an IIModelInterface-providing 
        I*TableSchema interface had already been created (for base class) and 
        assigned to the super class--and that interface will match as one of 
        the domain_base interfaces here.
        """
        domain_bases = []
        domain_implements = []
        for iface in interface.implementedBy(domain_model):
            if IIModelInterface.providedBy(iface):
                domain_bases.append(iface)
            else:
                domain_implements.append(iface)
        domain_bases = tuple(domain_bases) or (IAlchemistContent,)
        return domain_bases, domain_implements
    bases, implements = get_domain_interfaces(ti.domain_model)
    '''
    
    # derived_table_schema:
    # - ALWAYS dynamically generated
    # - directlyProvides IIModelInterface (by virtue of IAlchemistContent)
    type_key = naming.polymorphic_identity(ti.domain_model)
    # use the class's mapper select table as input for the transformation
    table_schema_interface_name = naming.table_schema_interface_name(type_key)
    domain_table = utils.get_local_table(ti.domain_model)
    
    derived_table_schema = transmute(
        domain_table,
        annotation=ti.descriptor_model,
        interface_name=table_schema_interface_name,
        __module__=INTERFACE_MODULE.__name__,
        #_generated_by="bungeni.alchemist.catalyst.generate_table_schema_interface"
        #bases=bases)
        bases=(IAlchemistContent,))
    
    # apply, register on type_info, set on module
    interface.classImplements(ti.domain_model, derived_table_schema)
    utils.inisetattr(ti, "derived_table_schema", derived_table_schema)
    setattr(INTERFACE_MODULE, table_schema_interface_name, derived_table_schema)
    log.info("generate_table_schema_interface: %s", derived_table_schema)
    
    # defensive sanity check - that derived_table_schema is precisely the FIRST
    # resolving IIModelInterface-providing interface implemented by domain_model
    # !+ this failing does not necessarily mean an incorrectness
    for iface in interface.implementedBy(ti.domain_model):
        if IIModelInterface.providedBy(iface):
            assert iface is derived_table_schema, (ti.domain_model, 
                iface, id(iface), 
                derived_table_schema, id(derived_table_schema))
            break
    
    '''!+DO_NOT_REORDER_USER_APPLIED_INTERFACES
    # prepend derived_table_schema, register on type_info, set on INTERFACE_MODULE
    implements.insert(0, derived_table_schema)

    # if a conventionally-named domain interface exists, domain model must implement it
    model_interface_name = naming.model_interface_name(type_key)
    model_interface = getattr(INTERFACE_MODULE, model_interface_name, None)
    if model_interface is not None:
        assert model_interface in implements, model_interface        
    
    # apply implemented interfaces
    interface.classImplementsOnly(ti.domain_model, *implements)
    '''


def apply_security(ti):
    domain_model, descriptor_model = ti.domain_model, ti.descriptor_model
    type_key = naming.polymorphic_identity(domain_model)
    log.debug("APPLY SECURITY: %s %s", type_key, domain_model)
    # first, "inherit" security settings of super classes i.e. equivalent of 
    # something like <require like_class=".domain.Doc" />
    for c in domain_model.__bases__:
        if c is object:
            continue
        log.debug("    LIKE_CLASS: %s", c)
        protectLikeUnto(domain_model, c)
    
    # !+DECL permissions here--for CUSTOM types only, and SINCE r9946--override
    # what is defined in domain.zcml, as opposed to vice-versa (probably 
    # because CUSTOM types are setup at a later stage). 
    # So (for CUSTOM types only?) we use the parametrized 
    # bungeni.{type_key}.{Mode} as the view/edit permission:
    pv_type = "zope.Public" # view permission, for type
    pe_type = "zope.Public" # edit permission, for type
    if descriptor_model.scope == "custom":
        pv_type = "bungeni.%s.View" % (type_key)
        pe_type = "bungeni.%s.Edit" % (type_key)
    
    # !+SCHEMA_FIELDS(mr, oct-2012) all this seems superfluous anyway, as is 
    # (always?) overwritten further down? Switch to base loop on superset of 
    # names (dir(cls)?) and then decide ONCE on various criteria how to
    # protect the name.
    _view_protected = set() # remember names protected for view
    _edit_protected = set() # remember names protected for edit
    
    # sorted (for clearer logging) list of attr names that are BOTH defined
    # by the db mapped-table schema AND have a dedicated UI Field.
    dts_attrs = [ n for n in ti.derived_table_schema.names(all=True) ]
    df_attrs = [ f.get("name") for f in descriptor_model.fields ]
    attrs = sorted(set(dts_attrs).union(set(df_attrs)))
    
    log.debug("    DTS+Fields: %s, %s", 
        ti.derived_table_schema.__name__, descriptor_model.__name__)
    for n in attrs:
        # !+DECL special cases, do not override domain.zcml...
        if n in ("response_text",):
            continue
        _view_protected.add(n); _edit_protected.add(n)
        pv = pv_type
        pe = pe_type
        model_field = descriptor_model.get(n)
        if model_field:
            if descriptor_model.scope != "custom":
                # !+DECL proceed as before for now
                pv = model_field.view_permission # always "zope.Public"
                pe = model_field.edit_permission # always "zope.ManageContent"
        # !+DECL parametrize all permissions by type AND mode, ensure to grant
        # to appropriate roles. What about non-workflows or non-catalyzed types?
        protectName(domain_model, n, pv)
        protectSetAttribute(domain_model, n, pe)
        DTS = n in dts_attrs and "dts" or "   "
        DF = n in df_attrs and "df" or "  "
        log.debug("         %s %s [%s]  view:%s  edit:%s  %x",
                DTS, DF, n, pv, pe, id(model_field))
        if n not in domain_model.__dict__:
            log.debug("           ---- [%s] !+SCHEMA_FIELDS not in %s.__dict__",
                    n, domain_model)
    
    # container attributes (never a UI Field for these)
    log.debug("      __dict__: %s" % (domain_model))
    for k in sorted(domain_model.__dict__.keys()):
        # !+ if IManagedContainer.providedBy(v): ?
        v = domain_model.__dict__[k]
        if isinstance(v, ManagedContainerDescriptor):
            if k in _view_protected:
                log.debug("           ---- %s RESETTING...", k)
            _view_protected.add(k)
            log.debug("        managed %s view:%s" % (k, "zope.Public"))
        elif isinstance(v, orm.attributes.InstrumentedAttribute):     
            if k in _view_protected:
                log.debug("           ---- %s RESETTING...", k)
            _view_protected.add(k)
            log.debug("   instrumented [%s]  view:%s", k, "zope.Public")
        else:
            log.debug("           ---- [%s] !+SCHEMA_FIELD IN __dict__ but NOT "
                "instrumented OR managed", k)
            continue
        if k not in attrs:
            log.debug("           ---- [%s] !+SCHEMA_FIELDS not in attrs", k)
        protectName(domain_model, k, "zope.Public") #!+pv_type
    
    # Dump permission_id required to getattr/setattr for "custom" types.
    # We only dump the security settings for "custom" types as it only these 
    # are processed AFTER that domain.zcml has been executed (for other types,
    # loaded earlier during app startup, it is the settings in domain.zcml 
    # (executed later during app startup) that ends up applying.
    if descriptor_model.scope == "custom":
        from zope.security import proxy, checker
        dmc = checker.getChecker(proxy.ProxyFactory(domain_model()))
        log.debug("       checker: %s", dmc)
        for n in sorted(_view_protected.union(["response_text"])):
            g = dmc.get_permissions.get(n)
            s = dmc.set_permissions.get(n) #dmc.setattr_permission_id(n)
            log.debug("                [%s]  get:%s  set:%s",
                    n, getattr(g, "__name__", g), s)


def generate_container_class(ti):
    """Generate a zope3 container class for a domain model.
    """
    type_key = naming.polymorphic_identity(ti.domain_model)
    container_name = naming.container_class_name(type_key)
    container_iname = naming.container_interface_name(type_key)
    base_interfaces = (IAlchemistContainer,)
    
    # logging variables
    msg = (ti.domain_model.__name__, CONTAINER_MODULE.__name__, container_name)
    
    # container class - if we already have one, exit                
    if getattr(CONTAINER_MODULE, container_name, None):
        log.info("generate_container_class [model=%s] found container %s.%s, skipping" % msg)
        ti.container_class = getattr(CONTAINER_MODULE, container_name)
        return
    
    container_class = type(container_name,
        (AlchemistContainer,),
        dict(_class=ti.domain_model, 
            __module__=CONTAINER_MODULE.__name__)
    )
    # set on CONTAINER_MODULE, register on type_info
    setattr(CONTAINER_MODULE, container_name, container_class)
    ti.container_class = container_class
    log.info("generate_container_class [model=%s] generated container %s.%s" % msg)
    
    # container interface - if we already have one, skip creation 
    # !+ should always be newly created?
    container_iface = getattr(INTERFACE_MODULE, container_iname, None)
    msg = (ti.domain_model.__name__, CONTAINER_MODULE.__name__, container_iname)
    if container_iface is not None:
        assert issubclass(container_iface, IAlchemistContainer)
        log.info("generate_container_class [model=%s] skipping container interface %s.%s for" % msg)
    else:
        container_iface = interface.interface.InterfaceClass(
            container_iname,
            bases=base_interfaces,
            __module__=INTERFACE_MODULE.__name__
        )
        # set on INTERFACE_MODULE, register on type_info
        setattr(INTERFACE_MODULE, container_iname, container_iface)
        ti.container_interface = container_iface
        log.info("generate_container_class [model=%s] generated container interface %s.%s" % msg)
    
    # setup security
    for n, d in container_iface.namesAndDescriptions(all=True):
        protectName(container_class, n, "zope.Public")
    # apply implementedBy
    if not container_iface.implementedBy(container_class):
        interface.classImplements(container_class, container_iface)


def generate_collection_traversal(ti):
    
    # !+ merge with utils.get_managed_containers?
    def get_collection_names(domain_model):
        return [ k for k, v in domain_model.__dict__.items()
            if IManagedContainer.providedBy(v) ]
    
    collection_names = get_collection_names(ti.domain_model)
    
    if not collection_names:
        return
    # Note: the templated CollectionTraverser TYPE returned by this is
    # instantiated per "inherited and catalysed" descriptor e.g. for Motion, 
    # it is instantiated once for DocDescriptor and once for MotionDescriptor.
    traverser = CollectionTraverser(*collection_names)
    
    # provideSubscriptionAdapter(factory, adapts=None, provides=None)
    component.provideSubscriptionAdapter(traverser, 
        adapts=(ti.derived_table_schema, IPublisherRequest), 
        provides=ITraverserPlugin)
    # provideAdapter(factory, adapts=None, provides=None, name="")
    component.provideAdapter(PluggableTraverser,
        adapts=(ti.derived_table_schema, IPublisherRequest),
        provides=IPublishTraverse)


