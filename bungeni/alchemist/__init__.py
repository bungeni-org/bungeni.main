# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist -- intermediary to ore.alchemist package

- all bungeni usage of ore.alchemist should go through this package
- any customizations/enhancements/fixes of ore.alchemist elements should 
    be done here (as opposed to having forked code sprinkled in various 
    places over the code). 
    E.g. of a customization might be as simple as to intercept specific calls 
    to add logging.

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


__all__ = [ 'Session']

from ore.alchemist.session import Session



