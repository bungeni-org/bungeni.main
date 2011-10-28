# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""The Bungeni object domain mappings

$Id$
"""
log = __import__("logging").getLogger("bungeni.models.orm")

import sqlalchemy as rdb
from sqlalchemy.orm import mapper, class_mapper, relation, column_property, \
    backref
from bungeni.alchemist.traversal import one2many

import schema
import domain
import interfaces

# !+PARAMETRIZABLE_DOCTYPES
def configurable_mappings(kls):
    """Add mappings, as per configured features for a domain type.
    
    Executed on adapters.load_workflow()
    """
    name = kls.__name__
    # auditable, determine properties and set mapper for change class/table
    if interfaces.IAuditable.implementedBy(kls):
        change_kls = getattr(domain, "%sChange" % (name))
        change_tbl = getattr(schema, "%s_changes" % (schema.un_camel(name)))
        def changes_properties(change_tbl):
            return {
                "user": relation(domain.User,
                    primaryjoin=(change_tbl.c.user_id == schema.users.c.user_id),
                    uselist=False,
                    lazy=True
                ),
            }
        mapper(change_kls, change_tbl, 
            properties=changes_properties(change_tbl)
        )
    # versionable, determine properties and set mapper for version class/table
    if interfaces.IVersionable.implementedBy(kls):
        assert change_kls, "May not be IVersionable and not IAuditable"
        version_kls = getattr(domain, "%sVersion" % (name))
        version_tbl = getattr(schema, "%s_versions" % (schema.un_camel(name)))
        def versions_properties(item_class, change_class, versions_table):
            props = {
                "change": relation(change_class, uselist=False),
                "head": relation(item_class, uselist=False)
            }
            return props
        mapper(version_kls, version_tbl,
            properties=versions_properties(kls, change_kls, version_tbl)
        )
    # attachmentable, add related properties to version class/table 
    if interfaces.IAttachmentable.implementedBy(kls):
        # !+ current constrain
        assert version_kls, "May not be IAttachmentable and not IVersionable"
        class_mapper(version_kls).add_property("attached_files",
            relation(domain.AttachedFileVersion,
                primaryjoin=rdb.and_(
                    version_tbl.c.content_id ==
                        schema.attached_file_versions.c.item_id,
                    version_tbl.c.version_id ==
                        schema.attached_file_versions.c.file_version_id
                ),
                foreign_keys=[
                    schema.attached_file_versions.c.item_id,
                    schema.attached_file_versions.c.file_version_id
                ]
            )
        )
    # finally, add any properties to the master kls itself
    def mapper_add_configurable_properties(kls):
        kls_mapper = class_mapper(kls)
        def configurable_properties(kls, mapper_properties):
            """Add properties, as per configured features for a domain type.
            """
            # auditable
            if interfaces.IAuditable.implementedBy(kls):
                change_kls = getattr(domain, "%sChange" % (name))
                mapper_properties["changes"] = relation(change_kls,
                    backref="origin", 
                    lazy=True,
                    cascade="all, delete-orphan",
                    passive_deletes=False
                )
            # versionable
            if interfaces.IVersionable.implementedBy(kls):
                kls.versions = one2many("versions",
                    "bungeni.models.domain.%sVersionContainer" % (name),
                    "content_id")
            # attachmentable
            if interfaces.IAttachmentable.implementedBy(kls):
                pass # nothing to do
            return mapper_properties
        for key, prop in configurable_properties(kls, {}).items():
            kls_mapper.add_property(key, prop)
    #
    mapper_add_configurable_properties(kls)

# !+/PARAMETRIZABLE_DOCTYPES

#user address types
#!+TYPES_CUSTOM mapper(domain.PostalAddressType, schema.postal_address_types)

# Users
# general representation of a person
mapper(domain.User, schema.users,
    properties={
        "user_addresses": relation(domain.UserAddress,
            # !+HEAD_DOCUMENT_ITEM(mr, sep-2011) standardize name
            backref=backref("item", remote_side=schema.users.c.user_id)
        ),
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

# The document that the user is being currently editing
mapper(domain.CurrentlyEditingDocument, schema.currently_editing_document,
    properties = {
        "user": relation(domain.User, uselist=False),
        "document": relation(domain.ParliamentaryItem, uselist=False)
    }
)

# Groups

mapper(domain.Group, schema.groups,
    primary_key=[schema.groups.c.group_id],
    properties={
        "members": relation(domain.GroupMembership),
        # !+GROUP_PRINCIPAL_ID(ah,sep-2011) - removing group_principal_id as 
        # orm property, this is now on the schema.
        #"group_principal_id": column_property(
        #    ("group." + schema.groups.c.type + "." +
        #     rdb.cast(schema.groups.c.group_id, rdb.String)
        #    ).label("group_principal_id")
        #),
        "contained_groups": relation(domain.Group,
            backref=backref("parent_group",
                remote_side=schema.groups.c.group_id)
        ),
        "group_addresses": relation(domain.GroupAddress,
            # !+HEAD_DOCUMENT_ITEM(mr, sep-2011) standardize name
            backref=backref("item", remote_side=schema.groups.c.group_id)
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

''' !+TYPES_CUSTOM
mapper(domain.CommitteeTypeStatus, schema.committee_type_status)
mapper(domain.CommitteeType, schema.committee_type,
    properties={
        "committee_type_status": relation(domain.CommitteeTypeStatus,
            uselist=False, 
            lazy=False
        )
    }
)
'''
mapper(domain.Committee, schema.committees,
    inherits=domain.Group,
    polymorphic_on=schema.groups.c.type,
    polymorphic_identity="committee",
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
        # !+NAMING(mr, jul-2011)
        "itemsignatories": relation(domain.User, secondary=schema.signatories),
        "attached_files": relation(domain.AttachedFile,
            # !+HEAD_DOCUMENT_ITEM(mr, sep-2011) standardize name, "head", 
            # "document", "item"
            backref=backref("item",
                remote_side=schema.parliamentary_items.c.parliamentary_item_id)
        ),
        "event_item": relation(domain.EventItem,
            primaryjoin=rdb.and_(
                schema.parliamentary_items.c.parliamentary_item_id ==
                    schema.event_items.c.item_id),
            uselist=False,
            # !+HEAD_DOCUMENT_ITEM(mr, sep-2011) standardize name
            backref=backref("item",
                remote_side=schema.parliamentary_items.c.parliamentary_item_id),
        ),
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
        "ministry": relation(domain.Ministry, lazy=False, join_depth=2),
        "question_type": relation(domain.QuestionType, uselist=False,
            lazy=False
        ),
        "response_type": relation(domain.ResponseType, uselist=False,
            lazy=False
        ),
    }
)

mapper(domain.Motion, schema.motions,
    inherits=domain.ParliamentaryItem,
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="motion",
    properties={}
)

mapper(domain.Bill, schema.bills,
    inherits=domain.ParliamentaryItem,
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="bill",
    properties={}
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
        "group": relation(domain.Group,
            primaryjoin=(
                schema.agenda_items.c.group_id == schema.groups.c.group_id),
            backref="agenda_items",
            lazy=False,
            uselist=False
        )
    }
)

mapper(domain.TabledDocument, schema.tabled_documents,
    inherits=domain.ParliamentaryItem,
    polymorphic_on=schema.parliamentary_items.c.type,
    polymorphic_identity="tableddocument",
    properties={}
)

mapper(domain.AttachedFileType, schema.attached_file_types)
mapper(domain.AttachedFile, schema.attached_files,
    properties={
        "type": relation(domain.AttachedFileType, uselist=False)
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

mapper(domain.Signatory, schema.signatories,
    properties={
        "item": relation(domain.ParliamentaryItem, uselist=False),
        "user": relation(domain.User, uselist=False),
    }
)

#!+TYPES_CUSTOM mapper(domain.BillType, schema.bill_types)
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

#!+TYPES_CUSTOM mapper(domain.AddressType, schema.address_types)
mapper(domain.UserAddress, schema.user_addresses,
    properties={
        "country": relation(domain.Country, uselist=False, lazy=False),
    },
)
mapper(domain.GroupAddress, schema.group_addresses,
    properties={
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

