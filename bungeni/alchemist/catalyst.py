# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist catalyst - [
    alchemist.catalyst.ui
]

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


from alchemist.catalyst.ui import AddForm
from alchemist.catalyst.ui import DisplayForm
from alchemist.catalyst.ui import EditForm

###

import logging
from zope import interface, component
from zope.publisher.interfaces import IPublisherRequest, IPublishTraverse
from z3c.traverser.interfaces import ITraverserPlugin
from z3c.traverser.traverser import PluggableTraverser

from alchemist.traversal.interfaces import IManagedContainer
from alchemist.traversal.collection import CollectionTraverser

from ore.alchemist import sa2zs, interfaces

from sqlalchemy import orm, __version__ as sa_version
sa_version = map(int, sa_version.split("."))

#

logging_setup = False

import bungeni.models.interfaces
import bungeni.ui.content

def catalyst(_context, 
        class_,
        descriptor, 
        #view_module=None, # !+?
        interface_module=bungeni.models.interfaces,
        #container_module=None, # !+?
        ui_module=bungeni.ui.content,
        echo=False
    ):
    from alchemist.catalyst.zcml import CatalystContext
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
        
        from alchemist.catalyst.domain import ApplySecurity
        ApplySecurity(ctx)
        
        # behavior.ApplyIndexing()
        # behavior.ApplyWorkflows()
        # behavior.ApplyVersioning()
        
        # create a container class 
        from alchemist.catalyst import container
        container.GenerateContainer(ctx)
        
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
        ispec = ctx.domain_model.__module__.rsplit(".",1)[0]+".interfaces"
        ctx.interface_module = resolve(ispec)
    
    # interface for domain model
    if not interface_name:
        interface_name = "I%s"%(ctx.domain_model.__name__)
    
    if ctx.echo:
        ctx.logger.debug("%s: generated interface %s.%s " % (
            ctx.domain_model.__name__, ctx.interface_module.__name__,
            interface_name))
    
    from alchemist.catalyst.domain import getDomainInterfaces
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
        if (interfaces.IIModelInterface.providedBy(iface) and 
            iface.__name__ == interface_name):
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

