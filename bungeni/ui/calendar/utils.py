from datetime import datetime
from datetime import timedelta
from datetime import time
from datetime import date
from time import mktime
from dateutil import rrule

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

    
