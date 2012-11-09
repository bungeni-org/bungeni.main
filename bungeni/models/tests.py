"""
$Id$
"""

from zope import interface
from zope import component

import unittest

from zope.testing import doctest, doctestunit
from zope.app.testing import placelesssetup
from zope.configuration import xmlconfig

from bungeni.models import schema

from bungeni.core.workflows import adapters
from bungeni.ui import descriptor

zcml_slug = """
<configure xmlns="http://namespaces.zope.org/zope"
        xmlns:db="http://namespaces.objectrealms.net/rdb"
    >
    <include package="bungeni.alchemist" file="meta.zcml"/>
    <!-- Setup Database Connection -->
    <include package="bungeni_custom.sys" file="db.zcml" />
    <db:bind engine="bungeni-test" metadata="bungeni.models.schema.metadata" />
    <db:bind engine="bungeni-test" metadata="bungeni.alchemist.security.metadata" />
</configure>
"""

def setUp(test):
    placelesssetup.setUp()
    xmlconfig.string(zcml_slug)
    schema.metadata.create_all(checkfirst=True)

def tearDown(test):
    placelesssetup.tearDown()
    schema.metadata.drop_all(checkfirst=True)


def test_suite():

    doctests = ('readme.txt', 
                'settings.txt', 
                #!+BookedResources 'resourcebooking.txt',
                'venue.txt'
                )
    
    globs = dict(interface=interface, component=component)

    test_suites = []
    for filename in doctests:
        test_suite = doctestunit.DocFileSuite(filename,
                                              setUp = setUp,
                                              tearDown = tearDown,
                                              globs = globs,
                                              optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS)
        test_suites.append(test_suite)

    return unittest.TestSuite(test_suites)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
        
