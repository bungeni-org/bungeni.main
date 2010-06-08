
import random, md5, string

from AccessControl import ClassSecurityInfo
from AccessControl.SecurityManagement import getSecurityManager
from Globals import InitializeClass

from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements

from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin
from Products.PluggableAuthService.interfaces.plugins import IUserEnumerationPlugin
from Products.PluggableAuthService.interfaces.plugins import IUserAdderPlugin
from Products.PluggableAuthService.interfaces.plugins import IRolesPlugin
from Products.PluggableAuthService.interfaces.plugins import IRoleAssignerPlugin
from Products.PluggableAuthService.interfaces.plugins import IRoleEnumerationPlugin

from Products.PlonePAS.interfaces.plugins import IUserManagement
from Products.PlonePAS.interfaces.capabilities import IDeleteCapability
from Products.PlonePAS.interfaces.capabilities import IPasswordSetCapability
from Products.PlonePAS.interfaces.capabilities import IAssignRoleCapability

from Products.PluggableAuthService.permissions import ManageUsers
from Products.PluggableAuthService.permissions import SetOwnPassword

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

import sqlalchemy as rdb
import schema
from alchemist.security import schema as security_schema
from ore.alchemist import Session

from bungeni.models import domain

manage_addBungeniUserManagerForm = PageTemplateFile('zmi/user-plugin-add.pt', globals())

def manage_addBungeniUserManager(self, id, title='', REQUEST=None):
    """Add a BungeniUserManager to a Pluggable Auth Service."""
    um = UserManager(id, title )
    self._setObject(um.getId(), um)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(
                                '%s/manage_workspace'
                                '?manage_tabs_message='
                                'BungeiUserManager+added.'
                            % self.absolute_url())

def generate_salt( ):
    return ''.join( random.sample( string.letters, 12 ) )

def encrypt( word, salt ):
    return md5.md5( word + salt).hexdigest()

def safeencode(v):
    if isinstance(v, unicode):
        return v.encode('utf-8')
    return v

