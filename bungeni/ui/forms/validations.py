# encoding: utf-8
"""
form validations for custom forms
"""

import datetime
from zope import interface
from bungeni.core.i18n import _

from bungeni.alchemist import Session
from bungeni.alchemist.interfaces import IAlchemistContent
from bungeni.alchemist.interfaces import IAlchemistContainer

import sqlalchemy as rdb

from bungeni.models import interfaces
from bungeni.models import schema
from bungeni.models import venue
from bungeni.models import domain
from bungeni.ui.utils import queries, date as ui_date
from bungeni.ui.calendar.utils import generate_dates
from bungeni.ui.calendar.utils import datetimedict
from zope.security.proxy import removeSecurityProxy
from interfaces import Modified


def null_validator(*args, **kwargs):
    return []


def validate_start_date_within_parent( parent, data ):
    """ Check that the start date is inside the restrictictions.
    It must not start before the contextParents start date or end
    after the contextsParents end date"""
    errors =[]
    if data.get('start_date',None):
        start = ui_date.get_date(data['start_date'])
        if getattr(parent, 'start_date', None):
            pstart = ui_date.get_date(parent.start_date)
            if start < pstart:
                errors.append( interface.Invalid( 
                _(u"Start date must be after (%s)") % pstart, 
                "start_date" ))
        if getattr(parent, 'end_date', None):
            pend = ui_date.get_date(parent.end_date)
            if start > pend:
                errors.append( interface.Invalid( 
                _(u"Start date must be prior to (%s)") % pend, 
                "start_date" ))
    return errors

def validate_start_date_equals_end_date(action, data, context, container):
    """ Check that the start date is inside the restrictictions.
    It must not start before the contextParents start date or end
    after the contextsParents end date"""
    errors =[]
    if data.get('start_date',None) and data.get('end_date', None):
        start = ui_date.get_date(data['end_date']) 
        end = ui_date.get_date(data['start_date'])
        if start != end:
            errors.append( interface.Invalid( 
                _(u"End date must be equal to start date") , 
                "end_date" ))
    return errors

    
def validate_end_date_within_parent( parent, data ):
    """
    Check that the end date is inside the restrictictions.
    It must not end before the context.Parents start date or end
    after the context.Parents end date
    """
    errors =[]
    if data.get( 'end_date', None):
        end = ui_date.get_date(data['end_date'])
        if getattr(parent, 'start_date', None):
            pstart = ui_date.get_date(parent.start_date)
            if end < pstart:
                errors.append( interface.Invalid( 
                _(u"End date must be after (%s)")  % pstart, 
                "end_date" ))
        if getattr(parent, 'end_date', None):
            pend = ui_date.get_date(parent.end_date)
            if end > pend:
                errors.append( interface.Invalid( 
                _(u"End date must be prior to (%s)") % pend, 
                "end_date" ))
    return errors




 
def validate_date_range_within_parent(action, data, context, container):
    errors = validate_start_date_within_parent( container.__parent__, data )
    errors = errors + validate_end_date_within_parent( container.__parent__, data )
    return errors


        


class AllPartyMemberships(object):
    """ Helper class to get all partymemberships
    for all users """

all_party_memberships = rdb.join( 
        schema.user_group_memberships, schema.groups).join(
           schema.political_parties)
        
rdb.orm.mapper(AllPartyMemberships, all_party_memberships)

def validate_party_membership(action, data, context, container):
    errors = []
    parent_id = getattr(container.__parent__, 'parent_group_id', None)
    if interfaces.IPartyMember.providedBy(context):
        party_member = context
        user_id = context.user_id
    else:
        party_member = None
        user_id = data['user_id']
    if data.get('start_date',None):
        for r in queries.validate_membership_in_interval(party_member, 
                    AllPartyMemberships, 
                    data['start_date'],
                    user_id,
                    parent_id=parent_id,
                    with_parent=True):
            overlaps = r.short_name
            errors.append(interface.Invalid(
                _("The person is a member in (%s) at that date") % overlaps, 
                "start_date" ))
    if data.get('end_date', None):
        for r in queries.validate_membership_in_interval(party_member, 
                    AllPartyMemberships, 
                    data['end_date'],
                    user_id,
                    parent_id=parent_id,
                    with_parent=True):
            overlaps = r.short_name
            errors.append(interface.Invalid(
                _("The person is a member in (%s) at that date") % overlaps, 
                "end_date" ))
    for r in queries.validate_open_membership(party_member, 
            AllPartyMemberships, 
            user_id, 
            parent_id=parent_id, 
            with_parent=True):
        overlaps = r.short_name
        errors.append(interface.Invalid(
                    _("The person is a member in (%s) at that date") % overlaps, 
                    "end_date" )) 
    return errors
         

