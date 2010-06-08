#!/usr/bin/env python
# encoding: utf-8
import datetime

import sqlalchemy.sql.expression as sql
from sqlalchemy.orm import mapper
import sqlalchemy as rdb

from ore.alchemist import Session

from bungeni.models import domain, schema

bookedvenues = schema.venues.join(schema.sittings)

class BookedVenue(object):
    """ venue booked for a Sitting """

mapper(BookedVenue, bookedvenues)


def get_available_venues( start, end, sitting=None ):
    """get all venues that are not booked for a sitting
    (but sitting if given)
    in the given time period 
    SQL:
    SELECT * 
    FROM venues 
    WHERE venues.venue_id NOT IN (SELECT group_sittings.venue_id 
        FROM group_sittings 
        WHERE (group_sittings.start_date BETWEEN '2000-01-01' AND '2000-01-02' 
        OR group_sittings.end_date BETWEEN '2000-01-01'  AND '2000-01-02'
        OR '2000-01-01'  BETWEEN group_sittings.start_date AND 
            group_sittings.end_date 
        OR '2000-01-02'  BETWEEN group_sittings.start_date AND 
            group_sittings.end_date) 
        AND group_sittings.venue_id IS NOT NULL)
    """
    session = Session()
    query = session.query(domain.Venue)
    b_filter = sql.and_(
                    sql.or_( 
                        sql.between(schema.sittings.c.start_date, start, end), 
                        sql.between(schema.sittings.c.end_date, start, end),
                        sql.between(start, schema.sittings.c.start_date, 
                                    schema.sittings.c.end_date),
                        sql.between(end, schema.sittings.c.start_date, 
                                    schema.sittings.c.end_date)
                        ),
                    schema.sittings.c.venue_id != None)
    if sitting:
        if sitting.sitting_id:
            b_filter = sql.and_(b_filter,
                        schema.sittings.c.sitting_id != sitting.sitting_id)
    query = query.filter(
                sql.not_(
                    schema.venues.c.venue_id.in_(
                        sql.select( [schema.sittings.c.venue_id] 
                                    ).where(b_filter)
                    )))
    venues = query.all()
    #session.close()
    return venues
    
def get_unavailable_venues( start, end, sitting = None ):
    """
    get all venues that are  booked 
    in the given time period
    """
    assert( type(start) == datetime.datetime )
    assert( type(end) == datetime.datetime )
    session = Session()
    b_filter = sql.or_( 
                    sql.between(schema.sittings.c.start_date, start, end), 
                    sql.between(schema.sittings.c.end_date, start, end),
                    sql.between(start, schema.sittings.c.start_date, 
                                schema.sittings.c.end_date),
                    sql.between(end, schema.sittings.c.start_date, 
                                schema.sittings.c.end_date)
                    )
    if sitting:
        if sitting.sitting_id:
            b_filter = sql.and_(b_filter,
                        schema.sittings.c.sitting_id != sitting.sitting_id)
    query = session.query(BookedVenue).filter(b_filter)
    venues = query.all()
    #session.close()
    return venues

def check_venue_bookings( start, end, venue, sitting=None ):
    """
    return all sittings (but sitting if given) a venue is booked for
    in the period
    """
    assert( type(start) == datetime.datetime )
    assert( type(end) == datetime.datetime ) 
    session = Session()
    b_filter = sql.and_(sql.or_( 
                    sql.between(schema.sittings.c.start_date, start, end), 
                    sql.between(schema.sittings.c.end_date, start, end),
                    sql.between(start, schema.sittings.c.start_date, 
                                schema.sittings.c.end_date),
                    sql.between(end, schema.sittings.c.start_date, 
                                schema.sittings.c.end_date)
                        ),
                    schema.sittings.c.venue_id == venue.venue_id)
    if sitting:
        if sitting.sitting_id:
            b_filter = sql.and_(b_filter,
                        schema.sittings.c.sitting_id != sitting.sitting_id)
    query = session.query(BookedVenue).filter(b_filter)
    venues = query.all()
    #session.close()
    return venues
    
def check_availability( start, end, venue, sitting=None):
    """
    check if the venue is available 
    in the given period
    """
    return check_venue_bookings( start, end, venue, sitting) == []


