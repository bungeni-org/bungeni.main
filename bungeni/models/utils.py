# bungeni - http://www.bungeni.org/
# Parliamentary and Legislative Information System
# Copyright (C) 2010 UN/DESA - http://www.un.org/esa/desa/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Utilities to help with working with queries on the domain model

$Id$
"""
log = __import__("logging").getLogger("bungeni.models.utils")


from zope.security.management import getInteraction
from zope.publisher.interfaces import IRequest
import sqlalchemy as sa
from sqlalchemy import sql
from sqlalchemy.orm import eagerload
from bungeni.alchemist import Session
import domain, schema, delegation


# !+ move "contextual" utils to ui.utils.contextual

# !+rename get_request_principal(), get_request_principal_id()
def get_principal():
    """ () -> either(zope.security.interfaces.IGroupAwarePrincipal, None)
    """
    interaction = getInteraction()
    for participation in interaction.participations:
        if IRequest.providedBy(participation):
            return participation.principal

def get_principal_id():
    """ () -> either(str, None), login name of current principal, or None.
    """
    principal = get_principal()
    if principal is not None:
        return principal.id


# !+rename get_request_user(), get_request_user_id()
def get_db_user(context=None):
    """ get the logged in user 
    Note: context is not used, but accommodated for as a dummy optional input 
    parameter to allow usage of this utility in e.g.
    bungeni.core.app: container_getter(get_db_user, "questions")
    """
    principal_id = get_principal_id()
    session = Session()
    query = session.query(domain.User).filter(domain.User.login == principal_id)
    results = query.all()
    if len(results) == 1:
        return results[0]

def get_db_user_id(context=None):
    """ get the (numerical) user_id for the currently logged in user
    """
    db_user = get_db_user(context)
    if db_user is not None:
        return db_user.user_id

def is_current_or_delegated_user(user_id):
    """Is this user (a delegation of) the currently logged user?
    """
    current_user = get_db_user()
    # Only if there is a user logged in!
    if current_user:
        if current_user.user_id == user_id:
            return True
        for d in delegation.get_user_delegations(current_user.user_id):
            if d.user_id == user_id:
                return True
    return False

from zope.securitypolicy.interfaces import IPrincipalRoleMap
def get_prm_owner_principal_id(context):
    """Get the principal_id, if any, of the bungeni.Owner for context.
    Raise ValueError if multiple, return None if none.
    """
    principal_ids = [ pid for (pid, setting) in 
        IPrincipalRoleMap(context).getPrincipalsForRole("bungeni.Owner") 
        if setting ]
    len_pids = len(principal_ids)
    if len_pids > 1:
        # multiple Owner roles, force exception
        raise ValueError("Ambiguous, multiple Owner roles assigned.")
    elif len_pids == 1:
        return principal_ids[0]

def get_user_for_principal_id(principal_id):
    """Get the User for this principal_id.
    """
    # !+group_principal(mr, may-2012) and when principal_id is for a group?
    query = Session().query(domain.User).filter(domain.User.login == principal_id)
    try:
        return query.one()
    except sa.exc.InvalidRequestError:
        # !+ sqlalchemy.orm.exc NoResultFound, MultipleResultsFound
        return None


# contextual
def get_current_parliament(context=None):
    from bungeni.core import globalsettings
    return globalsettings.get_current_parliament()


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


def get_current_parliament_governments(parliament=None):
    if parliament is None:
        parliament = get_current_parliament()
    governments = Session().query(domain.Government).filter(
            sql.and_(domain.Government.parent_group_id == parliament.group_id,
                     domain.Government.status == "active")).all()
    return governments

def get_current_parliament_committees(parliament=None):
    if parliament is None:
        parliament = get_current_parliament(None)
    committees = Session().query(domain.Committee).filter(
            sql.and_(domain.Committee.parent_group_id == parliament.group_id,
                     domain.Committee.status == "active")).all()
    return committees

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


def get_ministries_for_user_in_government(user_id, government_id):
    """Get the ministries where user_id is a active member."""
    session = Session()
    query = session.query(domain.Ministry).join(domain.Minister).filter(
        sa.and_(
            schema.user_group_membership.c.user_id == user_id,
            schema.group.c.parent_group_id == government_id,
            schema.group.c.status == "active",
            schema.user_group_membership.c.active_p == True))
    return query.all()
def get_ministry_ids_for_user_in_government(user_id, government_id):
    """Get the ministry ids where user_id is a active member."""
    return [ ministry.group_id for ministry in
             get_ministries_for_user_in_government(user_id, government_id) ]
    '''
    # alternative approach to get ministry_ids: 
    connection = session.connection(domain.Group)
    ministries_ids_query = sa.select([schema.group.c.group_id],
        from_obj=[
        sa.join(schema.group, schema.user_group_membership,
        schema.group.c.group_id == schema.user_group_membership.c.group_id),
        ],
        whereclause =
            sa.and_(
            schema.user_group_membership.c.user_id==user_id,
            schema.group.c.parent_group_id==government_id,
            schema.group.c.status=="active",
            schema.user_group_membership.c.active_p==True))
    session = Session()
    connection = session.connection(domain.Group)
    return [ group_id[0] for group_id in 
             connection.execute(ministries_ids_query) ]
    '''


def get_groups_held_for_user_in_parliament(user_id, parliament_id):
    """ get the Offices (functions/titles) held by a user """
    session = Session()
    connection = session.connection(domain.Group)
    group_ids = get_all_group_ids_in_parliament(parliament_id)
    #!+MODELS(miano, 16 march 2011) Why are these queries hardcorded?
    #TODO:Fix this
    offices_held = sa.select([schema.group.c.short_name,
        schema.group.c.full_name,
        schema.group.c.type,
        schema.title_type.c.title_name,
        schema.member_title.c.start_date,
        schema.member_title.c.end_date,
        schema.user_group_membership.c.start_date,
        schema.user_group_membership.c.end_date,
        ],
        from_obj=[
        sa.join(schema.group, schema.user_group_membership,
        schema.group.c.group_id == schema.user_group_membership.c.group_id
            ).outerjoin(
            schema.member_title, schema.user_group_membership.c.membership_id ==
            schema.member_title.c.membership_id).outerjoin(
                schema.title_type,
                schema.member_title.c.title_type_id ==
                    schema.title_type.c.title_type_id)],
            whereclause=sa.and_(
                schema.group.c.group_id.in_(group_ids),
                schema.user_group_membership.c.user_id == user_id),
            order_by=[schema.user_group_membership.c.start_date,
                        schema.user_group_membership.c.end_date,
                        schema.member_title.c.start_date,
                        schema.member_title.c.end_date]
            )
    o_held = connection.execute(offices_held)
    return o_held

def get_group_ids_for_user_in_parliament(user_id, parliament_id):
    """ get the groups a user is member of for a specific parliament """
    session = Session()
    connection = session.connection(domain.Group)
    group_ids = get_all_group_ids_in_parliament(parliament_id)
    my_groups = sa.select([schema.user_group_membership.c.group_id],
        sa.and_(schema.user_group_membership.c.active_p == True,
            schema.user_group_membership.c.user_id == user_id,
            schema.user_group_membership.c.group_id.in_(group_ids)),
        distinct=True)
    my_group_ids = []
    for group_id in connection.execute(my_groups):
        my_group_ids.append(group_id[0])
    return my_group_ids

def get_parliament_for_group_id(group_id):
    if group_id is None:
        return None
    session = Session()
    group = session.query(domain.Group).get(group_id)
    if group.type == "parliament":
        return group
    else:
        return get_parliament_for_group_id(group.parent_group_id)

def get_parliament_for_user(user):
    if user.group_membership:
        return get_parliament_for_group_id(user.group_membership[0].group.group_id)
    # !+ what guarantees that "first" [0] group the user is a member of is
    # the right place to start?

def getattr_ancestry(context, name, parent_ref="__parent__"):
    """Get the first encountered non-None value for attribute {name}, 
    cascading upwards to parent via {parent_ref}.
    """
    while context is not None:
        value = getattr(context, name, None)
        if value is not None:
            return value
        context = getattr(context, parent_ref, None)


# misc queries

# !+parliament_mapper_property(mr, jan-2013) some types/tables define a 
# parliament_id column, but not parliament mapper property... add it?
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
    # .filter(domain.User.user_id == user_id).one()


# misc

from bungeni.models import fields
BINARY_COLUMN_TYPES = [sa.types.Binary, fields.FSBlob]
def is_column_binary(column):
    """return true if column is binary - assumption (one column)"""
    if column.type.__class__  in BINARY_COLUMN_TYPES:
        return True
    return False



