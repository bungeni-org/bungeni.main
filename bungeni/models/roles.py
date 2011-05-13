from zope.securitypolicy.interfaces import IPrincipalRoleMap
from bungeni.models import interfaces
import zope.configuration.config as config
from zope.securitypolicy.interfaces import IRole 
from zope.securitypolicy.role import Role 
from zope.component import getGlobalSiteManager
from zope import interface    
from bungeni.models import interfaces
from zope.component import getUtility
from zope.component.zcml import handler
from zope.annotation.interfaces import IAnnotations
from zope import component

class SubRoleAnnotations(object):
    interface.implements(interfaces.ISubRoleAnnotations)
    component.adapts(IRole)
    def __init__(self):
        self.sub_roles = []
        self.is_sub_role = False
    
def sub_role_configure(context, id, title, description, role):
    role_annt = interfaces.ISubRoleAnnotations(getUtility(IRole, role))
    role_annt.sub_roles.append(id)
    sub_role = Role(id, title, description)
    sub_role_annt = interfaces.ISubRoleAnnotations(sub_role)
    sub_role_annt.is_sub_role = True
    gsm = getGlobalSiteManager()
    gsm.registerUtility(sub_role, IRole, id)
    
    
def sub_role_handler(context, **kw):
    context.action(discriminator=('RegisterSubRoles', kw["id"], kw["role"]),
                   callable=sub_role_configure,
                   args = (context, kw["id"], kw["title"], getattr(kw, "description", None), kw["role"])
                   )
