# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Date utilities for the UI

usage: 
from bungeni.ui.utils import date

$Id: utils.py 6292 2010-03-22 12:33:25Z mario.ruggier $
"""

from zope.security.interfaces import NoInteraction
from zope.i18n.locales import locales

import datetime
import re
from bungeni.ui.utils import common
from bungeni.capi import capi

# date


def getDisplayDate(request):
    """ () -> datetime.date
    Get the date (for filtering data display) from the request, first 
    trying request["date"], then request["display_date"].
    
    Assumption: relation being being queried has date columns named 
    "start_date" and "end_date"
    """
    # !+DISPLAYDATE(mr, sep-2010) 
    # when are request["date"] and request["display_date"] defined?
    DisplayDate = request.get("date", request.get("display_date", None))
    if DisplayDate:
        try:
            y, m, d = (int(x) for x in DisplayDate.split("-"))
            return datetime.date(y, m, d)
        except:
            pass

''' !+DATERANGEFILTER(mr, sep-2010) use IDateRangeFilter adaptors?

def getFilter(displayDate):
    """(either(datetime.date|None) -> filter_by:str
    
    Filter on a date for which to display the data.
    #SQL WHERE:
    # displayDate BETWEEN start_date and end_date
    # OR
    # displayDate > start_date and end_date IS NULL

    Assumption: relation being being queried has date columns named 
    "start_date" and "end_date"
    """
    if displayDate:
        return """
        ( ('%(displayDate)s' BETWEEN start_date AND end_date )
        OR
        ( '%(displayDate)s' > start_date AND end_date IS NULL) )
        """ % ({"displayDate": displayDate})
    return ""
'''

def getLocaleFormatter(
            request=None, 
            category="date",    # "date" | "time" | "dateTime"
            length="medium"     # "short" | "medium" | "long" | "full" | None
        ):
    """See: zope.i18n.locales.LocaleDates.getFormatter
    """
    if request is None:
        try:
            request = common.get_request()
        except NoInteraction:
            request = None
    if request and hasattr(request, "locale"):
        return request.locale.dates.getFormatter(category, length)
    else:
        return locales.getLocale(capi.default_language).dates.getFormatter(
            category, length)

 
def parseDateTime(s):
    """Create datetime object representing date/time
       expressed in a string
 
    Takes a string in the format produced by calling str()
    on a python datetime object and returns a datetime
    instance that would produce that string.
 
    Acceptable formats are: "YYYY-MM-DD HH:MM:SS.ssssss+HH:MM",
                            "YYYY-MM-DD HH:MM:SS.ssssss",
                            "YYYY-MM-DD HH:MM:SS+HH:MM",
                            "YYYY-MM-DD HH:MM:SS"
    Where ssssss represents fractional seconds.     The timezone
    is optional and may be either positive or negative
    hours/minutes east of UTC.
    """
    if s is None:
        return None
    # Split string in the form 2007-06-18 19:39:25.3300-07:00
    # into its constituent date/time, microseconds, and
    # timezone fields where microseconds and timezone are
    # optional.
    m = re.match(r'(.*?)(?:\.(\d+))?(([-+]\d{1,2}):(\d{2}))?$',
                 str(s))
    datestr, fractional, tzname, tzhour, tzmin = m.groups()
 
    # Create tzinfo object representing the timezone
    # expressed in the input string.  The names we give
    # for the timezones are lame: they are just the offset
    # from UTC (as it appeared in the input string).  We
    # handle UTC specially since it is a very common case
    # and we know its name.
    if tzname is None:
        tz = None
    else:
        tzhour, tzmin = int(tzhour), int(tzmin)
        if tzhour == tzmin == 0:
            tzname = 'UTC'
        tz = FixedOffset(timedelta(hours=tzhour,
                                   minutes=tzmin), tzname)
 
    # Convert the date/time field into a python datetime
    # object.
    x = datetime.datetime.strptime(datestr, "%Y-%m-%d %H:%M:%S")
 
    # Convert the fractional second portion into a count
    # of microseconds.
    if fractional is None:
        fractional = '0'
    fracpower = 6 - len(fractional)
    fractional = float(fractional) * (10 ** fracpower)
 
    # Return updated datetime object with microseconds and
    # timezone information.
    return x.replace(microsecond=int(fractional), tzinfo=tz)
 
