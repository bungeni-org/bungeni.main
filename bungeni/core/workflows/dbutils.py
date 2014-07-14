# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""db specific utilities to retrive values, restriction etc 
from the db implementation.

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflows")


from zope.security.proxy import removeSecurityProxy
import sqlalchemy as sa
from sqlalchemy.orm import mapper

from bungeni.alchemist import Session
import bungeni.models.domain as domain
import bungeni.models.schema as schema
import bungeni.models.interfaces as interfaces
from bungeni.utils.misc import describe
from bungeni import _


# !+GROUP_GENERALIZE generalize spawn_doc to arbitrary group (not chamber)
# allow from any type of group to any type of group e.g. from chamber to committee?
# use target_group_conceptual_name or target_group_sub_type instead of target_chamber_type ?
def spawn_doc(source_doc, target_chamber_type, target_type_key, target_state_id):
    """Utility to help create parametrized "transfer to chamber" actions.
    Returns the newly spawned doc.
    
    Notes:
    
    - sub-docs "signatories", "attachments", "events" are not carried over to 
        the new doc
    
    - the "owner" of the new doc is the original owner i.e. the member of the 
        originating chamber (but this could be changed on the spawned document?)
    
    - if an explicit version prior to spawning is desired, include the "version"
        action in the actions of the workflow destination state.
    
    """
    from bungeni.core.workflow.interfaces import IStateController
    from bungeni.core.workflows.utils import assign_ownership
    from bungeni.utils import naming
    from bungeni.capi import capi
    
    source_doc = removeSecurityProxy(source_doc)
    session = Session()
    session.merge(source_doc)
    
    # get the singleton "active" chamber of target_chamber_type
    target_chamber = session.query(domain.Chamber
        ).filter(sa.and_(
                domain.Chamber.sub_type == target_chamber_type, 
                domain.Chamber.status == "active")).one()
    
    # get target domain model type, source/target descriptors
    source_ti = capi.get_type_info(source_doc.__class__)
    target_ti = capi.get_type_info(target_type_key)
    
    # create target instance
    target_doc = target_ti.domain_model()
    session.add(target_doc)
    
    # set new "key" values
    target_doc.chamber = target_chamber
    target_doc.group = target_chamber
    target_doc.owner_id = source_doc.owner.user_id # !+PrincipalRoleMap
    target_doc.head = source_doc
    
    # carry-over other values
    for attr_name in [
            #files -> not carried over !+ parametrize as optional?
            #signatories -> not carried over
            #events -> not carried over
            
            #"doc_id", -> auto
            #"chamber_id", -> target_chamber.group_id
            #"owner_id",
            #"type", -> auto, from target_type
            "doc_type",
            "doc_procedure",
            #"type_number", -> a progressive number by type?
            #"registry_number", -> a reference to this resource !+ when do we set it here?
            # "uri", -> ?
            "acronym",
            "title",
            "sub_title",
            "description",
            "summary",
            "language",
            "body",
            #"status", -> auto
            #"status_date", -> auto
            #"group_id", -> target_chamber.group_id
            "subject",
            "doc_date",
            "coverage",
            "doc_urgency",
            "geolocation",
            #"head_id", -> here, this is the "origin" document 
            #"timestamp", -> auto
            
            "source_title",
            "source_creator",
            "source_subject",
            "source_description",
            "source_publisher",
            "source_publisher_address",
            "source_contributors",
            "source_date",
            "source_type",
            "source_format",
            "source_doc_source",
            "source_language",
            "source_relation",
            "source_coverage",
            "source_rights",
        ]:
        source_value = getattr(source_doc, attr_name)
        if source_value is not None:
            setattr(target_doc, attr_name, source_value)
    
    # transfer any extended properties
    for (xp_name, xp_type) in target_ti.domain_model.extended_properties:
        if has_attr(source_doc, xp_name):
            source_value = getattr(source_doc, xp_name)
            if source_value is not None:
                setattr(target_doc, xp_name, source_value)
    
    # status (needs values to be updated first), also does a db flush()
    IStateController(target_doc).set_status(target_state_id)
    
    # !+PrincipalRoleMap
    assign_ownership(target_doc)
    
    log.info("Spawned new document [%s] : (%r, %r, %r) -- from: %s", 
        target_doc, target_chamber_type, target_type_key, target_state_id, source_doc)
    return target_doc




def get_max_type_number(domain_model):
    """Get the current maximum numeric value for this domain_model's type_number.
    If None (no existing instance as yet defines one) return 0.
    !+RESETTABLE per parliamentary session
    """
    session = Session()
    return session.query(sa.func.max(domain_model.type_number)).scalar() or 0

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
        sa.func.count(domain.Doc.registry_number)).filter(
            domain.Doc.registry_number != None).scalar() or 0
    specific_model = removeSecurityProxy(specific_model)
    registry_count_specific = session.query(
        sa.func.count(specific_model.registry_number)).filter(
            specific_model.registry_number != None).scalar() or 0
    return registry_count_general, registry_count_specific


