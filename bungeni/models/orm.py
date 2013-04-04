
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

import schema
import domain
from bungeni.utils.naming import polymorphic_identity


mapper(domain.Principal, schema.principal,
    # principal should only be created as user or group
    #polymorphic_identity=polymorphic_identity(domain.Principal),
    polymorphic_on=schema.principal.c.type, # polymorphic discriminator
    properties={}
)


# Users
# general representation of a person
mapper(domain.User, schema.user,
    inherits=domain.Principal,
    polymorphic_identity=polymorphic_identity(domain.User),
    properties={
        # !+ADDRESS naming, use addresses
        "user_addresses": relation(domain.UserAddress,
            # !+HEAD_DOCUMENT_ITEM(mr, sep-2011) standardize name
            backref=backref("head", remote_side=schema.principal.c.principal_id)
        ),
        "subscriptions": relation(domain.Doc,
            secondary=schema.user_doc
        ),
    }
)

mapper(domain.UserSubscription, schema.user_doc)

mapper(domain.AdminUser, schema.admin_user,
    properties={
        "user": relation(domain.User)
    }
)

# The document that the user is being currently editing
mapper(domain.CurrentlyEditingDocument, schema.currently_editing_document,
    properties={
        "user": relation(domain.User, uselist=False),
        "document": relation(domain.Doc, uselist=False), # !+rename "doc"
    }
)

# Hash for password restore link
mapper(domain.PasswordRestoreLink, schema.password_restore_link,
    properties={
        "user": relation(domain.User, uselist=False),
    }
)

# Groups

mapper(domain.Group, schema.group,
    inherits=domain.Principal,
    polymorphic_identity=polymorphic_identity(domain.Group),
    properties={
        "members": relation(domain.GroupMembership),
        "titletypes": relation(domain.TitleType),
        "contained_groups": relation(domain.Group,
            primaryjoin=rdb.and_(
                schema.group.c.group_id == schema.group.c.parent_group_id
            ),
            backref=backref("parent_group",
                remote_side=schema.group.c.group_id)
        ),
        # !+ADDRESS naming, use addresses
        "group_addresses": relation(domain.GroupAddress,
            # !+HEAD_DOCUMENT_ITEM(mr, sep-2011) standardize name
            backref=backref("head", remote_side=schema.principal.c.principal_id)
        ),
        # "keywords": relation(domain.Keyword, secondary=schema.group_keywords)
    },
)

# Keywords for groups
#mapper(domain.Keyword, schema.keywords,
#    properties = {
#       "group": relation(domain.Group, 
#            secondary=schema.group_keyword, backref="keyword"
#       ),
#    }
#)

# delegate rights to act on behalf of a user
mapper(domain.UserDelegation, schema.user_delegation,
    properties={
        "user": relation(domain.User,
            primaryjoin=rdb.and_(
                schema.user_delegation.c.user_id == schema.user.c.user_id
            ),
            uselist=False,
            lazy=True
        ),
        "delegation": relation(domain.User,
            primaryjoin=rdb.and_(
                (schema.user_delegation.c.delegation_id ==
                    schema.user.c.user_id),
                schema.user.c.active_p == "A"
            ),
            uselist=False,
            lazy=True
        ),
    }
)

mapper(domain.GroupDocumentAssignment, schema.group_document_assignment,
    properties={
        "group": relation(domain.Group,
            primaryjoin=schema.group_document_assignment.c.group_id ==
                schema.group.c.group_id,
            uselist=False,
            lazy=False),
    }
)

# group subclasses

mapper(domain.Government,
    inherits=domain.Group,
    polymorphic_identity=polymorphic_identity(domain.Government)
)

mapper(domain.Parliament, schema.parliament,
    inherits=domain.Group,
    polymorphic_identity=polymorphic_identity(domain.Parliament)
)

mapper(domain.PoliticalGroup, schema.political_group,
    inherits=domain.Group,
    polymorphic_identity=polymorphic_identity(domain.PoliticalGroup)
)

mapper(domain.Ministry,
    inherits=domain.Group,
    polymorphic_identity=polymorphic_identity(domain.Ministry)
)

