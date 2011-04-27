# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist traversal - [
    alchemist.traversal.managed
]

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


# alchemist.traversal.managed
from zope.security.proxy import removeSecurityProxy
from alchemist.traversal.managed import one2many, One2Many
from alchemist.traversal.managed import ManagedContainerDescriptor

class One2ManyIndirect(One2Many):
    """
    Similar to one2many but gets a listing of indirectly related
    objects e.g. addresses for an MP with addresses defined on User
    Assumes shared foreign key has the same name
    """
    def getQueryModifier(self, instance, container):
        attr_value = getattr(instance, self.fk)
        return getattr(container.domain_model, self.fk) == attr_value
        
    def setConstrainedValues(self, instance, target):
        trusted = removeSecurityProxy(instance)
        attr_value = getattr(instance, self.fk) 
        setattr(target, self.fk, attr_value)
    

def one2manyindirect(name, container, fk):
    constraint = One2ManyIndirect(fk)
    container = ManagedContainerDescriptor(name, container, constraint)
    return container


