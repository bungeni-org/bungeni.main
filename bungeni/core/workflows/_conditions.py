# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Workflow transition conditions.

Signature of all utilities here: 

    (info:WorkflowInfo, context:Object) -> bool

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflows._conditions")

from bungeni.ui.interfaces import IFormEditLayer
from bungeni.ui.utils import common

import dbutils
import utils


# common

# the condition for the transition from "" (None) to either "draft" or to 
# "working_draft" seems to need the explicit condition (and negation of 
# condition) on each of the two transition options 
def user_is_not_context_owner(info, context):
    return not user_is_context_owner(info, context)

def user_is_context_owner(info, context):
    def user_is_context_owner(context):
        """Test if current user is the context owner e.g. to check if someone 
        manipulating the context object is other than the owner of the object.
        """
        user_login = utils.get_principal_id()
        owner_login = utils.get_owner_login_pi(context)
        return user_login == owner_login
    return user_is_context_owner(context)


# parliamentary items

def is_scheduled(info, context):
    """Is Parliamentary Item scheduled.
    """
    return dbutils.isItemScheduled(context.parliamentary_item_id)


# group

def has_end_date(info, context):
    """A group can only be dissolved if an end date is set.
    """
    return context.end_date != None


# groupsitting

def has_venue(info, context):
    return context.venue is not None


# question

def is_written_response(info, context):
    return context.ministry_id is not None and context.response_type == u"W"

def is_oral_response(info, context):
    return context.response_type == u"O"

def response_allow_submit(info, context):
    # The "submit_response" workflow transition should NOT be displayed when 
    # the UI is displaying the question in "edit" mode (as this transition
    # will cause deny of bungeni.Question.Edit to the Minister).
    request = common.get_request()
    if IFormEditLayer.providedBy(request):
        return False
    if context.response_text is None:
        return False
    else:
        return True

def is_ministry_set(info, context):
    return context.ministry_id is not None


# user

def has_date_of_death(info, context):
    return context.date_of_death is not None

def not_has_date_of_death(info, context):
    return context.date_of_death is None


#

