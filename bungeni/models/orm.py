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
import interfaces


def polymorphic_identity(cls):
    """Formalize convention of determining the polymorphic discriminator value 
    for a domain class as a function of the class name.
    """
    return schema.un_camel(cls.__name__)


# !+PARAMETRIZABLE_DOCTYPES
def configurable_mappings(kls):
    """Configuration mappings for declarative-model types.
    """
    name = kls.__name__
    mapper_add_relation_vertical_properties(kls)
    
    # auditable, determine properties, map audit class/table
    if interfaces.IAuditable.implementedBy(kls):
        # either defined manually or created dynamically in domain.auditable()
        audit_kls = getattr(domain, "%sAudit" % (name))
        # assumption: audit_kls only uses single inheritance (at least for 
        # those created dynamically in domain.auditable())
        base_audit_kls = audit_kls.__bases__[0] 
        assert issubclass(base_audit_kls, domain.Audit), \
            "Audit class %s is not a proper subclass of %s" % (
                audit_kls, domain.Audit)
        if domain.CREATE_AUDIT_CLASS_FOR(kls):
            mapper(audit_kls,
                inherits=base_audit_kls,
                polymorphic_identity=polymorphic_identity(kls)
            )
        # propagate any extended attributes on head kls also to its audit_kls
        for vp_name, vp_type in kls.extended_properties:
            mapper_add_relation_vertical_property(audit_kls, vp_name, vp_type)
    
    # add any properties to the head kls itself
    def mapper_add_configurable_properties(kls):
        kls_mapper = class_mapper(kls)
        def configurable_properties(kls, mapper_properties):
            """Add properties, as per configured features for a domain type.
            """
            # auditable
            if interfaces.IAuditable.implementedBy(kls):
                # kls.changes <-> change.audit.audit_head=doc:
                # doc[@TYPE] <-- TYPE_audit <-> audit <-> change
                
                # get head table for kls, and its audit table.
                tbl = kls_mapper.mapped_table
                audit_tbl = getattr(schema, "%s_audit" % (tbl.name))
                
                # get tbl PK column
                assert len(tbl.primary_key) == 1
                pk_col = [ c for c in tbl.primary_key ][0]
                mapper_properties["changes"] = relation(domain.Change,
                    primaryjoin=rdb.and_(
                        pk_col == audit_tbl.c.get(pk_col.name),
                    ),
                    secondary=audit_tbl,
                    secondaryjoin=rdb.and_(
                        audit_tbl.c.audit_id == schema.change.c.audit_id,
                    ),
                    lazy=True,
                    order_by=schema.change.c.audit_id.desc(),
                    cascade="all",
                    passive_deletes=False,
                )
            # versionable
            if interfaces.IVersionable.implementedBy(kls):
                pass
            return mapper_properties
        for key, prop in configurable_properties(kls, {}).items():
            kls_mapper.add_property(key, prop)
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
            backref=backref("head", remote_side=schema.users.c.user_id)
        ),
        "subscriptions": relation(domain.Doc,
            secondary=schema.user_doc
        ),
    }
)

mapper(domain.AdminUser, schema.admin_users,
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
            backref=backref("head", remote_side=schema.groups.c.group_id)
        ),
        # "keywords": relation(domain.Keyword, secondary=schema.groups_keywords)
    },
    polymorphic_on=schema.groups.c.type,
    polymorphic_identity=polymorphic_identity(domain.Group)
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
    polymorphic_identity=polymorphic_identity(domain.Government)
)

mapper(domain.Parliament, schema.parliaments,
    inherits=domain.Group,
    polymorphic_on=schema.groups.c.type,
    polymorphic_identity=polymorphic_identity(domain.Parliament)
)

mapper(domain.PoliticalEntity, schema.political_parties,
    inherits=domain.Group,
    polymorphic_on=schema.groups.c.type,
    polymorphic_identity=polymorphic_identity(domain.PoliticalEntity)
)

mapper(domain.PoliticalParty,
    inherits=domain.PoliticalEntity,
    polymorphic_on=schema.groups.c.type,
    polymorphic_identity=polymorphic_identity(domain.PoliticalParty)
)

mapper(domain.PoliticalGroup,
    inherits=domain.PoliticalEntity,
    polymorphic_on=schema.groups.c.type,
    polymorphic_identity=polymorphic_identity(domain.PoliticalGroup)
)

mapper(domain.Ministry,
    inherits=domain.Group,
    polymorphic_on=schema.groups.c.type,
    polymorphic_identity=polymorphic_identity(domain.Ministry)
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
    polymorphic_identity=polymorphic_identity(domain.Committee)
)

