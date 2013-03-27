# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist -- intermediary to all alchemist packages

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")

# used directly in bungeni
__all__ = [
    "Session",
]


"""How do we access the current session in use:

from bungeni.alchemist import Session
session = Session()
assert session is Session()
"""

from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.scoping import ScopedSession
from transaction._transaction import Status as ZopeStatus
import warnings
from zope.sqlalchemy import ZopeTransactionExtension

TWOPHASE = True

class AlchemistWarning(RuntimeWarning):
    """Warnings of features that will be removed in a next version.
    """

class AlchemistTransactionExtension(ZopeTransactionExtension):
    def before_commit(self, session):
        # zope.sqlalchemy makes an assert here, to not allow saving the session
        # directly, so that commits must go through the transaction.
        # Alchemist's manager worked without this, and so we must provide a
        # BBB for alchemist users. We change the assert to a mare warning.
        if self.transaction_manager.get().status != ZopeStatus.COMMITTING: 
            warnings.warn(
                "Transaction must be committed using the transaction manager", 
                AlchemistWarning)

Session = ScopedSession(
    sessionmaker(
        autoflush=True, 
        autocommit=False,
        extension=AlchemistTransactionExtension(),
        twophase=TWOPHASE))


