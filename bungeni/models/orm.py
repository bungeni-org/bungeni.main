
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


# Users
# general representation of a person
mapper(domain.User, schema.user,
    properties={
        "user_addresses": relation(domain.UserAddress,
            # !+HEAD_DOCUMENT_ITEM(mr, sep-2011) standardize name
            backref=backref("head", remote_side=schema.user.c.user_id)
        ),
        "subscriptions": relation(domain.Doc,
            secondary=schema.user_doc
        ),
    }
)

mapper(domain.UserSubscription, schema.user_doc)

mapper(domain.AdminUser, schema.admin_user,
    properties={
        "user":relation(domain.User)
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
    primary_key=[schema.group.c.group_id],
    properties={
        "members": relation(domain.GroupMembership),
        # !+GROUP_PRINCIPAL_ID(ah,sep-2011) - removing group_principal_id as 
        # orm property, this is now on the schema.
        #"group_principal_id": column_property(
        #    ("group." + schema.groups.c.type + "." +
        #     rdb.cast(schema.group.c.group_id, rdb.String)
        #    ).label("group_principal_id")
        #),
        "titletypes": relation(domain.TitleType),
        "contained_groups": relation(domain.Group,
            backref=backref("parent_group",
                remote_side=schema.group.c.group_id)
        ),
        "group_addresses": relation(domain.GroupAddress,
            # !+HEAD_DOCUMENT_ITEM(mr, sep-2011) standardize name
            backref=backref("head", remote_side=schema.group.c.group_id)
        ),
        # "keywords": relation(domain.Keyword, secondary=schema.group_keywords)
    },
    polymorphic_on=schema.group.c.type,
    polymorphic_identity=polymorphic_identity(domain.Group)
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

# group subclasses

mapper(domain.Government,
    inherits=domain.Group,
    polymorphic_on=schema.group.c.type,
    polymorphic_identity=polymorphic_identity(domain.Government)
)

mapper(domain.Parliament, schema.parliament,
    inherits=domain.Group,
    polymorphic_on=schema.group.c.type,
    polymorphic_identity=polymorphic_identity(domain.Parliament)
)

mapper(domain.PoliticalGroup, schema.political_group,
    inherits=domain.Group,
    polymorphic_on=schema.group.c.type,
    polymorphic_identity=polymorphic_identity(domain.PoliticalGroup)
)

mapper(domain.Ministry,
    inherits=domain.Group,
    polymorphic_on=schema.group.c.type,
    polymorphic_identity=polymorphic_identity(domain.Ministry)
)

mapper(domain.Committee, schema.committee,
    inherits=domain.Group,
    polymorphic_on=schema.group.c.type,
    polymorphic_identity=polymorphic_identity(domain.Committee)
)

mapper(domain.Office, schema.office,
    inherits=domain.Group,
    polymorphic_on=schema.group.c.type,
    polymorphic_identity=polymorphic_identity(domain.Office)
)


# Ministers and Committee members are defined by their group membership in a 
# ministry or committee (group)

# we need to specify join clause for user explicitly because we have multiple fk
# to the user table.
mapper(domain.GroupMembership, schema.user_group_membership,
    properties={
        "user":relation(domain.User,
            primaryjoin=rdb.and_(schema.user_group_membership.c.user_id ==
                schema.user.c.user_id),
            uselist=False,
            lazy=False),
        "group":relation(domain.Group,
            primaryjoin=(schema.user_group_membership.c.group_id ==
                schema.group.c.group_id),
            uselist=False,
            lazy=True),
        "replaced":relation(domain.GroupMembership,
            primaryjoin=(schema.user_group_membership.c.replaced_id ==
                schema.user_group_membership.c.membership_id),
            uselist=False,
            lazy=True),
        "sub_roles":relation(domain.GroupMembershipRole),
        "member_titles":relation(domain.MemberTitle)
    },
    polymorphic_on=schema.user_group_membership.c.membership_type,
    polymorphic_identity=polymorphic_identity(domain.GroupMembership)
)
# !+HEAD_DOCUMENT_ITEM(mr, sep-2011) standardize name, "head", "document", "item"
domain.GroupMembership.head = domain.GroupMembership.user

mapper(domain.GroupMembershipRole, schema.group_membership_role,
       properties={
        "member":relation(domain.GroupMembership)
        }
)

# !+RENAME ParliamentMember
mapper(domain.MemberOfParliament, schema.parliament_membership,
    inherits=domain.GroupMembership,
    primary_key=[schema.user_group_membership.c.membership_id],
    properties={
        "start_date": column_property(
            schema.user_group_membership.c.start_date.label("start_date")),
        "end_date": column_property(
            schema.user_group_membership.c.end_date.label("end_date")),
    },
    polymorphic_on=schema.user_group_membership.c.membership_type,
    polymorphic_identity=polymorphic_identity(domain.MemberOfParliament)
)

mapper(domain.Minister,
    inherits=domain.GroupMembership,
    polymorphic_on=schema.user_group_membership.c.membership_type,
    polymorphic_identity=polymorphic_identity(domain.Minister)
)

mapper(domain.CommitteeMember,
    inherits=domain.GroupMembership,
    polymorphic_on=schema.user_group_membership.c.membership_type,
    polymorphic_identity=polymorphic_identity(domain.CommitteeMember)
)

mapper(domain.PoliticalGroupMember,
    inherits=domain.GroupMembership,
    polymorphic_on=schema.user_group_membership.c.membership_type,
    polymorphic_identity=polymorphic_identity(domain.PoliticalGroupMember)
)

mapper(domain.OfficeMember,
    inherits=domain.GroupMembership,
    polymorphic_on=schema.user_group_membership.c.membership_type,
    polymorphic_identity=polymorphic_identity(domain.OfficeMember)
)

# staff assigned to a group (committee, ...)

mapper(domain.CommitteeStaff,
    inherits=domain.GroupMembership,
    polymorphic_on=schema.user_group_membership.c.membership_type,
    polymorphic_identity=polymorphic_identity(domain.CommitteeStaff)
)

mapper(domain.Session, schema.session,
    properties={
        "group": relation(domain.Parliament, lazy=False),
    }
)

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
            order_by=schema.item_schedule.c.planned_order,
            cascade="all"
        ),
        "sa_attendance": relation(domain.SittingAttendance,
            cascade="all"
        ),
        "reports": relation(domain.SittingReport,
            cascade="all"
        ),
        "venue": relation(domain.Venue, lazy=False),
    }
)