mapper(domain.Office, schema.offices,
    inherits=domain.Group,
    polymorphic_on=schema.groups.c.type,
    polymorphic_identity=polymorphic_identity(domain.Office)
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
    polymorphic_identity=polymorphic_identity(domain.GroupMembership)
)
# !+HEAD_DOCUMENT_ITEM(mr, sep-2011) standardize name, "head", "document", "item"
domain.GroupMembership.head = domain.GroupMembership.user

#!+TYPES_CUSTOM mapper(domain.MemberElectionType, schema.member_election_types)

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
    polymorphic_identity=polymorphic_identity(domain.MemberOfParliament)
)

mapper(domain.Minister,
    inherits=domain.GroupMembership,
    polymorphic_on=schema.user_group_memberships.c.membership_type,
    polymorphic_identity=polymorphic_identity(domain.Minister)
)

mapper(domain.CommitteeMember,
    inherits=domain.GroupMembership,
    polymorphic_on=schema.user_group_memberships.c.membership_type,
    polymorphic_identity=polymorphic_identity(domain.CommitteeMember)
)

mapper(domain.PartyMember,
    inherits=domain.GroupMembership,
    polymorphic_on=schema.user_group_memberships.c.membership_type,
    polymorphic_identity=polymorphic_identity(domain.PartyMember)
)

mapper(domain.OfficeMember,
    inherits=domain.GroupMembership,
    polymorphic_on=schema.user_group_memberships.c.membership_type,
    polymorphic_identity=polymorphic_identity(domain.OfficeMember)
)

# staff assigned to a group (committee, ...)

mapper(domain.CommitteeStaff,
    inherits=domain.GroupMembership,
    polymorphic_on=schema.user_group_memberships.c.membership_type,
    polymorphic_identity=polymorphic_identity(domain.CommitteeStaff)
)

mapper(domain.ParliamentSession, schema.parliament_sessions)

mapper(domain.Sitting, schema.sitting,
    properties={
        "group": relation(domain.Group,
            primaryjoin=schema.sitting.c.group_id == schema.groups.c.group_id,
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
            order_by=schema.item_schedules.c.planned_order
        ),
        "venue": relation(domain.Venue),
    }
)


''' !+BookedResources
mapper(domain.ResourceType, schema.resource_types)
mapper(domain.Resource, schema.resources)
mapper(domain.ResourceBooking, schema.resourcebookings)
'''

mapper(domain.Venue, schema.venues)

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
        # sqlalchemy.orm.relationship(cascade="refresh-expire, expunge, delete")
        cascade="save-update, merge, delete-orphan",
        single_parent=True,
        lazy=True, # !+ True gives DetachedInstanceError in listings, while 
        # False gives sqlalchemy.exc.ProgrammingError (missing FROM-clause 
        # entry for table ... ) !!
    )


mapper(domain.vp.Text, schema.vp_text)
mapper(domain.vp.TranslatedText, schema.vp_translated_text)

mapper(domain.Doc, schema.doc,
    polymorphic_on=schema.doc.c.type, # polymorphic discriminator
    polymorphic_identity=polymorphic_identity(domain.Doc),
    properties={
        "owner": relation(domain.User,
            primaryjoin=rdb.and_(schema.doc.c.owner_id ==
                schema.users.c.user_id),
            uselist=False,
            lazy=False),
        # !+AlchemistManagedContainer, X same as amc_X.values(), property @X?
        # !+ARCHETYPE_MAPPER(mr, apr-2012) keep this mapper property always 
        # present on predefined archetype mapper, or dynamically instrument it 
        # on each on mapper of each (sub-archetype) type having this feature?
        "item_signatories": relation(domain.Signatory), #!+rename sa_signatories
        "attachments": relation(domain.Attachment), # !+ARCHETYPE_MAPPER
        "sa_events": relation(domain.Event, uselist=True), # !+ARCHETYPE_MAPPER
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
        ),
        "versions": relation(domain.DocVersion, # !+ARCHETYPE_MAPPER
            primaryjoin=rdb.and_(
                schema.doc.c.doc_id == schema.doc_audit.c.doc_id,
            ),
            secondary=schema.doc_audit,
            secondaryjoin=rdb.and_(
                schema.doc_audit.c.audit_id == schema.audit.c.audit_id,
                schema.audit.c.audit_id == schema.change.c.audit_id,
                # !+NO_INHERIT_VERSION needs this
                schema.change.c.action == "version",
            ),
            #!+backref: version.audit.audit_head
            uselist=True,
            lazy=True,
            order_by=schema.change.c.audit_id.desc(),
        ),
        "group": relation(domain.Group,
            primaryjoin=schema.doc.c.group_id == schema.groups.c.group_id,
            #backref="agenda_items",
            lazy=False,
            uselist=False,
        )
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
                schema.users.c.user_id),
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

