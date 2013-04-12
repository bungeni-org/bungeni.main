# bungeni - http://www.bungeni.org/
# Parliamentary and Legislative Information System
# Copyright (C) 2010 UN/DESA - http://www.un.org/esa/desa/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Utilities to help with working with queries on the domain model

$Id$
"""
log = __import__("logging").getLogger("bungeni.models.utils")


import sqlalchemy as sa
from sqlalchemy import sql
from sqlalchemy.orm import eagerload
from zope.securitypolicy.interfaces import IPrincipalRoleMap
from bungeni.alchemist import Session
from bungeni.models import interfaces, domain, delegation
from bungeni.utils import common


# legislature and chambers

def get_chamber_for_context(context):
    """Return the chamber in which the context exists.
    """
    # first look for current parliament from context tree
    chamber = common.getattr_ancestry(context, None, "__parent__",
        acceptable=interfaces.IParliament.providedBy)
    # !+ should this ever be None here?
    if chamber is None:
        # check logged in user's chamber
        chamber = get_login_user_chamber()
    return chamber


def get_chamber_for_group(group):
    """Cascade up first group ancestry to chamber, returning it (or None).
    """
    return common.getattr_ancestry(group, None, "parent_group",
        acceptable=interfaces.IParliament.providedBy)
    ''' !+ equivalent alternative:
    if group:
        if group.type == "parliament":
            return group
        else:
            return get_chamber_for_group(group.parent_group)
    '''


def user_delegatations(user):
    session = Session()
    delegations = session.query(domain.UserDelegation).filter(
        domain.UserDelegation.delegation_id == user.user_id).all()
    return delegations


def get_login_user_chamber():
    user = get_login_user()
    if user:
        user_delegations = user_delegatations(user)
        if user_delegations:
            user = user_delegations[0].user
        for gm in user.group_membership:
            # cascade up first group ancestry, to chamber (or None)
            return get_chamber_for_group(gm.group)


def get_login_user():
    """Get the logged in user, if any.
    Returns None if no user logged in or no such user.
    """
    login = common.get_request_login()
    try:
        return get_user_for_login(login)
    except sa.orm.exc.NoResultFound:
        return


def get_user_for_login(login):
    """Get the User for this login name.
    Raises sa.orm.exc InvalidRequestError, NoResultFound, MultipleResultsFound
    """
    return Session().query(domain.User).filter(domain.User.login == login).one()


def is_current_or_delegated_user(user):
    """Is this user (a delegation of) the currently logged user?
    """
    current_user = get_login_user()
    # Only if there is a user logged in!
    if current_user:
        if current_user.user_id == user.user_id:
            return True
        for d in delegation.get_user_delegations(current_user):
            if d.user_id == user.user_id:
                return True
    return False


def get_owner_for_context(context):
    """Get the user who is the bungeni.Owner (via the PrincipalRoleMap) for
    the context, if any. Raise ValueError if multiple, return None if none.
    """
    # !+OWNER_TO_DRAFTER
    logins = get_pids_with_role_on_context(context, "bungeni.Owner")
    if logins:
        # may only have up to one Owner role assigned
        if len(logins) > 1:
            raise ValueError("Ambiguous, multiple Owner roles assigned.")
        return get_user_for_login(logins[0])


def get_pids_with_role_on_context(context, role_id):
    """Get the principal_ids (via the PrincipalRoleMap) who have the role on
    the context, if any.
    """
    return [ pid for (pid, setting)
        in IPrincipalRoleMap(context).getPrincipalsForRole(role_id)
        if setting ]


def container_getter(parent_container_or_getter, name, query_modifier=None):
    """Get a child container with name from the specified parent
    container/container_callback."""
    #from bungeni.alchemist.interfaces import IAlchemistContainer
    # !+ the parent container SHOULD be implementing IAlchemistContainer but it
    # does not seem to! As a best alternative, that is close but conceptually 
    # not quite the same, we check for IBungeniGroup
    from bungeni.models.interfaces import IBungeniGroup
    def func(context):
        if IBungeniGroup.providedBy(parent_container_or_getter):
            parent_container = parent_container_or_getter
        else:
            parent_container = parent_container_or_getter(context)
        #
        try:
            c = getattr(parent_container, name)
        except AttributeError:
            # the container we need is not there, data may be missing in the db
            from zope.publisher.interfaces import NotFound
            raise NotFound(context, name)
        c.setQueryModifier(sql.and_(c.getQueryModifier(), query_modifier))
        return c
    func.__name__ = "get_%s_container" % name
    return func


def get_all_group_ids_in_parliament(parliament_id):
    """ get all groups (group_ids) in a parliament
    including the sub (e.g. ministries) groups """
    session = Session()
    group_ids = [parliament_id, ]
    query = session.query(domain.Group).filter(
        domain.Group.parent_group_id == parliament_id).options(
            eagerload("contained_groups"))
    results = query.all()
    for result in results:
        group_ids.append(result.group_id)
        for group in result.contained_groups:
            group_ids.append(group.group_id)
    return group_ids

# !+parliament_mapper_property(mr, jan-2013) some types/tables define a 
# parliament_id column, but not parliament mapper property... add it?
# !+rename get_chamber_by_id
def get_parliament(parliament_id):
    return Session().query(domain.Parliament).get(parliament_id)            


def get_member_of_parliament(user_id):
    """Get the MemberOfParliament instance for user_id.
    Raises sqlalchemy.orm.exc.NoResultFound
    """
    return Session().query(domain.MemberOfParliament
        ).filter(domain.MemberOfParliament.user_id == user_id).one()


def get_user(user_id):
    """Get the User instance for user_id.
    Raises sqlalchemy.orm.exc.NoResultFound
    """
    return Session().query(domain.User).get(user_id)


# misc
def is_column_binary(column):
    """Return true if column is binary - assumption (one column).
    """
    return isinstance(column.type, sa.types.Binary)
