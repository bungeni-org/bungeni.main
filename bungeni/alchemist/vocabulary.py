# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist vocabulary - [
    ore.alchemist.vocabulary
]

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


# used directly in bungeni
__all__ = [
    "DatabaseSource",   # alias -> ore.alchemist.vocabulary
]


from ore.alchemist.vocabulary import DatabaseSource