mapper(domain.Committee, schema.committee,
    inherits=domain.Group,
    polymorphic_identity=polymorphic_identity(domain.Committee)
)

mapper(domain.JointCommittee,
    inherits=domain.Committee,
    polymorphic_identity=polymorphic_identity(domain.JointCommittee)
)

mapper(domain.Office,
    inherits=domain.Group,
    polymorphic_identity=polymorphic_identity(domain.Office)
)


# Ministers and Committee members are defined by their group membership in a 
# ministry or committee (group)

# we need to specify join clause for user explicitly because we have multiple fk
# to the user table.
mapper(domain.GroupMembership, schema.user_group_membership,
    polymorphic_identity=polymorphic_identity(domain.GroupMembership),
    polymorphic_on=schema.user_group_membership.c.membership_type,
    properties={
        "user": relation(domain.User,
            primaryjoin=rdb.and_(schema.user_group_membership.c.user_id ==
                schema.user.c.user_id),
            uselist=False,
            backref="group_membership",
            lazy=False),
        "group": relation(domain.Group,
            primaryjoin=(schema.user_group_membership.c.group_id ==
                schema.group.c.group_id),
            uselist=False,
            lazy=True),
        "replaced": relation(domain.GroupMembership,
            primaryjoin=(schema.user_group_membership.c.replaced_id ==
                schema.user_group_membership.c.membership_id),
            uselist=False,
            lazy=True),
        "sub_roles": relation(domain.GroupMembershipRole),
        "member_titles": relation(domain.MemberTitle)
    },
)
# !+HEAD_DOCUMENT_ITEM(mr, sep-2011) standardize name, "head", "document", "item"
domain.GroupMembership.head = domain.GroupMembership.user

mapper(domain.GroupMembershipRole, schema.group_membership_role,
    properties={
        "member": relation(domain.GroupMembership)
    }
)

# !+RENAME ParliamentMember
mapper(domain.MemberOfParliament, schema.parliament_membership,
    inherits=domain.GroupMembership,
    polymorphic_identity=polymorphic_identity(domain.MemberOfParliament),
    primary_key=[schema.user_group_membership.c.membership_id],
    properties={
        "start_date": column_property(
            schema.user_group_membership.c.start_date.label("start_date")),
        "end_date": column_property(
            schema.user_group_membership.c.end_date.label("end_date")),
    },
)

mapper(domain.Minister,
    inherits=domain.GroupMembership,
    polymorphic_identity=polymorphic_identity(domain.Minister)
)

mapper(domain.CommitteeMember,
    inherits=domain.GroupMembership,
    polymorphic_identity=polymorphic_identity(domain.CommitteeMember)
)

mapper(domain.PoliticalGroupMember,
    inherits=domain.GroupMembership,
    polymorphic_identity=polymorphic_identity(domain.PoliticalGroupMember)
)

mapper(domain.OfficeMember,
    inherits=domain.GroupMembership,
    polymorphic_identity=polymorphic_identity(domain.OfficeMember)
)

# staff assigned to a group (committee, ...)

mapper(domain.CommitteeStaff,
    inherits=domain.GroupMembership,
    polymorphic_identity=polymorphic_identity(domain.CommitteeStaff)
)

mapper(domain.Session, schema.session,
    properties={
        "group": relation(domain.Parliament, lazy=False),
    }
)

mapper(domain.AgendaTextRecord, schema.agenda_text_record)

mapper(domain.Sitting, schema.sitting,
    properties={
        "group": relation(domain.Group,
            primaryjoin=schema.sitting.c.group_id == schema.group.c.group_id,
            uselist=False,
            lazy=True
        ),
        "start_date": column_property(
            schema.sitting.c.start_date.label("start_date")
        ),
        "end_date": column_property(
            schema.sitting.c.end_date.label("end_date")
        ),
        "item_schedule": relation(domain.ItemSchedule,
            order_by=schema.item_schedule.c.real_order,
            cascade="all"
        ),
        "sa_attendance": relation(domain.SittingAttendance,
            cascade="all"
        ),
        "reports": relation(domain.SittingReport,
            cascade="all"
        ),
        "venue": relation(domain.Venue, lazy=False),
        "debate_record": relation(domain.DebateRecord, lazy=True)
    }
)


