
# db specific utilities to retrive values, restriction etc
# from the db implementation
import sqlalchemy as rdb
from sqlalchemy.orm import mapper
from bungeni.alchemist import Session
import bungeni.models.domain as domain
import bungeni.models.schema as schema
import bungeni.models.interfaces as interfaces


def get_user(user_id):
    assert user_id, "Must have valid user_id"
    return Session().query(domain.User).get(user_id)


''' !+UNUSED(mr, mar-2011)
def getQuestionWorkflowTrail(question):
    """Return tha trail of workflow states traversed by the question.
    
    Depends on the <ParliamentaryItem>Change.notes attribute being filled 
    with a serialized python dict containing entries for the workflow's 
    transition's (source, destination) states.
    """
    # !+ note, another way to do it is via raw-SQL:
    # but, replace all such raw-sql with SA-based fetching.
    #item_id = context.parliamentary_item_id
    #from bungeni.ui.utils import queries, statements
    #sql_timeline = statements.sql_question_timeline
    #timeline_changes = queries.execute_sql(sql_timeline, item_id=item_id) 
    session = Session()
    wf_changes = session.query(domain.QuestionChange
        ).filter(domain.QuestionChange.content_id==question.question_id
        ).filter(domain.QuestionChange.action=="workflow"
        ).order_by(domain.QuestionChange.date).all()
    states = []
    for wfc in wf_changes:
        if wfc.notes:
            xtras = eval(wfc.notes)
            for xtra in xtras:
                states.append(xtra.get("destination"))
    return states
'''

def removeQuestionFromItemSchedule(question_id):
    """
    when a question gets postponed the previous schedules of that
    question are invalidated so they do not show up in the schedule 
    calendar any more
    """
    session = Session()
    active_filter = rdb.and_(
        schema.item_schedules.c.item_id == question_id,
        schema.item_schedules.c.active==True
    )
    item_schedule = session.query(domain.ItemSchedule).filter(active_filter)
    results = item_schedule.all()
    if (len(results)==1):
        results[0].active = False
    
'''def set_pi_registry_number(item):
    session = Session()
    connection = session.connection(domain.ParliamentaryItem)
    sequence = rdb.Sequence("registry_number_sequence")
    item.registry_number = connection.execute(sequence)'''

def set_pi_registry_number(item, mask):
    session = Session()
    connection = session.connection(domain.ParliamentaryItem)
    item.registry_number = mask
    
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
    
def setTabledDocumentSerialNumber(tabled_document):
    session = Session()
    connection = session.connection(domain.TabledDocument)
    sequence = rdb.Sequence("tabled_document_number_sequence")
    tabled_document.tabled_document_number = connection.execute(sequence)
    
def setQuestionSerialNumber(question):
    """
     Approved questions are given a serial number enabling the clerks office
     to record the order in which questions are received and hence enforce 
     a first come first served policy in placing the questions on the order
     paper. The serial number is re-initialized at the start of each session
    """
    session = Session()
    connection = session.connection(domain.Question)
    sequence = rdb.Sequence("question_number_sequence")
    question.question_number = connection.execute(sequence)

def is_pi_scheduled(parliamentary_item_id):
    return len(getActiveItemSchedule(parliamentary_item_id)) >= 1
    
def getActiveItemSchedule(parliamentary_item_id):
    """Get active itemSchedule instances for parliamentary item.
    
    Use may also be to get scheduled dates e.g.
    for item_schedule in getActiveItemSchedule(parliamentary_item_id)
        # item_schedule.item_status, item_schedule.item
        s = item_schedule.sitting
        s.start_date, s.end_date, s.status
    """
    session = Session()
    active_filter = rdb.and_(
        schema.item_schedules.c.item_id == parliamentary_item_id,
        schema.item_schedules.c.active == True
    )
    item_schedule = session.query(domain.ItemSchedule).filter(active_filter)
    results = item_schedule.all()
    sorted_results = [ (r.sitting.start_date, r) for r in results ]
    sorted_results = sorted(sorted_results)
    sorted_results.reverse()
    return [ r for (d, r) in sorted_results ]

def setMotionSerialNumber(motion):
    """
     Number that indicate the order in which motions have been approved 
     by the Speaker. The Number is reset at the start of each new session
     with the first motion assigned the number 1
    """
    session = Session()
    connection = session.connection(domain.Motion)
    sequence = rdb.Sequence("motion_number_sequence")
    motion.motion_number = connection.execute(sequence)

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
                             

    