''' !+NO_INHERIT_VERSION mapping domain.Version is actually unnecessary then
#vm = mapper(domain.Version,
mapper(domain.Version,
    inherits=domain.Change,
    polymorphic_on=schema.change.c.action, # polymorphic discriminator
    polymorphic_identity=polymorphic_identity(domain.Version),
)
# !+polymorphic_identity_multi only allows a single value... but, we can tweak 
# the version mapper's polymorphic_map to allow multiple values for 
# polymorphic_identity (but attachment.versions does not pick up reversions):
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
        # !+ only for versionable doc sub-types that are also attachmentable
        "attachments": relation(domain.AttachmentVersion, # !+ARCHETYPE_MAPPER
            primaryjoin=rdb.and_(
                schema.change.c.audit_id == schema.change_tree.c.parent_id,
                #schema.change.c.action == "version", # !+constraint
            ),
            secondary=schema.change_tree,
            secondaryjoin=rdb.and_(
                schema.change_tree.c.child_id == schema.change.c.audit_id,
                #"version" == schema.change.c.action, # !+constraint
            ),
            #backref=backref("parent", 
            #    uselist=False
            #),
            uselist=True,
            lazy=True,
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
            #cascade="all",
            order_by=schema.attachment_audit.c.audit_id.desc(),
        ),
        "versions": relation(domain.AttachmentVersion, # !+ARCHETYPE_MAPPER
            primaryjoin=rdb.and_(
                schema.attachment.c.attachment_id ==
                    schema.attachment_audit.c.attachment_id,
            ),
            secondary=schema.attachment_audit,
            secondaryjoin=rdb.and_(
                schema.attachment_audit.c.audit_id == schema.audit.c.audit_id,
                schema.audit.c.audit_id == schema.change.c.audit_id,
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
        ),
    }
)
mapper(domain.AttachmentAudit, schema.attachment_audit,
    inherits=domain.Audit,
    polymorphic_identity=polymorphic_identity(domain.Attachment) # on head class
)
mapper(domain.AttachmentVersion,
    inherits=domain.Change, # !+NO_INHERIT_VERSION
    properties={
        #!+eventable items supporting feature "event":
        #"sa_events": relation(domain.Event, uselist=True),
    },
)

mapper(domain.Heading, schema.headings,
    properties={
        "group": relation(domain.Group, 
            backref=backref("group",
                remote_side=schema.headings.c.group_id
            )
        )
    }
)

#!+TYPES_CUSTOM mapper(domain.QuestionType, schema.question_types)
#!+TYPES_CUSTOM mapper(domain.ResponseType, schema.response_types)


#Items scheduled for a sitting expressed as a relation
# to their item schedule

mapper(domain.ItemSchedule, schema.item_schedules,
    properties={
        "sitting": relation(domain.Sitting, uselist=False),
    }
)

mapper(domain.EditorialNote, schema.editorial_note)

mapper(domain.ItemScheduleDiscussion, schema.item_schedule_discussions,
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
        "audits": relation(domain.SignatoryAudit,
            primaryjoin=rdb.and_(schema.signatory.c.signatory_id == 
                schema.signatory_audit.c.signatory_id),
            backref="audit_head",
            uselist=True,
            lazy=True,
            order_by=schema.signatory_audit.c.signatory_id.desc(),
        ),
    }
)
mapper(domain.SignatoryAudit, schema.signatory_audit,
    inherits=domain.Audit,
    polymorphic_identity=polymorphic_identity(domain.Signatory), # on head class
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

mapper(domain.SittingAttendance, schema.sitting_attendance,
    properties={
        "user": relation(domain.User, uselist=False, lazy=False),
        "sitting": relation(domain.Sitting, uselist=False, lazy=False),
    }
)
#!+TYPES_CUSTOM mapper(domain.AttendanceType, schema.attendance_types)
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


mapper(domain.Report,
    inherits=domain.Doc,
    polymorphic_on=schema.doc.c.type,
    polymorphic_identity=polymorphic_identity(domain.Report)
)

mapper(domain.SittingReport, schema.sitting_reports, # !+?
    properties={
        "sitting": relation(domain.Sitting,
            backref="reports",
            lazy=True,
            uselist=False
        ),
        "report": relation(domain.Report, # !+doc.head
            backref="sitting",
            lazy=True,
            uselist=False
        ),
    }
)

mapper(domain.Report4Sitting, schema.sitting_reports,
    inherits=domain.Report
)

mapper(domain.ObjectTranslation, schema.translations)


# !+IChange-vertical-properties special case: 
# class is NOT workflowed, and in any case __dynamic_features__ = False
mapper_add_relation_vertical_properties(domain.Change)