class UserManager( BasePlugin ):
    meta_type = 'Bungeni User Manager'
    security = ClassSecurityInfo()

    def __init__(self, id, title=None):
        self.id = self.id = id
        self.title = title

    security.declarePrivate('invalidateCacheForChangedUser')
    def invalidateCacheForChangedUser(self, user_id):
        pass

    #
    # IUserManagement implementation
    #

    security.declarePrivate('doChangeUser')
    def doChangeUser(self, login, password, **kw):
        # userSetPassword in PlonePAS expects a RuntimeError when a plugin doesn't hold the user.
        try:
            self.updateUserPassword(login, login, password)
        except KeyError:
            raise RuntimeError, "User does not exist: %s"%login


    security.declarePrivate('doDeleteUser')
    def doDeleteUser(self, login):
        try:
            self.removeUser(login)
        except KeyError:
            return False
        return True
    
    #
    # IDeleteCapability implementation
    #

    def allowDeletePrincipal(self, id):
        return self._uid( id ) is not None


    #
    # IPasswordSetCapability implementation
    #
    def allowPasswordSet(self, id):
        return self._uid( id ) is not None

    #
    # IAuthenticationPlugin implementation
    #

    security.declarePrivate('authenticateCredentials')
    def authenticateCredentials(self, credentials):
        login = credentials.get('login')
        password = credentials.get('password')
        if not login or not password: return None
        
        res = self._uid( login, auth=True )
        if not res: return None
        
        if encrypt( password, res['salt'] ) == res['password']:
            return login, login
        return None
        
    #
    # IUserEnumerationPlugin implementation
    #
    security.declarePrivate('enumerateUsers')
    def enumerateUsers( self
                      , id=None
                      , login=None
                      , exact_match=False
                      , sort_by=None
                      , max_results=None
                      , **kw
                      ):
        """See IUserEnumerationPlugin.
        """
        if id is None:
            id = login

        # try to normalize the list of ids/logins into single sequence
        if isinstance( login, (list, tuple ) ):
            if isinstance( id, (list, tuple ) ):
                ids = []
                ids.extend( id )
                ids.extend( login )
            else:
                ids = list( login )
                ids.append( id )
            id = ids
        elif isinstance( id, (list, tuple ) ) and login:
            id = list(id)
            id.append( login )
        elif id and login:
            id = [ id, login]
            
        if id is None and exact_match:
            return []
        elif id is None:
            clause = None
            for key, value in kw.items():
                column = getattr(schema.users.c, key, None)
                if column:
                    clause = rdb.and_(clause, column.contains(value))
                else:
                    like_val ='%' + str(value) +'%'
                    clause = rdb.and_(clause, 
                        rdb.or_(schema.users.c.login.like(like_val),
                                schema.users.c.first_name.like(like_val),
                                schema.users.c.last_name.like(like_val)
                            )
                        )
        elif isinstance( id, (list, tuple)) and exact_match:
            statements = []
            for i in id:
                statements.append( schema.users.c.login == i )
            clause = rdb.or_( *statements )
        elif isinstance( id, (list, tuple)) and not exact_match:
            like_val ='%' + str(id) +'%'
            clause = rdb.or_(*(map( schema.users.c.login.like, like_val)))
        elif not exact_match:
            like_val ='%' + str(id) +'%'
            clause = rdb.or_(schema.users.c.login.like(like_val),
                             schema.users.c.first_name.like(like_val),
                             schema.users.c.last_name.like(like_val)
                            )
        else:
            clause = schema.users.c.login == id
        session = Session()
        query = session.query(domain.User).filter(
                        rdb.and_( clause,
                            schema.users.c.active_p == 'A',
                            schema.users.c.login != None
                                ) )
        if sort_by:
            assert sort_by in ('login', 'last_name')
            query = query.order_by( getattr( schema.users.c, sort_by ) )
        else:
            query = query.order_by(schema.users.c.last_name, schema.users.c.first_name)
                    
        if max_results is not None and isinstance( max_results, int ):
            query =query.limit( max_results )

        return [ dict( id=safeencode(r.login), 
                title= u"%s %s" %(r.first_name, r.last_name),
                fullname= u"%s %s" %(r.first_name, r.last_name),
                email = (r.email),
                login=safeencode(r.login), pluginid=self.id ) 
                for r in query.all()]

    #
    # IUserAdderPlugin implementation
    #
    security.declarePrivate('doAddUser')
    def doAddUser(self, login, password):
        try:
            self.addUser(login, login, password)
        except KeyError:
            return False
        return True

    #
    # (notional)IZODBUserManager interface
    #
    security.declareProtected(ManageUsers, 'listUserIds')
    def listUserIds(self):
        users = schema.users.select( [schema.users.c.login ], schema.users.c.active_p == 'A').execute()
        return tuple([safeencode(r['login']) for r in users] )
    
    security.declareProtected(ManageUsers, 'listUserInfo')
    def listUserInfo(self):
        users = schema.users.select( [schema.users.c.login ], schema.users.c.active_p == 'A').execute()
        return [ dict( id=safeencode(r['login']),
                       login=safeencode(r['login']), pluginid=self.id ) for r in users]

    security.declareProtected(ManageUsers, 'getUserInfo')
    def getUserInfo(self, user_id ):
        uid = self._uid( user_id )
        if not uid:
            return None
        return dict( id=user_id, login=user_id, pluginid=self.id )

    security.declareProtected(ManageUsers, 'getLoginForUserId')
    def getLoginForUserId(self, user_id):
        return user_id
    
    security.declarePrivate('addUser')
    def addUser(self, user_id, login_name, password): # raises keyerror, lookup error
        salt = generate_salt()
        e_pass = encrypt( password, salt )
        if self._uid( login_name ):
            raise KeyError("Duplicate User Id: %s"%user_id)
        insert = schema.users.insert()
        insert.values( login = user_id, salt = salt, password = e_pass, type="user",
                       # dummy values for non null fields
                       first_name=u"unknown", last_name=u"unknown", email=u"unknown",
                       ).execute()
    
    security.declarePrivate('removeUser')
    def removeUser(self, user_id): # raises keyerror
        uid = self._uid( user_id )
        if not uid:
            raise KeyError("Invalid User"%uid)
        # update user to show as inactive
        schema.users.update().where( schema.users.c.user_id == uid ).values( active_p = 'I').execute()

    security.declarePrivate('updateUserPassword')
    def updateUserPassword(self, user_id, login_name, password): # raise keyerror, lookup error
        uid = self._uid( user_id )
        if uid is None:
            raise KeyError("Invalid User %s"%user_id )
        salt = generate_salt()
        e_pass = encrypt( password, salt )
        schema.users.update().where( schema.users.c.user_id == uid ).values(
            salt = salt,
            password = e_pass
            ).execute()

   #
    # Allow users to change their own login name and password.
    #
    security.declareProtected(SetOwnPassword, 'getOwnUserInfo')
    def getOwnUserInfo(self):
        """Return current user's info."""
        user_id = getSecurityManager().getUser().getId()
        return self.getUserInfo(user_id)
    
    def _uid( self, login, auth=False ):
        cols = [ schema.users.c.user_id ]
        if auth:
            cols.extend( [schema.users.c.password, schema.users.c.salt ] )

        session = Session()
        connection = session.connection(domain.Group)

        res = connection.execute(rdb.select( cols,
                          rdb.and_( schema.users.c.login == login,
                                    schema.users.c.active_p == 'A' )))
                       
        uid_tuple = res.fetchone()
        if not uid_tuple:
            return None
        if auth:
            return uid_tuple
        return uid_tuple[0]

    def _gid( self, name ):
        session = Session()
        groups = session.query(domain.Group).filter(
            domain.Group.group_principal_id == name).all()
        if not groups:
            return
        return groups[0].group_principal_id

    def allowRoleAssign(self, prinicipal_id, role_id):
        if role_id.startswith('bungeni.'):
            return True

    """ Assign a role to an identified principal
    """

    def assignRolesToPrincipal(self, roles, principal_id, setting=True):
        if self._uid(principal_id) is None and self._gid(principal_id) is None:
            return

        session = Session()
        connection = session.connection(domain.Group)
        if setting is True:
            # delete global mappings
            connection.execute(security_schema.principal_role_map.delete().where(
                rdb.and_(
                    security_schema.principal_role_map.c.principal_id == principal_id,
                    security_schema.principal_role_map.c.object_id == None,
                    security_schema.principal_role_map.c.object_type == None)))

        
            # update existing
            connection.execute(
                security_schema.principal_role_map.update().where(
                    rdb.and_(
                        security_schema.principal_role_map.c.principal_id==principal_id,
                        security_schema.principal_role_map.c.object_type==None,
                        security_schema.principal_role_map.c.object_id==None)).values(
                    setting=False))

        # insert new global mappings
        for role_id in tuple(roles):
            connection.execute(
                security_schema.principal_role_map.insert().values(
                    principal_id=principal_id,
                    role_id=role_id,
                    setting=setting,
                    object_type=None,
                    object_id=None))

            # remove from roles so other plugins won't attempt to
            # assign as well
            roles.remove(role_id)

        return True
    
    def doAssignRoleToPrincipal(self, principal_id, role ):

        """ Create a principal/role association in a Role Manager

        o Return a Boolean indicating whether the role was assigned or not
        """

        return self.assignRolesToPrincipal((role,), principal_id)

    def doRemoveRoleFromPrincipal(self, principal_id, role ):

        """ Remove a principal/role association from a Role Manager

        o Return a Boolean indicating whether the role was removed or not
        """

        return self.assignRolesToPrincipal((role,), principal_id, False)

    def getRolesForPrincipal(self, principal, request=None ):

        """ principal -> ( role_1, ... role_N )

        o Return a sequence of role names which the principal has.

        o May assign roles based on values in the REQUEST object, if present.
        """

        principal_id = principal.getId()
        session = Session()
        connection = session.connection(domain.Group)
        mappings = connection.execute(rdb.select(
            [security_schema.principal_role_map.c.role_id],
            rdb.and_(
                security_schema.principal_role_map.c.principal_id==principal_id,
                security_schema.principal_role_map.c.setting==True,
                security_schema.principal_role_map.c.object_type==None,
                security_schema.principal_role_map.c.object_id==None)))
        role_names = []
        for (role_name,) in mappings:
            role_names.append(role_name)
        return role_names


    """ Allow querying roles by ID, and searching for roles.
    """
    def enumerateRoles( self,
                        id=None
                      , exact_match=False
                      , sort_by=None
                      , max_results=None
                      , **kw
                      ):

        """ -> ( role_info_1, ... role_info_N )

        o Return mappings for roles matching the given criteria.

        o 'id' in combination with 'exact_match' true, will
          return at most one mapping per supplied ID ('id' and 'login'
          may be sequences).

        o If 'exact_match' is False, then 'id' may be treated by 
          the plugin as "contains" searches (more complicated searches 
          may be supported by some plugins using other keyword arguments).

        o If 'sort_by' is passed, the results will be sorted accordingly.
          known valid values are 'id' (some plugins may support others).

        o If 'max_results' is specified, it must be a positive integer,
          limiting the number of returned mappings.  If unspecified, the
          plugin should return mappings for all roles satisfying the 
          criteria.

        o Minimal keys in the returned mappings:
        
          'id' -- (required) the role ID

          'pluginid' -- (required) the plugin ID (as returned by getId())

          'properties_url' -- (optional) the URL to a page for updating the
                              role's properties.

          'members_url' -- (optional) the URL to a page for updating the
                           principals to whom the role is assigned.

        o Plugin *must* ignore unknown criteria.

        o Plugin may raise ValueError for invalid critera.

        o Insufficiently-specified criteria may have catastrophic
          scaling issues for some implementations.
        """

        pluginid = self.getId()
        session = Session()
        connection = session.connection(domain.Group)
        
        mappings = connection.execute(rdb.select(
            [security_schema.principal_role_map.c.role_id]))
        
        role_ids = []
        for (role_id,) in mappings:
            role_ids.append(role_id)
        
        return [{
            'id': role_id,
            'pluginid': pluginid,
            } for role_id in role_ids]
            
classImplements( UserManager,
                 IAuthenticationPlugin,
                 IUserEnumerationPlugin,
                 IUserAdderPlugin,
                 IUserManagement,
                 IDeleteCapability,
                 IPasswordSetCapability,
                 IRolesPlugin,
                 IRoleAssignerPlugin,
                 IRoleEnumerationPlugin,
                 IAssignRoleCapability )

InitializeClass( UserManager )
