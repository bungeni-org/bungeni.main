
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
    
    # !+RolePermissionMap
    #gsm.registerAdapter(
    #    bungeni.alchemist.security.GlobalRolePermissionMap,
    #     (bungeni.models.interfaces.IBungeniApplication,),
    #     zope.securitypolicy.interfaces.IRolePermissionMap)
    
    gsm.registerAdapter(
        bungeni.alchemist.security.LocalPrincipalRoleMap,
         (bungeni.models.interfaces.IBungeniContent,),
         zope.securitypolicy.interfaces.IPrincipalRoleMap)
    
    # !+RolePermissionMap
    #gsm.registerAdapter(
    #    bungeni.alchemist.security.LocalRolePermissionMap,
    #     (bungeni.models.interfaces.IBungeniContent,),
    #     zope.securitypolicy.interfaces.IRolePermissionMap) 


from bungeni.core.workflow.states import get_object_state
from bungeni.core.workflow.xmlimport import ACTIONS_MODULE
def version_increment_for_state(context):
    """Return 0 or 1, depending on whether the current workflow state 
    defines a version="true".
    """
    state = get_object_state(context)
    return int(ACTIONS_MODULE.version in state.actions)

