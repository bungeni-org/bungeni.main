# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni alchemist utilities.
$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")

from sqlalchemy.orm import class_mapper


def get_local_table(kls):
    """Get the Selectable which this kls's Mapper manages. May be None.
    
    Note difference to "mapped_table" that is Selectable to which this kls's 
    Mapper is mapped (and in addition to a Table and Alias may slo be a Join.
    """
    return class_mapper(kls).local_table


