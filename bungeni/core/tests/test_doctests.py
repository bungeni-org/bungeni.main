"""
$Id$
"""

from zope import interface
from zope import component

import os
import copy
import shutil
import unittest
import datetime

from zope.testing import doctest, doctestunit
from zope.app.testing import placelesssetup, ztapi
from zope.configuration import xmlconfig

from bungeni.models import metadata
from bungeni.models.interfaces import IBungeniContent
from bungeni.models.interfaces import IDirectoryLocation
from bungeni.core.interfaces import IFilePathChooser
from bungeni.core.interfaces import IVersionedFileRepository

zcml_slug = """
<configure xmlns="http://namespaces.zope.org/zope"
           xmlns:db="http://namespaces.objectrealms.net/rdb">

  <include package="bungeni.core" file="ftesting.zcml" />
  
</configure>
"""

def setUp(test):
    placelesssetup.setUp()
    xmlconfig.string( zcml_slug )
    metadata.create_all( checkfirst=True )
    
def tearDown( test ):
    placelesssetup.tearDown()
    metadata.drop_all( checkfirst=True )


def test_suite():
    from bungeni.core.app import BungeniApp

    # NOTE: to run an individual test txt file from the commandline:
    #
    #       $ bin/test -s bungeni.core -t file.txt
    #
    doctests = (
                #'audit.txt',
                'version.txt',
                #'odf.txt',
                'workflows/question.txt',
                'workflows/motion.txt',
                'workflows/bill.txt',
                'workflows/transitioncron.txt',
                )

    docfiles = ("bungeni.core.transformation",)
    
    # set up global symbols for doctests
    today = datetime.date.today()
    globs = dict(
        interface=interface,
        component=component,
        datetime=datetime,
        os=os,
        copy=copy,
        app=BungeniApp(),
        today=today,
        yesterday=today-datetime.timedelta(1),
        daybeforeyesterday=today-datetime.timedelta(2),
        tomorrow=today+datetime.timedelta(1),
        dayat=today+datetime.timedelta(2),
        path=os.path.dirname(__file__),
        )

    test_suites = []
    for filename in doctests:
        test_suite = doctestunit.DocFileSuite(
            os.path.join(os.path.pardir, filename),
            setUp = setUp,
            tearDown = tearDown,
            globs = globs,
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS)
        
        test_suites.append(test_suite)

    for filename in docfiles:
        test_suite = doctestunit.DocTestSuite(
            filename,
            setUp=setUp,
            tearDown=tearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS)
        test_suites.append(test_suite)


    return unittest.TestSuite( test_suites )

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')


