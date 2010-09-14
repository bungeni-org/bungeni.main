# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Date utilities for the UI

usage: 
from bungeni.ui.utils import date

$Id: utils.py 6292 2010-03-22 12:33:25Z mario.ruggier $
"""

import datetime
from bungeni.ui.i18n import _
from bungeni.ui.utils import common

# date

def get_date(date):
    if type(date) == datetime.datetime:
        return date.date()
    elif type(date) == datetime.date:
        return date
    else:
        raise TypeError (_("date must be of type datetime or date"))


def getDisplayDate(request):
    """ () -> datetime.date
    
    Get the date for which to display the data.
    #SQL WHERE:
    # displayDate BETWEEN start_date and end_date
    # OR
    # displayDate > start_date and end_date IS NULL
    """
    DisplayDate = request.get("date", None)
    if not DisplayDate:
        if request.has_key("display_date"):
            DisplayDate = request["display_date"]
    if DisplayDate:
        try:
            y, m, d = (int(x) for x in DisplayDate.split("-"))
            return datetime.date(y, m, d)
        except:
            pass
    return None


def getFilter(displayDate):
    """(either(datetime.date|None) -> filter_by:str
    """
    if displayDate:
        return """
        ( ('%(displayDate)s' BETWEEN start_date AND end_date )
        OR
        ( '%(displayDate)s' > start_date AND end_date IS NULL) )
        """ % ({ "displayDate" : displayDate})
    return ""


def getLocaleFormatter(
            request=None, 
            category="date",    # "date" | "time" | "dateTime"
            length="medium"     # "short" | "medium" | "long" | "full" | None
        ):
    """See: zope.i18n.locales.LocaleDates.getFormatter
    """
    if request is None:
        request = common.get_request()
    return request.locale.dates.getFormatter(category, length)

