# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""User delegations

$Id$
"""
log = __import__("logging").getLogger("bungeni.models.delegation")

from bungeni.alchemist import Session
import sqlalchemy as sa
import  domain


def get_user_delegations(user):
    """Get all delegations for a given user.
    Both delegator and delegee must be active.
    """
    query = Session().query(domain.UserDelegation).filter(
        sa.and_(domain.UserDelegation.delegation_id == user.user_id))
    results = query.all()
    for result in results:
        if ((result.user.active_p == "A") and
                (len(result.user.login) > 1) and
                (result.delegation.active_p == "A")
            ):
            yield result.user

