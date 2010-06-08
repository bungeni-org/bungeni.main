import zope.securitypolicy.interfaces
from bungeni.core.workflows import dbutils

class conditions:
    pass

    
class actions:
    @staticmethod
    def create(info, context):
        user_id = dbutils.get_user_login(context.user_id)
        if user_id:
            zope.securitypolicy.interfaces.IPrincipalRoleMap( context 
                ).assignRoleToPrincipal( u'bungeni.Owner', user_id) 
                   
