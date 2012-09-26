# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist catalyst - [
    alchemist.catalyst.ui
]

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


# used directly in bungeni
__all__ = [
    "AddForm",      # alias -> alchemist.catalyst.ui
    "DisplayForm",  # alias -> alchemist.catalyst.ui
    "EditForm",     # alias -> alchemist.catalyst.ui
    "catalyse_descriptors"
    #"sa2zs",        # alias -> ore.alchemist !+ALCHEMIST_INTERNAL
    #"catalyst",     # redefn -> alchemist.catalyst.zcml !+ALCHEMIST_INTERNAL
    #"ApplySecurity",      # alias -> alchemist.catalyst.domain !+ALCHEMIST_INTERNAL
]
from alchemist.catalyst.ui import AddForm
from alchemist.catalyst.ui import DisplayForm
from alchemist.catalyst.ui import EditForm
from ore.alchemist import sa2zs

# from bungeni.alchemist, used only here

from bungeni.alchemist.interfaces import (
    IAlchemistContent,
    IAlchemistContainer,
    IManagedContainer,
    IIModelInterface,
)
from bungeni.alchemist.container import AlchemistContainer
from bungeni.alchemist.traversal import CollectionTraverser
from bungeni.alchemist import utils

###

import logging
import types

from zope import interface, component
from zope.dottedname.resolve import resolve
from zope.publisher.interfaces import IPublisherRequest, IPublishTraverse
from zope.app.security.protectclass import protectName # !+remove

from z3c.traverser.interfaces import ITraverserPlugin
from z3c.traverser.traverser import PluggableTraverser

from sqlalchemy import orm

import bungeni.models.interfaces
import bungeni.ui.content


def catalyse_descriptors(module):
    """Catalyze descriptor classes in specified module. 
    Relate each descriptor to a domain type via naming convention:
    - if no domain type exists with that name, ignore
    !+ this is probably catalyzing some descriptors unnecessarily... 
    !+ if there is a need to be finer grained or for an explicit declaration
    of what descriptors should be catalysed, a flag may be added e.g. a 
    catalyse:bool attribute could be added on Descriptor class.
    """
    import sys
    import inspect
    from bungeni.alchemist.model import IModelDescriptor
    from bungeni.models import domain
    from bungeni.core.workflow.interfaces import IWorkflowed
    from bungeni.core import type_info
    from bungeni.utils.capi import capi
    from bungeni.utils import naming
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
    
    for descriptor in descriptor_classes():
        descriptor_name = descriptor.__name__
        assert descriptor_name.endswith("Descriptor")
        kls_name = descriptor_name[0:-len("Descriptor")]
        try:
            # need a dedicated domain type
            kls = getattr(domain, kls_name) # AttributeError
            # only catalyze mapped domain types
            kls_mapper = orm.class_mapper(kls) # UnmappedClassError
        except (AttributeError, orm.exc.UnmappedClassError):
            # no corresponding domain class, ignore e.g. Model
            # unmapped class e.g. Address
            debug.log_exc(sys.exc_info(), log_handler=log.warn)
            continue
        # catalyse each (domain_model, descriptor) pair
        ctx = CatalystContext()
        #setup_log(ctx) #!+INI
        catalyst(ctx, kls, descriptor)
        # type_info, register the descriptor
        type_key = naming.polymorphic_identity(kls)
        ti = capi.get_type_info(type_key)
        # non-workflowed types had not had domain_model set as yet...
        if (not IWorkflowed.implementedBy(kls) 
                or ti.domain_model is None # otherwise report4_sitting fails...
            ):
            # non-workflowed type - domain_model not set as yet...
            #assert ti.domain_model is None, "%s domain_model %s is %s not None" % (
            #    type_key, ti.domain_model, kls)
            ti.domain_model = kls
        assert ti.domain_model is kls, "%s domain_model %s is not %s" % (
                type_key, ti.domain_model, kls)
        ti.descriptor_model = descriptor
    
    m = "\n\nDone all workflow/descriptor setup... running with:\n\n%s\n\n" % (
            "\n\n".join(sorted(
                [ "%s: %s" % (key, ti) for key, ti in capi.iter_type_info() ])
            ))
    log.debug(m)

def setup_log(ctx):
    ctx.logger = log
    logging.basicConfig()
    formatter = logging.Formatter("ALCHEMIST: %(module)s -> %(message)s")
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    ctx.logger.addHandler(console)
    ctx.logger.setLevel(logging.DEBUG)
    #console.propagate = False       
    ctx.logger.propagate = False  
    

