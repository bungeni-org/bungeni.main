# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Resource Booking

$Id$
"""
log = __import__("logging").getLogger("bungeni.models.resourcebooking")


import datetime

import sqlalchemy.sql.expression as sql
import sqlalchemy as rdb
from sqlalchemy.orm import mapper

from bungeni.alchemist import Session
from bungeni.models import domain, schema


#!+BookedResources(mr, oct-2011)
raise UserWarning("!+BookedResources(mr, oct-2011) needs conceptual+ review!")


bookedresources = rdb.join(
    schema.resources, 
    schema.resourcebookings, 
    schema.resources.c.resource_id == schema.resourcebookings.c.resource_id
).join(
    schema.group_sittings, 
    schema.resourcebookings.c.group_sitting_id == 
        schema.group_sittings.c.group_sitting_id
)
class BookedResources(object):
    """Resources booked for a sitting.
    """
mapper(BookedResources, bookedresources) 


def get_available_resources(start, end):
    """get all resources that are not booked for a sitting
    in the given time period 
    """
    assert(type(start) == datetime.datetime)
    assert(type(end) == datetime.datetime)
    session = Session()
    #start_end={'start': start, 'end':end}
    sql_booked_resources =  """
    SELECT resources.resource_id AS resources_resource_id
    FROM resources JOIN resourcebookings 
                   ON resources.resource_id = resourcebookings.resource_id 
                   JOIN group_sittings 
                   ON resourcebookings.group_sitting_id = group_sittings.group_sitting_id 
    WHERE group_sittings.start_date BETWEEN :start AND :end 
          OR group_sittings.end_date BETWEEN :start AND :end
          OR :start BETWEEN group_sittings.start_date AND group_sittings.end_date
          OR :end BETWEEN group_sittings.start_date AND group_sittings.end_date
    """ 
    
    sql_resources = """
    SELECT resources_1.resource_id AS resources_1_resource_id
    FROM resources AS resources_1
    WHERE resources_1.resource_id NOT IN (%s) """ % sql_booked_resources
    connection = session.connection(domain.Resource)
    query = connection.execute(rdb.text(sql_resources), start=start, end=end)
    resources= query.fetchall()
    return resources


def get_unavailable_resources(start, end):
    """Get all resources that are  booked in the given time period.
    """
    assert(type(start) == datetime.datetime)
    assert(type(end) == datetime.datetime)
    session = Session()
    b_filter = sql.or_(
        sql.between(schema.group_sittings.c.start_date, start, end), 
        sql.between(schema.group_sittings.c.end_date, start, end),
        sql.between(start, 
            schema.group_sittings.c.start_date, schema.group_sittings.c.end_date),
        sql.between(end, 
            schema.group_sittings.c.start_date, schema.group_sittings.c.end_date)
    )
    query = session.query(BookedResources).filter(b_filter)
    resources = query.all()
    return resources


def check_bookings(start, end, resource):
    """Return all group_sittings a resource is booked for in the period.
    """
    assert(type(resource) == domain.Resource)
    assert(type(start) == datetime.datetime)
    assert(type(end) == datetime.datetime)
    session = Session()
    b_filter = sql.and_(
        schema.resources.c.resource_id == resource.resource_id,
        sql.or_(
            sql.between(schema.group_sittings.c.start_date, start, end), 
            sql.between(schema.group_sittings.c.end_date, start, end),
            sql.between(start, 
                schema.group_sittings.c.start_date, schema.group_sittings.c.end_date),
            sql.between(end, 
                schema.group_sittings.c.start_date, schema.group_sittings.c.end_date)
        )
    )
    query = session.query(BookedResources).filter(b_filter)
    bookings = query.all()
    return bookings

                    
def check_availability(start, end, resource):
    """Check if the resource is available in the given period.
    """
    assert(type(resource) == domain.Resource)
    assert(type(start) == datetime.datetime)
    assert(type(end) == datetime.datetime) 
    return check_bookings(start, end, resource) == []


def book_resource(sitting, resource):
    """Book a resource for a sitting, check if the resource is available first
    """
    assert(type(sitting) == domain.GroupSitting)
    assert(type(resource) == domain.Resource)
    session = Session()
    # check if resource is already boooked for this sitting
    cq = session.query(domain.ResourceBooking).filter(
            sql.and_(domain.ResourceBooking.resource_id == 
                        resource.resource_id,
                    domain.ResourceBooking.group_sitting_id == sitting.group_sitting_id))
    results = cq.all()
    if results:
        # !+DOCTTEST(mr, sep-2010) a doctest depends on this print !
        print "already booked"
        return
        #nothing to do here it is already booked
    
    if check_availability(sitting.start_date, sitting.end_date, resource):
        booking = domain.ResourceBooking()
        booking.resource_id = resource.resource_id
        booking.group_sitting_id = sitting.group_sitting_id 
        session.add(booking)
        session.flush()
    else:
        # !+DOCTTEST(mr, sep-2010) a doctest depends on this print !
        print "not available"


def unbook_resource(sitting, resource):
    """Remove a resource from a sitting.
    """
    assert(type(sitting) == domain.GroupSitting)
    assert(type(resource) == domain.Resource)
    session = Session()
    cq = session.query(domain.ResourceBooking).filter(
        sql.and_(
            domain.ResourceBooking.resource_id == resource.resource_id,
            domain.ResourceBooking.group_sitting_id == sitting.group_sitting_id
        )
    )
    results = cq.all()
    for result in results:
        session.delete(result)
        session.flush()

