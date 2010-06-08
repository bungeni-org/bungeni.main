
import zope.securitypolicy.interfaces
from bungeni.core.workflows import utils
from bungeni.core.workflows import dbutils
from bungeni.models.utils import get_principal_id

class actions(object):
    @staticmethod
    def create( info, context ):
        zope.securitypolicy.interfaces.IPrincipalRoleMap( 
            context ).assignRoleToPrincipal( 
                u'bungeni.Owner',  context.login)
                
    @staticmethod
    def resurrect( info, context ):
        context.date_of_death = None
        

class conditions(object):
    @staticmethod
    def has_date_of_death(info, context):
        return not (context.date_of_death is None)

    @staticmethod
    def not_has_date_of_death(info, context):
        return context.date_of_death is None
