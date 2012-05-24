
# db specific utilities to retrive values, restriction etc
# from the db implementation

from zope.security.proxy import removeSecurityProxy
import sqlalchemy as rdb
from sqlalchemy.orm import mapper
from bungeni.alchemist import Session
import bungeni.models.domain as domain
import bungeni.models.schema as schema
import bungeni.models.interfaces as interfaces


#!+BREAKS_TESTS(mr, may-2012) Remove, should probably be using context.owner?
def get_user(user_id):
    assert user_id, "Must have valid user_id"
    return Session().query(domain.User).get(user_id)

def get_max_type_number(domain_model):
    """Get the current maximum numeric value for this domain_model's type_number.
    If None (no existing instance as yet defines one) return 0.
    !+RESETTABLE per parliamentary session
    """
    session = Session()
    return session.query(rdb.func.max(domain_model.type_number)).scalar() or 0

def get_registry_counts(specific_model):
    """ kls -> (registry_count_general, registry_count_specific)
    Returns the general (all docs) and specific (for the type) counts of how
    many docs have been "registered" (received by parliament) to date.

    !+REGISTRY(mr, apr-2011) should probably have dedicated columns for such 
    information i.e. seq_received, seq_received_type, seq_approved
    !+RESETTABLE per parliamentary session
    !+manually set out-of-sequence numbers may result in non-uniqueness
    """
    session = Session()
    registry_count_general = session.query(
        rdb.func.count(domain.Doc.registry_number)).filter(
            domain.Doc.registry_number != None).scalar() or 0
    specific_model = removeSecurityProxy(specific_model)
    registry_count_specific = session.query(
        rdb.func.count(specific_model.registry_number)).filter(
            specific_model.registry_number != None).scalar() or 0
    return registry_count_general, registry_count_specific


def unschedule_doc(doc):
    """ 
    when a question gets postponed the previous schedules of that
    question are invalidated so they do not show up in the schedule 
    calendar any more
    """
    # only pertinent if doc is transiting from a scheduled state...
    # !+unschedule(mr, may-2012) review this logic here, seems clunky...
    session = Session()
    active_filter = rdb.and_(
        schema.item_schedules.c.item_id == doc.doc_id,
        schema.item_schedules.c.active==True
    )
    item_schedule = session.query(domain.ItemSchedule).filter(active_filter)
    results = item_schedule.all()
    if (len(results)==1):
        results[0].active = False

'''
# !+REGISTRY(mr, apr-2011) rework handling of registry and progessive numbers
# should store these counts (per type) in a generic table
# !+RESETTABLE per parliamentary session
def get_next_reg():
    session = Session()
    sequence = rdb.Sequence("registry_number_sequence")
    connection = session.connection(domain.ParliamentaryItem)
    return connection.execute(sequence)
def get_next_prog(context):
    session = Session()
    sequence = rdb.Sequence("%s_registry_sequence" % context.type)
    connection = session.connection(context.__class__)
    return connection.execute(sequence)
'''

def is_pi_scheduled(doc_id):
    return len(getActiveItemSchedule(doc_id)) >= 1
    
def getActiveItemSchedule(doc_id):
    """Get active itemSchedule instances for parliamentary item.
    
    Use may also be to get scheduled dates e.g.
    for item_schedule in getActiveItemSchedule(doc_id)
        # item_schedule.item_status, item_schedule.item
        s = item_schedule.sitting
        s.start_date, s.end_date, s.status
    """
    session = Session()
    active_filter = rdb.and_(
        schema.item_schedules.c.item_id == doc_id,
        schema.item_schedules.c.active == True
    )
    item_schedule = session.query(domain.ItemSchedule).filter(active_filter)
    results = item_schedule.all()
    sorted_results = [ (r.sitting.start_date, r) for r in results ]
    sorted_results = sorted(sorted_results)
    sorted_results.reverse()
    return [ r for (d, r) in sorted_results ]