''' !+BookedResources
mapper(domain.ResourceType, schema.resource_types)
mapper(domain.Resource, schema.resources)
mapper(domain.ResourceBooking, schema.resourcebookings)
'''

mapper(domain.Venue, schema.venue)


# vertical properties

mapper(domain.vp.Text, schema.vp_text)
mapper(domain.vp.TranslatedText, schema.vp_translated_text)
mapper(domain.vp.Datetime, schema.vp_datetime)


# doc 

mapper(domain.Doc, schema.doc,
    polymorphic_on=schema.doc.c.type, # polymorphic discriminator
    polymorphic_identity=polymorphic_identity(domain.Doc),
    properties={
        "owner": relation(domain.User,
            primaryjoin=rdb.and_(schema.doc.c.owner_id ==
                schema.user.c.user_id),
            uselist=False,
            lazy=False),
        # !+AlchemistManagedContainer, X same as amc_X.values(), property @X?
        # !+ARCHETYPE_MAPPER(mr, apr-2012) keep this mapper property always 
        # present on predefined archetype mapper, or dynamically instrument it 
        # on each on mapper of each (sub-archetype) type having this feature?
        "item_signatories": relation(domain.Signatory, uselist=True,
            cascade="all"), #!+rename sa_signatories
        "attachments": relation(domain.Attachment, 
            cascade="all"), # !+ARCHETYPE_MAPPER
        "sa_events": relation(domain.Event, uselist=True, 
            cascade="all"), # !+ARCHETYPE_MAPPER
        # for sub parliamentary docs, non-null implies a sub doc
        #"head": relation(domain.Doc,
        #    uselist=False,
        #    lazy=True,
        #),
        "audits": relation(domain.DocAudit, # !+ARCHETYPE_MAPPER
            primaryjoin=rdb.and_(
                schema.doc.c.doc_id == schema.doc_audit.c.doc_id
            ),
            backref="audit_head",
            uselist=True,
            lazy=True,
            order_by=schema.doc_audit.c.audit_id.desc(),
            cascade="all",
            passive_deletes=False, # SA default
        ),
        "versions": relation(domain.DocVersion, # !+ARCHETYPE_MAPPER
            primaryjoin=rdb.and_(
                schema.doc.c.doc_id == schema.doc_audit.c.doc_id,
            ),
            secondary=schema.doc_audit,
            secondaryjoin=rdb.and_(
                schema.doc_audit.c.audit_id == schema.change.c.audit_id,
                # !+NO_INHERIT_VERSION needs this
                schema.change.c.action == "version",
            ),
            #!+backref: version.audit.audit_head
            uselist=True,
            lazy=True,
            order_by=schema.change.c.audit_id.desc(),
            viewonly=True,
        ),
        "group": relation(domain.Group,
            primaryjoin=schema.doc.c.group_id == schema.group.c.group_id,
            #backref="agenda_items",
            lazy=False,
            uselist=False,
        ),
        "group_assignment": relation(domain.GroupDocumentAssignment,
            primaryjoin=schema.doc.c.doc_id == schema.group_document_assignment.c.doc_id,
            lazy=False,
            uselist=True,
        )
    }
)


# audit

mapper(domain.Audit, schema.audit,
    polymorphic_on=schema.audit.c.audit_type, # polymorphic discriminator
    polymorphic_identity=polymorphic_identity(domain.Audit)
)
mapper(domain.Change, schema.change,
    # !+ always created with a concrete {type}_audit record
    #polymorphic_on=schema.change.c.action, # polymorphic discriminator
    #polymorphic_identity="*" !+
    properties={
        "audit": relation(domain.Audit,
            primaryjoin=rdb.and_(schema.change.c.audit_id ==
                schema.audit.c.audit_id),
            backref=backref("change", uselist=False),
            uselist=False,
            lazy=True,
        ),
        "user": relation(domain.User,
            primaryjoin=rdb.and_(schema.change.c.user_id ==
                schema.user.c.user_id),
            uselist=False,
            lazy=False
        ),
        "children": relation(domain.Change,
            primaryjoin=rdb.and_(
                schema.change.c.audit_id == schema.change_tree.c.parent_id,
            ),
            secondary=schema.change_tree,
            secondaryjoin=rdb.and_(
                schema.change_tree.c.child_id == schema.change.c.audit_id,
                # child.action == action, # !+constraint
            ),
            backref=backref("parent",
                uselist=False
            ),
            uselist=True,
            lazy=True,
        ),
    }
)
mapper(domain.ChangeTree, schema.change_tree)

