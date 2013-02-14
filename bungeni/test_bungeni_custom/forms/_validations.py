# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Form schema (custom) validations.

Signature of all utilities here:

    (action, data, context, container) -> [error:str]

For samples of source definitions of form validators, see the following 
corresponding bungeni module:

    bungeni.ui.descriptor.constraints

$Id$
"""
log = __import__("logging").getLogger("bungeni_custom.forms")

from bungeni.ui.forms.validations import (
    
    validate_date_range_within_parent,
    validate_government_dates,
    validate_group_membership_dates,
    validate_member_titles,
    validate_chamber_dates,
    validate_venues,
    validate_email_availability,
    
)

