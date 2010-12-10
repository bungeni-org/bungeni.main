from datetime import datetime
from datetime import timedelta
from datetime import time
from datetime import date
from time import mktime
from dateutil.rrule import rrule
from dateutil.rrule import DAILY, WEEKLY, MONTHLY, YEARLY
from dateutil.rrule import SU, MO, TU, WE, TH, FR, SA

marker = object()
date_range_delimiter=':'
def timestamp_from_date(date):
    return mktime(date.timetuple())

def pack_date_range(start, end):
    return date_range_delimiter.join(map(
        lambda date: (date and str(int(timestamp_from_date(date))) or ""),
        (start, end)))

def unpack_date_range(value):
    try:
        start, end = value.split(date_range_delimiter)
    except (ValueError):
        start = value
        end = None
    try:
        start = date.fromtimestamp(int(start))
    except (TypeError, ValueError):
        start = None
    try:
        end = date.fromtimestamp(int(end))
    except (TypeError, ValueError):
        end = None

    return start, end

class date_generator(object):
    def __iter__(self):
        return iter(self.rrule)

def nth_day_of_week(weekday):
    class generator(date_generator):
        def __init__(self, date):
            self.rrule = rrule.rrule(
                rrule.WEEKLY,
                dtstart=date,
                byweekday=rrule.weekdays[weekday])

    return generator
    
def nth_day_of_month(day):
    class generator(date_generator):
        def __init__(self, date):
            self.rrule = rrule.rrule(
                rrule.MONTHLY,
                dtstart=date,
                bymonthday=day)

    return generator

def first_nth_weekday_of_month(weekday):
    class generator(date_generator):
        def __init__(self, date):
            self.rrule = rrule.rrule(
                rrule.MONTHLY,
                dtstart=date,
                byweekday=rrule.FR(+1))

    return generator

def generate_dates(generator, *generators):
    """Generate dates from generators.

      >>> from datetime import date

    Every nth day of the week.
    
      >>> mondays = nth_day_of_week(0)

      >>> generator = iter(mondays(date(1999, 12, 1)))
      >>> generator.next().strftime('%x')
      '12/06/99'

      >>> generator.next().strftime('%x')
      '12/13/99'

   Every nth day of the month.
   
      >>> day_21st = nth_day_of_month(21)

      >>> generator = iter(day_21st(date(1999, 12, 1)))
      >>> generator.next().strftime('%x')
      '12/21/99'

      >>> generator.next().strftime('%x')
      '01/21/00'

    Every first nth weekday of the month.
    
      >>> first_thursday = first_nth_weekday_of_month(3)

      >>> generator = iter(first_thursday(date(1999, 12, 1)))
      >>> generator.next().strftime('%x')
      '12/03/99'

      >>> generator.next().strftime('%x')
      '01/07/00'

    """
    
    if len(generators) == 0:
        for date in generator:
            yield date

    aggregate = generate_dates(*generators)

    while aggregate:
        date1 = generator.next()
        date2 = aggregate.next()

        if date1 < date2:
            yield date1
            date1 = generator.next()
        else:
            yield date2
            date2 = aggregate.next()

class join_dicts(object):
    def __init__(self, *dicts):
        self.dicts = dicts

    def __getitem__(self, key):
        for d in self.dicts:
            value = d.get(key, marker)
            if value is not marker:
                return value
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default
            
class base:
    def __getitem__(self, key):
        """Standard `strftime()` substitutions."""

        try:
            key = str(key)
        except UnicodeDecodeError:
            raise KeyError(key)
        
        result = self.strftime("%"+str(key))
        
        if result == "":
            raise KeyError(key)

        return result

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

class timedict(time, base):
    pass

class datetimedict(datetime, base):
    @classmethod
    def fromdatetime(self, dt):
        return datetimedict(
            dt.year, dt.month, dt.day,
            dt.hour, dt.minute, dt.second)

    @classmethod
    def fromdate(self, dt):
        return datetimedict(
            dt.year, dt.month, dt.day)

    def __add__(self, other):
        return datetimedict.fromdatetime(datetime.__add__(self, other))

    def __sub__(self, other):
        return datetimedict.fromdatetime(datetime.__sub__(self, other))

    def totimestamp(self):
        return mktime(self.timetuple())

def generate_recurrence_dates(recurrence_start_date, 
                                        recurrence_end_date, recurrence_type):
    '''generates recurrence dates for sittings given the start date, end
       date and the recurrence type in the format used by dhtmlxcalendar 
       Refer to the URL below
       http://docs.dhtmlx.com/doku.php?id=dhtmlxscheduler:recurring_events
       tests in ui/calendar/readme.txt
    '''
    rec_args = recurrence_type.split("_")
    #rec_type - type of repeating "day","week","month","year"
    rec_type = rec_args[0]
    #count - how much intervals of "type" come between events
    count  = rec_args[1]
    #count2 and day - used to define day of month (first Monday, third Friday, etc)
    day = rec_args[2]
    count2 = rec_args[3]
    #days - comma separated list of affected week days
    days = rec_args[4].split("#")[0]
    #extra - extra may contain the number of occurences of the recurrence
    extra  = rec_args[4].split("#")[1]
    rrule_count = None
    if (extra != "no") and (extra != ""):
        try:
            rrule_count = int(extra)
        except TypeError, ValueError:
            rrule_count = None
    freq_map = {"day":DAILY,"week":WEEKLY,"month":MONTHLY,"year":YEARLY}
    freq = freq_map[rec_type]
    if count != "":
        interval = int(count)
    else:
        interval = 1
    byweekday=None
    # rrule map starts with 0:MO, dhtmlxcalendar starts with 0:SU
    day_map = {0:SU,1:MO,2:TU,3:WE,4:TH,5:FR,6:SA}
    if (count2 != "") and (day != ""):    
        byweekday = day_map[int(day)](+int(count2))
    elif (days != ""):
        byweekday = map(int,days.split(","))
    if rrule_count is not None:
        if byweekday is not None:
            return list(rrule(freq, 
                                  dtstart=recurrence_start_date, 
                                  until=recurrence_end_date, 
                                  count=rrule_count, 
                                  byweekday=byweekday, 
                                  interval=interval))  
        else:
            return list(rrule(freq, 
                                  dtstart=recurrence_start_date, 
                                  until=recurrence_end_date, 
                                  count=rrule_count, 
                                  interval=interval))
    else:
        if byweekday is not None:
            return list(rrule(freq, 
                                dtstart=recurrence_start_date, 
                                until=recurrence_end_date, 
                                byweekday=byweekday, 
                                interval=interval))  
        else:
            return list(rrule(freq, 
                                dtstart=recurrence_start_date, 
                                until=recurrence_end_date, 
                                interval=interval))   
