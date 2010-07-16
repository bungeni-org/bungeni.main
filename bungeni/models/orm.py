
import sqlalchemy as rdb
from sqlalchemy.orm import mapper, relation, column_property, backref

import schema
import domain


# Users
# general representation of a person
mapper(domain.User, schema.users,
    properties={
        "user_addresses": relation(domain.UserAddress),
    }
)

# Groups

mapper(domain.Group, schema.groups,
    primary_key=[schema.groups.c.group_id],
    properties={
        "members": relation(domain.GroupMembership),
        "group_principal_id": column_property(
                ("group.%s." % (schema.groups.c.type) + 
                    rdb.cast(schema.groups.c.group_id, rdb.String)
            ).label("group_principal_id")),
        "contained_groups": relation(domain.Group, 
            backref=backref("parent_group", 
                remote_side=schema.groups.c.group_id)
        ),
        # "keywords": relation(domain.Keyword, secondary=schema.groups_keywords)
    },
    polymorphic_on=schema.groups.c.type,
    polymorphic_identity="group"
)

# Keywords for groups
#mapper(domain.Keyword, schema.keywords,
#    properties = {
#       "groups": relation(domain.Group, 
#            secondary=schema.groups_keywords, backref="keywords"
#       ),
#    }
#)

# delegate rights to act on behalf of a user
mapper(domain.UserDelegation, schema.user_delegations, 
    properties={
        "user": relation(domain.User,
            primaryjoin=rdb.and_(
                schema.user_delegations.c.user_id==
                schema.users.c.user_id
            ),
            uselist=False,
            lazy=True
        ),
        "delegation": relation(domain.User,
            primaryjoin=rdb.and_(
                schema.user_delegations.c.delegation_id==
                schema.users.c.user_id,
                schema.users.c.active_p=="A"
            ),
            uselist=False,
            lazy=True
        ),
    }
)

# group subclasses

s_government = rdb.select([schema.groups.c.group_id,
                    schema.groups.c.start_date,
                    schema.groups.c.end_date,
                    schema.groups.c.parent_group_id,
                    schema.groups.c.status,
                    schema.groups.c.short_name,
                    schema.groups.c.full_name],
                    whereclause = 
                    schema.groups.c.type ==
                    "government",
                    from_obj=[schema.groups]).alias("list_government")

mapper(domain.ListGovernment, s_government)

mapper(domain.Government,
        inherits=domain.Group,
        polymorphic_on=schema.groups.c.type,
        polymorphic_identity="government"
)

s_parliament = rdb.select([schema.groups.c.group_id,
                    schema.groups.c.start_date,
                    schema.groups.c.end_date,
                    schema.groups.c.parent_group_id,
                    schema.groups.c.short_name,
                    schema.groups.c.status,
                    schema.parliaments.c.election_date,
                    schema.groups.c.full_name],
                    whereclause = 
                    schema.groups.c.type ==
                    "parliament",
                    from_obj=[schema.groups.join(schema.parliaments)
                        ]
                    ).alias("list_parliament")


mapper( domain.ListParliament, s_parliament)

mapper( domain.Parliament, schema.parliaments,
        inherits=domain.Group,
        polymorphic_on=schema.groups.c.type,
        polymorphic_identity="parliament"
        )

mapper( domain.PoliticalEntity, schema.political_parties,
        inherits=domain.Group,
        polymorphic_on=schema.groups.c.type,
        polymorphic_identity="political-entity"
        )
        
mapper( domain.PoliticalParty, 
        inherits=domain.PoliticalEntity,
        polymorphic_on=schema.groups.c.type,
        polymorphic_identity="political-party"
        )

mapper( domain.PoliticalGroup, 
        inherits=domain.PoliticalEntity,
        polymorphic_on=schema.groups.c.type,
        polymorphic_identity="political-group"
        )
        
mapper( domain.Ministry,
        inherits=domain.Group,
        polymorphic_on=schema.groups.c.type,
        polymorphic_identity="ministry"
        )


s_committee = rdb.select([schema.groups.c.group_id,
                    schema.groups.c.start_date,
                    schema.groups.c.end_date,
                    schema.groups.c.parent_group_id,
                    schema.groups.c.short_name,
                    schema.groups.c.status,
                    schema.committee_type.c.committee_type_id.label("_fk_committee_type_id"),
                    schema.committee_type.c.committee_type.label("committee_type_id"),
                    schema.committee_type.c.committee_type,
                    schema.groups.c.full_name],
                    whereclause = 
                    schema.groups.c.type ==
                    "committee",
                    from_obj=[schema.groups.join(schema.committees.join(
                            schema.committee_type),
                        schema.groups.c.group_id == 
                        schema.committees.c.committee_id)
                        ]
                    ).alias("list_committee")


