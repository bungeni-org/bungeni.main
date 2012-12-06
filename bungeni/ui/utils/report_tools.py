# -*- coding: utf-8 -*-
# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Reporting utilities

Recommended usage:
`from bungeni.ui.utils import report_tools`

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.utils.reports")

import re

DEFAULT_SPAN_HOURS = 168

SPAN_LENGTHS = { 'h':1, 'd': 24, 'w':168 }

RE_ONE_DY_WK_HR = re.compile("^([1-9]{1}[0-9]?)([hdw]{1})$")
RE_DY_HR = re.compile("^([1-9]{1}[0-9]?)(d)([0-9]{1}|1[0-9]?|2[0-3]?)(h)$")
RE_WK_DY = re.compile("^([1-9]{1}[0-9]?)([w]{1})([1-6]{1})(d)$")
RE_WK_DY_HR = re.compile("^([1-9]{1}[0-9]?)([w]{1})([1-6]{1})(d)([0-9]{1}|1[0-9]?|2[0-3]?)(h)$")

MATCHERS = [RE_ONE_DY_WK_HR, RE_DY_HR, RE_WK_DY, RE_WK_DY_HR]

def match_period_spec(period):
    """Match time specification against regular expressions in `MATCHERS`
    
    >>> from bungeni.ui.utils import report_tools
    >>> report_tools.match_period_spec("")
    ()
    >>> report_tools.match_period_spec("1")
    ()
    >>> report_tools.match_period_spec("a")
    ()
    >>> report_tools.match_period_spec("x")
    ()
    >>> report_tools.match_period_spec("1h")
    ('1', 'h')
    >>> report_tools.match_period_spec("10h")
    ('10', 'h')
    >>> report_tools.match_period_spec("9d")
    ('9', 'd')
    >>> report_tools.match_period_spec("12w")
    ('12', 'w')
    >>> report_tools.match_period_spec("2w1d")
    ('2', 'w', '1', 'd')
    >>> report_tools.match_period_spec("12W")
    ('12', 'w')
    >>> report_tools.match_period_spec("3d6h")
    ('3', 'd', '6', 'h')
    >>> report_tools.match_period_spec("3d37h")
    ()
    >>> report_tools.match_period_spec("3w4d")
    ('3', 'w', '4', 'd')
    >>> report_tools.match_period_spec("3w40d")
    ()
    >>> report_tools.match_period_spec("4w5d2h")
    ('4', 'w', '5', 'd', '2', 'h')
    >>> report_tools.match_period_spec("4w14d2h")
    ()
    >>> report_tools.match_period_spec("4w6d29h")
    ()
    
    """
    assert isinstance(period, basestring)
    period = period.lower()
    matched = ()
    for matcher in MATCHERS:
        test_match = matcher.match(period)
        if test_match is not None:
            matched = test_match.groups()
            break
    return matched


def compute_hours(period):
    """Compute the sum in hours from a span spec
    
    >>> from bungeni.ui.utils import report_tools
    >>> report_tools.compute_hours("9G")
    168
    >>> report_tools.compute_hours("1h")
    1
    >>> report_tools.compute_hours("2h")
    2
    >>> report_tools.compute_hours("2d")
    48
    >>> report_tools.compute_hours("1w")
    168
    >>> report_tools.compute_hours("7d")
    168
    >>> report_tools.compute_hours("7d")
    168
    >>> report_tools.compute_hours("3d2h")
    74
    >>> report_tools.compute_hours("2w1d")
    360
    >>> report_tools.compute_hours("4w6d3h")
    819
    
    """
    parsed = match_period_spec(period)
    _len_spec = len(parsed)
    if (_len_spec > 0) and (_len_spec % 2 == 0):
        _x_ops = [ parsed[x] for x in range(0, _len_spec, 2) ]
        _y_ops = [ parsed[y] for y in range(1, _len_spec, 2) ]
        _z_sum = [ int(_x_ops[z]) * SPAN_LENGTHS[_y_ops[z]] 
                   for z in range(0, (_len_spec / 2))
        ]
        return sum(_z_sum)

    else:
        log.error(u"Provided timespan spec %s does not parse", period)
        return DEFAULT_SPAN_HOURS