def validate_parliament_dates(action, data, context, container):
    """Parliaments must not overlap."""
    errors = []
    if interfaces.IParliament.providedBy(context):
        parliament = context
    else:
        parliament = None
    results = queries.validate_date_in_interval(parliament, 
                domain.Parliament, 
                data['start_date'])
    for result in results:
        overlaps = result.short_name
        errors.append(interface.Invalid(
            _("The start date overlaps with (%s)") % overlaps, "start_date"))
    if data['end_date']:
        results = queries.validate_date_in_interval(parliament, 
                    domain.Parliament, 
                    data['start_date'])
        for result in results:
            overlaps = result.short_name
            errors.append(interface.Invalid(
                _("The end date overlaps with (%s)") % overlaps, "end_date"))
            
    results = queries.validate_date_in_interval(parliament, domain.Parliament, data['election_date'])
    for result in results:
        overlaps = result.short_name
        errors.append(interface.Invalid(
            _("The election date overlaps with (%s)") % 
            overlaps, 
            "election_date")
            )

    if parliament is None:
        results = queries.validate_open_interval(parliament, domain.Parliament)
        for result in results:
            overlaps = result.short_name
            errors.append(interface.Invalid(
                _("Another parliament is not yet dissolved (%s)") % overlaps,
                "election_date"))
        
    return errors

def validate_government_dates(action, data, context, container):
    errors = []
    if interfaces.IGovernment.providedBy(context):
        government = context
    else:
        government = None
            
    if container.__parent__.end_date is not None:
        if data['start_date'] > container.__parent__.end_date:
            errors.append(  interface.Invalid(
                _("Start date cannot be after the parliaments dissolution (%s)") 
                % container.__parent__.end_date , 
                "start_date") )
    if container.__parent__.start_date > data['start_date']:
        errors.append( interface.Invalid(
            _("Start date must start after the swearing in of the parliament (%s)") 
            % container.__parent__.start_date , 
            "start_date") )
    results = queries.validate_date_in_interval(government, 
                    domain.Government, 
                    data['start_date'])
    for result in results:
        overlaps = result.short_name
        errors.append(interface.Invalid(
            _("The start date overlaps with (%s)") % overlaps, 
            "start_date"))
    if data['end_date']:
        results = queries.validate_date_in_interval(government, 
                    domain.Government, 
                    data['start_date'])
        for result in results:
            overlaps = result.short_name
            errors.append(interface.Invalid(
                _("The end date overlaps with (%s)") % overlaps, 
                "end_date"))

    if government is None:
        results = queries.validate_open_interval(government, domain.Government)
        for result in results:
            overlaps = result.short_name
            errors.append(interface.Invalid(
                _("Another government is not yet dissolved (%s)") % overlaps,
                "start_date"))
        
    return errors
  
def validate_group_membership_dates(action, data, context, container):
    """ A User must be member of a group only once at a time """
    errors =[]
    group_id = container.__parent__.group_id
    if interfaces.IBungeniGroupMembership.providedBy(context):
        group_membership = context
    else:
        group_membership = None
    #!(murithi, apr-2011) VALIDATION - this may be improved
    user_id = data.get('user_id', None)
    if user_id is None:
        return errors
    session = Session()
    if data['start_date']:
        for r in queries.validate_membership_in_interval(group_membership, 
                    domain.GroupMembership, 
                    data['start_date'],
                    user_id, group_id):
            overlaps = r.group.short_name
            errors.append(interface.Invalid(
                _("The person is a member in (%s) at that date") % overlaps, 
                "start_date", "user_id" ))
    if data['end_date']:
        for r in queries.validate_membership_in_interval(group_membership, 
                    domain.GroupMembership, 
                    data['end_date'],
                    user_id, group_id):
            overlaps = r.group.short_name
            errors.append(interface.Invalid(
                _("The person is a member in (%s) at that date") % overlaps, 
                "end_date", "user_id" ))
    for r in queries.validate_open_membership(group_membership, 
                domain.GroupMembership, 
                user_id, group_id):
        overlaps = r.group.short_name
        errors.append(interface.Invalid(
                    _("The person is a member in (%s) at that date") % overlaps, 
                    "end_date", "user_id" )) 
    return errors
                 

class GroupMemberTitle(object):
    """ Titels that may be held by multiple persons of the
    group at the same time"""

group_member_title = rdb.join(schema.user_group_memberships, 
        schema.member_titles).join(
            schema.title_types)
            
                        