mapper(domain.ListCommittee, s_committee)

mapper( domain.Committee, schema.committees,
        inherits=domain.Group,
        polymorphic_on=schema.groups.c.type,
        polymorphic_identity="committee",
        properties={
            "committee_type": relation( domain.CommitteeType,
                              uselist=False,
                              lazy=False ),
            },
        )
        

mapper( domain.Office, schema.offices,
        inherits=domain.Group,
        polymorphic_on=schema.groups.c.type,
        polymorphic_identity="office"
        )

   

# Ministers and Committee members are defined by their group membership in a 
# ministry or committee (group)

# we need to specify join clause for user explicitly because we have multiple fk
# to the user table.
mapper(domain.GroupMembership, schema.user_group_memberships,
    properties={
        "user":relation(domain.User,
            primaryjoin=rdb.and_(schema.user_group_memberships.c.user_id==
                schema.users.c.user_id),
            uselist=False,
            lazy=False),
        "group":relation(domain.Group,
            primaryjoin=(schema.user_group_memberships.c.group_id==
                schema.groups.c.group_id),
            uselist=False,
            lazy=True),
        "replaced":relation(domain.GroupMembership,
            primaryjoin=(schema.user_group_memberships.c.replaced_id==
                schema.user_group_memberships.c.membership_id),
            uselist=False,
            lazy=True),
        "member_titles":relation(domain.MemberRoleTitle)
    },
    polymorphic_on=schema.user_group_memberships.c.membership_type,
    polymorphic_identity="member",
)

mapper(domain.MemberOfParliament, schema.parliament_memberships,
    inherits=domain.GroupMembership,
    primary_key=[schema.user_group_memberships.c.membership_id], 
    properties={
        "constituency":relation(domain.Constituency,
            primaryjoin=(schema.parliament_memberships.c.constituency_id==
                            schema.constituencies.c.constituency_id),
            uselist=False,
            lazy=False),
        "constituency_id":[schema.parliament_memberships.c.constituency_id],
        "party":relation(domain.PoliticalParty,
            primaryjoin=(schema.parliament_memberships.c.party_id==
                            schema.political_parties.c.party_id),
            uselist=False,
            lazy=False),
        "party_id":[schema.parliament_memberships.c.party_id],
        "start_date":column_property(
            schema.user_group_memberships.c.start_date.label("start_date")), 
        "end_date":column_property(
            schema.user_group_memberships.c.end_date.label("end_date")),
    },
    polymorphic_on=schema.user_group_memberships.c.membership_type,
    polymorphic_identity="parliamentmember",
)

s_member_of_parliament = rdb.select([schema.user_group_memberships.c.membership_id,
                    schema.user_group_memberships.c.start_date,
                    schema.user_group_memberships.c.end_date,
                    schema.user_group_memberships.c.group_id,
                    schema.parliament_memberships.c.elected_nominated,
                    schema.users.c.first_name,
                    schema.users.c.middle_name,
                    schema.users.c.last_name,
                    (schema.users.c.first_name + " " +
                    schema.users.c.last_name).label("user_id"),
                    schema.users.c.user_id.label("_fk_user_id"),
                    schema.constituencies.c.name.label("constituency_id"),
                    schema.parliament_memberships.c.constituency_id.label("_fk_constituency_id"),
                    schema.constituencies.c.name.label("name")],
                    from_obj=[schema.parliament_memberships.join(
                            schema.constituencies).join(schema.user_group_memberships
                        ).join(
                        schema.users, schema.user_group_memberships.c.user_id==
                              schema.users.c.user_id)]).alias("list_member_of_parliament")
                    


mapper(domain.ListMemberOfParliament,s_member_of_parliament)

s_minister = rdb.select([schema.user_group_memberships.c.membership_id,
                    schema.user_group_memberships.c.start_date,
                    schema.user_group_memberships.c.end_date,
                    schema.user_group_memberships.c.group_id,
                    schema.users.c.first_name,
                    schema.users.c.middle_name,
                    schema.users.c.last_name,
                    (schema.users.c.first_name + " " +
                    schema.users.c.last_name).label("user_id"),
                    schema.users.c.user_id.label("_fk_user_id"),],
                    whereclause = 
                    schema.user_group_memberships.c.membership_type ==
                    "minister",
                    from_obj=[schema.user_group_memberships.join(
                        schema.users, schema.user_group_memberships.c.user_id==
                              schema.users.c.user_id)],
                              ).alias("list_minister")