# alchemist.catalyst.zcml 

class CatalystContext(object):
    """Context object to hold configuration settings and generated objects.
    """
    descriptor = None
    domain_model = None
    domain_interface = None
    mapper = None
    interface_module = None
    container_module = None
    container_class = None
    ui_module = None
    views = None
    relation_viewlets = None
    logger = None
    echo = False #!+INI True


def catalyst(ctx,
        kls,
        descriptor, 
        #view_module=None, # !+?
        interface_module=bungeni.models.interfaces,
        #container_module=None, # !+?
        ui_module=bungeni.ui.content,
    ):
    ctx.descriptor = descriptor
    ctx.domain_model = kls
    ctx.mapper = orm.class_mapper(kls)
    ctx.interface_module = interface_module
    ctx.container_module = None # !+container_module(mr, jul-2011), expected
    # to be defined by alchemist.catalyst.container.GenerateContainer
    ctx.ui_module = ui_module
    
    ctx.views = {} # keyed by view type (add|edit)
    ctx.relation_viewlets = {} # keyed by relation name
    
    #ctx.logger.debug("context=%s, class=%s, descriptor=%s, echo=%s" % ( #!+INI
    log.debug("context=%s, class=%s, descriptor=%s, echo=%s" % (
            ctx, kls, descriptor, ctx.echo))
    
    # create a domain interface if it doesn't already exist 
    # this also creates an adapter between the interface and desc.
    GenerateDomainInterface(ctx)
    
    from alchemist.catalyst.domain import ApplySecurity #!+ALCHEMIST_INTERNAL
    ApplySecurity(ctx)
    
    # create a container class 
    GenerateContainer(ctx)
    
    # generate collection traversal 
    GenerateCollectionTraversal(ctx)
    
    return ctx


