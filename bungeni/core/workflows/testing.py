
import zope.component
import zope.securitypolicy.interfaces
import bungeni.alchemist.security
import bungeni.models.interfaces


def setup_security_adapters():
    gsm = zope.component.getGlobalSiteManager()
    
    gsm.registerAdapter(
        bungeni.alchemist.security.GlobalPrincipalRoleMap,
         (bungeni.models.interfaces.IBungeniApplication,),
         zope.securitypolicy.interfaces.IPrincipalRoleMap)
    
    gsm.registerAdapter(
        bungeni.alchemist.security.GlobalRolePermissionMap,
         (bungeni.models.interfaces.IBungeniApplication,),
         zope.securitypolicy.interfaces.IRolePermissionMap)
    
    gsm.registerAdapter(
        bungeni.alchemist.security.LocalPrincipalRoleMap,
         (bungeni.models.interfaces.IBungeniContent,),
         zope.securitypolicy.interfaces.IPrincipalRoleMap)
    
    gsm.registerAdapter(
        bungeni.alchemist.security.LocalRolePermissionMap,
         (bungeni.models.interfaces.IBungeniContent,),
         zope.securitypolicy.interfaces.IRolePermissionMap) 

