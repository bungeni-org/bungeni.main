
from ore.alchemist import Session
from bungeni.models import domain

from OFS.Cache import Cacheable

from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.interfaces.plugins import IPropertiesPlugin
from Products.PluggableAuthService.interfaces.plugins import IUpdatePlugin
from Products.PluggableAuthService.utils import createViewName

from Products.PlonePAS.interfaces.plugins import IMutablePropertiesPlugin
from Products.PlonePAS.sheet import MutablePropertySheet


class PropertyProvider( BasePlugin, Cacheable ):

    def __init__(self, id, title=""):
        self.id = self.id = id
        self.title = title

    def getPropertiesForUser(self, user, request=None):
        """Get property values for a user or group.
        Returns a dictionary of values or a PropertySheet.
        """
        view_name = createViewName('getPropertiesForUser', user)
        cached_info = self.ZCacheable_get(view_name=view_name)
        if cached_info is not None:
            return MutablePropertySheet(self.id, **cached_info)
        data = None
        session = Session()
        if user.isGroup():
            groups = session.query(domain.Group).filter(
                domain.Group.group_principal_id == user.getUserName()).all()
            if len(groups) == 1:
                group = groups[0]
                data =  { 
                    'title' : group.short_name or u"",
                    'description' : group.description or u"",
                    }
        else:
            users = session.query(domain.User).filter(
                domain.User.login == user.getUserName()).all()
            if len(users) == 1:
                b_user = users[0]
                data =  {
                    'fullname' : u"%s %s" %(b_user.first_name, b_user.last_name),
                    'email' : b_user.email or u"",
                    'description' : b_user.description or u"",
                    'notification': b_user.recieve_notification or False,
                    }
        if data:
            self.ZCacheable_set(data, view_name=view_name)
            sheet = MutablePropertySheet(self.id, **data)
            return sheet

        
    #
    # IMutablePropertiesPlugin implementation
    #
    def setPropertiesForUser(self, user, propertysheet):
        session = Session()
        if user.isGroup():
            groups = session.query(domain.Group).filter(
                domain.Group.group_principal_id == user.getUserName()).all()
            if len(groups) == 1:
                group = groups[0]
                #we do not set any attributes from plone here
        else:
            users = session.query(domain.User).filter(
                domain.User.login == user.getUserName()).all()
            if len(users) == 1:
                b_user = users[0]
                email =  propertysheet.getProperty('email')
                if email:
                    b_user.email = email
                recieve_notification = propertysheet.getProperty('notification')
                if recieve_notification != None:
                    b_user.recieve_notification = recieve_notification
        view_name = createViewName('getPropertiesForUser', user) 
        cached_info = self.ZCacheable_invalidate(view_name=view_name)

classImplements(PropertyProvider,
                IPropertiesPlugin,
                IUpdatePlugin,
                IMutablePropertiesPlugin)

    