mapper( domain.ListMinister, s_minister)
   
mapper( domain.Minister, 
        inherits=domain.GroupMembership,
        polymorphic_on=schema.user_group_memberships.c.membership_type,
        polymorphic_identity="minister",
        )
             
s_committeemember = rdb.select([schema.user_group_memberships.c.membership_id,
                    schema.user_group_memberships.c.start_date,
                    schema.user_group_memberships.c.end_date,
                    schema.user_group_memberships.c.group_id,
                    schema.users.c.first_name,
                    schema.users.c.middle_name,
                    schema.users.c.last_name,
                    (schema.users.c.first_name + " " +
                    schema.users.c.last_name).label("user_id"),
                    schema.users.c.user_id.label("_fk_user_id"),],
                    whereclause = 
                    schema.user_group_memberships.c.membership_type ==
                    "committeemember",
                    from_obj=[schema.user_group_memberships.join(
                        schema.users, schema.user_group_memberships.c.user_id==
                              schema.users.c.user_id)],
                              ).alias("list_committeemember")

mapper(domain.ListCommitteeMember, s_committeemember)
 
mapper( domain.CommitteeMember, 
        inherits=domain.GroupMembership,
        polymorphic_on=schema.user_group_memberships.c.membership_type,
        polymorphic_identity="committeemember",
        )

s_partymember = rdb.select([schema.user_group_memberships.c.membership_id,
                    schema.user_group_memberships.c.start_date,
                    schema.user_group_memberships.c.end_date,
                    schema.user_group_memberships.c.group_id,
                    schema.users.c.first_name,
                    schema.users.c.middle_name,
                    schema.users.c.last_name,
                    (schema.users.c.first_name + " " +
                    schema.users.c.last_name).label("user_id"),
                    schema.users.c.user_id.label("_fk_user_id"),],
                    whereclause = 
                    schema.user_group_memberships.c.membership_type ==
                    "partymember",
                    from_obj=[schema.user_group_memberships.join(
                        schema.users, schema.user_group_memberships.c.user_id==
                              schema.users.c.user_id)],
                              ).alias("list_partymember")

mapper(domain.ListPartyMember,s_partymember)
                
mapper( domain.PartyMember, 
        inherits=domain.GroupMembership,
        polymorphic_on=schema.user_group_memberships.c.membership_type,
        polymorphic_identity="partymember",
        )
        
s_officemember = rdb.select([schema.user_group_memberships.c.membership_id,
                    schema.user_group_memberships.c.start_date,
                    schema.user_group_memberships.c.end_date,
                    schema.user_group_memberships.c.group_id,
                    schema.users.c.first_name,
                    schema.users.c.middle_name,
                    schema.users.c.last_name,
                    (schema.users.c.first_name + " " +
                    schema.users.c.last_name).label("user_id"),
                    schema.users.c.user_id.label("_fk_user_id"),],
                    whereclause = 
                    schema.user_group_memberships.c.membership_type ==
                    "officemember",
                    from_obj=[schema.user_group_memberships.join(
                        schema.users, schema.user_group_memberships.c.user_id==
                              schema.users.c.user_id)],
                              ).alias("list_officemember")



mapper(domain.ListOfficeMember, s_officemember)
                
mapper( domain.OfficeMember, 
        inherits=domain.GroupMembership,
        polymorphic_on=schema.user_group_memberships.c.membership_type,
        polymorphic_identity="officemember",
        )
                                         
 
                
# staff assigned to a group (committee, ...)


s_committeestaff = rdb.select([schema.user_group_memberships.c.membership_id,
                    schema.user_group_memberships.c.start_date,
                    schema.user_group_memberships.c.end_date,
                    schema.user_group_memberships.c.group_id,
                    schema.users.c.first_name,
                    schema.users.c.middle_name,
                    schema.users.c.last_name,
                    (schema.users.c.first_name + " " +
                    schema.users.c.last_name).label("user_id"),
                    schema.users.c.user_id.label("_fk_user_id"),],
                    whereclause = 
                    schema.user_group_memberships.c.membership_type ==
                    "committeestaff",
                    from_obj=[schema.user_group_memberships.join(
                        schema.users, schema.user_group_memberships.c.user_id==
                              schema.users.c.user_id)],
                              ).alias("list_committeestaff")

mapper(domain.ListCommitteeStaff,s_committeestaff)

mapper( domain.CommitteeStaff,
        inherits=domain.GroupMembership,
        polymorphic_on=schema.user_group_memberships.c.membership_type,
        polymorphic_identity="committeestaff",
        )

                
