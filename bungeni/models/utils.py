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
from bungeni.alchemist import Session
from bungeni.models import interfaces, domain, schema, delegation
from bungeni.utils import common


# legislature and chambers


def get_context_chamber(context):
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
    ''' !+ assume unicameral, date
    import datetime
    date = None
    if parliament is None:
        def getFilter(date):
            return sql.or_(
                sql.between(date, 
                    schema.group.c.start_date, schema.group.c.end_date),
                sql.and_(
                    schema.group.c.start_date<=date, 
                    schema.group.c.end_date==None))
        if not date:
            date = datetime.date.today()
        session = Session()
        query = session.query(domain.Parliament).filter(getFilter(date))
        try:
            parliament = query.one()
        except:
            ##XXX raise(_(u"inconsistent data: none or more than one parliament found for this date"))
            # !+DATA(mb, July-2012) this should get the one active parliament
            # needs some review if there is more than one parliament active e.g.
            # bicameral legislatures
            query = session.query(domain.Parliament).filter(schema.group.c.status=="active")
            try:
                parliament = query.one()
            except Exception, e:
                log.error("Could not find active parliament. Activate a parliament"
                    " in Bungeni admin :: %s", e.__repr__())
                raise ValueError("Unable to locate a currently active parliament")
    '''


def get_group_chamber(group):
    """Cascade up first group ancestry to chamber, returning it (or None).
    """
    return common.getattr_ancestry(group, None, "parent_group",
        acceptable=interfaces.IParliament.providedBy)
    ''' !+ equivalent alternative:
    if group:
        if group.type == "parliament":
            return group
        else:
            return get_group_chamber(group.parent_group)
    '''

def get_login_user_chamber():
    user = get_login_user()
    if user:
        for gm in user.group_membership:
            # cascade up first group ancestry, to chamber (or None)
            return get_group_chamber(gm.group)


def get_login_user():
    """Get the logged in user. Returns None if no user logged in.
    """
    login = common.get_request_login()
    if login:
        return get_user_for_login(login)

def get_user_for_login(login):
    """Get the User for this login name.
    """
    # !+group_principal(mr, may-2012) and when principal_id is for a group?
    return Session().query(domain.User).filter(domain.User.login == login).one()
    # !+ sa.exc InvalidRequestError, NoResultFound, MultipleResultsFound


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


from zope.securitypolicy.interfaces import IPrincipalRoleMap
def get_owner_user(context):
    """Get the user who is the bungeni.Owner (via the PrincipalRoleMap) for 
    the context, if any. Raise ValueError if multiple, return None if none.
    """
    logins = [ pid
        for (pid, setting) 
        in IPrincipalRoleMap(context).getPrincipalsForRole("bungeni.Owner") 
        if setting ]
    if logins:
        # may only have up to one Owner role assigned
        if len(logins) > 1:
            raise ValueError("Ambiguous, multiple Owner roles assigned.")
        return get_user_for_login(logins[0])


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

''' !+UNUSED and adding overhead to refactoring efforts
def get_context_chamber_governments(parliament=None):
    if parliament is None:
        parliament = get_context_chamber()
    governments = Session().query(domain.Government).filter(
            sql.and_(domain.Government.parent_group_id == parliament.group_id,
                     domain.Government.status == "active")).all()
    return governments
'''


''' !+UNUSED and adding overhead to refactoring efforts
def get_context_chamber_committees(parliament=None):
    if parliament is None:
        parliament = get_context_chamber(None)
    committees = Session().query(domain.Committee).filter(
            sql.and_(domain.Committee.parent_group_id == parliament.group_id,
                     domain.Committee.status == "active")).all()
    return committees
'''


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


# misc queries

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
    # .filter(domain.User.user_id == user_id).one()


# misc

def is_column_binary(column):
    """Return true if column is binary - assumption (one column).
    """
    return isinstance(column.type, sa.types.Binary)


