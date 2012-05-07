Tests for generating recurrent sittings dates
---------------------------------------------
The format for the recurrence type string is described at this URL
http://docs.dhtmlx.com/doku.php?id=dhtmlxscheduler:recurring_events

    >>> from bungeni.ui.calendar.utils import generate_recurrence_dates
    >>> import datetime
    >>> dates = []
    >>> start_date = datetime.datetime.strptime("2010-10-02 10:00", '%Y-%m-%d %H:%M')
    >>> end_date = datetime.datetime.strptime("2010-10-10 10:00", '%Y-%m-%d %H:%M')
    
Repeat event daily
    >>> recurrence_type = "day_1___#no"
    >>> generate_recurrence_dates(start_date, end_date, recurrence_type)
        [datetime.datetime(2010, 10, 2, 10, 0), 
         datetime.datetime(2010, 10, 3, 10, 0), 
         datetime.datetime(2010, 10, 4, 10, 0), 
         datetime.datetime(2010, 10, 5, 10, 0), 
         datetime.datetime(2010, 10, 6, 10, 0), 
         datetime.datetime(2010, 10, 7, 10, 0), 
         datetime.datetime(2010, 10, 8, 10, 0), 
         datetime.datetime(2010, 10, 9, 10, 0), 
         datetime.datetime(2010, 10, 10, 10, 0)]

Repeat the event every 3 days
    >>> recurrence_type = "day_3___#no"
    >>> generate_recurrence_dates(start_date, end_date, recurrence_type)
        [datetime.datetime(2010, 10, 2, 10, 0), 
         datetime.datetime(2010, 10, 5, 10, 0), 
         datetime.datetime(2010, 10, 8, 10, 0)]

Repeat the event every 4 days, stop after 5 occurences
    >>> recurrence_type = "day_4___#5"
    >>> generate_recurrence_dates(start_date, end_date, recurrence_type)
        [datetime.datetime(2010, 10, 2, 10, 0), 
         datetime.datetime(2010, 10, 6, 10, 0), 
         datetime.datetime(2010, 10, 10, 10, 0)]
         
Repeat the event every workday
    >>> recurrence_type = "week_1___1,2,3,4,5#no"
    >>> generate_recurrence_dates(start_date, end_date, recurrence_type)
        [datetime.datetime(2010, 10, 4, 10, 0),
         datetime.datetime(2010, 10, 5, 10, 0),
         datetime.datetime(2010, 10, 6, 10, 0), 
         datetime.datetime(2010, 10, 7, 10, 0), 
         datetime.datetime(2010, 10, 8, 10, 0)]

Repeat the event every workday, stop after 5 occurences
    >>> recurrence_type = "week_1___1,2,3,4,5#5"
    >>> generate_recurrence_dates(start_date, end_date, recurrence_type)
        [datetime.datetime(2010, 10, 4, 10, 0), 
         datetime.datetime(2010, 10, 5, 10, 0), 
         datetime.datetime(2010, 10, 6, 10, 0), 
         datetime.datetime(2010, 10, 7, 10, 0), 
         datetime.datetime(2010, 10, 8, 10, 0)]
         
Repeat the event weekly on Mondays, Tuesdays and Saturdays
    >>> recurrence_type = "week_1___1,2,6#no"
    >>> generate_recurrence_dates(start_date, end_date, recurrence_type)
        [datetime.datetime(2010, 10, 2, 10, 0), 
         datetime.datetime(2010, 10, 4, 10, 0), 
         datetime.datetime(2010, 10, 5, 10, 0), 
         datetime.datetime(2010, 10, 9, 10, 0)]
         
Repeat the event weekly on Mondays, Tuesdays and Saturdays, stop after 3 occurences
    >>> recurrence_type = "week_1___1,2,6#3"
    >>> generate_recurrence_dates(start_date, end_date, recurrence_type)
        [datetime.datetime(2010, 10, 2, 10, 0), 
         datetime.datetime(2010, 10, 4, 10, 0), 
         datetime.datetime(2010, 10, 5, 10, 0)]
         
Repeat every nth day of every month
nth day being the day in the start date
    >>> end_date = datetime.datetime.strptime("2011-10-10 10:00", '%Y-%m-%d %H:%M')
    >>> recurrence_type = "month_1___#no"
    >>> generate_recurrence_dates(start_date, end_date, recurrence_type)
        [datetime.datetime(2010, 10, 2, 10, 0),
         datetime.datetime(2010, 11, 2, 10, 0), 
         datetime.datetime(2010, 12, 2, 10, 0),
         datetime.datetime(2011, 1, 2, 10, 0),
         datetime.datetime(2011, 2, 2, 10, 0),
         datetime.datetime(2011, 3, 2, 10, 0),
         datetime.datetime(2011, 4, 2, 10, 0),
         datetime.datetime(2011, 5, 2, 10, 0),
         datetime.datetime(2011, 6, 2, 10, 0), 
         datetime.datetime(2011, 7, 2, 10, 0), 
         datetime.datetime(2011, 8, 2, 10, 0), 
         datetime.datetime(2011, 9, 2, 10, 0), 
         datetime.datetime(2011, 10, 2, 10, 0)]
         
