
import sqlalchemy as rdb
from sqlalchemy.orm import mapper, relation, column_property, backref

import schema
import domain


# Users
# general representation of a person
mapper(domain.User, schema.users,
    properties={"user_addresses": relation(domain.UserAddress)}
)

# Groups

mapper(domain.Group, schema.groups,
    primary_key=[schema.groups.c.group_id],
    properties={
        "members": relation(domain.GroupMembership),
        "group_principal_id": column_property(
            #
            # !+ ATTENTION: the following sqlalchemy str concat (on c.type) 
            # gives some VERY strange behaviour :
            #
            # print "group." + schema.groups.c.type + "."
            # >>> :type_1 || groups.type || :param_1
            #
            # print group.groups.type.
            # >>> "group.%s." % (schema.groups.c.type)
            #
            ("group." + schema.groups.c.type + "." +
             rdb.cast(schema.groups.c.group_id, rdb.String)
            ).label("group_principal_id")
        ),
        "contained_groups": relation(domain.Group,
            backref=backref("parent_group",
                remote_side=schema.groups.c.group_id)
        ),
        "group_addresses": relation(domain.GroupAddress),
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
                schema.user_delegations.c.user_id == schema.users.c.user_id
            ),
            uselist=False,
            lazy=True
        ),
        "delegation": relation(domain.User,
            primaryjoin=rdb.and_(
                (schema.user_delegations.c.delegation_id == 
                    schema.users.c.user_id),
                schema.users.c.active_p == "A"
            ),
            uselist=False,
            lazy=True
        ),
    }
)

# group subclasses

mapper(domain.Government,
    inherits=domain.Group,
    polymorphic_on=schema.groups.c.type,
    polymorphic_identity="government"
)

mapper(domain.Parliament, schema.parliaments,
    inherits=domain.Group,
    polymorphic_on=schema.groups.c.type,
    polymorphic_identity="parliament"
)

mapper(domain.PoliticalEntity, schema.political_parties,
    inherits=domain.Group,
    polymorphic_on=schema.groups.c.type,
    polymorphic_identity="political-entity"
)

mapper(domain.PoliticalParty,
    inherits=domain.PoliticalEntity,
    polymorphic_on=schema.groups.c.type,
    polymorphic_identity="political-party"
)

mapper(domain.PoliticalGroup,
    inherits=domain.PoliticalEntity,
    polymorphic_on=schema.groups.c.type,
    polymorphic_identity="political-group"
)

mapper(domain.Ministry,
    inherits=domain.Group,
    polymorphic_on=schema.groups.c.type,
    polymorphic_identity="ministry"
)

mapper(domain.Committee, schema.committees,
    inherits=domain.Group,
    polymorphic_on=schema.groups.c.type,
    polymorphic_identity="committee",
    properties={
        "committee_type": relation(domain.CommitteeType,
            uselist=False,
            lazy=False
        ),
    },
)

mapper(domain.Office, schema.offices,
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
            primaryjoin=rdb.and_(schema.user_group_memberships.c.user_id ==
                schema.users.c.user_id),
            uselist=False,
            lazy=False),
        "group":relation(domain.Group,
            primaryjoin=(schema.user_group_memberships.c.group_id ==
                schema.groups.c.group_id),
            uselist=False,
            lazy=True),
        "replaced":relation(domain.GroupMembership,
            primaryjoin=(schema.user_group_memberships.c.replaced_id ==
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
        "constituency": relation(domain.Constituency,
            primaryjoin=(schema.parliament_memberships.c.constituency_id ==
                            schema.constituencies.c.constituency_id),
            uselist=False,
            lazy=False),
        "constituency_id": [schema.parliament_memberships.c.constituency_id],
        "province": relation(domain.Province,
            primaryjoin=(schema.parliament_memberships.c.province_id ==
                            schema.provinces.c.province_id),
            uselist=False,
            lazy=False),
        "province_id": [schema.parliament_memberships.c.province_id],
        "region": relation(domain.Region,
            primaryjoin=(schema.parliament_memberships.c.region_id ==
                            schema.regions.c.region_id),
            uselist=False,
            lazy=False),
        "region_id": [schema.parliament_memberships.c.region_id],
        "party": relation(domain.PoliticalParty,
            primaryjoin=(schema.parliament_memberships.c.party_id ==
                            schema.political_parties.c.party_id),
            uselist=False,
            lazy=False),
        "party_id": [schema.parliament_memberships.c.party_id],
        "start_date": column_property(
            schema.user_group_memberships.c.start_date.label("start_date")),
        "end_date": column_property(
            schema.user_group_memberships.c.end_date.label("end_date")),
    },
    polymorphic_on=schema.user_group_memberships.c.membership_type,
    polymorphic_identity="parliamentmember",
)

