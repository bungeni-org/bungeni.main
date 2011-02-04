
from zope.security.proxy import removeSecurityProxy

from bungeni.core.workflows import utils, dbutils


class actions:

    @staticmethod
    def invalidate_caches(info, context):
        """GroupSitting JSON Listing caches should be invalidated for 
        any transition towards or away from a "public" state.
        """
        # we import here because module load time the setup of various
        # GroupSitting-related classes (descriptor, ...) is not yet complete
        from bungeni.ui import container
        container.invalidate_caches_for("GroupSitting", "transition")
    redraft_agenda = invalidate_caches
    publish_minutes = invalidate_caches
    redraft_minutes = invalidate_caches
    
    @staticmethod
    def to_draft_minutes(info, context):
        dbutils.set_real_order(removeSecurityProxy(context))
        actions.invalidate_caches(info, context)
        
    @staticmethod
    def publish_agenda(info, context):
        utils.schedule_sitting_items(info, context)
        actions.invalidate_caches(info, context)
        
class conditions:
    
    @staticmethod
    def all_items_unscheduled(info, context):
        trusted = removeSecurityProxy(context)
        for schedule in trusted.item_schedule:
            if schedule.item.status==u"scheduled":
                return False
        return True

    @staticmethod
    def has_venue(info, context):
        return removeSecurityProxy(context).venue is not None

