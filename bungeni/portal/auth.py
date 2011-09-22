"""
``repoze.who`` authenticator plugins against a relational database
"""
log = __import__("logging").getLogger("bungeni.portal.auth")

from zope import interface
from zope.app.security.principalregistry import principalRegistry
from zope.app.security.interfaces import PrincipalLookupError

from repoze.who.interfaces import IAuthenticator
from repoze.who.interfaces import IMetadataProvider

from bungeni.alchemist import Session
from sqlalchemy.exceptions import UnboundExecutionError
import sqlalchemy as rdb
from sqlalchemy.orm import eagerload, lazyload

from bungeni.models import domain, delegation


def get_user(login_id):
    session = Session()
    try:
        db_user = session.query(domain.User).filter(
            domain.User.login == login_id).one()
    except rdb.orm.exc.NoResultFound:
        log.error("No user with login id, %s exists" % login_id)
        return None
    except rdb.orm.exc.MultipleResultsFound:
        log.error("Multiple users found with the same login id, %s" %
                  login_id)
        return None
    else:
        return db_user


def get_user_groups(login_id):
    """ get group for users:
    a) the groups defined by his user_group_memberships
    b) the users who have him assigned as a delegation
    c) the groups of the delegation user.
    """
    groups = set()
    groups.add(login_id)

    def get_groups(user_id):
        principal_ids = []
        session = Session()
        query = session.query(domain.GroupMembership).filter(
            rdb.and_(domain.GroupMembership.user_id == user_id,
                     domain.GroupMembership.active_p == True)).options(
            eagerload("group"), lazyload("user"))
        for membership in query:
                principal_ids.append(membership.group.group_principal_id)
        return principal_ids
    user_id = get_user(login_id).user_id
    if user_id:
        for elem in get_groups(user_id):
            groups.add(elem)
    user_delegations = delegation.get_user_delegations(user_id)
    for user in user_delegations:
        for elem in getGroups(user.user_id):
            groups.add(elem)
    return groups


class AlchemistWhoPlugin(object):
    interface.implements(IAuthenticator, IMetadataProvider)

    def get_groups(self, login_id):
        groups = get_user_groups(login_id)
        groups.add("zope.Authenticated")
        groups.add("zope.anybody")
        return groups

    def authenticate(self, environ, identity):
        if not ('login' in identity and 'password' in identity):
            return None
        user = get_user(identity['login'])
        if user and user.checkPassword(identity['password']):
            return identity['login']

    def add_metadata(self, environ, identity):
        userid = identity.get('repoze.who.userid')
        user = get_user(userid)
        groups = None
        if user is not None:
            groups = tuple(self.get_groups(userid))
            try:
                session = Session()
            except UnboundExecutionError, e:
                log.warn(e)
            admin_user = session.query(domain.AdminUser).get(user.user_id)
            if admin_user:
                groups = groups + ('zope.manager',)
            identity.update({
                'email': user.email,
                'title': u"%s, %s" % (user.last_name, user.first_name),
                'groups': groups,
                })


class GlobalAuthWhoPlugin(object):
    interface.implements(IAuthenticator, IMetadataProvider)

    def authenticate(self, environ, identity):
        if not ('login' in identity and 'password' in identity):
            return None

        principal = self.get_principal_by_login(identity['login'])
        if principal and principal.validate(identity['password']):
            return identity['login']

    def get_principal(self, id):
        try:
            return principalRegistry.getPrincipal(id)
        except PrincipalLookupError:
            pass
        except KeyError:
            pass

    def get_principal_by_login(self, login):
        try:
            return principalRegistry.getPrincipalByLogin(login)
        except PrincipalLookupError:
            pass
        except KeyError:
            pass

    def add_metadata(self, environ, identity):
        login = identity.get('repoze.who.userid')
        principal = self.get_principal_by_login(login)
        if principal is not None:
            identity.update({
                'title': principal.title,
                'groups': tuple(principal.groups) + (principal.id,),
                })
