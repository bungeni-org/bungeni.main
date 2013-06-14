# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Handler that generates Akoma Ntoso uri for parliamentary content.  
"""

import bungeni.ui.utils as ui_utils
from bungeni.capi import capi


# !+GET_URI duplication?

def generate_uri(item, event):
    uri = ""
    
    if item.type == "bill":
        if item.publication_date is not None and item.registry_number:
            uri = "/bungeni/%s/%s/%s/%s/%s@/main" % (capi.legislature.country_code,
                                                     item.type, 
                                                     item.publication_date,
                                                     item.registry_number, 
                                                     item.language)
    else:
        if item.status_date is not None and item.registry_number:
            uri = "/bungeni/%s/%s/%s/%s/%s@/main" % (capi.legislature.country_code,
                                                     item.type, 
                                                     item.status_date.date(),
                                                     item.registry_number, 
                                                     item.language)
    
    if item.uri is None and uri:
        item.uri = uri