mapper( domain.ParliamentSession, schema.parliament_sessions )
mapper( domain.GroupSitting, schema.sittings,
        properties = {
            "sitting_type": relation(
                domain.SittingType, uselist=False),
            "group": relation( domain.Group,
                               primaryjoin=schema.sittings.c.group_id==schema.groups.c.group_id,
                               uselist=False,
                               lazy=True ),
            "start_date" :  column_property(schema.sittings.c.start_date.label("start_date")), 
            "end_date" :  column_property(schema.sittings.c.end_date.label("end_date")), 
            "item_schedule" : relation(domain.ItemSchedule, order_by=schema.items_schedule.c.planned_order),
            "venue" : relation(domain.Venue)
            })

mapper( domain.ResourceType, schema.resource_types )
mapper( domain.Resource, schema.resources )
mapper( domain.ResourceBooking, schema.resourcebookings)

mapper( domain.Venue, schema.venues )

##############################
# Parliamentary Items

mapper( domain.ParliamentaryItem, schema.parliamentary_items,
        polymorphic_on=schema.parliamentary_items.c.type,
        polymorphic_identity="item", 
        properties = {
                    "owner": relation( domain.User,
                              primaryjoin=rdb.and_(schema.parliamentary_items.c.owner_id==schema.users.c.user_id ),
                              uselist=False,
                              lazy=False ),
                    "consignatories": relation( domain.User,
                              secondary=schema.consignatories,),
                    "attached_files": relation( domain.AttachedFile),
                }
         )

s_heading = rdb.select([schema.parliamentary_items.c.parliamentary_item_id,
                    schema.parliamentary_items.c.short_name,
                    schema.parliamentary_items.c.submission_date.label("submission_date"),
                    schema.parliamentary_items.c.status,
                    schema.parliamentary_items.c.status_date,
                    schema.parliamentary_items.c.parliament_id,
                    schema.users.c.first_name,
                    schema.users.c.middle_name,
                    schema.users.c.last_name,
                    (schema.users.c.first_name + " " +
                    schema.users.c.last_name).label("owner_id"),
                    schema.parliamentary_items.c.owner_id.label("_fk_owner_id")
                    ],
                    whereclause = 
                    schema.parliamentary_items.c.type ==
                    "heading",
                    from_obj=[schema.parliamentary_items.join(
                        schema.users, schema.parliamentary_items.c.owner_id==
                              schema.users.c.user_id)],
                              ).alias("list_heading")


mapper( domain.ListHeading, s_heading)

mapper( domain.Heading,
        inherits=domain.ParliamentaryItem,
        polymorphic_on=schema.parliamentary_items.c.type,
        polymorphic_identity="heading")

s_question = rdb.select([schema.parliamentary_items.c.parliamentary_item_id,
                    schema.parliamentary_items.c.short_name,
                    schema.parliamentary_items.c.submission_date.label("submission_date"),
                    schema.parliamentary_items.c.status,
                    schema.parliamentary_items.c.status_date,
                    schema.parliamentary_items.c.parliament_id,
                    schema.questions.c.approval_date,
                    schema.questions.c.ministry_submit_date,
                    schema.questions.c.question_number,
                    schema.users.c.first_name,
                    schema.users.c.middle_name,
                    schema.users.c.last_name,
                    (schema.users.c.first_name + " " +
                    schema.users.c.last_name).label("owner_id"),
                    schema.groups.c.full_name.label("ministry_id"),
                    schema.parliamentary_items.c.owner_id.label("_fk_owner_id"),
                    schema.questions.c.ministry_id.label("_fk_ministry_id"),
                    ],
                    whereclause = 
                    schema.parliamentary_items.c.type ==
                    "question",
                    from_obj=[schema.parliamentary_items.join(
                        schema.questions.join(schema.groups, schema.questions.c.ministry_id==
                        schema.groups.c.group_id), 
                        schema.parliamentary_items.c.parliamentary_item_id ==
                        schema.questions.c.question_id
                        ).join(schema.users, schema.parliamentary_items.c.owner_id==
                              schema.users.c.user_id)],
                              ).alias("list_questions")

mapper(domain.ListQuestion,s_question)


mapper( domain.Question, schema.questions,
        inherits=domain.ParliamentaryItem,
        polymorphic_on=schema.parliamentary_items.c.type,
        polymorphic_identity="question",
        properties = {
             "changes":relation( domain.QuestionChange, backref="origin",
             cascade="all, delete-orphan", passive_deletes=False),
             "ministry": relation( domain.Ministry),
             }
        )
        
