
import sqlalchemy as rdb
from sqlalchemy.orm import mapper, relation, column_property, backref

import schema
import domain

def changes_relation(change_class):
    return relation(change_class,
        backref="origin",
        lazy=False,
        cascade="all, delete-orphan",
        passive_deletes=False
    )

def changes_properties(change_table):
    return {
        "user": relation(domain.User,
            primaryjoin=(
                change_table.c.user_id == schema.users.c.user_id
            ),
            uselist=False,
            lazy=True,
        ),
    }
def versions_properties(item_class, change_class, versions_table):
    return {
        "change": relation(change_class, uselist=False),
        "head": relation(item_class, uselist=False),
        "attached_files": relation(domain.AttachedFileVersion,
            primaryjoin=rdb.and_(
                versions_table.c.content_id ==
                    schema.attached_file_versions.c.item_id,
                versions_table.c.version_id ==
                    schema.attached_file_versions.c.file_version_id
            ),
            foreign_keys=[
                schema.attached_file_versions.c.item_id,
                schema.attached_file_versions.c.file_version_id
            ]
        ),
    }

#user address types
mapper(domain.PostalAddressType, schema.postal_address_types)

# Users
# general representation of a person
mapper(domain.User, schema.users,
    properties={
        "user_addresses": relation(domain.UserAddress),
        "subscriptions": relation(domain.ParliamentaryItem,
            secondary=schema.users_parliamentary_items
        ),
    }
)

mapper(domain.AdminUser, schema.admin_users,
    properties = {
        "user":relation(domain.User)
    }
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

mapper(domain.CommitteeTypeStatus, schema.committee_type_status)
mapper(domain.CommitteeType, schema.committee_type,
    properties={
        "committee_type_status": relation(domain.CommitteeTypeStatus,
            uselist=False, lazy=False
        )
    }
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
        "member_titles":relation(domain.MemberTitle)
    },
    polymorphic_on=schema.user_group_memberships.c.membership_type,
    polymorphic_identity="member",
)

mapper(domain.MemberElectionType, schema.member_election_types)

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
        "member_election_type": relation(domain.MemberElectionType, uselist=False,
            lazy=False
        ),
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
mapper(domain.GroupSitting, schema.group_sittings,
    properties={
        "group_sitting_type": relation(domain.GroupSittingType, uselist=False),
        "group": relation(domain.Group,
            primaryjoin=schema.group_sittings.c.group_id == schema.groups.c.group_id,
            uselist=False,
            lazy=True
        ),
        "start_date": column_property(
            schema.group_sittings.c.start_date.label("start_date")
        ),
        "end_date": column_property(
            schema.group_sittings.c.end_date.label("end_date")
        ),
        "item_schedule": relation(domain.ItemSchedule,
            order_by=schema.item_schedules.c.planned_order
        ),
        "venue": relation(domain.Venue),
        "changes": changes_relation(domain.GroupSittingChange),
    }
)

mapper(domain.GroupSittingChange, schema.group_sitting_changes,
         properties=changes_properties(schema.group_sitting_changes)
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
        "cosignatories": relation(domain.User,
            secondary=schema.cosignatories),
        "attached_files": relation(domain.AttachedFile)
    }
)

mapper(domain.Heading,
    inherits=domain.ParliamentaryItem,
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="heading"
)
mapper(domain.QuestionType, schema.question_types)
mapper(domain.ResponseType, schema.response_types)
mapper(domain.Question, schema.questions,
    inherits=domain.ParliamentaryItem,
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="question",
    properties={
        "changes": changes_relation(domain.QuestionChange),
        "ministry": relation(domain.Ministry, lazy=False, join_depth=2),
        "question_type": relation(domain.QuestionType, uselist=False,
            lazy=False
        ),
        "response_type": relation(domain.ResponseType, uselist=False,
            lazy=False
        ),
    }
)

mapper(domain.QuestionChange, schema.question_changes,
    properties=changes_properties(schema.question_changes)        
)
mapper(domain.QuestionVersion, schema.question_versions,
    properties=versions_properties(domain.Question, domain.QuestionChange,
        schema.question_versions)
)

mapper(domain.Motion, schema.motions,
    inherits=domain.ParliamentaryItem,
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="motion",
    properties={
        "changes": changes_relation(domain.MotionChange),
    }
)

mapper(domain.MotionChange, schema.motion_changes,
    properties=changes_properties(schema.motion_changes)
)
mapper(domain.MotionVersion, schema.motion_versions,
    properties=versions_properties(domain.Motion, domain.MotionChange,
        schema.motion_versions)
)

