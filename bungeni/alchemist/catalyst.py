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
    
    "catalyst",     # redefn -> alchemist.catalyst.zcml
    
    #!+ALCHEMIST_INTERNAL "CatalystContext",    # alias -> alchemist.catalyst.zcml
    #!+ALCHEMIST_INTERNAL "ApplySecurity",      # alias -> alchemist.catalyst.domain
    #!+ALCHEMIST_INTERNAL "getDomainInterfaces",# alias -> alchemist.catalyst.domain
]


from alchemist.catalyst.ui import AddForm
from alchemist.catalyst.ui import DisplayForm
from alchemist.catalyst.ui import EditForm

#

from bungeni.alchemist.interfaces import (
    IAlchemistContainer,
    IManagedContainer,
    IIModelInterface,
)
from bungeni.alchemist import sa2zs
from bungeni.alchemist.container import AlchemistContainer
from bungeni.alchemist.traversal import CollectionTraverser


###

import logging
import types

from zope import interface, component
from zope.dottedname.resolve import resolve
from zope.publisher.interfaces import IPublisherRequest, IPublishTraverse
from zope.app.security.protectclass import protectName # !+remove

from z3c.traverser.interfaces import ITraverserPlugin
from z3c.traverser.traverser import PluggableTraverser

from sqlalchemy import orm, __version__ as sa_version
sa_version = map(int, sa_version.split("."))

#

logging_setup = False

import bungeni.models.interfaces
import bungeni.ui.content


# alchemist.catalyst.zcml 

def catalyst(_context, 
        class_,
        descriptor, 
        #view_module=None, # !+?
        interface_module=bungeni.models.interfaces,
        #container_module=None, # !+?
        ui_module=bungeni.ui.content,
        echo=False
    ):
    from alchemist.catalyst.zcml import CatalystContext #!+ALCHEMIST_INTERNAL
    ctx = CatalystContext()
    ctx.descriptor = descriptor
    ctx.domain_model = class_
    ctx.mapper = orm.class_mapper(class_)
    ctx.interface_module = interface_module
    #ctx.mapper = 
    ctx.container_module = None # !+container_module(mr, jul-2011), expected
    # to be defined by alchemist.catalyst.container.GenerateContainer
    ctx.ui_module = ui_module
    ctx.echo = echo
    
    ctx.views = {} # keyed by view type (add|edit)
    ctx.relation_viewlets = {} # keyed by relation name 
    ctx.logger = log
    ctx.logger.debug("context=%s, class=%s, descriptor=%s, echo=%s" % (
            _context, class_, descriptor, echo))
    
    global logging_setup # !+?
    
    if ctx.echo and not logging_setup:
        logging_setup = True
        logging.basicConfig()
        formatter = logging.Formatter("ALCHEMIST: %(module)s -> %(message)s")
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        ctx.logger.addHandler(console)
        ctx.logger.setLevel(logging.DEBUG)
        #console.propagate = False       
        ctx.logger.propagate = False  
    
    try:
        # create a domain interface if it doesn't already exist 
        # this also creates an adapter between the interface and desc.
        GenerateDomainInterface(ctx)
        
        from alchemist.catalyst.domain import ApplySecurity #!+ALCHEMIST_INTERNAL
        ApplySecurity(ctx)
        
        # behavior.ApplyIndexing()
        # behavior.ApplyWorkflows()
        # behavior.ApplyVersioning()
        
        # create a container class 
        GenerateContainer(ctx)
        
        # generate collection traversal 
        GenerateCollectionTraversal(ctx)
    except:
        import sys, traceback, pdb
        traceback.print_exc()
        pdb.post_mortem(sys.exc_info()[-1])
        raise