''' !+NO_INHERIT_VERSION mapping domain.Version is actually unnecessary
#vm = mapper(domain.Version,
mapper(domain.Version,
    inherits=domain.Change,
    polymorphic_on=schema.change.c.action, # polymorphic discriminator
    polymorphic_identity=polymorphic_identity(domain.Version), #!+only concrete {type}_audit record are created
)
# !+polymorphic_identity_multi only allows a single value... e.g. if needed to 
# add a 2nd value such as "reversion" would not be able to -- but seems we 
# should be able to tweak the version mapper's polymorphic_map to allow 
# multiple values for polymorphic_identity (but does not work anyway 
# attachment.versions does not pick up reversions):
#vm.polymorphic_map["reversion"] = vm.polymorphic_map["version"]
#del vm
'''

mapper(domain.DocAudit, schema.doc_audit,
    inherits=domain.Audit,
    polymorphic_identity=polymorphic_identity(domain.Doc) # on head class
)

mapper(domain.DocVersion,
    # !+NO_INHERIT_VERSION(mr, apr-2012) inheriting from domain.Version will 
    # always give an empty doc.versions / attachment.versions / ... lists !
    inherits=domain.Change,
    # !+ messes up DocVersions... will be typed as AttachmentVersion!
    #polymorphic_identity="version", #!+polymorphic_identity(domain.Version),
    properties={
        # !+ only for versionable doc sub-types that also support "attachment"
        # !+ rename: attachment_versions
        "attachments": relation(domain.AttachmentVersion, # !+ARCHETYPE_MAPPER
            primaryjoin=rdb.and_(
                schema.change.c.audit_id == schema.change_tree.c.parent_id,
            ),
            secondary=schema.change_tree,
            secondaryjoin=rdb.and_(
                schema.change_tree.c.child_id == schema.change.c.audit_id,
                schema.change.c.audit_id == schema.audit.c.audit_id,
                schema.audit.c.audit_type == polymorphic_identity(domain.Attachment),
            ),
            #backref=backref("parent", 
            #    uselist=False
            #),
            uselist=True,
            lazy=True,
            order_by=schema.change.c.audit_id.desc(),
            viewonly=True,
        ),
        #!+eventable items supporting feature "event":
        #"sa_events": relation(domain.Event, uselist=True),
    },
)


mapper(domain.AgendaItem,
    inherits=domain.Doc,
    polymorphic_identity=polymorphic_identity(domain.AgendaItem),
)


mapper(domain.Event,
    inherits=domain.Doc,
    polymorphic_identity=polymorphic_identity(domain.Event),
    properties={
        "head": relation(domain.Doc,
            primaryjoin=rdb.and_(
               schema.doc.c.head_id == schema.doc.c.doc_id,
               # !+unnecessary (explicit constraint of no events on events)
               schema.doc.c.type != polymorphic_identity(domain.Event),
            ),
            remote_side=schema.doc.c.doc_id,
            uselist=False,
            lazy=True,
        ),
    },
)
#!+EVENTS on parliamentary documents:
# - behave also "like" a parliamentary document
# - AgendaItem should NOT support Event?
# - Event should NOT support Event