mapper( domain.QuestionChange, schema.question_changes )
mapper( domain.QuestionVersion, schema.question_versions,
        properties= {"change": relation( domain.QuestionChange, uselist=False),
                     "head": relation( domain.Question, uselist=False),
                     "attached_files": relation( domain.AttachedFileVersion,
                        primaryjoin = rdb.and_(
                            schema.question_versions.c.content_id ==
                            schema.attached_file_versions.c.item_id,
                            schema.question_versions.c.version_id ==
                            schema.attached_file_versions.c.file_version_id
                        ),
                        foreign_keys=[schema.attached_file_versions.c.item_id,
                            schema.attached_file_versions.c.file_version_id]
                        ),}
        )


s_motion = rdb.select([schema.parliamentary_items.c.parliamentary_item_id,
                    schema.parliamentary_items.c.short_name,
                    schema.parliamentary_items.c.submission_date,
                    schema.parliamentary_items.c.status,
                    schema.parliamentary_items.c.status_date,
                    schema.parliamentary_items.c.parliament_id,
                    schema.motions.c.approval_date,
                    schema.motions.c.motion_number,
                    schema.motions.c.notice_date,
                    schema.users.c.first_name,
                    schema.users.c.middle_name,
                    schema.users.c.last_name,
                    schema.parliamentary_items.c.owner_id.label("_fk_owner_id"),
                    (schema.users.c.first_name + " " +
                    schema.users.c.last_name).label("owner_id"),],
                    whereclause = 
                    schema.parliamentary_items.c.type ==
                    "motion",
                    from_obj=[schema.parliamentary_items.join(
                        schema.motions).join(schema.users, schema.parliamentary_items.c.owner_id==
                              schema.users.c.user_id)],
                              ).alias("list_motion")

mapper(domain.ListMotion,s_motion)

mapper( domain.Motion, schema.motions,
        inherits=domain.ParliamentaryItem,
        polymorphic_on=schema.parliamentary_items.c.type,
        polymorphic_identity="motion",
        properties = {
             "changes":relation( domain.MotionChange, backref="origin",
             cascade="all, delete-orphan", passive_deletes=False),}
        )
        
mapper( domain.MotionChange, schema.motion_changes )
mapper( domain.MotionVersion, schema.motion_versions,
        properties= {"change":relation( domain.MotionChange, uselist=False),
                     "head": relation( domain.Motion, uselist=False),
                     "attached_files": relation( domain.AttachedFileVersion,
                        primaryjoin = rdb.and_(
                            schema.motion_versions.c.content_id ==
                            schema.attached_file_versions.c.item_id,
                            schema.motion_versions.c.version_id ==
                            schema.attached_file_versions.c.file_version_id
                        ),
                        foreign_keys=[schema.attached_file_versions.c.item_id,
                            schema.attached_file_versions.c.file_version_id]
                        ),}
        )


s_bill= rdb.select([schema.parliamentary_items.c.parliamentary_item_id,
                    schema.parliamentary_items.c.short_name,
                    schema.parliamentary_items.c.submission_date,
                    schema.parliamentary_items.c.status,
                    schema.parliamentary_items.c.status_date,
                    schema.parliamentary_items.c.parliament_id,
                    schema.bills.c.publication_date,
                    schema.bills.c.ministry_id,
                    schema.users.c.first_name,
                    schema.users.c.middle_name,
                    schema.users.c.last_name,
                    (schema.users.c.first_name + " " +
                    schema.users.c.last_name).label("owner_id"),
                    schema.parliamentary_items.c.owner_id.label("_fk_owner_id"),],
                    whereclause = 
                    schema.parliamentary_items.c.type ==
                    "bill",
                    from_obj=[schema.parliamentary_items.join(
                        schema.bills).join(schema.users, schema.parliamentary_items.c.owner_id==
                              schema.users.c.user_id)],
                              ).alias("list_bill")


mapper( domain.ListBill, s_bill)
        
mapper( domain.Bill, schema.bills,
        inherits=domain.ParliamentaryItem,
        polymorphic_on=schema.parliamentary_items.c.type,
        polymorphic_identity="bill",
        properties = {
             "changes":relation( domain.BillChange, backref="origin",
             cascade="all, delete-orphan", passive_deletes=False)
             }
        )
mapper( domain.BillChange, schema.bill_changes )
mapper( domain.BillVersion, schema.bill_versions, 
        properties= {"change":relation( domain.BillChange, uselist=False),
                     "head": relation( domain.Bill, uselist=False),
                     "attached_files": relation( domain.AttachedFileVersion,
                        primaryjoin = rdb.and_(
                            schema.bill_versions.c.content_id ==
                            schema.attached_file_versions.c.item_id,
                            schema.bill_versions.c.version_id ==
                            schema.attached_file_versions.c.file_version_id
                        ),
                        foreign_keys=[schema.attached_file_versions.c.item_id,
                            schema.attached_file_versions.c.file_version_id]
                        ),}
        )