''' !+BookedResources
mapper(domain.ResourceType, schema.resource_types)
mapper(domain.Resource, schema.resources)
mapper(domain.ResourceBooking, schema.resourcebookings)
'''

mapper(domain.Venue, schema.venue)

##############################
# Document

def mapper_add_relation_vertical_properties(kls):
    """Instrument any extended attributes as vertical properties.
    """
    for vp_name, vp_type in kls.extended_properties:
        mapper_add_relation_vertical_property(kls, vp_name, vp_type)
def mapper_add_relation_vertical_property(kls, vp_name, vp_type):
    """Add the SQLAlchemy internal mapper property for the vertical property.
    """
    kls_mapper = class_mapper(kls)
    object_type = kls_mapper.local_table.name # kls_mapper.mapped_table.name
    assert len(kls_mapper.primary_key) == 1
    object_id_column = kls_mapper.primary_key[0]
    kls_mapper.add_property("_vp_%s" % (vp_name),
        relation_vertical_property(
            object_type, object_id_column, vp_name, vp_type)
    )
def relation_vertical_property(object_type, object_id_column, vp_name, vp_type):
    """Get the SQLAlchemy internal property for the vertical property.
    """
    vp_table = class_mapper(vp_type).mapped_table
    return relation(vp_type,
        primaryjoin=rdb.and_(
            object_id_column == vp_table.c.object_id,
            object_type == vp_table.c.object_type,
            vp_name == vp_table.c.name,
        ),
        foreign_keys=[vp_table.c.object_id],
        uselist=False,
        # !+abusive, cannot create a same-named backref to multiple classes!
        #backref=object_type,
        # sqlalchemy.orm.relationship(cascade="save-update, merge, 
        #       refresh-expire, expunge, delete, delete-orphan")
        # False (default) -> "save-update, merge"
        # "all" -> "save-update, merge, refresh-expire, expunge, delete"
        cascade="all",
        single_parent=True,
        lazy=False, # !+LAZY(mr, jul-2012) gives orm.exc.DetachedInstanceError
        # e.g. in business/questions listing:
        # Parent instance <Question at ...> is not bound to a Session; 
        # lazy load operation of attribute '_vp_response_type' cannot proceed
    )