mapper(domain.Bill, schema.bills,
    inherits=domain.ParliamentaryItem,
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="bill",
    properties={
        "changes": changes_relation(domain.BillChange),
    }
)
mapper(domain.BillChange, schema.bill_changes,
    properties=changes_properties(schema.bill_changes)
)
mapper(domain.BillVersion, schema.bill_versions,
    properties=versions_properties(domain.Bill, domain.BillChange,
        schema.bill_versions)
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
        "changes": changes_relation(domain.AgendaItemChange),
        "group": relation(domain.Group,
            primaryjoin=(
                schema.agenda_items.c.group_id == schema.groups.c.group_id),
            backref="agenda_items",
            lazy=False,
            uselist=False
        )
    }
)
mapper(domain.AgendaItemChange, schema.agenda_item_changes,
    properties=changes_properties(schema.agenda_item_changes)
)
mapper(domain.AgendaItemVersion, schema.agenda_item_versions,
    properties=versions_properties(domain.AgendaItem, domain.AgendaItemChange,
        schema.agenda_item_versions)
)

mapper(domain.TabledDocument, schema.tabled_documents,
    inherits=domain.ParliamentaryItem,
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="tableddocument",
    properties={
        "changes": changes_relation(domain.TabledDocumentChange),
    }
)

mapper(domain.TabledDocumentChange, schema.tabled_document_changes,
    properties=changes_properties(schema.tabled_document_changes)
)
mapper(domain.TabledDocumentVersion, schema.tabled_document_versions,
    properties=versions_properties(domain.TabledDocument,
        domain.TabledDocumentChange, schema.tabled_document_versions)
)

mapper(domain.AttachedFileType, schema.attached_file_types)

mapper(domain.AttachedFile, schema.attached_files,
    properties={
        "changes": changes_relation(domain.AttachedFileChange),
        "type": relation(domain.AttachedFileType, uselist=False)
    }
)
mapper(domain.AttachedFileChange, schema.attached_file_changes,
    properties=changes_properties(schema.attached_file_changes)
)
mapper(domain.AttachedFileVersion, schema.attached_file_versions,
    properties={
        "change": relation(domain.AttachedFileChange, uselist=False),
        "head": relation(domain.AttachedFile, uselist=False),
    }
)

#Items scheduled for a sitting expressed as a relation
# to their item schedule

mapper(domain.ItemSchedule, schema.item_schedules,
    properties={
        "item": relation(
            domain.ParliamentaryItem,
            uselist=False
        ),
        "discussion": relation(
            domain.ItemScheduleDiscussion,
            uselist=False,
            cascade="all, delete-orphan"
        ),
        "sitting": relation(domain.GroupSitting, uselist=False),
    }
)

mapper(domain.ItemScheduleDiscussion, schema.item_schedule_discussions)

# items scheduled for a sitting
# expressed as a join between item and schedule

mapper(domain.Cosignatory, schema.cosignatories,
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
mapper(domain.GroupSittingType, schema.group_sitting_types)

mapper(domain.GroupSittingAttendance, schema.group_sitting_attendance,
    properties={
        "user": relation(domain.User, uselist=False, lazy=False),
        "attendance_type": relation(domain.AttendanceType,
            uselist=False,
            lazy=False
        ),
        "sitting": relation(domain.GroupSitting, uselist=False, lazy=False),
    }
)
mapper(domain.AttendanceType, schema.attendance_types)
mapper(domain.TitleType, schema.title_types,
    properties={ "group": relation(domain.Group, uselist=False, lazy=False) }
)
mapper(domain.MemberTitle, schema.member_titles,
    properties={
        "title_type": relation(domain.TitleType, uselist=False, lazy=False),
        "member": relation(domain.GroupMembership, uselist=False, lazy=False),
    }
)

mapper(domain.AddressType, schema.address_types)
mapper(domain.UserAddress, schema.user_addresses,
    properties={
        "address_type": relation(domain.AddressType, uselist=False, lazy=False),
        "postal_address_type": relation(domain.PostalAddressType, uselist=False,
            lazy=False
        ),
        "country": relation(domain.Country, uselist=False, lazy=False),
    },
)
mapper(domain.GroupAddress, schema.group_addresses,
    properties={
        "address_type": relation(domain.AddressType, uselist=False, lazy=False),
        "postal_address_type": relation(domain.PostalAddressType, 
            uselist=False, lazy=False
        ),
        "country": relation(domain.Country, uselist=False, lazy=False),
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
            backref="group_sittings",
            lazy=True,
            uselist=False
        ),
    }
)

mapper(domain.Report4Sitting, schema.sitting_reports,
    inherits=domain.Report
)

mapper(domain.ObjectTranslation, schema.translations)