s_event = rdb.select([schema.parliamentary_items.c.parliamentary_item_id,
                    schema.parliamentary_items.c.short_name,
                    schema.parliamentary_items.c.submission_date,
                    schema.parliamentary_items.c.status,
                    schema.parliamentary_items.c.status_date,
                    schema.parliamentary_items.c.parliament_id,
                    schema.event_items.c.event_date,
                    schema.event_items.c.item_id,
                    schema.users.c.first_name,
                    schema.users.c.middle_name,
                    schema.users.c.last_name,
                    (schema.users.c.first_name + " " +
                    schema.users.c.last_name).label("owner_id"),
                    schema.parliamentary_items.c.owner_id.label("_fk_owner_id"),],
                    whereclause = 
                    schema.parliamentary_items.c.type ==
                    "event",
                    from_obj=[schema.parliamentary_items.join(
                        schema.agenda_items).join(schema.users, schema.parliamentary_items.c.owner_id==
                              schema.users.c.user_id)],
                              ).alias("list_event")

mapper( domain.ListEventItem, s_event) 

mapper( domain.EventItem, schema.event_items, 
        inherits=domain.ParliamentaryItem,
        inherit_condition=(
                    schema.event_items.c.event_item_id == 
                    schema.parliamentary_items.c.parliamentary_item_id),
        polymorphic_on=schema.parliamentary_items.c.type,
        polymorphic_identity="event")


s_agendaitem = rdb.select([schema.parliamentary_items.c.parliamentary_item_id,
                    schema.parliamentary_items.c.short_name,
                    schema.parliamentary_items.c.submission_date,
                    schema.parliamentary_items.c.status,
                    schema.parliamentary_items.c.status_date,
                    schema.parliamentary_items.c.parliament_id,
                    schema.agenda_items.c.approval_date,
                    schema.agenda_items.c.group_id,
                    schema.users.c.first_name,
                    schema.users.c.middle_name,
                    schema.users.c.last_name,
                    (schema.users.c.first_name + " " +
                    schema.users.c.last_name).label("owner_id"),
                    schema.parliamentary_items.c.owner_id.label("_fk_owner_id"),],
                    whereclause = 
                    schema.parliamentary_items.c.type ==
                    "agendaitem",
                    from_obj=[schema.parliamentary_items.join(
                        schema.agenda_items).join(schema.users, schema.parliamentary_items.c.owner_id==
                              schema.users.c.user_id)],
                              ).alias("list_agendaitem")


mapper(domain.ListAgendaItem, s_agendaitem)

mapper( domain.AgendaItem, schema.agenda_items, 
        inherits=domain.ParliamentaryItem,
        polymorphic_on=schema.parliamentary_items.c.type,
        polymorphic_identity="agendaitem",
        properties = {
             "changes" : relation( domain.AgendaItemChange, backref="origin",
             cascade="all, delete-orphan", passive_deletes=False),
             "group" : relation(domain.Group, 
                primaryjoin=(schema.agenda_items.c.group_id==schema.groups.c.group_id ),
                backref = "agenda_items",
                lazy = False,
                uselist=False,)
             })
mapper( domain.AgendaItemChange, schema.agenda_item_changes )
mapper( domain.AgendaItemVersion, schema.agenda_item_versions,
        properties= {"change":relation( domain.AgendaItemChange, uselist=False),
                     "head": relation( domain.AgendaItem, uselist=False),
                     "attached_files": relation( domain.AttachedFileVersion,
                        primaryjoin = rdb.and_(
                            schema.agenda_item_versions.c.content_id ==
                            schema.attached_file_versions.c.item_id,
                            schema.agenda_item_versions.c.version_id ==
                            schema.attached_file_versions.c.file_version_id
                        ),
                        foreign_keys=[schema.attached_file_versions.c.item_id,
                            schema.attached_file_versions.c.file_version_id]
                        ),}
        )


