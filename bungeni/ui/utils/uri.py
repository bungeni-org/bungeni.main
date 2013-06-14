# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Utilities to help with generating doc URIs

recommended usage:
from bungeni.ui.utils import uri

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.utils.uri")


from bungeni.capi import capi


def get_country(item):
    """The 2-letter country code for this bungeni instance.
    """
    return capi.legislature.country_code


def get_publication_date(item, format="%Y-%m-%d"):
    for attr in ["publication_date", "submission_date", "status_date"]:
        publication_date = getattr(item, attr, None)
        if publication_date:
            return publication_date.strftime(format)


def get_tmp_registry_number_substitute(item):
    # !+ for cases when registry_number is not yet set on the item.
    if item.type_number:
        return " [type_number:%s] " % item.type_number
    else:
        return " [doc_id:%s] " % item.doc_id


def get_frbr_work_url(item):
    return "/%s/%s/%s/main" % (
            get_country(item), 
            item.type, 
            get_publication_date(item))


def get_frbr_manifestation_url(item):
    return "/%s/%s/%s/%s@/main.xml" % (
            get_country(item), 
            item.type,
            get_publication_date(item), 
            item.language)


def get_frbr_expression_url(item):
    return "/%s/%s/%s/%s/%s@/main" % (
            get_country(item), 
            item.type, 
            get_publication_date(item), 
            item.registry_number or get_tmp_registry_number_substitute(item),
            item.language)


def get_uri(item):
    return "/bungeni%s" % (get_frbr_expression_url(item))



