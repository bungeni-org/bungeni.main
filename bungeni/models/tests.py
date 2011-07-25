"""
$Id$
"""

from zope import interface
from zope import component

import unittest

from zope.testing import doctest, doctestunit
from zope.app.testing import placelesssetup, ztapi
from zope.configuration import xmlconfig

from bungeni.models import metadata, interfaces
from interfaces import IAssignmentFactory, IContentAssignments, IContextAssignments
from bungeni.core.workflows import adapters
from bungeni.ui import descriptor

zcml_slug = """
<configure xmlns="http://namespaces.zope.org/zope"
           xmlns:db="http://namespaces.objectrealms.net/rdb">

  <include package="bungeni.alchemist" file="meta.zcml"/>
  <include package="alchemist.catalyst" file="meta.zcml"/>

  <!-- Setup Database Connection -->
  <db:engine
     name="bungeni-db"
     url="postgres://localhost/bungeni-test"
     />
     
  <db:bind
     engine="bungeni-db"
     metadata="bungeni.models.metadata" />

  <db:bind
     engine="bungeni-db"
     metadata="bungeni.alchemist.security.metadata" />

</configure>
"""

def setUp( test ):
    placelesssetup.setUp()
    xmlconfig.string( zcml_slug )
    metadata.create_all( checkfirst=True )
    
def tearDown( test ):
    placelesssetup.tearDown()
    metadata.drop_all( checkfirst=True )
    
def assignment_tests( ):
    import assignment
    def _setUp( test ):
        setUp( test )
        ztapi.provideAdapter( (interfaces.IBungeniContent, interfaces.IBungeniGroup ),
                              IAssignmentFactory,
                              assignment.GroupAssignmentFactory )

        ztapi.provideAdapter( interfaces.IBungeniContent,
                              IContentAssignments,
                              assignment.ContentAssignments )

        ztapi.provideAdapter( interfaces.IBungeniGroup,
                              IContextAssignments,
                              assignment.GroupContextAssignments )
        
    return doctestunit.DocFileSuite('assignment.txt',
                                    setUp = _setUp,
                                    tearDown = tearDown,
                                    optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS
                                    )

def test_suite():

    doctests = ('readme.txt', 
                'settings.txt', 
                'resourcebooking.txt',
                'venue.txt'
                )
    
    globs = dict(interface=interface, component=component)

    test_suites = []
    for filename in doctests:
        test_suite = doctestunit.DocFileSuite(filename,
                                              setUp = setUp,
                                              tearDown = tearDown,
                                              globs = globs,
                                              optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS )
        test_suites.append( test_suite )
            
    test_suites.append( assignment_tests() )
    
    return unittest.TestSuite( test_suites )

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
        