s_tableddocument = rdb.select([schema.parliamentary_items.c.parliamentary_item_id,
                    schema.parliamentary_items.c.short_name,
                    schema.parliamentary_items.c.submission_date,
                    schema.parliamentary_items.c.status,
                    schema.parliamentary_items.c.status_date,
                    schema.parliamentary_items.c.parliament_id, 
                    schema.tabled_documents.c.approval_date,
                    schema.users.c.first_name,
                    schema.users.c.middle_name,
                    schema.users.c.last_name,
                    (schema.users.c.first_name + " " +
                    schema.users.c.last_name).label("owner_id"),
                    schema.parliamentary_items.c.owner_id.label("_fk_owner_id"),],
                    whereclause = 
                    schema.parliamentary_items.c.type ==
                    "tableddocument",
                    from_obj=[schema.parliamentary_items.join(
                        schema.tabled_documents).join(schema.users, schema.parliamentary_items.c.owner_id==
                              schema.users.c.user_id)],
                              ).alias("list_tableddocument")

mapper( domain.ListTabledDocument, s_tableddocument)
              
mapper( domain.TabledDocument, schema.tabled_documents,
        inherits=domain.ParliamentaryItem,
        polymorphic_on=schema.parliamentary_items.c.type,
        polymorphic_identity="tableddocument",
        properties = {
             "changes":relation( domain.TabledDocumentChange, backref="origin",
             cascade="all, delete-orphan", passive_deletes=False),
             } )
             
mapper( domain.TabledDocumentChange, schema.tabled_document_changes )
mapper( domain.TabledDocumentVersion, schema.tabled_document_versions,
        properties= {"change":relation( domain.TabledDocumentChange, uselist=False),
                     "head": relation( domain.TabledDocument, uselist=False),
                     "attached_files": relation( domain.AttachedFileVersion,
                        primaryjoin = rdb.and_(
                            schema.tabled_document_versions.c.content_id ==
                            schema.attached_file_versions.c.item_id,
                            schema.tabled_document_versions.c.version_id ==
                            schema.attached_file_versions.c.file_version_id
                        ),
                        foreign_keys=[schema.attached_file_versions.c.item_id,
                            schema.attached_file_versions.c.file_version_id]
                        ),}
        )

mapper( domain.AttachedFile, schema.attached_files,
        properties = {
             "changes":relation( domain.AttachedFileChange, backref="origin",
             cascade="all, delete-orphan", passive_deletes=False),
             } )
mapper( domain.AttachedFileChange, schema.attached_file_changes )
mapper( domain.AttachedFileVersion, schema.attached_file_versions,
        properties= {"change":relation( domain.AttachedFileChange, uselist=False),
                     "head": relation( domain.AttachedFile, uselist=False)}
        )


#Items scheduled for a sitting expressed as a relation
# to their item schedule
        
mapper(domain.ItemSchedule, schema.items_schedule,
       properties = {
           "item": relation(
               domain.ParliamentaryItem,
               uselist=False),
           "discussion": relation(
               domain.ScheduledItemDiscussion,
               uselist=False,
               cascade="all, delete-orphan"),
           "sitting" : relation( domain.GroupSitting, uselist=False),
           }
       ) 

mapper(domain.ScheduledItemDiscussion, schema.item_discussion)


# items scheduled for a sitting
# expressed as a join between item and schedule

s_consignatories  = rdb.select([schema.consignatories.c.item_id,
                    schema.consignatories.c.user_id.label("consignatory"),
                    (schema.users.c.first_name + " " +
                    schema.users.c.last_name).label("user_id"),
                    schema.users.c.first_name,
                    schema.users.c.middle_name,
                    schema.users.c.last_name,
                    ],
                    from_obj=[
                        schema.consignatories.join(schema.users)
                        ],
                              ).alias("list_consignatories")

mapper( domain.ListConsignatory, s_consignatories)

       
mapper( domain.Consignatory, schema.consignatories,
        properties= {"item": relation(domain.ParliamentaryItem, uselist=False),
                      "user": relation(domain.User, uselist=False)})
#mapper( domain.Debate, schema.debates )


mapper( domain.BillType, schema.bill_types )
#mapper( domain.DocumentSource, schema.document_sources )
#


mapper( domain.HoliDay, schema.holidays )
        
######################
#

s_constituency = rdb.select([schema.constituencies.c.constituency_id,
                    schema.constituencies.c.name,
                    schema.constituencies.c.start_date,
                    schema.constituencies.c.end_date,
                    schema.provinces.c.province,
                    schema.regions.c.region,
                    schema.constituencies.c.province_id.label("_fk_province_id"),
                    schema.constituencies.c.region_id.label("_fk_region_id"),
                    schema.provinces.c.province.label("province_id"),
                    schema.regions.c.region.label("region_id"),],
                    from_obj=[schema.constituencies.outerjoin(
                        schema.regions).outerjoin(schema.provinces)],
                              ).alias("list_constituency")
    
