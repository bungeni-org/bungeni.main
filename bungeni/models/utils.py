# bungeni - http://www.bungeni.org/
# Parliamentary and Legislative Information System
# Copyright (C) 2010 UN/DESA - http://www.un.org/esa/desa/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Utilities to help with working with queries on the domain model

$Id$
"""
log = __import__("logging").getLogger("bungeni.models.utils")


import datetime
import sqlalchemy as sa
from sqlalchemy import sql
from sqlalchemy.orm import eagerload
from zope.securitypolicy.interfaces import IPrincipalRoleMap
from bungeni.alchemist import Session
from bungeni.alchemist.interfaces import IAlchemistContainer
from bungeni.core.interfaces import ISection
from bungeni.models import interfaces, domain, delegation
from bungeni.utils import common
from bungeni.capi import capi


def get_ancestor_group(group, acceptable=None):
    """Cascade up group ancestry to first acceptable(group), or None.
    """
    return common.getattr_ancestry(group, 
        horizontal_attr=None, vertical_attr="parent_group", acceptable=acceptable)


def is_descendent_of(group, ancestor):
    """Does group descend from ancestor?
    """
    if group is None:
        return False
    # !+ comparing with "is" keyword operator fails without removeSecurityProxy
    parent_group = group.parent_group
    return parent_group == ancestor or is_descendent_of(parent_group, ancestor)


def get_group_for_context(context):
    """Return the "main" (as meaning of this for type) group for this context,
    or None if no such logical group can be determined.
    
    The group may be None if:
    - context is a user who is not a member of any group within any chamber
    - context is a core.interfaces.ISection or workspace Container, for which
      there is no "contextual" chamber is defined in the traversal hierarchy
    - context is an IAlchemistContainer that is not hierarchically contained
      within an IBungeniContent (no such instance in its __parent__ ancestry)
    
    !+ should this be shipped out as a domain_model.group property, or 
    interfaces organized in "how group is determined" categories?
    """
    group = None
    if interfaces.IGroup.providedBy(context):
        group = context
    elif interfaces.IEvent.providedBy(context):
        group = context.group or context.head.group
    elif (interfaces.IDoc.providedBy(context) or 
            interfaces.IGroupMember.providedBy(context) or
            interfaces.IGroupAddress.providedBy(context) or
            interfaces.ISitting.providedBy(context) or
            interfaces.ITitleType.providedBy(context) or
            interfaces.IEditorialNote.providedBy(context) or
            interfaces.IHeading.providedBy(context)
        ):
        group = context.group
    elif (IAlchemistContainer.providedBy(context) or
            ISection.providedBy(context) # !+group ALWAYS None?
        ):
        group = get_group_for_context(context.__parent__)
    elif (interfaces.IAttachment.providedBy(context) or
            interfaces.ISignatory.providedBy(context)
        ):
        group = context.head.group
    elif (interfaces.IMemberTitle.providedBy(context) or
            interfaces.IMemberRole.providedBy(context)
        ):
        group = context.member.group
    elif (interfaces.IDebateRecord.providedBy(context) or
            interfaces.ISittingAttendance.providedBy(context)
        ):
        group = context.sitting.group
    if group is None:
        #from bungeni.utils import probing
        #log.warn(probing.interfaces(context))
        log.warn("!+GROUP_FOR_CONTEXT Cannot determine group for context: %s", context)
        #raise ValueError, "No group for context: %s" % (context)
    return group


# legislature and chambers

def get_chamber_for_context(context, name="group"):
    """Return the chamber in which the context exists.
    
    The chamber may be None if:
    - group is None
    - group is outside of a chamber !+LEGISLATURE_AS_CHAMBER this temporary 
    workaround will cause the returned "chamber" for a group outside either 
    chamber to be the Legislature e.g. for a ministry outside of both chambers
    """
    group = get_group_for_context(context)
    chamber = get_chamber_for_group(group) 
    if chamber is None:
        # !+USER_CHAMBER approximation, does this always give the correct chamber?
        user = get_login_user()
        if user:
            chamber = get_user_chamber(user)
            log.warn("!+USER_CHAMBER [%s] via LOGIN_USER %r GOT [%s]", 
                    context, user.login, chamber)
        else:
            log.warn("!+USER_CHAMBER [%s] - no USER logged in!", context)
    return chamber


def get_chamber_for_group(group):
    """Cascade up first group ancestry to chamber, returning it (or None).
    """
    return get_ancestor_group(group, acceptable=capi.chamber_type_info.interface.providedBy)
    ''' !+ equivalent alternative:
    if group:
        if group.type == "chamber":
            return group
        else:
            return get_chamber_for_group(group.parent_group)
    '''


def get_user_delegations(user):
    session = Session()
    delegations = session.query(domain.UserDelegation).filter(
        domain.UserDelegation.delegation_id == user.user_id).all()
    return delegations

def get_user_groups(user):
    """Get all user groups (including parent groups).
    """
    session = Session()
    query = session.query(domain.Group).join(
        domain.GroupMember).filter(
            sql.expression.and_(
                    domain.GroupMember.user_id == user.user_id,
                    domain.GroupMember.active_p == True,
                    #domain.Group.status.in_(status)
            )
        )
    groups = query.all()
    group_ids = [ group.group_id for group in groups ]
    # add parent group
    parent_groups = []
    for group in groups:
        if group.parent_group_id and group.parent_group_id not in group_ids:
            parent_groups.append(group.parent_group)
            group_ids.append(group.parent_group_id)
    return parent_groups + groups


def get_user_chamber(user):
    """Pick off the first non-None chamber via user's group memberships (via 
    the group) else return None. 
    
    !+GROUP_MEMBERSHIP_ORDER is this logic always comes out correct? 
    What is the order that user.group_membership is returned in? 
    Possibility of different chamber if different order?
    """
    user_delegations = get_user_delegations(user)
    if user_delegations:
        user = user_delegations[0].user
    for gm in user.group_membership:
        # cascade up the group ancestry, to chamber (or None)
        chamber = get_chamber_for_group(gm.group)
        if chamber is not None:
            return chamber


# user

def get_login_user():
    """Get the logged in user, if any.
    Returns None if no user logged in or no such user.
    """
    login = common.get_request_login()
    try:
        return get_user_for_login(login)
    except sa.orm.exc.NoResultFound:
        # !+ why is this silenced?
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


''' !+PrincipalRoleMap(mr, jun-2013) implement as an orm property as necessary
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
'''


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
    # not quite the same, we check for IGroup
    def func(context):
        if interfaces.IGroup.providedBy(parent_container_or_getter):
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


def get_all_group_ids_in_chamber(chamber_id):
    """ get all groups (group_ids) in a chamber
    including the sub (e.g. ministries) groups """
    session = Session()
    group_ids = [chamber_id,]
    query = session.query(domain.Group).filter(
        domain.Group.parent_group_id == chamber_id).options(
            eagerload("contained_groups"))
    results = query.all()
    for result in results:
        group_ids.append(result.group_id)
        for group in result.contained_groups:
            group_ids.append(group.group_id)
    return group_ids

# !+chamber_mapper_property(mr, jan-2013) some types/tables define a 
# chamber_id column, but not chamber mapper property... add it?
# !+rename get_chamber_by_id
# !+get_chamber unused
#def get_chamber(chamber_id):
#    return Session().query(domain.Chamber).get(chamber_id)            


def get_member_of_chamber(user_id):
    """Get the Member instance for user_id.
    Raises sqlalchemy.orm.exc.NoResultFound
    """
    return Session().query(domain.Member
        ).filter(domain.Member.user_id == user_id).one()


def get_user(user_id):
    """Get the User instance for user_id.
    Raises sqlalchemy.orm.exc.NoResultFound
    """
    return Session().query(domain.User).get(user_id)

def get_group(group_id):
    """Get the Group instance for group_id.
    Raises sqlalchemy.orm.exc.NoResultFound
    """
    return Session().query(domain.Group).get(group_id)


def get_group_conceptual_active(conceptual_name):
    """Get the one active group for conceptual_name.
    Raises sqlalchemy.orm.exc.NoResultFound.
    """
    return Session().query(domain.Group).filter(sql.expression.and_(
            domain.Group.conceptual_name == conceptual_name,
            # !+ACTIVE Group.active 
            domain.Group.start_date < datetime.datetime.today().date(),
            domain.Group.end_date == None # !+ cannot use "is" operator !
        )).one()


# misc
def is_column_binary(column):
    """Return true if column is binary - assumption (one column).
    """
    return isinstance(column.type, sa.types.Binary)


