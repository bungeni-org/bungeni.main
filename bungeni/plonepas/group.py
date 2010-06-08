
from AccessControl import ClassSecurityInfo
from OFS.Cache import Cacheable

from Products.PlonePAS.plugins.group import PloneGroup
from Products.PlonePAS.interfaces import group as IPloneGroups
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.interfaces.plugins import (IGroupsPlugin,
                                                              IGroupEnumerationPlugin)

#from zope import component
from datetime import datetime
import sqlalchemy as rdb
import schema

from bungeni.models import domain
from ore.alchemist import Session

manage_addBungeniGroupManagerForm = PageTemplateFile('zmi/group-plugin-add.pt', globals())

def manage_addBungeniGroupManager(self, id, db_utility, title='', REQUEST=None):
    """Add a GroupManager to a Pluggable Auth Service.
    """
    rm = GroupManager(id, db_utility, title)
    self._setObject( id, rm)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(
                                '%s/manage_workspace'
                                '?manage_tabs_message='
                                'BungeniGroupManager+added.'
                            % self.absolute_url())

class GroupManager( BasePlugin, Cacheable ):

    meta_type = "Bungeni Group Manager"

    security = ClassSecurityInfo()

    
    def __init__(self, id, title=None):
        self.id = self.id = id
        self.title = title

    #
    # IGroupsPlugin implementation
    #
    
    def getGroupsForPrincipal( self, principal, request=None ):
        """ principal -> ( group_1, ... group_N )

        o Return a sequence of group names to which the principal 
          (either a user or another group) belongs.

        o May assign groups based on values in the REQUEST object, if present
        """
        #XXX TODO: user delegations!, implement search for groups 
        # recursivly for this use case
        session = Session()

        return [r.group_principal_id
                for r in session.query(domain.Group).filter(
                    rdb.and_(
                        schema.users.c.login == principal.getId(),
                        schema.user_group_memberships.c.user_id == schema.users.c.user_id,
                        schema.groups.c.group_id == schema.user_group_memberships.c.group_id,
                        schema.groups.c.status == 'active',
                        schema.user_group_memberships.c.active_p == True)).all() ]

    #
    # IGroupsEnumeration implementation
    #

    def enumerateGroups( self, id=None
                       , exact_match=False
                       , sort_by=None
                       , max_results=None
                       , **kw
                       ):
        """ see IGroupEnumeration """

        session = Session()
        
        if id is None:
            clause = None
        elif isinstance( id, (list, tuple)) and exact_match:
            statements = []
            for i in id:
                statements.append( domain.Group.group_principal_id == i )
            clause = rdb.or_( *statements )
        elif isinstance( id, (list, tuple)) and not exact_match:
            clause = rdb.or_(*(map( domain.Group.group_principal_id.contains, id )))
        elif not exact_match:
            clause = domain.Group.group_principal_id.contains( id )
        else:
            clause = domain.Group.group_principal_id == id


        query = session.query(domain.Group).filter(
                        rdb.and_( clause,
                            domain.Group.status == 'active')
                        )
        if clause:
            query = query.filter(clause)
        if sort_by:
            assert sort_by in ('group_id', 'short_name')
            query = query.order_by( getattr( schema.groups.c, sort_by ) )

        if exact_match:
            max_results = 1
            
        if max_results is not None and isinstance( max_results, int ):
            query = query.limit( max_results )

        return [dict( id=r.group_principal_id, title=r.short_name, plugin=self.id )
                for r in query.all()]

    ####################
    # IGroupManagement 
    ####################
    
    def addGroup(self, id, **kw):
        """
        Create a group with the supplied id, roles, and groups.
        return True if the operation suceeded
        """
        raise NotImplementedError
        insert = schema.groups.insert()
        insert.values( short_name = id,
                       full_name = kw.get('title',''),
                       description = kw.get('description', ''),
                       start_date = datetime.now(),
                       type = "group",
                       ).execute()
        return True
        
    def addPrincipalToGroup(self, principal_id, group_id):
        """
        Add a given principal to the group.
        return True on success
        """
        raise NotImplementedError
        insert = schema.user_group_memberships.insert()
        group_id = self._gid( group_id )
        user_id  = self._uid( principal_id )
        if not group_id or not user_id:
            raise KeyError( "Invalid user %s or group %s"%( user_id, group_id ) )
        insert.values( group_id = group_id, user_id = user_id ).execute()
        return True

    def updateGroup(self, id, **kw):
        """
        Edit the given group. plugin specific
        return True on success
        """

        raise NotImplementedError("Group updates not implemented.")
        d = {}
        if 'title' in kw:
            d['full_name'] = kw['title']
        if 'description' in kw:
            d['description'] = kw['description']

        if not d:
            return True

        session = Session()
        session.update(domain.Group).filter(
            domain.Group.group_principal_id == id).values(**d)
        
        return True

    def setRolesForGroup(self, group_id, roles=()):
        """
        set roles for group
        return True on success
        """
        # why the heck is this even in the group api ? silly enfold developers.. tricks are for kids
        raise NotImplemented


    #
    #   IDeleteCapability implementation
    #
    def allowDeletePrincipal(self, principal_id):
        """True if this plugin can delete a certain group."""
        return False

        if self.getGroupById(principal_id):
            return True
        return False

    #
    #   IGroupCapability implementation
    #
    def allowGroupAdd(self, user_id, group_id):
        """True if this plugin will allow adding a certain user to a certain group."""
        return False

        present = self.enumerateGroups(id=group_id)
        if present: return True   # if we have a group, we can add users to it
                                  # slightly naive, but should be okay.
        return False

    def allowGroupRemove(self, user_id, group_id):
        """True if this plugin will allow removing a certain user from a certain group."""
        return False
        present = self._gid(group_id)
        if not present: return False   # if we don't have a group, we can't do anything
        
        groups = self.getGroupsForPrincipal(user_id)
        if group_id in groups: return True
        return False

    def removeGroup(self, group_id):
        """
        Remove the given group
        return True on success
        """
        return False
        # XXX also need to delete all memberships in the group, just set group as inactive
        gid = self._gid( group_id )
        schema.groups.delete().where( schema.groups.c.group_id == gid ).execute()

    def removePrincipalFromGroup(self, principal_id, group_id):
        """
        remove the given principal from the group
        return True on success
        """
        raise NotImplementedError
        
        group_id = self._gid( group_id )
        user_id  = self._uid( principal_id )
        if not group_id or not user_id:
            return False
        ugm = schema.user_group_memberships
        schema.user_group_memberships.delete().where(
            rdb.and_( ugm.c.user_id == user_id, ugm.c.group_id == group_id )
            ).execute()
                
        return True
    
    ###########################
    # IGroupIntrospection
    ###########################
    def _gid( self, name ):
        session = Session()
        groups = session.query(domain.Group).filter(
            rdb.and_(domain.Group.status == 'active', 
                domain.Group.group_principal_id == name)
                ).all()
        if not groups:
            return
        #return groups[0].group_id
        return groups[0].group_principal_id

    def _uid( self, login):
        session = Session()
        user = session.query(domain.User).filter(
            rdb.and_(
                domain.User.login == login,
                domain.User.active_p == 'A')
            ).one()
        if user is None:
            return
        return user.user_id

    def getGroupById(self, group_id):
        """
        Returns the portal_groupdata-ish object for a group
        corresponding to this id.
        """
        gid = self._gid( group_id )
        if not gid:
            return None
        return PloneGroup(gid).__of__( self )

    #################################
    # these interface methods are suspect for scalability.
    #################################

    def getGroups( self ):
        """
        Returns an iteration of the available groups
        """

        session = Session()
        groups = session.query(domain.Group).filter(
            domain.Group.status == 'active').all()
        return [PloneGroup(r.group_principal_id).__of__(self) for r in groups]
        
    def getGroupIds( self ):
        """
        Returns a list of the available groups
        """

        session = Session()
        session = Session()
        groups = session.query(domain.Group).filter(
            domain.Group.status == 'active').all()
        return [r.group_principal_id for r in groups]

    def getGroupMembers(self, group_id):
        """
        return the members of the given group
        """

        session = Session()
        ugm = schema.user_group_memberships

        users = session.query(domain.User).filter(
            rdb.and_(schema.users.c.user_id == ugm.c.user_id,
                     schema.groups.c.group_id == ugm.c.group_id,
                     domain.Group.group_principal_id == group_id,
                     ugm.c.active_p == True)).all()
        return [r.login for r in users]

classImplements( GroupManager,
                 IGroupsPlugin,
                 IGroupEnumerationPlugin,
                 IPloneGroups.IGroupIntrospection,
                 IPloneGroups.IGroupManagement )
