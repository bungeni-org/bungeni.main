# encoding: utf-8
"""
$Id$
"""

from zope import interface
from zope import component

import unittest

from zope.testing import doctest, doctestunit
from zope.app.testing import placelesssetup
from zope.configuration import xmlconfig
from bungeni.models import metadata
from bungeni.core.workflows import adapters

import forms.test_dates

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
     metadata="alchemist.security.metadata" />

  <!-- Setup Core Model --> 
  <include package="bungeni.ui" file="catalyst.zcml"/>
 
</configure>
"""

def setUp( test ):
    placelesssetup.setUp()
    xmlconfig.string( zcml_slug )
    metadata.create_all( checkfirst=True )
    
def tearDown( test ):
    placelesssetup.tearDown()
    metadata.drop_all( checkfirst=True )

def test_suite():
    doctests = ('forms/readme.txt',)

    docfiles = ("bungeni.ui.calendar.utils",
                "bungeni.ui.forms.forms")
    
    globs = dict(
        interface=interface,
        component=component)
    
    test_suites = []
    
    for filename in doctests:
        test_suite = doctestunit.DocFileSuite(
            filename,
            setUp=setUp,
            tearDown=tearDown,
            globs=globs,
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS)
        test_suites.append(test_suite)

    for filename in docfiles:
        test_suite = doctestunit.DocTestSuite(
            filename,
            setUp=setUp,
            tearDown=tearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS)
        test_suites.append(test_suite)

    test_suites.append(forms.test_dates.test_suite())
    return unittest.TestSuite( test_suites )

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')


