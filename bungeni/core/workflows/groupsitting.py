from bungeni.core.workflows import utils, dbutils
from zope.security.proxy import removeSecurityProxy

class actions:
    
    @staticmethod
    def draftminutes(info, context):
        dbutils.set_real_order(removeSecurityProxy(context))
    
    @staticmethod
    def publish_agenda(info, context):
        utils.schedule_sitting_items(info, context)

class conditions:
    
    @staticmethod
    def all_items_unscheduled(info, context):
        trusted = removeSecurityProxy(context)
        for schedule in trusted.item_schedule:
            if schedule.item.status==u"scheduled":
                return False
        return True

