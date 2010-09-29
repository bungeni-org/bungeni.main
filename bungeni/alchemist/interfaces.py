# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist interfaces - [
    ore.alchemist.interfaces
    alchemist.ui.interfaces
]

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


# ore.alchemist.interfaces

from ore.alchemist.interfaces import IAlchemistContent
from ore.alchemist.interfaces import IAlchemistContainer
from ore.alchemist.interfaces import IDatabaseEngine
from ore.alchemist.interfaces import IIModelInterface
from ore.alchemist.interfaces import IRelationChange

from alchemist.ui.interfaces import IContentViewManager