mapper(domain.Minister,
    inherits=domain.GroupMembership,
    polymorphic_on=schema.user_group_memberships.c.membership_type,
    polymorphic_identity="minister",
)

mapper(domain.CommitteeMember,
    inherits=domain.GroupMembership,
    polymorphic_on=schema.user_group_memberships.c.membership_type,
    polymorphic_identity="committeemember",
)

mapper(domain.PartyMember,
    inherits=domain.GroupMembership,
    polymorphic_on=schema.user_group_memberships.c.membership_type,
    polymorphic_identity="partymember",
)

mapper(domain.OfficeMember,
    inherits=domain.GroupMembership,
    polymorphic_on=schema.user_group_memberships.c.membership_type,
    polymorphic_identity="officemember",
)

# staff assigned to a group (committee, ...)

mapper(domain.CommitteeStaff,
    inherits=domain.GroupMembership,
    polymorphic_on=schema.user_group_memberships.c.membership_type,
    polymorphic_identity="committeestaff",
)

mapper(domain.ParliamentSession, schema.parliament_sessions)
mapper(domain.GroupSitting, schema.sittings,
    properties={
        "sitting_type": relation(domain.SittingType, uselist=False),
        "group": relation(domain.Group,
            primaryjoin=schema.sittings.c.group_id == schema.groups.c.group_id,
            uselist=False,
            lazy=True
        ),
        "start_date": column_property(
            schema.sittings.c.start_date.label("start_date")
        ),
        "end_date": column_property(
            schema.sittings.c.end_date.label("end_date")
        ),
        "item_schedule": relation(domain.ItemSchedule,
            order_by=schema.items_schedule.c.planned_order
        ),
        "venue": relation(domain.Venue)
    }
)

mapper(domain.ResourceType, schema.resource_types)
mapper(domain.Resource, schema.resources)
mapper(domain.ResourceBooking, schema.resourcebookings)

mapper(domain.Venue, schema.venues)

##############################
# Parliamentary Items

mapper(domain.ParliamentaryItem, schema.parliamentary_items,
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="item",
    properties={
        "owner": relation(domain.User,
            primaryjoin=rdb.and_(schema.parliamentary_items.c.owner_id ==
                schema.users.c.user_id),
            uselist=False,
            lazy=False),
        "consignatories": relation(domain.User,
            secondary=schema.consignatories),
        "attached_files": relation(domain.AttachedFile)
    }
)

mapper(domain.Heading,
    inherits=domain.ParliamentaryItem,
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="heading"
)

mapper(domain.Question, schema.questions,
    inherits=domain.ParliamentaryItem,
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="question",
    properties={
        "changes":relation(domain.QuestionChange, 
            backref="origin",
            cascade="all, delete-orphan", 
            passive_deletes=False
        ),
        "ministry": relation(domain.Ministry, lazy=False, join_depth=2),
    }
)

mapper(domain.QuestionChange, schema.question_changes)
mapper(domain.QuestionVersion, schema.question_versions,
    properties={
        "change": relation(domain.QuestionChange, uselist=False),
        "head": relation(domain.Question, uselist=False),
        "attached_files": relation(domain.AttachedFileVersion,
            primaryjoin=rdb.and_(
                schema.question_versions.c.content_id ==
                    schema.attached_file_versions.c.item_id,
                schema.question_versions.c.version_id ==
                    schema.attached_file_versions.c.file_version_id
            ),
            foreign_keys=[schema.attached_file_versions.c.item_id,
                schema.attached_file_versions.c.file_version_id
            ]
        ),
    }
)

mapper(domain.Motion, schema.motions,
    inherits=domain.ParliamentaryItem,
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="motion",
    properties={
        "changes": relation(domain.MotionChange, 
            backref="origin",
            cascade="all, delete-orphan", 
            passive_deletes=False
        ), 
    }
)