def GenerateDomainInterface(ctx, interface_name=None):
    # when called from zcml, most likely we'll get a class not an instance
    # if it is a class go ahead and call instantiate it
    if isinstance(ctx.descriptor, type):
        ctx.descriptor = ctx.descriptor()
                             
    # if the interface module is none, then use the nearest one to the domain class
    if ctx.interface_module is None:
        ctx.interface_module = naming.resolve_relative("..interfaces", ctx)
    
    # interface for domain model
    if not interface_name:
        interface_name = "I%s" % (ctx.domain_model.__name__)
    
    if ctx.echo:
        ctx.logger.debug("%s: generated interface %s.%s " % (
            ctx.domain_model.__name__, ctx.interface_module.__name__,
            interface_name))
    
    from alchemist.catalyst.domain import getDomainInterfaces #!+ALCHEMIST_INTERNAL
    bases, implements = getDomainInterfaces(ctx.domain_model)
    
    # use the class"s mapper select table as input for the transformation
    domain_mapper = orm.class_mapper(ctx.domain_model)
    ## 0.4 and 0.5 compatibility, 0.5 has the table as local_table (select_table) is none lazy gen?
    #domain_table  = getattr(domain_mapper, "local_table", domain_mapper.select_table)
    # The 0.6 has no attribute select_table attribute. We still have 0.4 
    # compitability thought
    domain_table  = (domain_mapper.local_table if sa_version[1] >= 5 
                                    else  domain_mapper.select_table)
    
    # if the domain model already implements a model interface, use it
    # instead of generating a new one
    for iface in interface.implementedBy(ctx.domain_model):
        if (IIModelInterface.providedBy(iface) and 
                iface.__name__ == interface_name
            ):
            domain_interface = iface
            break
    else:
        domain_interface = sa2zs.transmute(
            domain_table,
            annotation=ctx.descriptor,
            interface_name = interface_name,
            __module__ = ctx.interface_module.__name__,
            bases=bases)
    
    # if we're replacing an existing interface, make sure the new
    # interface implements it
    old = getattr(ctx.interface_module, interface_name, None)
    if old is not None:
        implements.append(old)
    
    implements.insert(0, domain_interface)
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
    
    interface.classImplementsOnly(ctx.domain_model, *implements)
    
    setattr(ctx.interface_module, interface_name, domain_interface)
    ctx.domain_interface = domain_interface


def GenerateCollectionTraversal(ctx):
    
    collection_names = []
    for k, v in ctx.domain_model.__dict__.items():
        if IManagedContainer.providedBy(v):
            collection_names.append(k)

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
        provides=IPublishTraverse
    )


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
        if isinstance(ctx.container_module, (str, unicode)):
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
        
        # if the interface module is none, then use the nearest one to the domain class
        if ctx.interface_module is None:
            ctx.interface_module = naming.resolve_relative("..interfaces", ctx)
        
        msg = (ctx.domain_model.__name__,
            ctx.container_module.__name__, container_iname)
        
        # if we already have a container interface class, skip creation
        container_interface = getattr(ctx.interface_module, container_iname, None)
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
    from bungeni.alchemist.model import IModelDescriptor, queryModelInterface
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
        catalyst(None, kls, descriptor, echo=True)
        # type_info, register the descriptor
        type_key = naming.polymorphic_identity(kls)
        try:
            ti = capi.get_type_info(type_key)
        except KeyError:
            # no TI entry, must be a non-workflowed domain type
            #assert not IWorkflowed.implementedBy(kls) #!+report4_sitting fails
            # add TI entry
            type_info._add(None, queryModelInterface(kls), None, kls, None, None)
            ti = capi.get_type_info(type_key)
            assert ti.domain_model is kls
        ti.descriptor_model = descriptor
        # !+NO_NEED_TO_INSTANTIATE here we cache an instance...
        ti.descriptor = descriptor()
    
    m = ("\n\nDone all workflow/descriptor related setup... running with:\n  " + 
        "\n  ".join(sorted([ "%s: %s" % (key, ti)
                for key, ti in capi.iter_type_info() ])) + 
        "\n")
    log.debug(m)