def set_doc_type_number(doc):
    """Sets the number that indicates the order in which docs of this type
    have been approved by the Speaker to be the current maximum + 1.
    
    The number is reset at the start of each new parliamentary session with the 
    first doc of this type being assigned the number 1.
    """
    doc.type_number = get_max_type_number(doc.__class__) + 1

#

def get_ministry(ministry_id):
    return Session().query(domain.Ministry).get(ministry_id)

class _Minister(object):
    pass

ministers = rdb.join(schema.groups,schema.user_group_memberships, 
        schema.groups.c.group_id == schema.user_group_memberships.c.group_id
    ).join(schema.users,
        schema.user_group_memberships.c.user_id == schema.users.c.user_id)
mapper(_Minister, ministers)

def get_ministers(ministry):
    """Get comma-seperated list of emails of all persons who are 
    ministry members.
    """
    query = Session().query(_Minister).filter(
        _Minister.group_id == ministry.group_id)
    return [ minister for minister in query.all() ]

#

def deactivateGroupMembers(group):
    """ upon dissolution of a group all group members
    are deactivated and get the end date of the group"""
    session = Session()
    group_id = group.group_id
    end_date = group.end_date
    assert(end_date != None)
    connection = session.connection(domain.Group)
    connection.execute(
        schema.user_group_memberships.update().where(
            rdb.and_(
                schema.user_group_memberships.c.group_id == group_id,
                schema.user_group_memberships.c.active_p == True
            )
        ).values(active_p=False)
    )
    connection.execute(
        schema.user_group_memberships.update().where(
            rdb.and_(
                schema.user_group_memberships.c.group_id == group_id,
                schema.user_group_memberships.c.end_date == None
            )
        ).values(end_date=end_date)
    )
    def deactivateGroupMemberTitles(group):
        group_members = rdb.select([schema.user_group_memberships.c.user_id],
                 schema.user_group_memberships.c.group_id == group_id)
        connection.execute(
            schema.member_titles.update().where(
                rdb.and_( 
                    schema.member_titles.c.membership_id.in_(group_members),
                    schema.member_titles.c.end_date == None
                ) 
            ).values(end_date=end_date)
        )
    deactivateGroupMemberTitles(group)


def endChildGroups(group):
    """ upon dissolution of a parliament for all committees,
    offices and political groups of this parliament the end date is 
    set 
    or upon dissolution of a government for all ministries 
    of this government the end date is set
    (in order to be able to dissolve those groups)"""
    def _end_parliament_group(group_class, parent_id, end_date):
        groups = session.query(group_class).filter(
            rdb.and_(group_class.status == "active",
                group_class.parent_group_id == parliament_id)).all()
        for group in groups:
            if group.end_date == None:
                group.end_date = end_date
        return groups
    
    session = Session()
    end_date = group.end_date
    assert(end_date != None)
    if interfaces.IParliament.providedBy(group):
        parliament_id = group.parliament_id
        committees = _end_parliament_group(domain.Committee, 
                    parliament_id,
                    end_date)
        for committee in committees:
            yield committee
        offices = _end_parliament_group(domain.Office,
                    parliament_id,
                    end_date)
        for office in offices:
            yield office
        political_groups =  _end_parliament_group(domain.PoliticalGroup,
                    parliament_id,
                    end_date)
        for political_group in political_groups:
            yield political_group
    elif interfaces.IGovernment.providedBy(group):
        government_id = group.group_id
        ministries = session.query(domain.Ministry).filter(
            rdb.and_(domain.Ministry.status == "active",
                domain.Ministry.parent_group_id == government_id)
                ).all()
        for ministry in ministries:
            if ministry.end_date == None:
                ministry.end_date = end_date
            yield ministry

def set_real_order(sitting):
    """ set planned order = real order """
    for item in sitting.item_schedule:
            item.real_order = item.planned_order
                             

    