rdb.orm.mapper( GroupMemberTitle, group_member_title )


def validate_member_titles(action, data, context, container):
    """Titles for members follow the restrictions:
    A person must have the same title only once (e.g. you cannot
    be chairperson in a group twice at a time)
    If a Title is unique (e.g. chairperson) there can be only one person 
    at a time in this group holding this title, other titles like member 
    may be applied to several persons at the same time""" 
    def get_q_user(date):
        return session.query(GroupMemberTitle).filter(
                rdb.and_(
                    schema.user_group_memberships.c.group_id == group_id,
                    schema.user_group_memberships.c.membership_id == membership_id,
                    schema.member_titles.c.title_type_id == title_type_id,
                    rdb.or_(
                        rdb.between(
                            date, 
                            schema.member_titles.c.start_date,
                            schema.member_titles.c.end_date),
                        schema.member_titles.c.end_date == None
                        )
                    )
                )
    def get_q_unique(date):
        return session.query(GroupMemberTitle).filter(
            rdb.and_(
                schema.user_group_memberships.c.group_id == group_id,
                schema.title_types.c.user_unique == True,
                schema.member_titles.c.title_type_id == title_type_id,
                rdb.or_(
                    rdb.between(
                        date, 
                        schema.member_titles.c.start_date,
                        schema.member_titles.c.end_date),
                    schema.member_titles.c.end_date == None
                    )
                )
            )
    errors = []
    group_id = container.__parent__.group_id
    user_id = container.__parent__.user_id
    membership_id = container.__parent__.membership_id
    session = Session()
    title_type_id = data.get('title_type_id', None)
    if interfaces.IMemberTitle.providedBy(context):
        title = context
    else:
        title = None
    date = datetime.date.today()
    if  data.get( 'start_date', None):
        date = data['start_date']
        q = get_q_user(date)
        results = q.all()
        for result in results:
            overlaps = result.title_name
            if title:
                if title.member_title_id == result.member_title_id:
                    continue
                else:
                    errors.append( interface.Invalid(
                        _(u"This persons already has the title %s") % 
                        overlaps, 
                        "start_date" ))
            else:
                errors.append( interface.Invalid(
                    _(u"This persons already has the title %s") % 
                    overlaps, 
                    "start_date" )) 
    if data.get('end_date',None):
        date = data['end_date']
        q = get_q_user(date)
        results = q.all()
        for result in results:
            overlaps = result.title_name
            if title:
                if title.member_title_id == result.member_title_id:
                    continue
                else:
                    errors.append( interface.Invalid(
                        _(u"This persons already has the title %s") % 
                        overlaps, 
                        "end_date" ))
            else:
                errors.append( interface.Invalid(
                    _(u"This persons already has the title %s") % 
                    overlaps, 
                    "end_date" ))
    if data.get('start_date',None):
        date = data['start_date']
        q = get_q_unique(date)
        results = q.all()
        for result in results:
            overlaps = result.title_name
            if title:
                if title.member_title_id == result.member_title_id:
                    continue
                else:
                    errors.append( interface.Invalid(
                        _(u"A person with the title %s already exists") % 
                        overlaps, 
                        "start_date" ))
            else:
                errors.append( interface.Invalid(
                    _(u"A person with the title %s already exists") % 
                    overlaps, 
                    "start_date" ))
            
    if data.get('end_date',None):
        date = data['end_date']
        q = get_q_unique(date)
        results = q.all()
        for result in results:
            overlaps = result.title_name
            if title:
                if title.member_title_id == result.member_title_id:
                    continue
                else:
                    errors.append( interface.Invalid(
                        _(u"A person with the title %s already exists") % 
                        overlaps, 
                        "end_date" ))
            else:
                errors.append( interface.Invalid(
                    _(u"A person with the title %s already exists") % 
                    overlaps, 
                    "end_date" ))
    return errors

def validate_venues(action, data, context, container):
    """A venue can only be booked for one sitting at once."""
    
    errors = []
    if interfaces.IGroupSitting.providedBy(context):
        sitting = context
    else:
        sitting = None
    venue_id = data.get('venue_id')
    if venue_id is not None:
        venue_id = long(venue_id)
        session = Session()
        svenue = session.query(domain.Venue).get(venue_id)
    else:
        return []
        
    start = data.get('start_date')
    end = data.get('end_date')
    if not(start and end):
        return []
                
    for booking in  venue.check_venue_bookings( start, end, svenue, sitting):
        errors.append(
            interface.Invalid(
                _(u'Venue "$venue" already booked in this time slot',
                  mapping={'venue': booking.short_name}),
                "venue_id"))
    return errors