mapper(domain.MotionChange, schema.motion_changes)
mapper(domain.MotionVersion, schema.motion_versions,
    properties={
        "change": relation(domain.MotionChange, uselist=False),
        "head": relation(domain.Motion, uselist=False),
        "attached_files": relation(domain.AttachedFileVersion,
            primaryjoin=rdb.and_(
                schema.motion_versions.c.content_id ==
                    schema.attached_file_versions.c.item_id,
                schema.motion_versions.c.version_id ==
                    schema.attached_file_versions.c.file_version_id
            ),
            foreign_keys=[
                schema.attached_file_versions.c.item_id,
                schema.attached_file_versions.c.file_version_id
            ]
        ), 
    }
)

mapper(domain.Bill, schema.bills,
    inherits=domain.ParliamentaryItem,
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="bill",
    properties={
        "changes": relation(domain.BillChange, 
            backref="origin",
            cascade="all, delete-orphan", 
            passive_deletes=False
        )
    }
)
mapper(domain.BillChange, schema.bill_changes)
mapper(domain.BillVersion, schema.bill_versions,
    properties={
        "change": relation(domain.BillChange, uselist=False),
        "head": relation(domain.Bill, uselist=False),
        "attached_files": relation(domain.AttachedFileVersion,
            primaryjoin=rdb.and_(
                schema.bill_versions.c.content_id ==
                    schema.attached_file_versions.c.item_id,
                schema.bill_versions.c.version_id ==
                    schema.attached_file_versions.c.file_version_id
            ),
            foreign_keys=[
                schema.attached_file_versions.c.item_id,
                schema.attached_file_versions.c.file_version_id
            ]
        ), 
    }
)

mapper(domain.EventItem, schema.event_items,
    inherits=domain.ParliamentaryItem,
    inherit_condition=(
        schema.event_items.c.event_item_id ==
            schema.parliamentary_items.c.parliamentary_item_id
    ),
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="event"
)

mapper(domain.AgendaItem, schema.agenda_items,
    inherits=domain.ParliamentaryItem,
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="agendaitem",
    properties={
        "changes": relation(domain.AgendaItemChange,
            backref="origin",
            cascade="all, delete-orphan",
            passive_deletes=False
        ),
        "group": relation(domain.Group,
            primaryjoin=(
                schema.agenda_items.c.group_id == schema.groups.c.group_id),
            backref="agenda_items",
            lazy=False,
            uselist=False
        )
    }
)
mapper(domain.AgendaItemChange, schema.agenda_item_changes)
mapper(domain.AgendaItemVersion, schema.agenda_item_versions,
    properties={
        "change": relation(domain.AgendaItemChange, uselist=False),
        "head": relation(domain.AgendaItem, uselist=False),
        "attached_files": relation(domain.AttachedFileVersion,
            primaryjoin=rdb.and_(
                schema.agenda_item_versions.c.content_id ==
                    schema.attached_file_versions.c.item_id,
                schema.agenda_item_versions.c.version_id ==
                    schema.attached_file_versions.c.file_version_id
            ),
            foreign_keys=[
                schema.attached_file_versions.c.item_id,
                schema.attached_file_versions.c.file_version_id
            ]
        ), 
    }
)

mapper(domain.TabledDocument, schema.tabled_documents,
    inherits=domain.ParliamentaryItem,
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="tableddocument",
    properties={
        "changes": relation(domain.TabledDocumentChange, 
            backref="origin",
            cascade="all, delete-orphan", 
            passive_deletes=False
        ),
    }
)

mapper(domain.TabledDocumentChange, schema.tabled_document_changes)
mapper(domain.TabledDocumentVersion, schema.tabled_document_versions,
    properties={
        "change": relation(domain.TabledDocumentChange, uselist=False),
        "head": relation(domain.TabledDocument, uselist=False),
        "attached_files": relation(domain.AttachedFileVersion,
            primaryjoin=rdb.and_(
                schema.tabled_document_versions.c.content_id ==
                    schema.attached_file_versions.c.item_id,
                schema.tabled_document_versions.c.version_id ==
                    schema.attached_file_versions.c.file_version_id
            ),
            foreign_keys=[
                schema.attached_file_versions.c.item_id,
                schema.attached_file_versions.c.file_version_id
            ]
        ), 
    }
)

