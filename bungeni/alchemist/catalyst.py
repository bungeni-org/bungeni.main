# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist catalyst

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


# List everything from this module intended for package-external use.
__all__ = [
    "catalyse_descriptors"
    #"catalyst",     # redefn -> alchemist.catalyst.zcml !+ALCHEMIST_INTERNAL
    #"ApplySecurity",      # redefn -> alchemist.catalyst.domain !+ALCHEMIST_INTERNAL
    #"GenerateDomainInterface" # redefn -> alchemist.catalyst.zcml !+ALCHEMIST_INTERNAL
    #"GenerateContainer", # redefn -> alchemist.catalyst.container !+ALCHEMIST_INTERNAL
    #"GenerateCollectionTraversal" # redefn -> alchemist.catalyst.zcml !+ALCHEMIST_INTERNAL
    #"sa2zs",        # alias -> ore.alchemist !+ALCHEMIST_INTERNAL
]
from ore.alchemist import sa2zs

# from bungeni.alchemist, used only here

from bungeni.alchemist.interfaces import (
    IAlchemistContent,
    IAlchemistContainer,
    IManagedContainer,
    IIModelInterface,
)
from bungeni.alchemist.container import AlchemistContainer
from bungeni.alchemist.traversal import CollectionTraverser, ManagedContainerDescriptor
from bungeni.alchemist import utils

###


from zope import interface, component
from zope.publisher.interfaces import IPublisherRequest, IPublishTraverse
from zope.app.security.protectclass import (
        protectName, # !+remove
        protectSetAttribute, 
        protectLikeUnto
)

from z3c.traverser.interfaces import ITraverserPlugin
from z3c.traverser.traverser import PluggableTraverser

from sqlalchemy import orm

# target modules
import bungeni.models.interfaces as INTERFACE_MODULE
import bungeni.models.domain as CONTAINER_MODULE
#import bungeni.ui.content as UI_MODULE

from bungeni.utils import naming


def catalyse_descriptors(module):
    """Catalyze descriptor classes in specified module. 
    Relate each descriptor to a domain type via naming convention:
    - if no domain type exists with that name, ignore
    !+ this is probably catalyzing some descriptors unnecessarily... 
    !+ if there is a need to be finer grained or for an explicit declaration
    of what descriptors should be catalysed, a flag may be added e.g. a 
    catalyse:bool attribute could be added on Descriptor class or xml defn.
    """
    import sys
    import inspect
    from bungeni.alchemist.model import IModelDescriptor
    from bungeni.models import domain
    from bungeni.utils.capi import capi
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
            # unmapped class e.g. Address, Version
            return False
    
    for descriptor_model in descriptor_classes():
        descriptor_name = descriptor_model.__name__
        assert descriptor_name.endswith("Descriptor")
        domain_model_name = descriptor_name[0:-len("Descriptor")]
        # need a dedicated domain type
        domain_model = getattr(domain, domain_model_name, None)
        # only catalyze "mapped domain models"
        if not (domain_model and is_model_mapped(domain_model)):
            log.warn("Not catalysing: %s" % (descriptor_name))
            continue
        # type_info, register descriptor_model, domain_model
        type_key = naming.type_key_from_descriptor_cls_name(descriptor_name)
        ti = capi.get_type_info(type_key)
        ti.descriptor_model = descriptor_model
        ti.domain_model = domain_model
        # catalyse each (domain_model, descriptor_model) pair
        catalyst(ti)
    
    m = "\n\nDone all setup of types... running with:\n\n%s\n\n" % (
            "\n\n".join(sorted(
                [ "%s: %s" % (key, ti) for key, ti in capi.iter_type_info() ])
            ))
    log.debug(m)


# alchemist.catalyst.zcml 

def catalyst(ti):
    log.info("CATALYST: domain_model=%s, descriptor_model=%s" % (
            ti.domain_model, ti.descriptor_model))
    # create a domain interface if it doesn't already exist 
    # this also creates an adapter between the interface and desc.
    generate_table_schema_interface(ti)
    # setup security
    ApplySecurity(ti)
    # create a container class 
    GenerateContainer(ti)
    # generate collection traversal 
    GenerateCollectionTraversal(ti)
    return ti