mapper(domain.Attachment, schema.attachment,
    properties={
        "head": relation(domain.Doc,
            primaryjoin=(schema.attachment.c.head_id == schema.doc.c.doc_id),
            uselist=False,
            lazy=False,
        ),
        "audits": relation(domain.AttachmentAudit, # !+ARCHETYPE_MAPPER
            primaryjoin=rdb.and_(schema.attachment.c.attachment_id == 
                schema.attachment_audit.c.attachment_id),
            backref="audit_head",
            uselist=True,
            lazy=True,
            order_by=schema.attachment_audit.c.audit_id.desc(),
            cascade="all",
            passive_deletes=False, # SA default
        ),
        "versions": relation(domain.AttachmentVersion, # !+ARCHETYPE_MAPPER
            primaryjoin=rdb.and_(
                schema.attachment.c.attachment_id ==
                    schema.attachment_audit.c.attachment_id,
            ),
            secondary=schema.attachment_audit,
            secondaryjoin=rdb.and_(
                schema.attachment_audit.c.audit_id == schema.change.c.audit_id,
                # !+NO_INHERIT_VERSION needs this
                schema.change.c.action == "version",
            ),
            #!+backref: version.audit.audit_head
            #backref="audit_head", !+ERROR: version.audit_head
            # *** UnmappedColumnError: No column attachment_audit.audit_id is 
            # configured on mapper Mapper|Version|change...
            uselist=True,
            lazy=True,
            order_by=schema.change.c.audit_id.desc(),
            viewonly=True,
        ),
    }
)
mapper(domain.AttachmentAudit, schema.attachment_audit,
    inherits=domain.Audit,
    polymorphic_identity=polymorphic_identity(domain.Attachment) # on head class
)
mapper(domain.AttachmentVersion,
    inherits=domain.Change, # !+NO_INHERIT_VERSION
    #polymorphic_on=schema.change.c.action,
    #polymorphic_identity="version", #!+polymorphic_identity(domain.Version),
    properties={
        # the reverse of DocVersion.attachment_versions
        # note: this works because when a new doc version is created, there is 
        # a dedicated entry in change_tree to link the head doc to a version of
        # each of its attachments
        # version
        "doc_versions": relation(domain.DocVersion,
            primaryjoin=rdb.and_(
                schema.change.c.audit_id == schema.change_tree.c.child_id,
            ),
            secondary=schema.change_tree,
            secondaryjoin=rdb.and_(
                schema.change_tree.c.parent_id == schema.change.c.audit_id,
                schema.change.c.audit_id == schema.doc_audit.c.audit_id,
            ),
            uselist=True,
            lazy=True,
            order_by=schema.change.c.audit_id.desc(),
            viewonly=True,
        ),
        #!+eventable items supporting feature "event":
        #"sa_events": relation(domain.Event, uselist=True),
    },
)

mapper(domain.Heading, schema.heading,
    properties={
        "group": relation(domain.Group, 
            backref=backref("group",
                remote_side=schema.heading.c.group_id
            )
        )
    }
)


# items scheduled for a sitting expressed as a relation to their item schedule

mapper(domain.ItemSchedule, schema.item_schedule,
    properties={
        "sitting": relation(domain.Sitting, uselist=False, lazy=False),
    }
)

mapper(domain.EditorialNote, schema.editorial_note)

mapper(domain.ItemScheduleDiscussion, schema.item_schedule_discussion,
    properties={
        "scheduled_item": relation(domain.ItemSchedule, uselist=False,
            backref=backref("itemdiscussions", cascade="all, delete-orphan")
        ),
    }
)

mapper(domain.ItemScheduleVote, schema.item_schedule_vote,
    properties={
        "scheduled_item": relation(domain.ItemSchedule, uselist=False,
            backref=backref("itemvotes", cascade="all, delete-orphan")
        ),
    }
)

# items scheduled for a sitting
# expressed as a join between item and schedule

mapper(domain.Signatory, schema.signatory,
    properties={
        "head": relation(domain.Doc, uselist=False),
        "user": relation(domain.User, uselist=False),
        "member": relation(domain.MemberOfParliament,
            primaryjoin=rdb.and_(schema.signatory.c.user_id == 
                schema.user_group_membership.c.user_id),
            secondary=schema.user_group_membership,
            uselist=False,
        ),
        "audits": relation(domain.SignatoryAudit,
            primaryjoin=rdb.and_(schema.signatory.c.signatory_id == 
                schema.signatory_audit.c.signatory_id),
            backref="audit_head",
            uselist=True,
            lazy=True,
            order_by=schema.signatory_audit.c.signatory_id.desc(),
            cascade="all",
            passive_deletes=False, # SA default
        ),
    }
)
mapper(domain.SignatoryAudit, schema.signatory_audit,
    inherits=domain.Audit,
    polymorphic_identity=polymorphic_identity(domain.Signatory), # on head class
)

