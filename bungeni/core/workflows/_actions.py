# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Workflow transition-to-state actions.

Signature of all transition-to-state action callables:

    (context:Object) -> None

All transition-to-state actions are executed "on workflow trransition" i.e. 
exactly when the status is updated from the source to the destination state, 
and in exactly the order they are specified in the state.@actions xml attribute.

REMEMBER: when a transition-to-state action is executed, the context.status 
is already updated to the destination state.

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflows._actions")

from bungeni.core.workflows import utils


# version
# - create a new version of an object and return it
# - context must be version-enabled
# - recommendation: when present, version should be first action to execute
from bungeni.core.version import (
    create_version as version
)
# !+capi.template_message_version_transition
#message_template = "New version on workflow transition to: %(status)s"
#message = message_template % context.__dict__


from bungeni.core.workflows.utils import (
    
    # when a doc reaches a state that semantically implies "receive"
    set_doc_registry_number,
    
    # when a doc is admitted
    set_doc_type_number,
    
    # when a doc is withdrawn
    unschedule_doc,
    
    # question !+CUSTOM
    assign_role_minister_question,
    
    # when a sitting's agenda is published
    schedule_sitting_items,
)


def activate(group):
    """Perform any actions required to activate a group.
    """
    utils.set_group_local_role(group)

def dissolve(group):
    """Perform any actions required to dissolve a group.
    
    When a group is dissolved all members of this group get the end date of 
    the group (if they do not have one yet) and there active_p status gets set
    to False.
    """
    from bungeni.core.workflows import dbutils
    dbutils.deactivateGroupMembers(group)
    groups = dbutils.endChildGroups(group)
    utils.dissolveChildGroups(groups, group)
    utils.unset_group_local_role(group)


# sitting

def set_real_order(sitting):
    """Set real order to planned order.
    """
    for item in sitting.item_schedule:
        item.real_order = item.planned_order


# user

def assign_owner_role(user):
    utils.assign_role("bungeni.Owner", user.login, user)
    user.date_of_death = None

