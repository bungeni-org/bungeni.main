# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist traversal

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


# used directly in bungeni
__all__ = [
    "one2many",                     # redefn -> alchemist.traversal.managed
    "ManagedContainerDescriptor",   # redefn -> alchemist.traversal.managed
    "CollectionTraverser",          # redefn -> alchemist.traversal.collection
    #!+ALCHEMIST_INTERNAL "One2Many", # redefn -> alchemist.traversal.managed
    #!+ALCHEMIST_INTERNAL "CollectionTraverser", # redefn -> alchemist.traversal.collection
    "PartialContainer",             # alias -> ore.alchemist.container
]

from ore.alchemist.container import PartialContainer

# alchemist.traversal

from bungeni.alchemist.interfaces import (
    IManagedContainer,
)

#

from zope import interface
from zope.app.security.protectclass import protectLikeUnto
from zope.security.proxy import removeSecurityProxy
from zope.publisher.interfaces import NotFound
from zope.location import ILocation
from zope.dottedname.resolve import resolve
from z3c.traverser.interfaces import ITraverserPlugin
from sqlalchemy import orm

# alchemist.traversal.managed    

class ConstraintManager(object):
    """Manages the constraints on a managed container.
    """
    def setConstrainedValues(self, instance, target):
        """Ensures existence of conformant constraint values
        to match the query.
        """
    
    def getQueryModifier(self, instance, container):
        """Given an instance inspect for the query to retrieve 
        related objects from the given alchemist container.
        """

class One2Many(ConstraintManager):
    
    def __init__(self, fk):
        self.fk = fk
    
    def getQueryModifier(self, instance, container):
        mapper = orm.class_mapper(instance.__class__)
        primary_key = mapper.primary_key_from_instance(instance)[0]
        return getattr(container.domain_model, self.fk) == primary_key 
    
    def setConstrainedValues(self, instance, target):
        trusted = removeSecurityProxy(instance)
        mapper = orm.object_mapper(trusted)
        primary_key = mapper.primary_key_from_instance(trusted)[0]
        #column = target.__class__.c[ self.fk ]
        #table = orm.class_mapper(target.__class__).mapped_table
        #column = table.c[ self.fk ]
        #setattr( target, column.name, primary_key )
        setattr(target, self.fk, primary_key)

def one2many(name, container, fk):
    constraint = One2Many(fk)
    container = ManagedContainerDescriptor(name, container, constraint)
    return container


class ManagedContainerDescriptor(object):
    _container_class = None
    interface.implements(IManagedContainer)
    
    def __init__(self, name, container, constraint):
        self.name = name
        self.container = container
        self.constraint = constraint
    
    def __get__(self, instance, cls):
        # initialization issue, elixir bootstraps by inspecting all class variables,
        # we may not have processed the fk class yet, when our context is processed
        # by elixir, in that case short circuit, else we'll get errors trying to 
        # process any additional subquery constraints.
        if instance is None and self._container_class is None:
            return None
        
        container = self.domain_container()
        if instance is None:
            return container
        container.__parent__ = instance
        container.__name__ = self.name
        container.setConstraintManager(self.constraint)
        return container
    
    @property
    def domain_container(self):
        if self._container_class:
           return self._container_class
        container_class = resolve(self.container)
        self._container_class = type("ManagedContainer", 
            (_ManagedContainer, container_class), 
            dict(container_class.__dict__))        
        protectLikeUnto(self._container_class, container_class)
        return self._container_class


class _ManagedContainer(PartialContainer):
    
    def __repr__(self):
        m = self.__class__.__bases__[1]
        s = "%s.%s" % (m.__module__, m.__name__)
        return "<Managed %s>" % s
    
    def __setitem__(self, key, value):
        super(_ManagedContainer, self).__setitem__(key, value)
        self.constraints.setConstrainedValues(self.__parent__, value)
    
    def setConstraintManager(self, constraints):
        self.constraints = constraints
        if self.__parent__ is not None:
            self.setQueryModifier( constraints.getQueryModifier(self.__parent__, self))


# alchemist.traversal.collection

class CollectionTraverserTemplate(object):
    """A traverser that knows how to look up objects by sqlalchemy collections """

    interface.implements(ITraverserPlugin)

    collection_attributes = ()
    
    def __init__(self, container, request):
        self.context = removeSecurityProxy(container)
        self.request = request
    
    def publishTraverse(self, request, name):
        """See zope.publisher.interfaces.IPublishTraverse"""
        if name in self.collection_attributes:
            container = getattr(self.context, name)
            if ILocation.providedBy(container):
                trusted_ctx = removeSecurityProxy(container)
                trusted_ctx.__parent__ = self.context
                trusted_ctx.__name__   = name
            return container
        raise NotFound(self.context, name, request)

def CollectionTraverser(*names):
    return type("CollectionsTraverser", 
        (CollectionTraverserTemplate,),
        {"collection_attributes": names})

