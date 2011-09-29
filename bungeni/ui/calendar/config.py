# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Calendar and Scheduling configuration

$Id:$
"""

ICAL_DOCUMENT_TEMPLATE="""BEGIN:VCALENDAR
VERSION:2.0
PRODID:Bungeni
%(event_data)s
END:VCALENDAR"""

ICAL_EVENT_TEMPLATE = """BEGIN:VEVENT
DTSTART:%(event_start)s
DTEND:%(event_end)s
LOCATION:%(event_venue)s
SUMMARY:%(event_summary)s
END:VEVENT"""