mapper(domain.ListConstituency, s_constituency)

mapper( domain.Constituency, schema.constituencies,
        properties={
        "province": relation( domain.Province,
                              uselist=False,
                              lazy=False ),
        "region": relation( domain.Region,
                              uselist=False,
                              lazy=False ),
        }
    )
mapper( domain.Province, schema.provinces )
mapper( domain.Region, schema.regions )
mapper( domain.Country, schema.countries )
mapper( domain.ConstituencyDetail, schema.constituency_details,
    properties={
    "constituency": relation( domain.Constituency,
                              uselist=False,
                              lazy=True,
                              backref = "details" ),
    } )
mapper( domain.CommitteeType, schema.committee_type )
mapper( domain.SittingType, schema.sitting_type )

s_sittingattendance  = rdb.select([schema.sitting_attendance.c.sitting_id,
                    schema.sitting_attendance.c.attendance_id.label("_fk_attendance_id"),
                    schema.sitting_attendance.c.member_id.label("_fk_member_id"),
                    schema.attendance_type.c.attendance_type.label("attendance_id"),
                    (schema.users.c.first_name + " " +
                    schema.users.c.last_name).label("member_id"),
                    schema.users.c.first_name,
                    schema.users.c.middle_name,
                    schema.users.c.last_name,
                    ],
                    from_obj=[
                        schema.sitting_attendance.join(
                        schema.attendance_type).join(schema.users)
                        ],
                              ).alias("list_sittingattendance")

mapper( domain.ListGroupSittingAttendance, s_sittingattendance)

mapper( domain.GroupSittingAttendance, schema.sitting_attendance,
        properties={
            "user": relation( domain.User,
                              uselist=False,
                              lazy=False ),
            "attendance_type": relation( domain.AttendanceType,
                                uselist = False,
                                lazy = False ), 
            "sitting": relation( domain.GroupSitting,
                                uselist = False,
                                lazy = False ),
                  }
         )
mapper( domain.AttendanceType, schema.attendance_type )
mapper( domain.MemberTitle, schema.user_role_types )
mapper( domain.MemberRoleTitle, schema.role_titles.join(schema.addresses),
    properties={
        "title_name": relation( domain.MemberTitle,
                              uselist=False,
                              lazy=False ),
    }
)

mapper( domain.AddressType, schema.address_types )
mapper( domain.UserAddress, schema.addresses)


s_group_item_assignments = rdb.select([schema.group_item_assignments.c.assignment_id,
                    schema.group_item_assignments.c.group_id.label("_fk_group_id"),
                    schema.group_item_assignments.c.item_id.label("_fk_item_id"),
                    schema.groups.c.short_name.label("item_id"),
                    (schema.groups.c.short_name + " - " +
                    schema.groups.c.full_name).label("group_id"),
                    schema.group_item_assignments.c.start_date,
                    schema.group_item_assignments.c.end_date,
                    schema.group_item_assignments.c.due_date,
                    ],
                    from_obj=[
                        schema.groups.join(
                        schema.group_item_assignments).join(schema.parliamentary_items)
                        ],
                              ).alias("list_group_item_assignments")


mapper(domain.ListGroupItemAssignment, s_group_item_assignments);

mapper(domain.GroupItemAssignment, schema.group_item_assignments,
        properties={
            "group": relation(domain.Group, 
                primaryjoin=(schema.group_item_assignments.c.group_id==schema.groups.c.group_id ),
                backref = "group_assignments",
                lazy = True,
                uselist=False,),
            "item": relation(
               domain.ParliamentaryItem,
                backref = "item_assignments",
               uselist=False),
            }
        )
mapper(domain.ItemGroupItemAssignment, schema.group_item_assignments,
        inherits=domain.GroupItemAssignment,)
        
mapper(domain.GroupGroupItemAssignment, schema.group_item_assignments,
        inherits=domain.GroupItemAssignment)
        
mapper(domain.Report, schema.reports,
        properties={
            "group": relation(domain.Group, 
                primaryjoin=(schema.reports.c.group_id == schema.groups.c.group_id ),
                backref = "reports",
                lazy = True,
                uselist=False,),}

    )

mapper( domain.SittingReport, schema.sitting_reports,
    properties={
        "sitting": relation(domain.GroupSitting, 
            backref = "reports",
            lazy = True,
            uselist=False,),
        "report": relation(domain.Report, 
            backref = "sittings",
            lazy = True,
            uselist=False,),
            }
    )
    
mapper( domain.Report4Sitting, schema.sitting_reports,
    inherits=domain.Report)

mapper (domain.ObjectTranslation, schema.translations)

    