@describe(_(u"Unschedule a document which has been scheduled"))
def unschedule_doc(doc):
    """When a doc gets postponed the previous schedules of that doc are 
    invalidated so they do not show up in the schedule calendar any more.
    """
    # only pertinent if doc is transiting from a scheduled state...
    # !+unschedule(mr, may-2012) review this logic here, seems clunky...
    session = Session()
    active_filter = sa.and_(
        schema.item_schedule.c.item_id == doc.doc_id,
        schema.item_schedule.c.active==True
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
    sequence = sa.Sequence("registry_number_sequence")
    connection = session.connection(domain.Doc)
    return connection.execute(sequence)
def get_next_prog(context):
    session = Session()
    sequence = sa.Sequence("%s_registry_sequence" % context.type)
    connection = session.connection(context.__class__)
    return connection.execute(sequence)
'''

def is_doc_scheduled(doc):
    return len(getActiveItemSchedule(doc)) >= 1
    
def getActiveItemSchedule(doc):
    """Get active itemSchedule instances for parliamentary item.
    
    Use may also be to get scheduled dates e.g.
    for item_schedule in getActiveItemSchedule(doc_id)
        # item_schedule.item_status, item_schedule.item
        s = item_schedule.sitting
        s.start_date, s.end_date, s.status
    """
    session = Session()
    active_filter = sa.and_(
        schema.item_schedule.c.item_id == doc.doc_id,
        schema.item_schedule.c.active == True,
        schema.item_schedule.c.item_type == doc.type,
    )
    item_schedule = session.query(domain.ItemSchedule).filter(active_filter)
    results = item_schedule.all()
    sorted_results = [ (r.sitting.start_date, r) for r in results ]
    sorted_results = sorted(sorted_results)
    sorted_results.reverse()
    return [ r for (d, r) in sorted_results ]

#

def get_ministry(group_id):
    return Session().query(domain.Ministry).get(group_id)


def deactivateGroupMembers(group):
    """ upon dissolution of a group all group members
    are deactivated and get the end date of the group"""
    session = Session()
    group_id = group.group_id
    end_date = group.end_date
    assert(end_date != None)
    connection = session.connection(domain.Group)
    connection.execute(
        schema.member.update().where(
            sa.and_(
                schema.member.c.group_id == group_id,
                schema.member.c.active_p == True
            )
        ).values(active_p=False)
    )
    connection.execute(
        schema.member.update().where(
            sa.and_(
                schema.member.c.group_id == group_id,
                schema.member.c.end_date == None
            )
        ).values(end_date=end_date)
    )
    def deactivateGroupMemberTitles(group):
        group_members = sa.select([schema.member.c.user_id],
                 schema.member.c.group_id == group_id)
        connection.execute(
            schema.member_title.update().where(
                sa.and_(
                    # !+ why is this checking member_id vales not in user_id values ???
                    schema.member_title.c.member_id.in_(group_members),
                    schema.member_title.c.end_date == None
                ) 
            ).values(end_date=end_date)
        )
    deactivateGroupMemberTitles(group)



def endChildGroups(group):
    """Upon dissolution of a chamber for all committees,
    offices and political groups of this chamber the end date is set 
    or upon dissolution of a government for all ministries 
    of this government the end date is set
    (in order to be able to dissolve those groups)"""
    # !+CUSTOM un-hardwire all refs to custom group types
    def _end_chamber_group(group_class, parent_id, end_date):
        groups = session.query(group_class).filter(
            sa.and_(group_class.status == "active",
                group_class.parent_group_id == chamber_id)).all()
        for group in groups:
            if group.end_date == None:
                group.end_date = end_date
        return groups
    
    session = Session()
    end_date = group.end_date
    assert(end_date != None)
    if interfaces.IChamber.providedBy(group):
        chamber_id = group.group_id
        committees = _end_chamber_group(
            domain.Committee, chamber_id, end_date)
        for committee in committees:
            yield committee
        offices = _end_chamber_group(domain.Office, chamber_id, end_date)
        for office in offices:
            yield office
        political_groups = _end_chamber_group(
            domain.PoliticalGroup, chamber_id, end_date)
        for political_group in political_groups:
            yield political_group
    elif interfaces.IGovernment.providedBy(group):
        government_id = group.group_id
        ministries = session.query(domain.Ministry).filter(
            sa.and_(domain.Ministry.status == "active",
                domain.Ministry.parent_group_id == government_id)
            ).all()
        for ministry in ministries:
            if ministry.end_date == None:
                ministry.end_date = end_date
            yield ministry



