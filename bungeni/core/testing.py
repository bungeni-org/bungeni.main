import index
import zope.interface
import zope.publisher.interfaces
import zope.security.management
import zope.security.testing
from sqlalchemy import create_engine
from zope import component

from bungeni.alchemist.interfaces import IDatabaseEngine
from bungeni import models as model
from bungeni.models.testing import setup_db


def setup_indexer():
    store_dir = index.setupStorageDirectory() + "-test"
    # search connection hub
    searcher = index.search.IndexSearch(store_dir)
    # async indexer 
    indexer = index.xappy.IndexerConnection(store_dir)
    # field definitions
    index.setupFieldDefinitions(indexer)


def create_principal(id="manager", title="Manager", groups=()):
    return zope.security.testing.Principal(id, title, groups)


#!+ make private to set_interaction
def create_participation(principal=None):
    if principal is None:
        principal = create_principal()
    participation = zope.security.testing.Participation(principal)
    zope.interface.alsoProvides(participation, 
        zope.publisher.interfaces.IRequest)
    return participation

def set_interaction(principal):
    """End current interaction (if any) and, if principal not None, start a 
    new one with principal participating.
    """
    zope.security.management.endInteraction()
    if principal is not None:
        zope.security.management.newInteraction(
            create_participation(principal))
    