mapper(domain.vp.Text, schema.vp_text)
mapper(domain.vp.TranslatedText, schema.vp_translated_text)

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

mapper(domain.GroupDocumentAssignment, schema.group_document_assignment,
    properties={
        "group": relation(domain.Group,
            primaryjoin=schema.group_document_assignment.c.group_id ==
                schema.group.c.group_id,
            uselist=False,
            lazy=False),
    }
)

mapper(domain.Audit, schema.audit,
    polymorphic_on=schema.audit.c.audit_type, # polymorphic discriminator
    polymorphic_identity=polymorphic_identity(domain.Audit)
)
mapper(domain.Change, schema.change,
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
    polymorphic_identity=polymorphic_identity(domain.Version),
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
    properties={
        # !+ only for versionable doc sub-types that also support "attachment"
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
    polymorphic_on=schema.doc.c.type,
    polymorphic_identity=polymorphic_identity(domain.AgendaItem),
)

mapper(domain.Bill,
    inherits=domain.Doc,
    polymorphic_on=schema.doc.c.type,
    polymorphic_identity=polymorphic_identity(domain.Bill),
)

mapper(domain.Motion, 
    inherits=domain.Doc,
    polymorphic_on=schema.doc.c.type,
    polymorphic_identity=polymorphic_identity(domain.Motion),
)

mapper(domain.Question,
    inherits=domain.Doc,
    polymorphic_on=schema.doc.c.type,
    polymorphic_identity=polymorphic_identity(domain.Question),
    properties={ #!+
        "ministry": relation(domain.Ministry, lazy=False, join_depth=2),
    }
)

mapper(domain.TabledDocument,
    inherits=domain.Doc,
    polymorphic_on=schema.doc.c.type,
    polymorphic_identity=polymorphic_identity(domain.TabledDocument),
)


mapper(domain.Event,
    inherits=domain.Doc,
    polymorphic_on=schema.doc.c.type, # polymorphic discriminator
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
    polymorphic_on=schema.change.c.action,
    polymorphic_identity=polymorphic_identity(domain.Version),
    properties={
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


#Items scheduled for a sitting expressed as a relation
# to their item schedule

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

######################
#

mapper(domain.Country, schema.country)


# !+RENAME simply to "Attendance"
mapper(domain.SittingAttendance, schema.sitting_attendance,
    properties={
        "member": relation(domain.User, uselist=False, lazy=False),
        "sitting": relation(domain.Sitting, uselist=False, lazy=False),
    }
)

mapper(domain.TitleType, schema.title_type,
    properties={ "group": relation(domain.Group, uselist=False, lazy=False) }
)
mapper(domain.MemberTitle, schema.member_title,
    properties={
        "title_type": relation(domain.TitleType, uselist=False, lazy=False),
        "member": relation(domain.GroupMembership, uselist=False, lazy=False),
    }
)

mapper(domain.UserAddress, schema.user_address,
    properties={
        "country": relation(domain.Country, uselist=False, lazy=False),
    },
)
mapper(domain.GroupAddress, schema.group_address,
    properties={
        "country": relation(domain.Country, uselist=False, lazy=False),
    },
)


mapper(domain.Report,
    inherits=domain.Doc,
    polymorphic_on=schema.doc.c.type,
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

# !+Report4Sitting domain.Report4Sitting inherits from domain.Report, it is 
# mapped to the ASSOCIATION table schema.sitting_report ?!!
mapper(domain.Report4Sitting, schema.sitting_report,
    inherits=domain.Report
)

mapper(domain.ObjectTranslation, schema.translation)


# !+IChange-vertical-properties special case: 
# class is NOT workflowed, and in any case has no available_dynamic_features
mapper_add_relation_vertical_properties(domain.Change)


