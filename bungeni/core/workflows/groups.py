import zope.securitypolicy.interfaces
from bungeni.models.utils import get_principal_id
from bungeni.core.workflows import utils
from bungeni.core.workflows import dbutils

class conditions:
    @staticmethod
    def has_end_date(info, context):
        """ a group can only be dissolved if 
         an end date is set """
        return context.end_date != None

    
class actions:
    @staticmethod
    def create(info, context):
        user_id = get_principal_id()
        if user_id:
            zope.securitypolicy.interfaces.IPrincipalRoleMap( context 
                ).assignRoleToPrincipal( u'bungeni.Owner', user_id) 
                
    @staticmethod
    def activate(info, context):
        utils.set_group_local_role(context)
    
    @staticmethod
    def dissolve(info, context):
        """ when a group is dissolved all members of this 
        group get the end date of the group (if they do not
        have one yet) and there active_p status gets set to
        False"""
        dbutils.deactivateGroupMembers(context)
        groups = dbutils.endChildGroups(context)
        utils.dissolveChildGroups(groups,context)
        utils.unset_group_local_role(context)
        
    @staticmethod
    def deactivate(info, context):
        utils.unset_group_local_role(context)
