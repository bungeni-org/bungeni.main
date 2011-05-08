from zope.securitypolicy.interfaces import IPrincipalRoleMap
from bungeni.models import interfaces
from bungeni.core.app import BungeniApp
import zope.configuration.config as config
from zope.securitypolicy.interfaces import IRole 
from zope.securitypolicy.role import Role 
from zope.component.zcml import utility  
def handle_authenticated_principal_created_event(event):
    pass
    
def get_group_context(context):
        if interfaces.IOffice.providedBy(context):
            return BungeniApp() #get_parliament(context)
        else:
            return context
            
def title_created(title, event):
    prm = IPrincipalRoleMap(get_group_context(title.title_type.group))
    prm.assignRoleToPrincipal(title.title_type.role_id, title.member.user.login)
    
def title_deleted(membership, event):
    prm = IPrincipalRoleMap(get_group_context(title.title_type.group))
    prm.unsetRoleForPrincipal(title.title_type.role_id, title.member.user.login)