mapper(domain.AttachedFile, schema.attached_files,
    properties={
        "changes": relation(domain.AttachedFileChange, 
            backref="origin",
            cascade="all, delete-orphan", 
            passive_deletes=False
        ),
    }
)
mapper(domain.AttachedFileChange, schema.attached_file_changes)
mapper(domain.AttachedFileVersion, schema.attached_file_versions,
    properties={
        "change": relation(domain.AttachedFileChange, uselist=False),
        "head": relation(domain.AttachedFile, uselist=False)
    }
)

#Items scheduled for a sitting expressed as a relation
# to their item schedule

mapper(domain.ItemSchedule, schema.items_schedule,
    properties={
        "item": relation(
            domain.ParliamentaryItem,
            uselist=False
        ),
        "discussion": relation(
            domain.ScheduledItemDiscussion,
            uselist=False,
            cascade="all, delete-orphan"
        ),
        "sitting": relation(domain.GroupSitting, uselist=False),
    }
)

mapper(domain.ScheduledItemDiscussion, schema.item_discussion)

# items scheduled for a sitting
# expressed as a join between item and schedule

mapper(domain.Consignatory, schema.consignatories,
    properties={
        "item": relation(domain.ParliamentaryItem, uselist=False),
        "user": relation(domain.User, uselist=False)
    }
)

mapper(domain.BillType, schema.bill_types)
#mapper(domain.DocumentSource, schema.document_sources)

mapper(domain.HoliDay, schema.holidays)

######################
#

mapper(domain.Constituency, schema.constituencies)
mapper(domain.Province, schema.provinces)
mapper(domain.Region, schema.regions)
mapper(domain.Country, schema.countries)
mapper(domain.ConstituencyDetail, schema.constituency_details,
    properties={
        "constituency": relation(domain.Constituency,
            uselist=False,
            lazy=True,
            backref="details"
        ),
    }
)
mapper(domain.CommitteeType, schema.committee_type)
mapper(domain.SittingType, schema.sitting_type)

mapper(domain.GroupSittingAttendance, schema.sitting_attendance,
    properties={
        "user": relation(domain.User, uselist=False, lazy=False),
        "attendance_type": relation(domain.AttendanceType, 
            uselist=False,
            lazy=False
        ),
        "sitting": relation(domain.GroupSitting, uselist=False, lazy=False),
    }
)
mapper(domain.AttendanceType, schema.attendance_type)
mapper(domain.MemberTitle, schema.user_role_types)
mapper(domain.MemberRoleTitle, schema.role_titles,
    properties={
        "title_name": relation(domain.MemberTitle, uselist=False, lazy=False),
    }
)

mapper(domain.AddressType, schema.address_types)
mapper(domain.UserAddress, schema.user_addresses,
    properties={
        "address_type": relation(domain.AddressType, uselist=False, lazy=False),
    },
)
mapper(domain.GroupAddress, schema.group_addresses,
    properties={
        "address_type": relation(domain.AddressType, uselist=False, lazy=False),
    },
)

mapper(domain.GroupItemAssignment, schema.group_item_assignments,
    properties={
        "group": relation(domain.Group,
            primaryjoin=(schema.group_item_assignments.c.group_id ==
                    schema.groups.c.group_id),
            backref="group_assignments",
            lazy=True,
            uselist=False
        ),
        "item": relation(domain.ParliamentaryItem, 
            backref="item_assignments",
            uselist=False
        ),
    }
)
mapper(domain.ItemGroupItemAssignment, schema.group_item_assignments,
    inherits=domain.GroupItemAssignment
)
mapper(domain.GroupGroupItemAssignment, schema.group_item_assignments,
    inherits=domain.GroupItemAssignment
)

mapper(domain.Report, schema.reports,
    inherits=domain.ParliamentaryItem,
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="report"
)

mapper(domain.SittingReport, schema.sitting_reports,
    properties={
        "sitting": relation(domain.GroupSitting,
            backref="reports",
            lazy=True,
            uselist=False
        ),
        "report": relation(domain.Report,
            backref="sittings",
            lazy=True,
            uselist=False
        ),
    }
)

mapper(domain.Report4Sitting, schema.sitting_reports,
    inherits=domain.Report
)

mapper(domain.ObjectTranslation, schema.translations)