def validate_recurring_sittings(action, data, context, container):
    """Validate recurring sittings.

    This validator determines the sittings that will be created and
    confirms the validity of them.
    """

    start = data.get('start_date')
    end = data.get('end_date')
    weekdays = data.get('weekdays')
    monthly = data.get('monthly')
    repeat = data.get('repeat')
    repeat_until = data.get('repeat_until')
    exceptions = data.get('exceptions', ())
    
    session = Session()
    group_id = container.__parent__.group_id
    group = session.query(domain.Group).get(group_id)
    sittings = group.sittings
    
    errors = []

    if weekdays or monthly:
        # this should be an invariant, but due to formlib's requirement
        # that invariant methods pertain to a single schema, it's not
        # possible
        if repeat_until is not None and repeat_until < start.date():
            #session.close()
            return [interface.Interface(
                _(u"If recurrence is limited by date, it "
                  "must lie after the starting date"),
                "repeat_until")]

        # verify that dates do not violate group's end date
        for date in generate_recurring_sitting_dates(
            start.date(), repeat, repeat_until, weekdays, monthly, exceptions):
            if group.end_date is not None and date > group.end_date:
                errors.append(interface.Invalid(
                    _(u"One or more events would be scheduled for $F, which is "
                      "after the scheduling group's end date",
                      mapping={'F':datetimedict.fromdate(date)}),
                    "repeat" if repeat else "repeat_until",
                    ))
                break

            event_data = {
                'start_date': datetime.datetime(
                    date.year, date.month, date.day, start.hour, start.minute),
                'end_date': datetime.datetime(
                    date.year, date.month, date.day, end.hour, end.minute),
                }

            errors.extend(validate_non_overlapping_sitting(
                action, event_data, context, container,
                "weekdays" if weekdays else "monthly"))

            if errors:
                break

            errors.extend(validate_venues(
                action, data, context, container))

            if errors:
                break

    return errors

def validate_non_overlapping_sitting(action, data, context, container, *fields):
    start = data.get('start_date')
    end = data.get('end_date',None)

    if not fields:
        fields = "start_date", "end_date"
        
    session = Session()
    group_id = container.__parent__.group_id
    group = session.query(domain.Group).get(group_id)
    sittings = group.sittings

    for sitting in queries.get_sittings_between(sittings, start, end):
        if context != sitting:
            return [interface.Invalid(
                _(u"One or more events would be scheduled for $F, which "
                  "overlaps with an existing sitting",
                  mapping={'F':datetimedict.fromdatetime(start)}),
                *fields)]


    return []

def validate_group_item_assignement(action, data, context, container):
    """ An item can be assigned to a group only once at a time """
    #TODO
    return []


def generate_recurring_sitting_dates(start_date, repeat, repeat_until,
                                     weekdays, monthly, exceptions):
    if repeat_until is not None:
        assert repeat_until > start_date

    generators = []
    if weekdays is not None:
        for weekday in weekdays:
            generators.append(iter(weekday(start_date)))
    
    if monthly is not None:
        generators.append(iter(monthly(start_date)))

    count = 0
    for date in generate_dates(*generators):
        if date in exceptions:
            continue
        count += 1
        if repeat and count > repeat:
            break
        if repeat_until and date.date() > repeat_until:
            break
        yield date.date()

def validate_sub_role_unique(action, data, context, container):
    errors = []
    sub_role_id = data["role_id"]
    if sub_role_id:
        group_id = container.__parent__.group_id
        session = Session()
        title_types = session.query(domain.TitleType).filter(schema.title_types.c.group_id==group_id).all()
        if sub_role_id in [title_type.role_id for title_type in title_types]:
            errors.append(interface.Invalid(
                        _(u"A title with %s sub role already exists") % 
                        sub_role_id))
    return errors

def diff_validator(form, context, data):
    """ Custom validator that checks if form timestamp differs from timestamp in db.
        Returns list of Modified errors for fields which differs from db values.
    """
    diff = form.request.form.get("diff","")
    errors = []
    last_timestamp = form.request.form.get("last_timestamp","")
    context = removeSecurityProxy(context)    
    current_timestamp = str(data.get('timestamp', ''))
    db_timestamp = str(context.timestamp)
    
    # if we're in diff mode we don't care if form.timestamp equals db timestamp    
    if (current_timestamp != db_timestamp and diff!="True") or\
       (last_timestamp!=db_timestamp and last_timestamp):
            for name, value in data.items():
                if context.__dict__[name] != value:
                    errors.append(Modified(_(u"Value was changed!"),name))
    return errors