def generate_table_schema_interface(ti):
    def get_domain_interfaces(domain_model):
        """Return the domain bases for an interface as well as a filtered 
        implements only list (base interfaces removed).
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
    
    # derived_table_schema:
    # - ALWAYS dynamically generated
    # - directlyProvides IIModelInterface
    type_key = naming.polymorphic_identity(ti.domain_model)
    # use the class's mapper select table as input for the transformation
    table_schema_interface_name = naming.table_schema_interface_name(type_key)
    domain_table = utils.get_local_table(ti.domain_model)
    bases, implements = get_domain_interfaces(ti.domain_model)
    derived_table_schema = sa2zs.transmute(
        domain_table,
        annotation=ti.descriptor_model,
        interface_name=table_schema_interface_name,
        __module__=INTERFACE_MODULE.__name__,
        bases=bases)
    # register interface on type_info and set on INTERFACE_MODULE
    ti.derived_table_schema = derived_table_schema
    setattr(INTERFACE_MODULE, table_schema_interface_name, derived_table_schema)
    log.info("generate_table_schema_interface [model=%s] generated [%s.%s]" % (
            ti.domain_model.__name__, INTERFACE_MODULE.__name__, 
            table_schema_interface_name))
    
    # if a conventionally-named domain interface exists, ensure that 
    # domain model implements it
    model_interface_name = naming.model_interface_name(type_key)
    model_interface = getattr(INTERFACE_MODULE, model_interface_name, None)
    if model_interface is not None:
        assert not issubclass(model_interface, derived_table_schema)
        if model_interface not in implements:
            implements.append(model_interface)
    # add derived_table_schema and apply
    implements.insert(0, derived_table_schema)
    interface.classImplementsOnly(ti.domain_model, *implements)


def ApplySecurity(ti):
    for c in ti.domain_model.__bases__:
        if c is object:
            continue
        protectLikeUnto(ti.domain_model, c)
    attributes = set(
        [ n for n,d in ti.derived_table_schema.namesAndDescriptions(1) ])
    attributes = attributes.union(
        set([ f.get("name") for f in ti.descriptor_model.fields ]))
    descriptor_model = ti.descriptor_model
    for n in attributes:
        model_field = descriptor_model.get(n)
        p = model_field and model_field.view_permission or "zope.Public"
        protectName(ti.domain_model, n, p)
    for n in attributes:
        model_field = descriptor_model.get(n)
        p = model_field and model_field.edit_permission or "zope.Public" # "zope.ManageContent"
        protectSetAttribute(ti.domain_model, n, p)
    for k, v in ti.domain_model.__dict__.items():
        if (isinstance(v, ManagedContainerDescriptor) or 
                isinstance(v, orm.attributes.InstrumentedAttribute)
            ):
            protectName(ti.domain_model, k, "zope.Public")


# alchemist.catalyst.container
def GenerateContainer(ti, 
            container_name=None, 
            container_iname=None,
            base_interfaces=()
        ):
        """Generate a zope3 container class for a domain model.
        """
        # create container
        container_name = container_name or \
            "%sContainer" % (ti.domain_model.__name__)
        
        # logging variables
        msg = (ti.domain_model.__name__, CONTAINER_MODULE.__name__, container_name)
        
        # if we already have a container class, exit                
        if getattr(CONTAINER_MODULE, container_name, None):
            log.info("GenerateContainer [model=%s] found container %s.%s, skipping" % msg)
            ti.container_class = getattr(CONTAINER_MODULE, container_name)
            return
        log.info("GenerateContainer [model=%s] generated container %s.%s" % msg)
        
        # if we already have a container class, exit
        container_class = type(container_name,
            (AlchemistContainer,),
            dict(_class=ti.domain_model, 
                __module__=CONTAINER_MODULE.__name__)
        )
        setattr(CONTAINER_MODULE, container_name, container_class)
        
        # save container class on catalyst context
        ti.container_class = container_class
        
        # interface for container
        container_iname = container_iname or "I%s" % container_name
        
        # if we already have a container interface class, skip creation
        container_interface = getattr(INTERFACE_MODULE, container_iname, None)
        msg = (ti.domain_model.__name__, 
            CONTAINER_MODULE.__name__, container_iname)
        if container_interface is not None:
            assert issubclass(container_interface, IAlchemistContainer)
            log.info("GenerateContainer [model=%s] skipping container interface %s.%s for" % msg)
        else:
            log.info("GenerateContainer [model=%s] generated container interface %s.%s" % msg)
            # ensure that our base interfaces include alchemist container 
            if base_interfaces:
                assert isinstance(base_interfaces, tuple)
                found = False
                for bi in base_interfaces:
                    found = issubclass(bi, IAlchemistContainer)
                    if found: break
                if not found:
                    base_interfaces = base_interfaces + (IAlchemistContainer,)
            else:
                base_interfaces = (IAlchemistContainer,)
            
            # create interface
            container_interface = interface.interface.InterfaceClass(
                container_iname,
                bases=base_interfaces,
                __module__=INTERFACE_MODULE.__name__
            )
            # store container interface for catalyst
            ti.container_interface = container_interface
            setattr(INTERFACE_MODULE, container_iname, container_interface)
        
        # setup security
        for n, d in container_interface.namesAndDescriptions(1):
            protectName(container_class, n, "zope.Public")
        
        if not container_interface.implementedBy(container_class):
            interface.classImplements(container_class, container_interface)
        ti.container_interface = container_interface


# alchemist.catalyst.zcml
def GenerateCollectionTraversal(ti):
    
    def get_collection_names(domain_model):
        return [ k for k, v in domain_model.__dict__.items()
            if IManagedContainer.providedBy(v) ]
    
    collection_names = get_collection_names(ti.domain_model)
    if not collection_names:
        return
    
    # Note: the templated CollectionTraverser TYPE returned by this is
    # instantiated multiple times in case of inheritance of catalyzed 
    # descriptors e.g. for Motion, it is instantiated once for 
    # ParliamentaryItemDescriptor and once for MotionDescriptor.
    traverser = CollectionTraverser(*collection_names)
    
    # provideSubscriptionAdapter(factory, adapts=None, provides=None)
    component.provideSubscriptionAdapter(traverser, 
        adapts=(ti.derived_table_schema, IPublisherRequest), 
        provides=ITraverserPlugin)
    # provideAdapter(factory, adapts=None, provides=None, name="")
    component.provideAdapter(PluggableTraverser,
        adapts=(ti.derived_table_schema, IPublisherRequest),
        provides=IPublishTraverse)


