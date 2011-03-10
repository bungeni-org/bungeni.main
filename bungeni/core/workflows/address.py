import zope.securitypolicy.interfaces
from bungeni.core.workflows import dbutils
from bungeni.models import utils as model_utils


class conditions:
    pass

    
class actions:
    
    @staticmethod
    def create(info, context):
        # !+OWNER_ADDRESS(mr, mov-2010) is this logic correct, also for admin?
        try:
            user_id = dbutils.get_user_login(context.user_id)
        except AttributeError:
            # 'GroupAddress' object has no attribute 'user_id'
            user_id = model_utils.get_principal_id()
        if user_id:
            zope.securitypolicy.interfaces.IPrincipalRoleMap(
                context).assignRoleToPrincipal(u"bungeni.Owner", user_id) 


