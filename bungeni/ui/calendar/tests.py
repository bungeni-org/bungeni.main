# encoding: utf-8
"""
$Id: tests.py 7341 2010-09-23 09:48:26Z mario.ruggier $
"""
import unittest

from zope.testing import doctest, doctestunit


def test_suite():
    doctests = ('readme.txt',)
    test_suites = []
    
    for filename in doctests:
        test_suite = doctestunit.DocFileSuite(
            filename,
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS)
        test_suites.append(test_suite)
    return unittest.TestSuite( test_suites )

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')


