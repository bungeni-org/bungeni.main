# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

""" Handler that generates Akoma Ntoso uri for parliamentary content.  
"""

import bungeni.ui.utils as ui_utils
from bungeni.capi import capi

def generate_uri(object, event):
    uri = ""
    
    if object.type == "bill":
        if object.publication_date is not None and object.registry_number:
            uri = "/bungeni/%s/%s/%s/%s/%s@/main" % (capi.legislature.country_code,
                                                     object.type, 
                                                     object.publication_date,
                                                     object.registry_number, 
                                                     object.language)
    else:
        if object.status_date is not None and object.registry_number:
            uri = "/bungeni/%s/%s/%s/%s/%s@/main" % (capi.legislature.country_code,
                                                     object.type, 
                                                     object.status_date.date(),
                                                     object.registry_number, 
                                                     object.language)

    if object.uri is None and uri:
        object.uri = uri