Repeat every nth day of every month, stop after 5 occurrences
nth day being the day in the start date
    >>> recurrence_type = "month_1___#5"
    >>> generate_recurrence_dates(start_date, end_date, recurrence_type)
        [datetime.datetime(2010, 10, 2, 10, 0),
         datetime.datetime(2010, 11, 2, 10, 0),
         datetime.datetime(2010, 12, 2, 10, 0),
         datetime.datetime(2011, 1, 2, 10, 0), 
         datetime.datetime(2011, 2, 2, 10, 0)]
         
Repeat every nth day of every 4 months
nth day being the day in the start date
    >>> recurrence_type = "month_4___#no"
    >>> generate_recurrence_dates(start_date, end_date, recurrence_type)
        [datetime.datetime(2010, 10, 2, 10, 0), 
         datetime.datetime(2011, 2, 2, 10, 0), 
         datetime.datetime(2011, 6, 2, 10, 0), 
         datetime.datetime(2011, 10, 2, 10, 0)]

Repeat every nth day of every 4 months, stop after 2 occurrences
nth day being the day in the start date
    >>> recurrence_type = "month_4___#2"
    >>> generate_recurrence_dates(start_date, end_date, recurrence_type)
        [datetime.datetime(2010, 10, 2, 10, 0), 
         datetime.datetime(2011, 2, 2, 10, 0)]
         
Repeat on the 2nd Monday of every month
    >>> recurrence_type = "month_1_1_2_#no"
    >>> generate_recurrence_dates(start_date, end_date, recurrence_type)
        [datetime.datetime(2010, 10, 11, 10, 0),
         datetime.datetime(2010, 11, 8, 10, 0), 
         datetime.datetime(2010, 12, 13, 10, 0), 
         datetime.datetime(2011, 1, 10, 10, 0), 
         datetime.datetime(2011, 2, 14, 10, 0), 
         datetime.datetime(2011, 3, 14, 10, 0), 
         datetime.datetime(2011, 4, 11, 10, 0), 
         datetime.datetime(2011, 5, 9, 10, 0), 
         datetime.datetime(2011, 6, 13, 10, 0), 
         datetime.datetime(2011, 7, 11, 10, 0), 
         datetime.datetime(2011, 8, 8, 10, 0), 
         datetime.datetime(2011, 9, 12, 10, 0), 
         datetime.datetime(2011, 10, 10, 10, 0)]
         
Repeat on the 2nd Monday of every month, stop after 5 occurrences
    >>> recurrence_type = "month_1_1_2_#5"
    >>> generate_recurrence_dates(start_date, end_date, recurrence_type)
        [datetime.datetime(2010, 10, 11, 10, 0), 
         datetime.datetime(2010, 11, 8, 10, 0), 
         datetime.datetime(2010, 12, 13, 10, 0), 
         datetime.datetime(2011, 1, 10, 10, 0), 
         datetime.datetime(2011, 2, 14, 10, 0)]
         
Repeat on the 2nd Monday of every 2 months
    >>> recurrence_type = "month_2_1_2_#no"
    >>> generate_recurrence_dates(start_date, end_date, recurrence_type)
        [datetime.datetime(2010, 10, 11, 10, 0),
         datetime.datetime(2010, 12, 13, 10, 0), 
         datetime.datetime(2011, 2, 14, 10, 0), 
         datetime.datetime(2011, 4, 11, 10, 0), 
         datetime.datetime(2011, 6, 13, 10, 0), 
         datetime.datetime(2011, 8, 8, 10, 0), 
         datetime.datetime(2011, 10, 10, 10, 0)]
         
Repeat every nth day of January of every year
nth day being the day in the start date
    >>> recurrence_type = "year_1___#no"
    >>> generate_recurrence_dates(start_date, end_date, recurrence_type)
        [datetime.datetime(2010, 10, 2, 10, 0), 
         datetime.datetime(2011, 10, 2, 10, 0)]
         
Repeat every 3rd Monday of January
    >>> recurrence_type = "year_1_1_3_#no"
    >>> generate_recurrence_dates(start_date, end_date, recurrence_type)
        [datetime.datetime(2011, 1, 17, 10, 0)]
