# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Form schema (custom) constraints.

Signature of all utilities here: 

    (context:Object) -> None
        failure raises zope.interface.Invalid

For samples of source definitions of form schema constraints , see the following 
corresponding bungeni module:

    bungeni.ui.descriptor.constraints

$Id$
"""
log = __import__("logging").getLogger("bungeni_custom.forms")

from bungeni.ui.descriptor.constraints import (
    
    # group, membership
    end_after_start,
    
    # membership
    active_and_substituted,
    substituted_end_date,
    inactive_no_end_date,
    
    # parliament membership
    member_start_after_elected,
    
    # user
    user_birth_death_dates,
    
)

