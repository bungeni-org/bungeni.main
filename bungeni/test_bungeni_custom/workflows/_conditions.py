# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Workflow transition (custom) conditions.

Signature of all utilities here: 

    (context:Object) -> bool
    
For samples of source definitions of transition conditions, see the following 
corresponding bungeni module:

    bungeni.core.workflows._conditions

$Id: _conditions.py 9869 2012-09-25 14:54:39Z borona.murithi $
"""
log = __import__("logging").getLogger("bungeni_custom.workflows")

from bungeni.core.workflows._conditions import (
    
    # doc
    is_scheduled,
    
    # group
    # A group can only be dissolved if an end date is set.
    has_end_date,
    
    # groupsitting
    has_venue,
    has_agenda,
    agenda_finalized,
    sitting_dummy,
    
    # question
    is_written_response,
    is_oral_response,  
    response_allow_submit, # The "submit_response" workflow transition should 
    # NOT be displayed when the UI is displaying the question in "edit" mode 
    # (this transition will deny bungeni.Question.Edit to the Minister).
    
    # user
    has_date_of_death,
    not_has_date_of_death,
    
    # auditables
    
    # child items
    # A doc is a draft iff its current current state is tagged with "draft".
    context_parent_is_draft, 
    context_parent_is_not_draft,
    context_parent_is_public,
    context_parent_is_not_public,
    user_may_edit_context_parent,
    
    # signatories
    pi_has_signatories,
    pi_signatories_check,
    pi_allow_signature,
    signatory_auto_sign,
    signatory_manual_sign,
    pi_signature_period_expired,
    pi_allow_signature_actions,
    pi_unsign_signature,
)


''' !+composite_condition(mr, may-2012) ability to do this in xml directly?
def may_edit_context_parent_and_is_not_public(context):
    """A composite condition, combines two conditions."""
    return (
        user_may_edit_context_parent(context) and 
        context_parent_is_not_public(context))
'''

