#!/usr/bin/env python
# encoding: utf-8
from bungeni.alchemist import Session
import sqlalchemy as rdb
import  domain

def get_user_delegations(user_id):
    """ get all delegations for a given user_id
    user_id = schema.users.c.user_id
    both delegator and delegee must be active
    """
    session = Session()
    query = session.query(domain.UserDelegation).filter(
                rdb.and_(
                domain.UserDelegation.delegation_id == user_id)
                )
    results = query.all()
    for result in results:
        if ((result.user.active_p == 'A') and
            (len(result.user.login) > 1) and
            (result.delegation.active_p == 'A')):
            yield result.user
    #session.close()