def GenerateDomainInterface(ctx):
    #!+NO_NEED_TO_INSTANTIATE
    # when called from zcml, most likely we'll get a class not an instance
    # if it is a class go ahead and call instantiate it
    #if isinstance(ctx.descriptor, type):
    #    ctx.descriptor = ctx.descriptor()
    
    assert ctx.interface_module, "No interface module."
    
    #!+alchemist.catalyst.domain.getDomainInterfaces
    def get_domain_interfaces(domain_model):
        """Return the domain bases for an interface as well as a filtered 
        implements only list.
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
    bases, implements = get_domain_interfaces(ctx.domain_model)
    
    # interface for domain model
    interface_name = "I%s" % (ctx.domain_model.__name__)
    if ctx.echo: #!+INI
        ctx.logger.debug("%s: generated interface %s.%s " % (
            ctx.domain_model.__name__, ctx.interface_module.__name__,
            interface_name))
    
    def get_model_interface(domain_model):
        """Get dedicated interface (name convention) that is marked as a domain
        model interface (provides IIModelInterface) AND is impelemented by the
        domain class.
        """
        interface_name = "I%s" % (domain_model.__name__) #!+naming
        for iface in interface.implementedBy(domain_model):
            if iface.__name__ == interface_name:
                if IIModelInterface.providedBy(iface):
                    #!+AUDIT_TESTS passes here in audit doctests (only?)
                    #raise Exception("!+%s provides %s!!"  % (iface, IIModelInterface))
                    return iface
    # if the domain model already implements a model interface, use it
    # instead of generating a new one
    domain_interface = get_model_interface(ctx.domain_model)
    if domain_interface is None:
        # use the class's mapper select table as input for the transformation
        domain_table = utils.get_local_table(ctx.domain_model)
        domain_interface = sa2zs.transmute(
            domain_table,
            annotation=ctx.descriptor,
            interface_name=interface_name,
            __module__=ctx.interface_module.__name__,
            bases=bases)
    
    # if we're replacing an existing interface, make sure the new
    # interface implements it
    old = getattr(ctx.interface_module, interface_name, None)
    if old is not None:
        if old not in implements:
            implements.append(old)
        #assert old is not domain_interface #!+AUDIT_TESTS fails
    # !+RETAIN_SAME_INTERFACE_CLASS determine whether a same-named interface 
    # already exists e.g. getattr(ctx.interface_module, interface_name) and
    # whether domain_model provides it... if so, then "splice" extra info from
    # auto-generated interface into the predefined one... 
    # ELSE adopt policy that if provided, then it must be fully defined 
    # (total resposibility of user, never auto-modified!).
    implements.insert(0, domain_interface)
    interface.classImplementsOnly(ctx.domain_model, *implements)
    setattr(ctx.interface_module, interface_name, domain_interface)
    ctx.domain_interface = domain_interface
    # ensure interfaces are unique, preserving the order
    #implements = [ ifc for i,ifc in enumerate(implements) 
    #               if implements.index(ifc)==i ]
    #
    # XXX: Oooh, strangely the above does not work... it turns out that 
    # implements contains seemingly repeated interfaces e.g. the first and last 
    # interfaces are both "<InterfaceClass bungeni.models.interfaces.IReport>"
    # but, they are not the same! So, to compare unique we use the string
    # representation of each interface:
    # str_implements = map(str, implements)
    # implements = [ ifc for i,ifc in enumerate(implements) 
    #                if str_implements.index(str(ifc))==i ]
    # Ooops making the interfaces unique breaks other things downstream :(


# alchemist.catalyst.container
def GenerateContainer(ctx, 
            container_name=None, 
            container_iname=None,
            base_interfaces=()
        ):
        """Generate a zope3 container class for a domain model.
        """
        # create container
        container_name = container_name or \
            "%sContainer" % (ctx.domain_model.__name__)
        
        # allow passing in dotted python path
        if isinstance(ctx.container_module, basestring):
            ctx.container_module = resolve(ctx.container_module)
        # if not present use the domain class's module
        elif ctx.container_module is None:
            ctx.container_module = resolve(ctx.domain_model.__module__)
        
        # sanity check we have a module for the container
        assert isinstance(ctx.container_module, types.ModuleType), "Invalid Container"
        
        # logging variables
        msg = (ctx.domain_model.__name__, 
            ctx.container_module.__name__, container_name)
        
        # if we already have a container class, exit                
        if getattr(ctx.container_module, container_name, None):
            if ctx.echo:
                ctx.logger.debug("%s: found container %s.%s, skipping" % msg)
            ctx.container_class = getattr(ctx.container_module, container_name)
            return
        
        if ctx.echo:
            ctx.logger.debug("%s: generated container %s.%s" % msg)
        
        # if we already have a container class, exit
        container_class = type(container_name,
            (AlchemistContainer,),
            dict(_class=ctx.domain_model, 
                __module__=ctx.container_module.__name__)
        )
        setattr(ctx.container_module, container_name, container_class)
        
        # save container class on catalyst context
        ctx.container_class = container_class
        
        # interface for container
        container_iname = container_iname or "I%s" % container_name
        
        # if we already have a container interface class, skip creation
        container_interface = getattr(ctx.interface_module, container_iname, None)
        msg = (ctx.domain_model.__name__, 
            ctx.container_module.__name__, container_iname)
        if container_interface is not None:
            assert issubclass(container_interface, IAlchemistContainer)
            if ctx.echo:
                ctx.logger.debug("%s: skipping container interface %s.%s for" % msg)
        else:
            if ctx.echo:
                ctx.logger.debug("%s: generated container interface %s.%s" % msg)
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
                __module__=ctx.interface_module.__name__
            )
            # store container interface for catalyst
            ctx.container_interface = container_interface
            setattr(ctx.interface_module, container_iname, container_interface)
        
        # setup security
        for n,d in container_interface.namesAndDescriptions(1):
            protectName(container_class, n, "zope.Public")
        
        if not container_interface.implementedBy(container_class):
            interface.classImplements(container_class, container_interface)
        ctx.container_interface = container_interface


# alchemist.catalyst.zcml
def GenerateCollectionTraversal(ctx):
    
    def get_collection_names(domain_model):
        return [ k for k, v in domain_model.__dict__.items()
            if IManagedContainer.providedBy(v) ]
    
    collection_names = get_collection_names(ctx.domain_model)
    if not collection_names:
        return
    
    # Note: the templated CollectionTraverser TYPE returned by this is
    # instantiated multiple times in case of inheritance of catalyzed 
    # descriptors e.g. for Motion, it is instantiated once for 
    # ParliamentaryItemDescriptor and once for MotionDescriptor.
    traverser = CollectionTraverser(*collection_names)
    
    # provideSubscriptionAdapter(factory, adapts=None, provides=None)
    component.provideSubscriptionAdapter(traverser, 
        adapts=(ctx.domain_interface, IPublisherRequest), 
        provides=ITraverserPlugin)
    # provideAdapter(factory, adapts=None, provides=None, name="")
    component.provideAdapter(PluggableTraverser,
        adapts=(ctx.domain_interface, IPublisherRequest),
        provides=IPublishTraverse)