mapper(domain.Holiday, schema.holiday)

mapper(domain.Country, schema.country)


# !+RENAME simply to "Attendance"
mapper(domain.SittingAttendance, schema.sitting_attendance,
    properties={
        "member": relation(domain.User, uselist=False, lazy=False),
        "sitting": relation(domain.Sitting, uselist=False, lazy=False),
    }
)

mapper(domain.TitleType, schema.title_type,
    properties={"group": relation(domain.Group, uselist=False, lazy=False)}
)
mapper(domain.MemberTitle, schema.member_title,
    properties={
        "title_type": relation(domain.TitleType, uselist=False, lazy=False),
        "member": relation(domain.GroupMembership, uselist=False, lazy=False),
    }
)

mapper(domain.UserAddress, schema.address,
    properties={
        "country": relation(domain.Country, uselist=False, lazy=False),
    },
)
mapper(domain.GroupAddress, schema.address,
    properties={
        "country": relation(domain.Country, uselist=False, lazy=False),
    },
)


mapper(domain.Report,
    inherits=domain.Doc,
    polymorphic_identity=polymorphic_identity(domain.Report)
)

mapper(domain.SittingReport, schema.sitting_report,
    properties={
        "sitting": relation(domain.Sitting,
            lazy=True,
            uselist=False
        ),
        "report": relation(domain.Report, # !+doc.head
            backref="sittingreport",
            lazy=True,
            uselist=False
        ),
    }
)

mapper(domain.ObjectTranslation, schema.translation)

mapper(domain.TimeBasedNotication, schema.time_based_notification)

mapper(domain.DebateRecord, schema.debate_record,
    properties={
        "sitting": relation(domain.Sitting,
            lazy=True,
            uselist=False
        ),
        "debate_record_items": relation(domain.DebateRecordItem,
            lazy=True,
            uselist=True
        ),
        "debate_media": relation(domain.DebateMedia,
            lazy=True,
            uselist=True
        ),
        "debate_takes": relation(domain.DebateTake,
            lazy=True,
            uselist=True
        ),
    }
)

mapper(domain.DebateRecordItem, schema.debate_record_item)

mapper(domain.DebateDoc, schema.debate_doc,
    inherits=domain.DebateRecordItem,
    polymorphic_on=schema.debate_record_item.c.type,
    polymorphic_identity="debate_doc",
    properties={
        "doc": relation(domain.Doc, lazy=True)
    }
)

mapper(domain.DebateSpeech, schema.debate_speech,
    inherits=domain.DebateRecordItem,
    polymorphic_on=schema.debate_record_item.c.type,
    polymorphic_identity="debate_speech",
    properties={
        "user": relation(domain.User, lazy=True)
    }
)

mapper(domain.DebateMedia, schema.debate_media)

mapper(domain.DebateTake, schema.debate_take,
    properties={
        "user": relation(domain.User, lazy=True),
        "debate_record": relation(domain.DebateRecord, lazy=True)
    }
)

mapper(domain.OAuthApplication, schema.oauth_application)
mapper(domain.OAuthAuthorization, schema.oauth_authorization,
    properties={
        "user": relation(domain.User, uselist=False, lazy=False),
        "application": relation(domain.OAuthApplication, uselist=False,
            lazy=False)
    }
)
mapper(domain.OAuthAuthorizationToken, schema.oauth_authorization_token,
    properties={
        "authorization": relation(domain.OAuthAuthorization, uselist=False,
            lazy=False),
    }
)

mapper(domain.OAuthAccessToken, schema.oauth_access_token,
    properties={
        "authorization_token": relation(domain.OAuthAuthorizationToken,
            uselist=False, lazy=False),
    }
)


# !+IChange-vertical-properties special case: 
# class is NOT workflowed, and in any case has no available_dynamic_features, no descriptor
import bungeni.alchemist.model
bungeni.alchemist.model.instrument_extended_properties(domain.Change, "change")

