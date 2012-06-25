import zope.interface
import zope.publisher.interfaces
import zope.security.management
import zope.security.testing

from bungeni.models.testing import setup_db

''' !+UNUSED(mr, may-2012)
def setup_indexer():
    import index
    store_dir = index.setupStorageDirectory() + "-test"
    # search connection hub
    searcher = index.search.IndexSearch(store_dir)
    # async indexer 
    indexer = index.xappy.IndexerConnection(store_dir)
    # field definitions
    index.setupFieldDefinitions(indexer)
'''

def catalyse_descriptors():
    # !+CATALYSE_DESCRIPTORS(mr, jun-2012) this should not be necessary here
    # (in addition to making UI a CORE dependency!), but without this trying 
    # IWorkflow(question) in the tests resyults in a could-not-adapt error. 
    # Note: prior to r9413 the equivalent of the following was being executed 
    # on import of bungeni.ui.descriptor.
    from bungeni.ui.descriptor import descriptor
    descriptor.catalyse_descriptors()
# do once for all core tests
catalyse_descriptors()


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
    
def refresh_dc_registrations():
    """!+DC_REGISTRATIONS(mr, may-2012) for some reason dc adapter registrations
    are being dropped across test_suites (interference with placelesssetup 
    setUp() and tearDown() methods!). 
    
    As a tmp workaround, a test_suite should call this to reload (and re-reg) 
    the adapters.
    
    Other issues:
    - why is dc.py in bungeni.core, when it is essentially ui?
    
    """
    import sys
    assert "bungeni.core.dc" in sys.modules, \
        "Module [bungeni.core.dc] is not yet loaded, should not be reloading it!"
    import bungeni.core.dc
    reload(bungeni.core.dc)

