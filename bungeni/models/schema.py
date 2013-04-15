# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""The Bungeni relational schema

$Id$
"""
log = __import__("logging").getLogger("bungeni.models.schema")

import sqlalchemy as sa
from fields import FSBlob
from datetime import datetime


metadata = sa.MetaData()


# users and groups because of the zope users and groups
PrincipalSequence = sa.Sequence("principal_sequence")


# vertical properties

vp_text = sa.Table("vp_text", metadata,
    sa.Column("object_id", sa.Integer, primary_key=True, nullable=False),
    sa.Column("object_type", sa.String(32), primary_key=True, nullable=False),
    sa.Column("name", sa.String(50), primary_key=True, nullable=False,),
    sa.Column("value", sa.UnicodeText),
)
vp_translated_text = sa.Table("vp_translated_text", metadata,
    sa.Column("object_id", sa.Integer, primary_key=True, nullable=False),
    sa.Column("object_type", sa.String(32), primary_key=True, nullable=False),
    sa.Column("name", sa.String(50), primary_key=True, nullable=False,),
    sa.Column("value", sa.UnicodeText),
    sa.Column("language", sa.String(5), nullable=False),
)
vp_datetime = sa.Table("vp_datetime", metadata,
    sa.Column("object_id", sa.Integer, primary_key=True, nullable=False),
    sa.Column("object_type", sa.String(32), primary_key=True, nullable=False),
    sa.Column("name", sa.String(50), primary_key=True, nullable=False,),
    sa.Column("value", sa.DateTime(timezone=False)),
)


# audit 

# generic change information
change = sa.Table("change", metadata,
    sa.Column("audit_id", sa.Integer, 
        sa.ForeignKey("audit.audit_id"),
        primary_key=True),
    sa.Column("user_id", sa.Integer, sa.ForeignKey("user.user_id"), 
        nullable=False),
    sa.Column("action", sa.Unicode(16), nullable=False),
    # accumulative count, per (change.audit.audit_head_id, change.action) 
    # e.g default: 1 + max(seq(head, "version")), see ui.audit _get_seq()
    sa.Column("seq", sa.Integer, nullable=False),
    sa.Column("procedure", sa.String(1), default="a", nullable=False),
    # audit datetime, exclusively managed by the system, real datetime of 
    # when change was actually affected
    sa.Column("date_audit", sa.DateTime(timezone=False),
        #!+CATALYSE(mr, nov-2010) fails descriptor catalisation
        #default=functions.current_timestamp(),
        server_default=sa.sql.text("now()"),
        nullable=False
    ),
    # user-modifiable effective datetime (defaults to audit_time);
    # this is the datetime to be used for all intents and purposes other 
    # than for "forensic" data auditing
    sa.Column("date_active", sa.DateTime(timezone=False),
        #!+CATALYSE(mr, nov-2010)
        #default=functions.current_timestamp(),
        server_default=sa.sql.text("now()"),
        nullable=False
    ),
    
    #sa.Column("description", sa.UnicodeText), #!+dynamic at runtime
    # possible explanatory note/remark/comment/observation/recommendation/etc 
    # about the change, manually added by the user; this is part of the 
    # audit history of a document and visible to all who have access to this
    # change record.
    # Workflow State at time of change - visibility of a change record 
    # depends on permissions of parent object in this specific state.
    
    #sa.Column("status", sa.Unicode(48)), # !+ use audit.status?
    # !+presumably already on head for when audit_head is itself a sub-document 
    # e.g. events, as knowing the status of also the "root" head document may 
    # be necessary to determine allowed access for *this* change record
    
    #sa.Column("root_status", sa.Unicode(48)),
)
# tree to relate change actions across parent and child objects 
# e.g. to snapshot a version tree of an object and its sub-objects. 
# Constraint: all related changes must be of same "action".
change_tree = sa.Table("change_tree", metadata,
    sa.Column("parent_id", sa.Integer, 
        sa.ForeignKey("change.audit_id"), 
        primary_key=True,
    ),
    sa.Column("child_id", sa.Integer, 
        sa.ForeignKey("change.audit_id"), 
        primary_key=True,
    ),
    sa.CheckConstraint("""parent_id != child_id""", 
        name="change_tree_check_not_same",
    ),
    #!+sa.CheckConstraint(parent.change.action == child.change.action),
)

audit_sequence = sa.Sequence("audit_sequence")
audit = sa.Table("audit", metadata,
    sa.Column("audit_id", sa.Integer, audit_sequence, primary_key=True),
    # audit_type, for polymorphic_identity
    sa.Column("audit_type", sa.String(30), nullable=False),
)

def make_audit_table(table, metadata):
    """Create an audit log table for an archetype.
    
    We prefix all additional audit-specific columns with "audit_" to avoid 
    potential clashing of column names from table being audited.
    """
    entity_name = table.name
    audit_tbl_name = "%s_audit" % (entity_name)
    columns = [
        sa.Column("audit_id", sa.Integer, 
            sa.ForeignKey("audit.audit_id"), 
            primary_key=True),
    ]
    def extend_cols(cols, ext_cols):
        names = [ c.name for c in cols ]
        for c in ext_cols:
            assert c.name not in names, "Duplicate column [%s]." % (c.name)
            names.append(c.name)
            if not c.primary_key:
                #!+should special ext col constraints NOT be carried over e.g.
                #  default value on ext, not/nullable on ext...?
                cols.append(c.copy())
            else: 
                # the single PK id of the "owning" object for which the change
                # is being logged; we retain the same original column name
                # i.e. doc_id for case of "doc", and have the audit_head_id 
                # property always read and write to this.
                assert c.name == "%s_id" % (entity_name), \
                    "Inconsistent PK column naming [%s != %s]" % (
                        "%s_id" % (entity_name), c.name)
                cols.append(
                    sa.Column(c.name, sa.Integer, 
                        sa.ForeignKey(table.c[c.name]),
                        nullable=False,
                        index=True
                    )),
    extend_cols(columns, table.columns)
    # !+additional tables...
    audit_tbl = sa.Table(audit_tbl_name, metadata, *columns,
        useexisting=False
    )
    return audit_tbl


#######################
# Users 
#######################

principal = sa.Table("principal", metadata,
    sa.Column("principal_id", sa.Integer, PrincipalSequence, primary_key=True),
    # !+PRINCIPAL_NAME(mr, mar-2013) should really be THE (natural) primary key,
    # and replace principal_id altogether!
    # !+principal_name sa.Column("principal_name", sa.Unicode(50), unique=True, nullable=False),
    # for polymorphic_identity
    sa.Column("type", sa.String(30), nullable=False),
)


user = sa.Table("user", metadata,
    sa.Column("user_id", sa.Integer, 
        sa.ForeignKey("principal.principal_id"),
        primary_key=True),
    # !+principal(mr, feb-2013) "login" should really be "principal_name" here
    sa.Column("login", sa.Unicode(80), 
        # !+principal_name sa.ForeignKey("principal.principal_name"),
        unique=True,
        nullable=False),
    sa.Column("salutation", sa.Unicode(128)), # !+vocabulary?
    sa.Column("title", sa.Unicode(128)), # !+vocabulary?
    sa.Column("first_name", sa.Unicode(256), nullable=False),
    sa.Column("last_name", sa.Unicode(256), nullable=False),
    sa.Column("middle_name", sa.Unicode(256)),
    sa.Column("email", sa.String(512), nullable=False),
    sa.Column("gender", sa.String(1),
        sa.CheckConstraint("""gender in ('M', 'F')""")  # (M)ale (F)emale
    ),
    sa.Column("date_of_birth", sa.Date),
    sa.Column("birth_country", sa.String(2),
        sa.ForeignKey("country.country_id")
    ),
    sa.Column("birth_nationality", sa.String(2),
        sa.ForeignKey("country.country_id")
    ),
    sa.Column("current_nationality", sa.String(2),
        sa.ForeignKey("country.country_id")
    ),
    sa.Column("marital_status", sa.Unicode(128),
        default=None,
        nullable=True,
    ),
    sa.Column("uri", sa.Unicode(1024), unique=True),
    sa.Column("date_of_death", sa.Date),
    sa.Column("type_of_id", sa.String(1)),
    sa.Column("national_id", sa.Unicode(256)),
    sa.Column("password", sa.String(36)
        # we store salted md5 hash hexdigests
    ),
    sa.Column("salt", sa.String(24)),
    sa.Column("description", sa.UnicodeText),
    sa.Column("remarks", sa.UnicodeText),
    sa.Column("image", sa.Binary),
    # !+active_p(mr, sep-2011) why is this "workflow status" column named
    # "active_p" and not "status"? Rename...
    # !+active_p(mr, sep-2011) why have identically named columns here and on 
    # group_memberships, with one being a string and other a bool?
    sa.Column("active_p", sa.String(1),
        sa.CheckConstraint("""active_p in ('A', 'I', 'D')"""),
        # !+active_p(mr, sep-2011) workflow status columns MUST not have a
        # default value--it is up to the workflow to decide what this should be!
        #default="A", # active/inactive/deceased
    ),
    #!+receive_notification comment out for now - will be used for user preferences
    sa.Column("receive_notification", sa.Boolean, default=True),
    sa.Column("language", sa.String(5), nullable=False),
)

admin_user = sa.Table("admin_user", metadata,
    sa.Column("user_id", sa.Integer,
        sa.ForeignKey("user.user_id"),
        primary_key=True,
    )
)

# associations table for many-to-many relation between user and doc
user_doc = sa.Table("user_doc", metadata,
    sa.Column("user_id", sa.Integer,
        sa.ForeignKey("user.user_id"),
        primary_key=True
    ),
    sa.Column("doc_id", sa.Integer,
        sa.ForeignKey("doc.doc_id"),
        primary_key=True
    )
)

# delegate rights to act on behalf of a user to another user
user_delegation = sa.Table("user_delegation", metadata,
    sa.Column("user_id", sa.Integer,
        sa.ForeignKey("user.user_id"),
        primary_key=True
    ),
    sa.Column("delegation_id", sa.Integer,
        sa.ForeignKey("user.user_id"),
        primary_key=True
    )
)

# document that user is being currently editing
currently_editing_document = sa.Table("currently_editing_document", metadata,
    sa.Column("user_id", sa.Integer,
        sa.ForeignKey("user.user_id"),
        primary_key=True
    ),
    sa.Column("currently_editing_id", sa.Integer,
        sa.ForeignKey("doc.doc_id"),
        primary_key=True
    ),
    sa.Column("editing_date", sa.DateTime(timezone=False)) 
)

# password restore links
password_restore_link = sa.Table("password_restore_link", metadata,
    sa.Column("user_id", sa.Integer,
        sa.ForeignKey("user.user_id"),
        primary_key=True
    ),
    sa.Column("hash", sa.Unicode(256), nullable=False),
    sa.Column("expiration_date", sa.DateTime(timezone=False), nullable=False) 
) 


# specific user classes
parliament_membership = sa.Table("parliament_membership", metadata,
    sa.Column("membership_id", sa.Integer,
        sa.ForeignKey("user_group_membership.membership_id"),
        primary_key=True
    ),
    # The region/province/constituency (divisions and order may be in any way 
    # as appropriate for the given parliamentary territory) for the 
    # representation of this member of parliament.
    # Hierarchical Controlled Vocabulary Micro Data Format: 
    # a triple-colon ":::" separated sequence of *key phrase paths*, each of 
    # which is a double-colon "::" separated sequence of *key phrases*.
    sa.Column("representation", sa.UnicodeText, nullable=True),
    # the political party of the MP as of the time he was elected
    sa.Column("party", sa.UnicodeText, nullable=True),
    # is the MP elected, nominated, ex officio member, ...
    sa.Column("member_election_type", sa.Unicode(128),
        default=u'elected',
        nullable=False,
    ),
    sa.Column("election_nomination_date", sa.Date), # nullable=False),
    sa.Column("leave_reason", sa.Unicode(40)),
)


#########################
# Countries
#########################

country = sa.Table("country", metadata,
    sa.Column("country_id", sa.String(2), primary_key=True),
    sa.Column("iso_name", sa.Unicode(80), nullable=False),
    sa.Column("country_name", sa.Unicode(80), nullable=False),
    sa.Column("iso3", sa.String(3)),
    sa.Column("numcode", sa.Integer),
    sa.Column("language", sa.String(5), nullable=False),
)

#######################
# Groups
#######################
# we"re using a very normalized form here to represent all kinds of
# groups and their relations to other things in the system.

group = sa.Table("group", metadata,
    sa.Column("group_id", sa.Integer,
        sa.ForeignKey("principal.principal_id"),
        primary_key=True),
    sa.Column("short_name", sa.Unicode(512), nullable=False),
    sa.Column("full_name", sa.Unicode(1024)),
    sa.Column("acronym", sa.Unicode(32), nullable=True),
    sa.Column("principal_name", sa.Unicode(32), 
        # !+login_regex - principal_name should also be a valid login name
        # !+principal_name sa.ForeignKey("principal.principal_name"),
        unique=True,
        nullable=False),
    sa.Column("description", sa.UnicodeText),
    # Workflow State
    sa.Column("status", sa.Unicode(32)),
    sa.Column("status_date", sa.DateTime(timezone=False),
        server_default=sa.sql.text("now()"),
        nullable=False
    ),
    sa.Column("start_date", sa.Date, nullable=False),
    sa.Column("end_date", sa.Date),
    sa.Column("sub_type", sa.Unicode(128), nullable=True),
    sa.Column("parent_group_id", sa.Integer,
        sa.ForeignKey("group.group_id")
     ),
    sa.Column("language", sa.String(5), nullable=False),
    #The role that members of this group get
    sa.Column("group_role", sa.Unicode(256), nullable=False),
    #custom fields
    sa.Column("custom1", sa.UnicodeText, nullable=True),
    sa.Column("custom2", sa.UnicodeText, nullable=True),
    sa.Column("custom3", sa.UnicodeText, nullable=True),
    sa.Column("custom4", sa.UnicodeText, nullable=True),
)

parliament = sa.Table("parliament", metadata,
    sa.Column("parliament_id", sa.Integer,
        sa.ForeignKey("group.group_id"),
        primary_key=True
    ),
   sa.Column("parliament_type", sa.String(30), nullable=True),
   sa.Column("election_date", sa.Date, nullable=False),
)

committee = sa.Table("committee", metadata,
    sa.Column("committee_id", sa.Integer,
        sa.ForeignKey("group.group_id"),
        primary_key=True
    ),
    sa.Column("group_continuity", sa.Unicode(128),
        default=u'permanent',
        nullable=False,
    ),
    sa.Column("num_members", sa.Integer),
    sa.Column("min_num_members", sa.Integer),
    sa.Column("quorum", sa.Integer),
    sa.Column("num_clerks", sa.Integer),
    sa.Column("num_researchers", sa.Integer),
    sa.Column("proportional_representation", sa.Boolean),
    sa.Column("default_chairperson", sa.Boolean),
    sa.Column("reinstatement_date", sa.Date),
)
# !+TYPES_CUSTOM_life_span(mr, oct-2011) the old and unused column "life_span" 
# on committee_types (values: "parliament", "annual"). But, if concept will
# still be needed, the planned and more generic "group.root_container" idea 
# can approximately provide it, and is what should be used. 


# political group (inside the parliament)
political_group = sa.Table("political_group", metadata,
    sa.Column("group_id", sa.Integer,
        sa.ForeignKey("group.group_id"), primary_key=True),
    sa.Column("logo_data", sa.Binary),
    sa.Column("logo_name", sa.String(127)),
    sa.Column("logo_mimetype", sa.String(127)),
)

###
#  the personal role of a user in terms of their membership this group
#  The personal roles a person may have varies with the context. In a party
#  one may have the role spokesperson, member, ...

title_type = sa.Table("title_type", metadata,
    sa.Column("title_type_id", sa.Integer, primary_key=True),
    sa.Column("group_id", sa.Integer, 
                sa.ForeignKey("group.group_id"), nullable=False),
    sa.Column("title_name", sa.Unicode(40), nullable=False),
    sa.Column("user_unique", sa.Boolean, default=False,), # nullable=False),
    sa.Column("sort_order", sa.Integer(2), nullable=False),
    sa.Column("language", sa.String(5), nullable=False),
)

# sub roles to be granted when a document is assigned to a user
group_membership_role = sa.Table("group_membership_role", metadata,
    sa.Column("membership_id", sa.Integer,
        sa.ForeignKey("user_group_membership.membership_id"),
        primary_key=True),
    sa.Column("role_id", sa.Unicode(256), nullable=False,
        primary_key=True),
    sa.Column("is_global", sa.Boolean, default=False),
)

# !+QUALIFIED_FEATURES(mr, apr-2013) may need to "qualify" each assignment, to 
# be able to guarantee/constrain the intended action of the assignment to the
# appropriate group e.g. imagine a doc is assigned to one group for a 
# "2nd opinion" and again to another (or same!) for a "response"... and a user 
# to carry out the implied actions, who may be a member of both assigned groups
group_document_assignment = sa.Table("group_document_assignment", metadata,
    sa.Column("group_id", sa.Integer,
        sa.ForeignKey("group.group_id"),
        primary_key=True),
    sa.Column("doc_id", sa.Integer,
        sa.ForeignKey("doc.doc_id"),
        primary_key=True),
)

#
# group memberships encompasses any user participation in a group, including
# substitutions.

user_group_membership = sa.Table("user_group_membership", metadata,
    sa.Column("membership_id", sa.Integer, primary_key=True),
    sa.Column("user_id", sa.Integer,
        sa.ForeignKey("user.user_id"),
        nullable=False
    ),
    sa.Column("group_id", sa.Integer,
        sa.ForeignKey("group.group_id"),
        nullable=False
    ),
    # Workflow State
    sa.Column("status", sa.Unicode(32)),
    sa.Column("status_date", sa.DateTime(timezone=False),
        server_default=sa.sql.text("now()"),
        nullable=False
    ),
    sa.Column("start_date", sa.Date,
        default=datetime.now,
        nullable=False
    ),
    sa.Column("end_date", sa.Date),
    sa.Column("notes", sa.UnicodeText),
    # we use this as an easier query to end_date in queries, needs to be set by
    # a cron process against end_date < current_time
    sa.Column("active_p", sa.Boolean, default=True),
    # these fields are only present when a membership is result of substitution
    # unique because you can only replace one specific group member.
    sa.Column("replaced_id", sa.Integer,
        sa.ForeignKey("user_group_membership.membership_id"),
        unique=True
    ),
    sa.Column("substitution_type", sa.Unicode(100)),
    # type of membership staff or member
    sa.Column("membership_type", sa.String(30),
        default="member",
        nullable=False,
    ),
    sa.Column("language", sa.String(5), nullable=False),
    sa.schema.UniqueConstraint("user_id", "group_id")
)

##############
# Titles
##############
# To indicate the title a persons has in a specific context (Ministry, 
# Committee, Parliament, ...) and for what period (from - to)

member_title = sa.Table("member_title", metadata,
    sa.Column("member_title_id", sa.Integer, primary_key=True),
    sa.Column("membership_id", sa.Integer,
        sa.ForeignKey("user_group_membership.membership_id"),
        nullable=False
    ),
    # title of user"s group role
    sa.Column("title_type_id", sa.Integer,
        sa.ForeignKey("title_type.title_type_id"),
        nullable=False
    ),
    sa.Column("start_date", sa.Date, default=datetime.now, nullable=False),
    sa.Column("end_date", sa.Date),
    sa.Column("language", sa.String(5), nullable=False),
    sa.schema.UniqueConstraint("membership_id", "title_type_id")
)


############
# Addresses
############

address = sa.Table("address", metadata,
    sa.Column("address_id", sa.Integer, primary_key=True),
    # user or group address
    sa.Column("principal_id", sa.Integer,
        sa.ForeignKey("principal.principal_id"),
        nullable=False
    ),
    sa.Column("logical_address_type", sa.Unicode(128),
        default=u"office",
        nullable=False,
    ),
    sa.Column("postal_address_type", sa.Unicode(128),
        default=u"street",
        nullable=False,
    ),
    sa.Column("street", sa.Unicode(256), nullable=True),
    sa.Column("city", sa.Unicode(256), nullable=True),
    sa.Column("zipcode", sa.Unicode(20)),
    sa.Column("country_id", sa.String(2),
        sa.ForeignKey("country.country_id"),
        nullable=True
    ),
    sa.Column("phone", sa.Unicode(256)),
    sa.Column("fax", sa.Unicode(256)),
    sa.Column("email", sa.String(512)),
    # Workflow State -> determines visibility
    sa.Column("status", sa.Unicode(16)),
    sa.Column("status_date", sa.DateTime(timezone=False),
        server_default=sa.sql.text("now()"),
        nullable=False
    ),
)


##################
# Activity 
#

session = sa.Table("session", metadata,
    sa.Column("session_id", sa.Integer, primary_key=True),
    sa.Column("parliament_id", sa.Integer, # group_id
        sa.ForeignKey("parliament.parliament_id"),
        nullable=False
    ),
    sa.Column("short_name", sa.Unicode(512), nullable=False), #!+ACRONYM
    sa.Column("full_name", sa.Unicode(1024), nullable=False), #!+NAME
    sa.Column("start_date", sa.Date, nullable=False),
    sa.Column("end_date", sa.Date),
    sa.Column("notes", sa.UnicodeText),
    sa.Column("language", sa.String(5), nullable=False),
)

sitting = sa.Table("sitting", metadata,
    sa.Column("sitting_id", sa.Integer, primary_key=True),
    sa.Column("group_id", sa.Integer,
        sa.ForeignKey("group.group_id"),
        nullable=False
    ),
    sa.Column("session_id", sa.Integer,
        sa.ForeignKey("session.session_id"),
        nullable=True
    ),
    sa.Column("short_name", sa.Unicode(512), nullable=True),
    sa.Column("start_date", sa.DateTime(timezone=False), nullable=False),
    sa.Column("end_date", sa.DateTime(timezone=False), nullable=False),
    sa.Column("sitting_length", sa.Integer),
    # if a sitting is recurring this is the id of the original sitting
    # there is no foreign key to the original sitting
    # like sa.ForeignKey("sitting.sitting_id")
    # to make it possible to delete the original sitting
    sa.Column("recurring_id", sa.Integer),
    sa.Column("recurring_type", sa.String(32)),
    sa.Column("recurring_end_date", sa.DateTime(timezone=False), 
        nullable=True),
    
    sa.Column("status", sa.Unicode(48)),
    sa.Column("status_date", sa.DateTime(timezone=False),
        server_default=sa.sql.text("now()"),
        nullable=False
    ),
    # venue for the sitting
    sa.Column("venue_id", sa.Integer, sa.ForeignKey("venue.venue_id")),
    sa.Column("language", sa.String(5), nullable=False),
    # other vocabularies
    sa.Column("activity_type", sa.Unicode(1024)),
    sa.Column("meeting_type", sa.Unicode(1024)),
    sa.Column("convocation_type", sa.Unicode(1024)),
)

sitting_attendance = sa.Table("sitting_attendance", metadata,
    sa.Column("sitting_id", sa.Integer,
        sa.ForeignKey("sitting.sitting_id"),
        primary_key=True
    ),
    sa.Column("member_id", sa.Integer,
        sa.ForeignKey("user.user_id"),
        primary_key=True
    ),
    sa.Column("attendance_type", sa.Unicode(128),
        default=u'present',
        nullable=False,
    ),
)

# headings
heading = sa.Table("heading", metadata,
    sa.Column("heading_id", sa.Integer, primary_key=True),
    sa.Column("text", sa.Unicode(512), nullable=False),
    sa.Column("status", sa.Unicode(32)),
    sa.Column("language", sa.String(5), nullable=False),
    sa.Column("group_id", sa.Integer, sa.ForeignKey("group.group_id"))
)


# venues for sittings:

venue = sa.Table("venue", metadata,
    sa.Column("venue_id", sa.Integer, primary_key=True),
    sa.Column("short_name", sa.Unicode(512), nullable=False),
    sa.Column("description", sa.UnicodeText),
    sa.Column("language", sa.String(5), nullable=False),
    sa.Column("group_id", sa.Integer, sa.ForeignKey("group.group_id"))
)


''' !+BookedResources
# resources for sittings like rooms ...

resource_types = sa.Table("resource_types", metadata,
    sa.Column("resource_type_id", sa.Integer, primary_key=True),
    sa.Column("short_name", sa.Unicode(512), nullable=False), #!+ACRONYM
    sa.Column("language", sa.String(5), nullable=False),
)

resources = sa.Table("resources", metadata,
    sa.Column("resource_id", sa.Integer, primary_key=True),
    sa.Column("resource_type_id", sa.Integer,
        sa.ForeignKey("resource_types.resource_type_id"),
        nullable=False
    ),
    sa.Column("short_name", sa.Unicode(512), nullable=False),
    sa.Column("description", sa.UnicodeText),
    sa.Column("language", sa.String(5), nullable=False),
)

resourcebookings = sa.Table("resourcebookings", metadata,
    sa.Column("resource_id", sa.Integer,
        sa.ForeignKey("resources.resource_id"),
        primary_key=True
    ),
    sa.Column("sitting_id", sa.Integer,
        sa.ForeignKey("sitting.sitting_id"),
        primary_key=True
    ),
)
'''


item_vote = sa.Table("item_vote", metadata,
    sa.Column("vote_id", sa.Integer, primary_key=True),
    sa.Column("item_id", sa.Integer, # !+RENAME doc_id
        sa.ForeignKey("doc.doc_id"),
        nullable=False
    ),
    sa.Column("date", sa.Date),
    sa.Column("affirmative_vote", sa.Integer),
    sa.Column("negative_vote", sa.Integer),
    sa.Column("remarks", sa.UnicodeText),
    sa.Column("language", sa.String(5), nullable=False),
)

item_member_vote = sa.Table("item_member_vote", metadata,
    sa.Column("vote_id", sa.Integer,
        sa.ForeignKey("item_vote"),
        primary_key=True,
        nullable=False
    ),
    sa.Column("member_id", sa.Integer,
        sa.ForeignKey("user.user_id"),
        primary_key=True,
        nullable=False
    ),
    sa.Column("vote", sa.Boolean,),
)

item_schedule = sa.Table("item_schedule", metadata,
    sa.Column("schedule_id", sa.Integer, primary_key=True),
    sa.Column("item_id", sa.Integer, nullable=False),
    sa.Column("item_type", sa.String(30), nullable=False),
    sa.Column("sitting_id", sa.Integer,
        sa.ForeignKey("sitting.sitting_id"),
        nullable=False
    ),
    sa.Column("planned_order", sa.Integer),
    sa.Column("real_order", sa.Integer),
    # item was discussed on this sitting sitting
    sa.Column("active", sa.Boolean, default=True),
    # workflow status of the item for this schedule
    # NOT workflow status of this item_schedule!
    sa.Column("item_status", sa.Unicode(64),)
)

editorial_note = sa.Table("editorial_note", metadata,
    sa.Column("editorial_note_id", sa.Integer, primary_key=True),
    sa.Column("text", sa.UnicodeText, nullable=True),
    sa.Column("group_id", sa.Integer, sa.ForeignKey("group.group_id"),
        nullable=True
    ),
    sa.Column("language", sa.String(5), nullable=False)
)

# store text record for a sitting or 
agenda_text_record = sa.Table("agenda_text_record", metadata,
    sa.Column("text_record_id", sa.Integer, primary_key=True),
    sa.Column("text", sa.UnicodeText, nullable=False),
    sa.Column("record_type", sa.String(30), nullable=False),
    sa.Column("language", sa.String(5), nullable=False),
)

# to produce the proceedings:
# capture the discussion on this item

item_schedule_discussion = sa.Table("item_schedule_discussion", metadata,
    sa.Column("discussion_id", sa.Integer, primary_key=True),
    sa.Column("schedule_id", sa.Integer,
        sa.ForeignKey("item_schedule.schedule_id")),
    sa.Column("body", sa.UnicodeText),
    sa.Column("sitting_time", sa.Time(timezone=False)),
    sa.Column("language", sa.String(5),
        nullable=False,
        default="en"
    ),
)

item_schedule_vote = sa.Table("item_schedule_vote", metadata,
    sa.Column("vote_id", sa.Integer, primary_key=True),
    sa.Column("schedule_id", sa.Integer,
        sa.ForeignKey("item_schedule.schedule_id")),
    sa.Column("time", sa.Time(timezone=False)),
    sa.Column("issue_item", sa.Unicode(1024)),
    sa.Column("issue_sub_item", sa.Unicode(1024)),
    sa.Column("document_uri", sa.Unicode(1024)),
    sa.Column("question", sa.Unicode(1024)),
    sa.Column("description", sa.UnicodeText),
    sa.Column("notes", sa.UnicodeText),
    sa.Column("result", sa.Unicode(255)),
    sa.Column("vote_type", sa.Unicode(255)),
    sa.Column("majority_type", sa.Unicode(255)),
    sa.Column("eligible_votes", sa.Integer),
    sa.Column("cast_votes", sa.Integer),
    sa.Column("votes_for", sa.Integer),
    sa.Column("votes_against", sa.Integer),
    sa.Column("votes_abstained", sa.Integer),
    sa.Column("roll_call", FSBlob(32)),
    sa.Column("mimetype", sa.Unicode(127)),
    sa.Column("language", sa.String(5),
        nullable=False,
        default="en"
    ),
)

sitting_report = sa.Table("sitting_report", metadata,
    sa.Column("report_id", sa.Integer,
        sa.ForeignKey("doc.doc_id"), primary_key=True
    ),
    sa.Column("sitting_id", sa.Integer,
        sa.ForeignKey("sitting.sitting_id"), primary_key=True
    ),
)

''' !+SUBSCRIPTIONS(mr, jun-2012) unused
# generic subscriptions, to any type
subscriptions = sa.Table("object_subscriptions", metadata,
    sa.Column("subscriptions_id", sa.Integer, primary_key=True),
    sa.Column("object_id", sa.Integer, nullable=False),
    sa.Column("object_type", sa.String(32), nullable=False),
    sa.Column("party_id", sa.Integer, nullable=False),
    sa.Column("party_type", sa.String(32), nullable=False),
    sa.Column("last_delivery", sa.Date, nullable=False),
    # delivery period
    # sa.Column("delivery_period", sa.Integer),
    # delivery type
    # sa.Column("delivery_type", sa.Integer),
)
'''

# NOT a parliamentary_item
# !+doc_attachment
attachment = sa.Table("attachment", metadata,
    sa.Column("attachment_id", sa.Integer, primary_key=True),
    # the id of the "owning" head document
    # !+doc_attachment -- this assumes that attachments are only for doc?
    sa.Column("head_id", sa.Integer,
        sa.ForeignKey("doc.doc_id"),
        nullable=False
    ),
    # attachment_type #!+attached_file_type
    sa.Column("type", sa.Unicode(128),
        default=u"document",
        nullable=False,
    ),
    sa.Column("title", sa.Unicode(255), nullable=False), #!+file
    sa.Column("description", sa.UnicodeText), #!+file
    sa.Column("data", FSBlob(32)), #!+file
    sa.Column("name", sa.String(200)), #!+file
    sa.Column("mimetype", sa.String(127)), #!+file
    # Workflow State
    sa.Column("status", sa.Unicode(48)),
    sa.Column("status_date", sa.DateTime(timezone=False),
        server_default=sa.sql.text("now()"),
        nullable=False
    ),
    sa.Column("language", sa.String(5), nullable=False),
)
attachment_index = sa.Index("attachment_head_id_idx", attachment.c["head_id"])
attachment_audit = make_audit_table(attachment, metadata)


# Document:
# base table for a workflowed parliamentary document
doc_sequence = sa.Sequence("doc_sequence")
doc = sa.Table("doc", metadata,
    # DB id
    sa.Column("doc_id", sa.Integer, doc_sequence, primary_key=True),
    
    # PARLIAMENT
    # parliament <=> dc:Publisher
    # The entity responsible for making the resource available. 
    # Examples of a Publisher include a person, an organization, or a service.
    # Typically, the name of a Publisher should be used to indicate the entity.
    # !+CONTAINER_CUSTODIAN_GROUPS(mr, apr-2011) parliament_id and group_id are
    # conceptually distinct while still being related:
    # - the general sense of parliament_id seems to be that of the 
    # "root_container" group (currently this may only be a parliament) in 
    # which the doc "exists"
    # - while the general sense of group_id seems to be that of a kind of
    # "custodian" group, to which the doc is "assigned to" for handling.
    # !+PARLIAMENT_ID should be nullable=False, but fails on creating an Event...
    sa.Column("parliament_id", sa.Integer,
        sa.ForeignKey("parliament.parliament_id"),
        nullable=True
    ),
    # !+bicameral(mr, feb-2012) should parliament_id simply always be 
    # chamber_id, and then have the concept of a chamber group, each of which
    # related to the singleton parliament group?
    #sa.Column("origin_chamber_id", sa.Integer,
    #    sa.ForeignKey("groups.group_id"), # !+ group (singular), chamber
    #    nullable=True
    #),
    
    # OWNERSHIP
    # owner <=> no dc equivalent
    # The bungeni user that submits (either directly, or someone else submits 
    # on his/her behalf) the document to Parliament. This is the "data owner" 
    # of the item (and not necessarily the conceptual owner, that may be an 
    # entity outside of Parliament). 
    sa.Column("owner_id", sa.Integer,
        sa.ForeignKey("user.user_id"),
        nullable=False
    ),
    
    # !+dc:Creator / dc:Author, by default this would be owner, but we can 
    # sometimes have an external source as the creator of a resource e.g a 
    # 3rd party entity who prepared a tabled document, or a citizen/etc who 
    # suggested a question to an MP. See Issue 755.
    #sa.Column("creator", sa.Unicode(1024), nullable=True),
    # !+dc:Contributor, these are the signatories? external contributors?
    # !+seconder clarify usage (was on motion); always 1? overlapssignatories?
    #sa.Column("seconder_id", sa.Integer, sa.ForeignKey("user.user_id")),
    
    # TYPE
    # sub document type discriminator: string enum
    # for polymorphic_identity <=> dc:Type
    sa.Column("type", sa.Unicode(128), nullable=False),
    # document typology: string enum (set by sub document type) 
    # e.g. oral/written, government/member
    # For validation of this field, we let upstream logic e.g. UI fields
    # using zope.schema.Choice combined with a vocabulary, to take 
    # responsibilty of validating this for *this* document type.
    sa.Column("doc_type", sa.Unicode(128),
        default=None,
        nullable=True,
    ),
    # document procedure: string enum (set by sub document type) 
    # e.g. urgent/ordinary, private/public
    sa.Column("doc_procedure", sa.Unicode(128),
        default=None,
        nullable=True,
    ),
    
    # IDENTIFICATION
    # document number e.g question_num, bill_num... a progressive number by type
    # !+registry_number, what is the relation?
    sa.Column("type_number", sa.Integer, nullable=True),
    # registry_number <=> dc:Identifier
    # An unambiguous reference to the resource within a given context. 
    # Recommended best practice is to identify the resource by means of a 
    # string or number conforming to a formal identification system.
    sa.Column("registry_number", sa.Unicode(128)),
    # uri, Akoma Ntoso <=> dc:Source
    # A Reference to a resource from which the present resource is derived. 
    # The present resource may be derived from the Source resource in whole or 
    # part.
    sa.Column("uri", sa.Unicode(1024), nullable=True), 
    
    # CONTENT
    sa.Column("acronym", sa.Unicode(48)),
    # !+LABEL(mr, jan-2011) display label e.g. for link text?
    # title <=> dc:Title !+DescriptiveProperties(mr, jan-2011)
    # The name given to the resource. Typically, a Title will be a name
    # by which the resource is formally known.
    sa.Column("title", sa.Unicode(1024), nullable=False),
    # description <=> dc:Description !+DescriptiveProperties(mr, jan-2011)
    # An account of the content of the resource. Description may include but is
    # not limited to: an abstract, table of contents, reference to a graphical
    # representation of content or a free-text account of the content.
    sa.Column("description", sa.UnicodeText, nullable=True),
    # original language of the document
    sa.Column("language", sa.String(5), nullable=False),
    sa.Column("body", sa.UnicodeText),
    
    # WORKFLOW
    sa.Column("status", sa.Unicode(48)),
    sa.Column("status_date", sa.DateTime(timezone=False),
        server_default=sa.sql.text("now()"),
        nullable=False
    ),
    # group responsible to "handle" this document... involves workflow: the 
    # precise meaning, and validation constraints of this is defined by each 
    # sub-type e.g. ministry for bill & question, group for agendaitem, ...
    # !+CONTAINER_CUSTODIAN_GROUPS
    sa.Column("group_id", sa.Integer,
        sa.ForeignKey("group.group_id"),
        nullable=True
    ),
    
    # !+workflow_note/motivation, should be stored on the change table?
    # !+personal_note, should be elsewhere, see issue 646 
    # the reviewer may add a recommendation note
    #sa.Column("note", sa.UnicodeText),
    
    # NOTIFICATION
    #!+receive_notification, must certainly be made obsolete...
    # Receive  Notifications -> triggers notification on workflow change
    #sa.Column("receive_notification", sa.Boolean,
    #    default=True
    #),
    
    # COVERAGE
    # duration that a document may be about
    #sa.Column("timespan", nullable=True)
    # subject <=> dc:Subject
    # The topic of the content of the resource. Typically, a Subject will be 
    # expressed as keywords or key phrases or classification codes that describe
    # the topic of the resource. Recommended best practice is to select a value 
    # from a controlled vocabulary or formal classification scheme.
    # Hierarchical Controlled Vocabulary Micro Data Format: 
    # a triple-colon ":::" separated sequence of *key phrase paths*, each of 
    # which is a double-colon "::" separated sequence of *key phrases*.
    sa.Column("subject", sa.UnicodeText, nullable=True),
    # coverage <=> dc:Coverage
    # The extent or scope of the content of the resource. Coverage will 
    # typically include spatial location (a place name or geographic co-ords), 
    # temporal period (a period label, date, or date range) or jurisdiction 
    # (such as a named administrative entity). Recommended best practice is to 
    # select a value from a controlled vocabulary (for example, the Thesaurus 
    # of Geographic Names [Getty Thesaurus of Geographic Names, 
    # http://www.getty.edu/research/tools/vocabulary/tgn/]). Where appropriate, 
    # named places or time periods should be used in preference to numeric 
    # identifiers such as sets of co-ordinates or date ranges.
    # Value uses same micro format as for "subject".
    sa.Column("coverage", sa.UnicodeText, nullable=True),
    sa.Column("geolocation", sa.UnicodeText, nullable=True),
    # !+DC(mr, jan-2011) consider addition of:
    # - Format
    # - Date, auto derive from workflow audit log
    # - Rights
    # - Reference, citations of other resources, implied from body content? 
    # - Relation, e.g. assigned to a Committee
    
    # head document (for sub documents e.g. events)
    sa.Column("head_id", sa.Integer, 
        sa.ForeignKey("doc.doc_id"), 
        nullable=True,
    ),
    # (event only?) date, needed? auto derive from workflow audit log?
    #sa.Column("date", sa.DateTime(timezone=False),
    #    nullable=False
    #),
    
    # DB timestamp of last modification
    sa.Column("timestamp", sa.DateTime(timezone=False),
        server_default=sa.sql.text("now()"),
        nullable=False
    ),
)
doc_index = sa.Index("doc_status_idx", doc.c["status"])
doc_audit = make_audit_table(doc, metadata)


signatory = sa.Table("signatory", metadata,
    sa.Column("signatory_id", sa.Integer,
        primary_key=True
    ),
    # the id of the "owning" head document
    sa.Column("head_id", sa.Integer,
        sa.ForeignKey("doc.doc_id"),
        nullable=False,
    ),
    sa.Column("user_id", sa.Integer,
        sa.ForeignKey("user.user_id"),
        nullable=False,
    ),
    sa.Column("status", sa.Unicode(32)),
    sa.UniqueConstraint("head_id", "user_id")
)
signatory_audit = make_audit_table(signatory, metadata)


# Tabled documents:
# a tabled document captures metadata about the document (owner, date, title, 
# description) and can have multiple physical documents attached.
# 
# The tabled documents form should have the following :
# -Document title
# -Document link
# -Upload field (s)
# -Document source / author agency (who is providing the document)
# 
# -Document submitter (who is submitting the document - a person)
# It must be possible to schedule a tabled document for a sitting

#document_sources = sa.Table(
#    "document_sources",
#    metadata,
#    sa.Column("document_source_id", sa.Integer, primary_key=True),
#    sa.Column("document_source", sa.Unicode(256)),
#)


#######################
# Settings
#######################

setting = sa.Table("setting", metadata,
    sa.Column("setting_id", sa.Integer, primary_key=True),
    sa.Column("object_id", sa.Integer), # scope
    sa.Column("object_type", sa.String(50)),
    sa.Column("propertysheet", sa.String(50)),
    sa.Column("name", sa.String(50)),
    sa.Column("value", sa.String(400)),
    sa.Column("type", sa.String(40)),
)
setting_index = sa.Index("setting_propsheet_idx", 
    setting.c["propertysheet"]
)

holiday = sa.Table("holiday", metadata,
    sa.Column("holiday_id", sa.Integer, primary_key=True),
    sa.Column("date", sa.Date, nullable=False),
    sa.Column("name", sa.Unicode(1024)),
    sa.Column("language", sa.String(5), nullable=False),
)


translation = sa.Table("translation", metadata,
    sa.Column("object_id", sa.Integer, primary_key=True, nullable=False),
    sa.Column("object_type", sa.String(50), primary_key=True, nullable=False),
    sa.Column("lang", sa.String(5), primary_key=True, nullable=False),
    sa.Column("field_name", sa.String(50), primary_key=True, nullable=False),
    sa.Column("field_text", sa.UnicodeText),
)
translation_lookup_index = sa.Index("translation_lookup_index",
    translation.c.object_id,
    translation.c.object_type,
    translation.c.lang
)


time_based_notification = sa.Table("time_based_notification", metadata,
    sa.Column("notification_id", sa.Integer, primary_key=True),
    sa.Column("object_id", sa.Integer, primary_key=True, nullable=False),
    sa.Column("object_type", sa.String(50),
        primary_key=True, nullable=False),
    sa.Column("object_status", sa.Unicode(32)),
    sa.Column("time_string", sa.String(50),
        primary_key=True, nullable=False),
    sa.Column("notification_date_time", sa.DateTime(timezone=False),
        nullable=False)
)

debate_record = sa.Table("debate_record", metadata,
    sa.Column("debate_record_id", sa.Integer, primary_key=True),
    sa.Column("sitting_id", sa.Integer, sa.ForeignKey("sitting.sitting_id"),
        unique=True),
    # Workflow State
    sa.Column("status", sa.Unicode(32)),
    sa.Column("status_date", sa.DateTime(timezone=False),
        server_default=sa.sql.text("now()"),
        nullable=False
    ),
)
debate_record_audit = make_audit_table(debate_record, metadata)

debate_record_item = sa.Table("debate_record_item", metadata,
    sa.Column("debate_record_item_id", sa.Integer, primary_key=True),
    sa.Column("debate_record_id", sa.Integer,
        sa.ForeignKey("debate_record.debate_record_id")),
    sa.Column("type", sa.String(30), nullable=False),
    sa.Column("start_date", sa.DateTime(timezone=False), nullable=False),
    sa.Column("end_date", sa.DateTime(timezone=False), nullable=False),
)
debate_record_item_audit = make_audit_table(debate_record_item, metadata)

debate_doc = sa.Table("debate_doc", metadata,
    sa.Column("debate_doc_id", sa.Integer,
        sa.ForeignKey("debate_record_item.debate_record_item_id"),
        primary_key=True),
    sa.Column("doc_id", sa.Integer, sa.ForeignKey("doc.doc_id"))
)

debate_speech = sa.Table("debate_speech", metadata,
    sa.Column("debate_speech_id", sa.Integer,
        sa.ForeignKey("debate_record_item.debate_record_item_id"),
        primary_key=True, unique=True),
    # require that all the speakers must have a user record in the system
    # users that are not MPs or staff can have a user record that is not active
    sa.Column("person_id", sa.ForeignKey("user.user_id")),
    sa.Column("text", sa.UnicodeText),
    # Workflow State
    sa.Column("status", sa.Unicode(32)),
    sa.Column("status_date", sa.DateTime(timezone=False),
        server_default=sa.sql.text("now()"),
        nullable=False
    ),
    sa.Column("language", sa.String(5), nullable=False)
)

debate_media = sa.Table("debate_media", metadata,
    sa.Column("debate_record_id", sa.Integer,
        sa.ForeignKey("debate_record.debate_record_id"), primary_key=True),
    sa.Column("media_id", sa.Integer, primary_key=True),
    sa.Column("media_path", sa.UnicodeText, nullable=False),
    sa.Column("media_type", sa.String(100), nullable=False)
)

debate_take = sa.Table("debate_take", metadata,
    sa.Column("debate_record_id", sa.Integer,
        sa.ForeignKey("debate_record.debate_record_id"), primary_key=True),
    sa.Column("debate_take_id", sa.Integer, primary_key=True),
    sa.Column("start_date", sa.DateTime(timezone=False), nullable=False),
    sa.Column("end_date", sa.DateTime(timezone=False), nullable=False),
    sa.Column("transcriber_id", sa.Integer, 
        sa.ForeignKey("user.user_id")),
    sa.Column("debate_take_name", sa.String(100), nullable=False)
)


# OAuth

oauth_application = sa.Table("oauth_application", metadata,
    sa.Column("application_id", sa.Integer, primary_key=True),
    sa.Column("identifier", sa.UnicodeText, nullable=False, 
        unique=True),
    sa.Column("name", sa.UnicodeText, nullable=False),
    sa.Column("secret", sa.String(100), nullable=False),
    sa.Column("redirection_endpoint", sa.UnicodeText, nullable=False)
)

oauth_authorization = sa.Table("oauth_authorization", metadata,
    sa.Column("authorization_id", sa.Integer, primary_key=True),
    sa.Column("user_id", sa.Integer, sa.ForeignKey("user.user_id"),
        nullable=False),
    sa.Column("application_id", sa.Integer,
        sa.ForeignKey("oauth_application.application_id"), nullable=False),
    sa.Column("active", sa.Boolean(), nullable=False)
)

oauth_authorization_token = sa.Table("oauth_authorization_token", metadata,
    sa.Column("authorization_token_id", sa.Integer, primary_key=True),
    sa.Column("authorization_id", sa.Integer, sa.ForeignKey(
        "oauth_authorization.authorization_id"), nullable=False),
    sa.Column("authorization_code", sa.String(100), nullable=False),
    sa.Column("expiry", sa.DateTime(timezone=False), nullable=False),
    sa.Column("refresh_token", sa.String(100), nullable=False),
)

oauth_access_token = sa.Table("oauth_access_token", metadata,
    sa.Column("access_token_id", sa.Integer, primary_key=True),
    sa.Column("authorization_token_id", sa.Integer,
        sa.ForeignKey("oauth_authorization_token.authorization_token_id"),
        nullable=False
    ),
    sa.Column("access_token", sa.String(100), nullable=False),
    sa.Column("expiry", sa.DateTime(timezone=False), nullable=False),
)

#for table_name in metadata.tables.keys():
#    print metadata.tables[table_name].name


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        db_uri = "sqlite://"
    elif len(sys.argv) != 2:
        print "schema.py DATABASE_URL"
        sys.exit(1)
    else:
        db_uri = sys.argv[1]

        db_uri = "sqlite://"
    db = sa.create_engine(db_uri, echo=True)
    metadata.bind = db

    try:
        metadata.drop_all()
        metadata.create_all()
    except:
        import pdb, traceback, sys
        traceback.print_exc()
        pdb.post_mortem(sys.exc_info()[-1])

