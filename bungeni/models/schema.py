# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""The Bungeni relational schema

$Id$
"""
log = __import__("logging").getLogger("bungeni.models.schema")

import sqlalchemy as rdb
from fields import FSBlob
from sqlalchemy.sql import text #, functions #!+CATALYSE(mr, nov-2010)
from datetime import datetime


metadata = rdb.MetaData()


# users and groups because of the zope users and groups
PrincipalSequence = rdb.Sequence("principal_sequence")


# vertical properties

vp_text = rdb.Table("vp_text", metadata,
    rdb.Column("object_id", rdb.Integer, primary_key=True, nullable=False),
    rdb.Column("object_type", rdb.String(32), primary_key=True, nullable=False),
    rdb.Column("name", rdb.String(50), primary_key=True, nullable=False,),
    rdb.Column("value", rdb.UnicodeText),
)
vp_translated_text = rdb.Table("vp_translated_text", metadata,
    rdb.Column("object_id", rdb.Integer, primary_key=True, nullable=False),
    rdb.Column("object_type", rdb.String(32), primary_key=True, nullable=False),
    rdb.Column("name", rdb.String(50), primary_key=True, nullable=False,),
    rdb.Column("value", rdb.UnicodeText),
    rdb.Column("language", rdb.String(5), nullable=False),
)


# audit 

# generic change information
change = rdb.Table("change", metadata,
    rdb.Column("audit_id", rdb.Integer, 
        rdb.ForeignKey("audit.audit_id"),
        primary_key=True),
    rdb.Column("user_id", rdb.Integer, rdb.ForeignKey("users.user_id"), 
        nullable=False),
    rdb.Column("action", rdb.Unicode(16), nullable=False),
    # accumulative count, per (change.audit.audit_head_id, change.action) 
    # e.g default: 1 + max(seq(head, "version")), see ui.audit _get_seq()
    rdb.Column("seq", rdb.Integer, nullable=False),
    rdb.Column("procedure", rdb.String(1), default="a", nullable=False),
    # audit datetime, exclusively managed by the system, real datetime of 
    # when change was actually affected
    rdb.Column("date_audit", rdb.DateTime(timezone=False),
        #!+CATALYSE(mr, nov-2010) fails descriptor catalisation
        #default=functions.current_timestamp(),
        server_default=text("now()"),
        nullable=False
    ),
    # user-modifiable effective datetime (defaults to audit_time);
    # this is the datetime to be used for all intents and purposes other 
    # than for "forensic" data auditing
    rdb.Column("date_active", rdb.DateTime(timezone=False),
        #!+CATALYSE(mr, nov-2010)
        #default=functions.current_timestamp(),
        server_default=text("now()"),
        nullable=False
    ),
    
    #rdb.Column("description", rdb.UnicodeText), #!+dynamic at runtime
    # possible explanatory note/remark/comment/observation/recommendation/etc 
    # about the change, manually added by the user; this is part of the 
    # audit history of a document and visible to all who have access to this
    # change record.
    # Workflow State at time of change - visibility of a change record 
    # depends on permissions of parent object in this specific state.
    
    #rdb.Column("status", rdb.Unicode(48)), # !+ use audit.status?
    # !+presumably already on head for when audit_head is itself a sub-document 
    # e.g. events, as knowing the status of also the "root" head document may 
    # be necessary to determine allowed access for *this* change record
    
    #rdb.Column("root_status", rdb.Unicode(48)),
)
# tree to relate change actions across parent and child objects 
# e.g. to snapshot a version tree of an object and its sub-objects. 
# Constraint: all related changes must be of same "action".
change_tree = rdb.Table("change_tree", metadata,
    rdb.Column("parent_id", rdb.Integer, 
        rdb.ForeignKey("change.audit_id"), 
        primary_key=True,
    ),
    rdb.Column("child_id", rdb.Integer, 
        rdb.ForeignKey("change.audit_id"), 
        primary_key=True,
    ),
    rdb.CheckConstraint("""parent_id != child_id""", 
        name="change_tree_check_not_same",
    ),
    #!+rdb.CheckConstraint(parent.change.action == child.change.action),
)

audit_sequence = rdb.Sequence("audit_sequence")
audit = rdb.Table("audit", metadata,
    rdb.Column("audit_id", rdb.Integer, audit_sequence, primary_key=True),
    # audit_type, for polymorphic_identity
    rdb.Column("audit_type", rdb.String(30), nullable=False),
)

def make_audit_table(table, metadata):
    """Create an audit log table for an archetype.
    
    We prefix all additional audit-specific columns with "audit_" to avoid 
    potential clashing of column names from table being audited.
    """
    entity_name = table.name
    audit_tbl_name = "%s_audit" % (entity_name)
    columns = [
        rdb.Column("audit_id", rdb.Integer, 
            rdb.ForeignKey("audit.audit_id"), 
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
                    rdb.Column(c.name, rdb.Integer, 
                        rdb.ForeignKey(table.c[c.name]),
                        nullable=False,
                        index=True
                    )),
    extend_cols(columns, table.columns)
    # !+additional tables...
    audit_tbl = rdb.Table(audit_tbl_name, metadata, *columns,
        useexisting=False
    )
    return audit_tbl


'''
def make_vocabulary_table(vocabulary_prefix, metadata, table_suffix="_types",
        column_suffix="_type"
    ):
    table_name = "%s%s" % (vocabulary_prefix, table_suffix)
    column_key = "%s%s_id" % (vocabulary_prefix, column_suffix)
    column_name = "%s%s_name" % (vocabulary_prefix , column_suffix)
    return rdb.Table(table_name, metadata,
        rdb.Column(column_key, rdb.Integer, primary_key=True),
        rdb.Column(column_name, rdb.Unicode(256),
            nullable=False,
            unique=True
        ),
        rdb.Column("language", rdb.String(5), nullable=False),
    )
'''

#######################
# Users 
#######################

users = rdb.Table("users", metadata,
    rdb.Column("user_id", rdb.Integer, PrincipalSequence, primary_key=True),
    # login is our principal id
    rdb.Column("login", rdb.Unicode(80), unique=True, nullable=True),
    rdb.Column("titles", rdb.Unicode(32)),
    rdb.Column("first_name", rdb.Unicode(256), nullable=False),
    rdb.Column("last_name", rdb.Unicode(256), nullable=False),
    rdb.Column("middle_name", rdb.Unicode(256)),
    rdb.Column("email", rdb.String(512), nullable=False),
    rdb.Column("gender", rdb.String(1),
        rdb.CheckConstraint("""gender in ('M', 'F')""")  # (M)ale (F)emale
    ),
    rdb.Column("date_of_birth", rdb.Date),
    rdb.Column("birth_country", rdb.String(2),
        rdb.ForeignKey("countries.country_id")
    ),
    rdb.Column("birth_nationality", rdb.String(2),
        rdb.ForeignKey("countries.country_id")
    ),
    rdb.Column("current_nationality", rdb.String(2),
        rdb.ForeignKey("countries.country_id")
    ),
    rdb.Column("uri", rdb.Unicode(1024), unique=True),
    rdb.Column("date_of_death", rdb.Date),
    rdb.Column("type_of_id", rdb.String(1)),
    rdb.Column("national_id", rdb.Unicode(256)),
    rdb.Column("password", rdb.String(36)
        # we store salted md5 hash hexdigests
    ),
    rdb.Column("salt", rdb.String(24)),
    rdb.Column("description", rdb.UnicodeText),
    rdb.Column("image", rdb.Binary),
    # !+active_p(mr, sep-2011) why is this "workflow status" column named
    # "active_p" and not "status"? Rename...
    # !+active_p(mr, sep-2011) why have identically named columns here and on 
    # group_memberships, with one being a string and other a bool?
    rdb.Column("active_p", rdb.String(1),
        rdb.CheckConstraint("""active_p in ('A', 'I', 'D')"""),
        # !+active_p(mr, sep-2011) workflow status columns MUST not have a
        # default value--it is up to the workflow to decide what this should be!
        #default="A", # active/inactive/deceased
    ),
    # comment out for now - will be used for user preferences
    rdb.Column("receive_notification", rdb.Boolean, default=True),
    rdb.Column("language", rdb.String(5), nullable=False),
)

admin_users = rdb.Table("admin_users", metadata,
    rdb.Column("user_id", rdb.Integer,
        rdb.ForeignKey("users.user_id"),
        primary_key=True,
    )
)

# associations table for many-to-many relation between user and doc
user_doc = rdb.Table("user_doc", metadata,
    rdb.Column("users_id", rdb.Integer,
        rdb.ForeignKey("users.user_id")
    ),
    rdb.Column("doc_id", rdb.Integer,
        rdb.ForeignKey("doc.doc_id")
    )
)

# delegate rights to act on behalf of a user to another user
user_delegations = rdb.Table("user_delegations", metadata,
    rdb.Column("user_id", rdb.Integer,
        rdb.ForeignKey("users.user_id"),
        primary_key=True
    ),
    rdb.Column("delegation_id", rdb.Integer,
        rdb.ForeignKey("users.user_id"),
        primary_key=True
    )
)

# document that user is being currently editing
currently_editing_document = rdb.Table("currently_editing_document", metadata,
    rdb.Column("user_id", rdb.Integer,
        rdb.ForeignKey("users.user_id"),
        primary_key=True # !+ so, a user can only edit only ONE document at a TIME ?!?!?!?!?
    ),
    rdb.Column("currently_editing_id", rdb.Integer,
        rdb.ForeignKey("doc.doc_id"),
        nullable=False,
    ),
    rdb.Column("editing_date", rdb.DateTime(timezone=False)) 
)

#!+TYPES_CUSTOM member_election_types = make_vocabulary_table("member_election", metadata)

# password restore links
password_restore_link = rdb.Table("password_restore_link", metadata,
    rdb.Column("user_id", rdb.Integer,
        rdb.ForeignKey("users.user_id"),
        primary_key=True
    ),
    rdb.Column("hash", rdb.Unicode(256), nullable=False),
    rdb.Column("expiration_date", rdb.DateTime(timezone=False), nullable=False) 
) 


# specific user classes
parliament_memberships = rdb.Table("parliament_memberships", metadata,
    rdb.Column("membership_id", rdb.Integer,
        rdb.ForeignKey("user_group_memberships.membership_id"),
        primary_key=True
    ),
    # The region/province/constituency (divisions and order may be in any way 
    # as appropriate for the given parliamentary territory) for the 
    # representation of this member of parliament.
    # Hierarchical Controlled Vocabulary Micro Data Format: 
    # a triple-colon ":::" separated sequence of *key phrase paths*, each of 
    # which is a double-colon "::" separated sequence of *key phrases*.
    rdb.Column("representation", rdb.UnicodeText, nullable=True),
    # the political party of the MP as of the time he was elected
    rdb.Column("party", rdb.UnicodeText, nullable=True),
    # is the MP elected, nominated, ex officio member, ...
    rdb.Column("member_election_type",
        rdb.Unicode(128),
        default="elected",
        nullable=False,
    ),
    rdb.Column("election_nomination_date", rdb.Date), # nullable=False),
    rdb.Column("leave_reason", rdb.Unicode(40)),
)


#########################
# Countries
#########################

countries = rdb.Table("countries", metadata,
    rdb.Column("country_id", rdb.String(2), primary_key=True),
    rdb.Column("iso_name", rdb.Unicode(80), nullable=False),
    rdb.Column("country_name", rdb.Unicode(80), nullable=False),
    rdb.Column("iso3", rdb.String(3)),
    rdb.Column("numcode", rdb.Integer),
    rdb.Column("language", rdb.String(5), nullable=False),
)

#######################
# Groups
#######################
# we"re using a very normalized form here to represent all kinds of
# groups and their relations to other things in the system.

groups = rdb.Table("groups", metadata,
    rdb.Column("group_id", rdb.Integer, PrincipalSequence, primary_key=True),
    rdb.Column("short_name", rdb.Unicode(512), nullable=False),
    rdb.Column("full_name", rdb.Unicode(1024)),
    rdb.Column("acronym", rdb.Unicode(32), nullable=True),
    rdb.Column("identifier", rdb.Unicode(32), nullable=True),
    rdb.Column("description", rdb.UnicodeText),
    # Workflow State
    rdb.Column("status", rdb.Unicode(32)),
    rdb.Column("status_date", rdb.DateTime(timezone=False),
        server_default=text("now()"),
        nullable=False
    ),
    rdb.Column("start_date", rdb.Date, nullable=False),
    rdb.Column("end_date", rdb.Date),
    rdb.Column("type", rdb.String(30), nullable=False),
    rdb.Column("sub_type", rdb.Unicode(128), nullable=True),
    # !+GROUP_PRINCIPAL_ID(ah,sep-2011) adding group principal id to schema
    rdb.Column("group_principal_id", rdb.Unicode(50)),
    rdb.Column("parent_group_id", rdb.Integer,
        rdb.ForeignKey("groups.group_id")
     ),
     rdb.Column("language", rdb.String(5), nullable=False),
    
    #custom fields
    rdb.Column("custom1", rdb.UnicodeText, nullable=True),
    rdb.Column("custom2", rdb.UnicodeText, nullable=True),
    rdb.Column("custom3", rdb.UnicodeText, nullable=True),
    rdb.Column("custom4", rdb.UnicodeText, nullable=True),
)
# !+GROUP_PRINCIPAL_ID(ah,sep-2011) adding index on group_principal_id column
groups_principal_id_index = rdb.Index("grp_grpprincipalid_idx", 
    groups.c["group_principal_id"]
)

offices = rdb.Table("offices", metadata,
    rdb.Column("office_id", rdb.Integer,
        rdb.ForeignKey("groups.group_id"),
        primary_key=True),
    #The role that members of this office will get
    rdb.Column("office_role", rdb.Unicode(256),
        nullable=False,
        unique=True
    ),
)

parliaments = rdb.Table("parliaments", metadata,
    rdb.Column("parliament_id", rdb.Integer,
        rdb.ForeignKey("groups.group_id"),
        primary_key=True
    ),
   rdb.Column("election_date", rdb.Date, nullable=False),
)

''' !+TYPES_CUSTOM
committee_type_status = make_vocabulary_table("committee_type_status", metadata,
    table_suffix="", column_suffix="")
committee_type = rdb.Table("committee_types", metadata,
    rdb.Column("committee_type_id", rdb.Integer, primary_key=True),
    rdb.Column("committee_type", rdb.Unicode(256), nullable=False),
    rdb.Column("description", rdb.UnicodeText),
    rdb.Column("life_span", rdb.Unicode(16)),
    rdb.Column("committee_type_status_id", rdb.Integer,
        rdb.ForeignKey("committee_type_status.committee_type_status_id"),
        nullable=False
    ),
    rdb.Column("language", rdb.String(5), nullable=False),
)
'''

committees = rdb.Table("committees", metadata,
    rdb.Column("committee_id", rdb.Integer,
        rdb.ForeignKey("groups.group_id"),
        primary_key=True
    ),
    rdb.Column("group_continuity",
        rdb.Unicode(128),
        default="permanent",
        nullable=False,
    ),
    rdb.Column("num_members", rdb.Integer),
    rdb.Column("min_num_members", rdb.Integer),
    rdb.Column("quorum", rdb.Integer),
    rdb.Column("num_clerks", rdb.Integer),
    rdb.Column("num_researchers", rdb.Integer),
    rdb.Column("proportional_representation", rdb.Boolean),
    rdb.Column("default_chairperson", rdb.Boolean),
    rdb.Column("reinstatement_date", rdb.Date),
)
# !+TYPES_CUSTOM_life_span(mr, oct-2011) the old and unused column "life_span" 
# on committee_types (values: "parliament", "annual"). But, if concept will
# still be needed, the planned and more generic "group.root_container" idea 
# can approximately provide it, and is what should be used. 


# political group (inside the parliament)
political_group = rdb.Table("political_group", metadata,
    rdb.Column("group_id", rdb.Integer,
        rdb.ForeignKey("groups.group_id"), primary_key=True),
    rdb.Column("logo_data", rdb.Binary),
    rdb.Column("logo_name", rdb.String(127)),
    rdb.Column("logo_mimetype", rdb.String(127)),
)

###
#  the personal role of a user in terms of their membership this group
#  The personal roles a person may have varies with the context. In a party
#  one may have the role spokesperson, member, ...

title_types = rdb.Table("title_types", metadata,
    rdb.Column("title_type_id", rdb.Integer, primary_key=True),
    rdb.Column("group_id", rdb.Integer, 
                rdb.ForeignKey("groups.group_id"), nullable=False),
    rdb.Column("role_id", rdb.Unicode(256), nullable=True),
    rdb.Column("title_name", rdb.Unicode(40), nullable=False),
    rdb.Column("user_unique", rdb.Boolean, default=False,), # nullable=False),
    rdb.Column("sort_order", rdb.Integer(2), nullable=False),
    rdb.Column("language", rdb.String(5), nullable=False),
)

#
# group memberships encompasses any user participation in a group, including
# substitutions.

user_group_memberships = rdb.Table("user_group_memberships", metadata,
    rdb.Column("membership_id", rdb.Integer, primary_key=True),
    rdb.Column("user_id", rdb.Integer,
        rdb.ForeignKey("users.user_id"),
        nullable=False
    ),
    rdb.Column("group_id", rdb.Integer,
        rdb.ForeignKey("groups.group_id"),
        nullable=False
    ),
    # Workflow State
    rdb.Column("status", rdb.Unicode(32)),
    rdb.Column("status_date", rdb.DateTime(timezone=False),
        server_default=text("now()"),
        nullable=False
    ),
    rdb.Column("start_date", rdb.Date,
        default=datetime.now,
        nullable=False
    ),
    rdb.Column("end_date", rdb.Date),
    rdb.Column("notes", rdb.UnicodeText),
    # we use this as an easier query to end_date in queries, needs to be set by
    # a cron process against end_date < current_time
    rdb.Column("active_p", rdb.Boolean, default=True),
    # these fields are only present when a membership is result of substitution
    # unique because you can only replace one specific group member.
    rdb.Column("replaced_id", rdb.Integer,
        rdb.ForeignKey("user_group_memberships.membership_id"),
        unique=True
    ),
    rdb.Column("substitution_type", rdb.Unicode(100)),
    # type of membership staff or member
    rdb.Column("membership_type", rdb.String(30),
        default="member",
        #nullable=False,
    ),
    rdb.Column("language", rdb.String(5), nullable=False),
)

##############
# Titles
##############
# To indicate the role a persons has in a specific context (Ministry, 
# Committee, Parliament, ...) and for what period (from - to)

member_titles = rdb.Table("member_titles", metadata,
    rdb.Column("member_title_id", rdb.Integer, primary_key=True),
    rdb.Column("membership_id", rdb.Integer,
        rdb.ForeignKey("user_group_memberships.membership_id"),
        nullable=False
    ),
    # title of user"s group role
    rdb.Column("title_type_id", rdb.Integer,
        rdb.ForeignKey("title_types.title_type_id"),
        nullable=False
    ),
    rdb.Column("start_date", rdb.Date, default=datetime.now, nullable=False),
    rdb.Column("end_date", rdb.Date),
    rdb.Column("language", rdb.String(5), nullable=False),
)


############
# Addresses
############

''' !+TYPES_CUSTOM 
address_types = rdb.Table("address_types", metadata,
    rdb.Column("address_type_id", rdb.Integer, primary_key=True),
    rdb.Column("address_type_name", rdb.Unicode(40)),
    rdb.Column("language", rdb.String(5), nullable=False),
)
postal_address_types = make_vocabulary_table("postal_address", metadata)
'''

def _make_address_table(metadata, fk_key="user"):
    assert fk_key in ("user", "group")
    table_name = "%s_addresses" % (fk_key) # e.g. user_addresses
    fk_col_name = "%s_id" % (fk_key) # e.g. user_id
    fk_target = "%ss.%s_id" % (fk_key, fk_key) # e.g. users.user_id
    return rdb.Table(table_name, metadata,
        rdb.Column("address_id", rdb.Integer, primary_key=True),
        # user|personal or group|official addresses
        rdb.Column(fk_col_name, rdb.Integer,
            rdb.ForeignKey(fk_target),
            nullable=False
        ),
        rdb.Column("logical_address_type",
            rdb.Unicode(128),
            default="office",
            nullable=False,
        ),
        rdb.Column("postal_address_type",
            rdb.Unicode(128),
            default="street",
            nullable=False,
        ),
        rdb.Column("street", rdb.Unicode(256), nullable=False),
        rdb.Column("city", rdb.Unicode(256), nullable=False),
        rdb.Column("zipcode", rdb.Unicode(20)),
        rdb.Column("country_id", rdb.String(2),
            rdb.ForeignKey("countries.country_id"),
            nullable=False
        ),
        rdb.Column("phone", rdb.Unicode(256)),
        rdb.Column("fax", rdb.Unicode(256)),
        rdb.Column("email", rdb.String(512)),
        # Workflow State -> determins visibility
        rdb.Column("status", rdb.Unicode(16)),
        rdb.Column("status_date", rdb.DateTime(timezone=False),
            server_default=text("now()"),
            nullable=False
        ),
    )
group_addresses = _make_address_table(metadata, "group")
user_addresses = _make_address_table(metadata, "user")


##################
# Activity 
#

sessions = rdb.Table("sessions", metadata,
    rdb.Column("session_id", rdb.Integer, primary_key=True),
    rdb.Column("parliament_id", rdb.Integer, # group_id
        rdb.ForeignKey("parliaments.parliament_id"),
        nullable=False
    ),
    rdb.Column("short_name", rdb.Unicode(512), nullable=False), #!+ACRONYM
    rdb.Column("full_name", rdb.Unicode(1024), nullable=False), #!+NAME
    rdb.Column("start_date", rdb.Date, nullable=False),
    rdb.Column("end_date", rdb.Date),
    rdb.Column("notes", rdb.UnicodeText),
    rdb.Column("language", rdb.String(5), nullable=False),
)

sitting = rdb.Table("sitting", metadata,
    rdb.Column("sitting_id", rdb.Integer, primary_key=True),
    rdb.Column("group_id", rdb.Integer,
        rdb.ForeignKey("groups.group_id"),
        nullable=False
    ),
    rdb.Column("short_name", rdb.Unicode(512), nullable=True),
    rdb.Column("start_date", rdb.DateTime(timezone=False), nullable=False),
    rdb.Column("end_date", rdb.DateTime(timezone=False), nullable=False),
    rdb.Column("sitting_length", rdb.Integer),
    # if a sitting is recurring this is the id of the original sitting
    # there is no foreign key to the original sitting
    # like rdb.ForeignKey("sitting.sitting_id")
    # to make it possible to delete the original sitting
    rdb.Column("recurring_id", rdb.Integer),
    rdb.Column("recurring_type", rdb.String(32)),
    rdb.Column("status", rdb.Unicode(48)),
    rdb.Column("status_date", rdb.DateTime(timezone=False),
        server_default=text("now()"),
        nullable=False
    ),
    # venue for the sitting
    rdb.Column("venue_id", rdb.Integer, rdb.ForeignKey("venues.venue_id")),
    rdb.Column("language", rdb.String(5), nullable=False),
    # other vocabularies
    rdb.Column("activity_type", rdb.Unicode(1024)),
    rdb.Column("meeting_type", rdb.Unicode(1024)),
    rdb.Column("convocation_type", rdb.Unicode(1024)),
)

sitting_attendance = rdb.Table("sitting_attendance", metadata,
    rdb.Column("sitting_id", rdb.Integer,
        rdb.ForeignKey("sitting.sitting_id"),
        primary_key=True
    ),
    rdb.Column("member_id", rdb.Integer,
        rdb.ForeignKey("users.user_id"),
        primary_key=True
    ),
    rdb.Column("attendance_type",
        rdb.Unicode(128),
        default="present",
        nullable=False,
    ),
)

# headings
headings = rdb.Table("headings", metadata,
    rdb.Column("heading_id", rdb.Integer, primary_key=True),
    rdb.Column("text", rdb.Unicode(512), nullable=False),
    rdb.Column("status", rdb.Unicode(32)),
    rdb.Column("language", rdb.String(5), nullable=False),
    rdb.Column("group_id", rdb.Integer, rdb.ForeignKey("groups.group_id"))
)

''' !+TYPES_CUSTOM
attendance_types = rdb.Table("attendance_types", metadata,
    rdb.Column("attendance_type_id", rdb.Integer, primary_key=True),
    rdb.Column("attendance_type", rdb.Unicode(40), nullable=False),
    rdb.Column("language", rdb.String(5), nullable=False),
)
'''

# venues for sittings:

venues = rdb.Table("venues", metadata,
    rdb.Column("venue_id", rdb.Integer, primary_key=True),
    rdb.Column("short_name", rdb.Unicode(512), nullable=False),
    rdb.Column("description", rdb.UnicodeText),
    rdb.Column("language", rdb.String(5), nullable=False),
)


''' !+BookedResources
# resources for sittings like rooms ...

resource_types = rdb.Table("resource_types", metadata,
    rdb.Column("resource_type_id", rdb.Integer, primary_key=True),
    rdb.Column("short_name", rdb.Unicode(512), nullable=False), #!+ACRONYM
    rdb.Column("language", rdb.String(5), nullable=False),
)

resources = rdb.Table("resources", metadata,
    rdb.Column("resource_id", rdb.Integer, primary_key=True),
    rdb.Column("resource_type_id", rdb.Integer,
        rdb.ForeignKey("resource_types.resource_type_id"),
        nullable=False
    ),
    rdb.Column("short_name", rdb.Unicode(512), nullable=False),
    rdb.Column("description", rdb.UnicodeText),
    rdb.Column("language", rdb.String(5), nullable=False),
)

resourcebookings = rdb.Table("resourcebookings", metadata,
    rdb.Column("resource_id", rdb.Integer,
        rdb.ForeignKey("resources.resource_id"),
        primary_key=True
    ),
    rdb.Column("sitting_id", rdb.Integer,
        rdb.ForeignKey("sitting.sitting_id"),
        primary_key=True
    ),
)
'''

#######################
# Parliament
#######################

item_votes = rdb.Table("item_votes", metadata,
    rdb.Column("vote_id", rdb.Integer, primary_key=True),
    rdb.Column("item_id", rdb.Integer, # !+RENAME doc_id
        rdb.ForeignKey("doc.doc_id"),
        nullable=False
    ),
    rdb.Column("date", rdb.Date),
    rdb.Column("affirmative_votes", rdb.Integer),
    rdb.Column("negative_votes", rdb.Integer),
    rdb.Column("remarks", rdb.UnicodeText),
    rdb.Column("language", rdb.String(5), nullable=False),
)

item_member_votes = rdb.Table("item_member_votes", metadata,
    rdb.Column("vote_id", rdb.Integer,
        rdb.ForeignKey("item_votes"),
        primary_key=True,
        nullable=False
    ),
    rdb.Column("member_id", rdb.Integer,
        rdb.ForeignKey("users.user_id"),
        primary_key=True,
        nullable=False
    ),
    rdb.Column("vote", rdb.Boolean,),
)

item_schedules = rdb.Table("item_schedules", metadata,
    rdb.Column("schedule_id", rdb.Integer, primary_key=True),
    rdb.Column("item_id", rdb.Integer, nullable=False),
    rdb.Column("item_type", rdb.String(30), nullable=False),
    rdb.Column("sitting_id", rdb.Integer,
        rdb.ForeignKey("sitting.sitting_id"),
        nullable=False
    ),
    rdb.Column("planned_order", rdb.Integer,
        rdb.Sequence("planned_order", 1, 1)
    ),
    rdb.Column("real_order", rdb.Integer),
    # item was discussed on this sitting sitting
    rdb.Column("active", rdb.Boolean, default=True),
    # workflow status of the item for this schedule
    # NOT workflow status of this item_schedule!
    rdb.Column("item_status", rdb.Unicode(64),)
)

editorial_note = rdb.Table("editorial_note", metadata,
    rdb.Column("editorial_note_id", rdb.Integer, primary_key=True),
    rdb.Column("text", rdb.UnicodeText, nullable=True),
    rdb.Column("group_id", rdb.Integer, rdb.ForeignKey("groups.group_id"),
        nullable=True
    ),
    rdb.Column("language", rdb.String(5), nullable=False)
)

# to produce the proceedings:
# capture the discussion on this item

item_schedule_discussions = rdb.Table("item_schedule_discussions", metadata,
    rdb.Column("discussion_id", rdb.Integer, primary_key=True),
    rdb.Column("schedule_id", rdb.Integer,
        rdb.ForeignKey("item_schedules.schedule_id"),),
    rdb.Column("body", rdb.UnicodeText),
    rdb.Column("sitting_time", rdb.Time(timezone=False)),
    rdb.Column("language", rdb.String(5),
        nullable=False,
        default="en"
    ),
)

sitting_report = rdb.Table("sitting_report", metadata,
    rdb.Column("report_id", rdb.Integer,
        rdb.ForeignKey("doc.doc_id"), primary_key=True
    ),
    rdb.Column("sitting_id", rdb.Integer,
        rdb.ForeignKey("sitting.sitting_id"), primary_key=True
    ),
)

''' !+SUBSCRIPTIONS(mr, jun-2012) unused
# generic subscriptions, to any type
subscriptions = rdb.Table("object_subscriptions", metadata,
    rdb.Column("subscriptions_id", rdb.Integer, primary_key=True),
    rdb.Column("object_id", rdb.Integer, nullable=False),
    rdb.Column("object_type", rdb.String(32), nullable=False),
    rdb.Column("party_id", rdb.Integer, nullable=False),
    rdb.Column("party_type", rdb.String(32), nullable=False),
    rdb.Column("last_delivery", rdb.Date, nullable=False),
    # delivery period
    # rdb.Column("delivery_period", rdb.Integer),
    # delivery type
    # rdb.Column("delivery_type", rdb.Integer),
)
'''

# NOT a parliamentary_item
# !+doc_attachment
attachment = rdb.Table("attachment", metadata,
    rdb.Column("attachment_id", rdb.Integer, primary_key=True),
    # the id of the "owning" head document
    # !+doc_attachment -- this assumes that attachments are only for doc?
    rdb.Column("head_id", rdb.Integer,
        rdb.ForeignKey("doc.doc_id"),
        nullable=False
    ),
    # attachment_type #!+attached_file_type
    rdb.Column("type", 
        rdb.Unicode(128),
        default="document",
        nullable=False,
    ),
    rdb.Column("title", rdb.Unicode(255), nullable=False), #!+file
    rdb.Column("description", rdb.UnicodeText), #!+file
    rdb.Column("data", FSBlob(32)), #!+file
    rdb.Column("name", rdb.String(200)), #!+file
    rdb.Column("mimetype", rdb.String(127)), #!+file
    # Workflow State
    rdb.Column("status", rdb.Unicode(48)),
    rdb.Column("status_date", rdb.DateTime(timezone=False),
        server_default=text("now()"),
        nullable=False
    ),
    rdb.Column("language", rdb.String(5), nullable=False),
)
attachment_index = rdb.Index("attachment_head_id_idx", attachment.c["head_id"])

# attachment_audit
attachment_audit = make_audit_table(attachment, metadata)


# Document:
# base table for a workflowed parliamentary document
doc_sequence = rdb.Sequence("doc_sequence")
doc = rdb.Table("doc", metadata,
    # DB id
    rdb.Column("doc_id", rdb.Integer, doc_sequence, primary_key=True),
    
    # PARLIAMENT
    # parliament <=> dc:Publisher
    # The entity responsible for making the resource available. 
    # Examples of a Publisher include a person, an organization, or a service.
    # Typically, the name of a Publisher should be used to indicate the entity.
    # !+CONTAINER_CUSTODIAN_GROUPS(mr, apr-2011) parliament_id and group_id are
    # conceptually distinct while still being related:
    # - the general sense of parliament_id seems to be that of the 
    # "root_container" group (currently this may only be a parliament) in 
    # which the doc "exists" in
    # - while the general sense of group_id seems to be that of a kind of
    # "custodian" group, to which the doc is "assigned to" for handling.
    # !+PARLIAMENT_ID should be nullable=False, but fails on creating an Event...
    rdb.Column("parliament_id", rdb.Integer,
        rdb.ForeignKey("parliaments.parliament_id"),
        nullable=True
    ),
    # !+bicameral(mr, feb-2012) should parliament_id simply always be 
    # chamber_id, and then have the concept of a chamber group, each of which
    # related to the singleton parliament group?
    #rdb.Column("origin_chamber_id", rdb.Integer,
    #    rdb.ForeignKey("groups.group_id"), # !+ group (singular), chamber
    #    nullable=True
    #),
    
    # OWNERSHIP
    # owner <=> no dc equivalent
    # The bungeni user that submits (either directly, or someone else submits 
    # on his/her behalf) the document to Parliament. This is the "data owner" 
    # of the item (and not necessarily the conceptual owner, that may be an 
    # entity outside of Parliament). 
    rdb.Column("owner_id", rdb.Integer,
        rdb.ForeignKey("users.user_id"),
        nullable=False
    ),
    
    # !+dc:Creator / dc:Author, by default this would be owner, but we can 
    # sometimes have an external source as the creator of a resource e.g a 
    # 3rd party entity who prepared a tabled document, or a citizen/etc who 
    # suggested a question to an MP. See Issue 755.
    #rdb.Column("creator", rdb.Unicode(1024), nullable=True),
    # !+dc:Contributor, these are the signatories? external contributors?
    # !+seconder clarify usage (was on motion); always 1? overlapssignatories?
    #rdb.Column("seconder_id", rdb.Integer, rdb.ForeignKey("users.user_id")),
    
    # TYPE
    # sub document type discriminator: string enum
    # for polymorphic_identity <=> dc:Type
    rdb.Column("type", rdb.Unicode(128), nullable=False),
    # document typology: string enum (set by sub document type) 
    # e.g. oral/written, government/member
    # For validation of this field, we let upstream logic e.g. UI fields
    # using zope.schema.Choice combined with a vocabulary, to take 
    # responsibilty of validating this for *this* document type.
    rdb.Column("doc_type",
        rdb.Unicode(128),
        default=None,
        nullable=True,
    ),
    # document procedure: string enum (set by sub document type) 
    # e.g. urgent/ordinary, private/public
    rdb.Column("doc_procedure",
        rdb.Unicode(128),
        default=None,
        nullable=True,
    ),
    
    # IDENTIFICATION
    # document number e.g question_num, bill_num... a progressive number by type
    # !+registry_number, what is the relation?
    rdb.Column("type_number", rdb.Integer, nullable=True),
    # registry_number <=> dc:Identifier
    # An unambiguous reference to the resource within a given context. 
    # Recommended best practice is to identify the resource by means of a 
    # string or number conforming to a formal identification system.
    rdb.Column("registry_number", rdb.Unicode(128)),
    # uri, Akoma Ntoso <=> dc:Source
    # A Reference to a resource from which the present resource is derived. 
    # The present resource may be derived from the Source resource in whole or 
    # part.
    rdb.Column("uri", rdb.Unicode(1024), nullable=True), 
    
    # CONTENT
    rdb.Column("acronym", rdb.Unicode(48)),
    # !+LABEL(mr, jan-2011) display label e.g. for link text?
    # title <=> dc:Title !+DescriptiveProperties(mr, jan-2011)
    # The name given to the resource. Typically, a Title will be a name
    # by which the resource is formally known.
    rdb.Column("title", rdb.Unicode(1024), nullable=False),
    # description <=> dc:Description !+DescriptiveProperties(mr, jan-2011)
    # An account of the content of the resource. Description may include but is
    # not limited to: an abstract, table of contents, reference to a graphical
    # representation of content or a free-text account of the content.
    rdb.Column("description", rdb.UnicodeText, nullable=True),
    # original language of the document
    rdb.Column("language", rdb.String(5), nullable=False),
    rdb.Column("body", rdb.UnicodeText),
    
    # WORKFLOW
    rdb.Column("status", rdb.Unicode(48)),
    rdb.Column("status_date", rdb.DateTime(timezone=False),
        server_default=text("now()"),
        nullable=False
    ),
    # group responsible to "handle" this document... involves workflow: the 
    # precise meaning, and validation constraints of this is defined by each 
    # sub-type e.g. ministry for bill & question, group for agendaitem, ...
    # !+CONTAINER_CUSTODIAN_GROUPS
    rdb.Column("group_id", rdb.Integer,
        rdb.ForeignKey("groups.group_id"),
        nullable=True
    ),
    
    # !+workflow_note/motivation, should be stored on the change table?
    # !+personal_note, should be elsewhere, see issue 646 
    # the reviewer may add a recommendation note
    #rdb.Column("note", rdb.UnicodeText),
    
    # NOTIFICATION
    #!+receive_notification, must certainly be made obsolete...
    # Receive  Notifications -> triggers notification on workflow change
    #rdb.Column("receive_notification", rdb.Boolean,
    #    default=True
    #),
    
    # COVERAGE
    # duration that a document may be about
    #rdb.Column("timespan", nullable=True)
    # subject <=> dc:Subject
    # The topic of the content of the resource. Typically, a Subject will be 
    # expressed as keywords or key phrases or classification codes that describe
    # the topic of the resource. Recommended best practice is to select a value 
    # from a controlled vocabulary or formal classification scheme.
    # Hierarchical Controlled Vocabulary Micro Data Format: 
    # a triple-colon ":::" separated sequence of *key phrase paths*, each of 
    # which is a double-colon "::" separated sequence of *key phrases*.
    rdb.Column("subject", rdb.UnicodeText, nullable=True),
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
    rdb.Column("coverage", rdb.UnicodeText, nullable=True),
    rdb.Column("geolocation", rdb.UnicodeText, nullable=True),
    # !+DC(mr, jan-2011) consider addition of:
    # - Format
    # - Date, auto derive from workflow audit log
    # - Rights
    # - Reference, citations of other resources, implied from body content? 
    # - Relation, e.g. assigned to a Committee
    
    # head document (for sub documents e.g. events)
    rdb.Column("head_id", rdb.Integer, 
        rdb.ForeignKey("doc.doc_id"), 
        nullable=True,
    ),
    # (event only?) date, needed? auto derive from workflow audit log?
    #rdb.Column("date", rdb.DateTime(timezone=False),
    #    nullable=False
    #),
    
    # DB timestamp of last modification
    rdb.Column("timestamp", rdb.DateTime(timezone=False),
        server_default=text("now()"),
        nullable=False
    ),
)
doc_index = rdb.Index("doc_status_idx", doc.c["status"])

# doc audit
doc_audit = make_audit_table(doc, metadata)


signatory = rdb.Table("signatory", metadata,
    rdb.Column("signatory_id", rdb.Integer,
        primary_key=True
    ),
    # the id of the "owning" head document
    rdb.Column("head_id", rdb.Integer,
        rdb.ForeignKey("doc.doc_id"),
        nullable=False,
    ),
    rdb.Column("user_id", rdb.Integer,
        rdb.ForeignKey("users.user_id"),
        nullable=False,
    ),
    rdb.Column("status", rdb.Unicode(32)),
    rdb.UniqueConstraint("head_id", "user_id")
)
# attachment_audit
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

#document_sources = rdb.Table(
#    "document_sources",
#    metadata,
#    rdb.Column("document_source_id", rdb.Integer, primary_key=True),
#    rdb.Column("document_source", rdb.Unicode(256)),
#)


#######################
# Settings
#######################

settings = rdb.Table("settings", metadata,
    rdb.Column("setting_id", rdb.Integer, primary_key=True),
    rdb.Column("object_id", rdb.Integer), # scope
    rdb.Column("object_type", rdb.String(50)),
    rdb.Column("propertysheet", rdb.String(50)),
    rdb.Column("name", rdb.String(50)),
    rdb.Column("value", rdb.String(400)),
    rdb.Column("type", rdb.String(40)),
)
settings_index = rdb.Index("settings_propsheet_idx", 
    settings.c["propertysheet"]
)

holiday = rdb.Table("holiday", metadata,
    rdb.Column("holiday_id", rdb.Integer, primary_key=True),
    rdb.Column("date", rdb.Date, nullable=False),
    rdb.Column("name", rdb.Unicode(1024)),
    rdb.Column("language", rdb.String(5), nullable=False),
)


translations = rdb.Table("translations", metadata,
    rdb.Column("object_id", rdb.Integer, primary_key=True, nullable=False),
    rdb.Column("object_type", rdb.String(50),
        primary_key=True,
        nullable=False
    ),
    rdb.Column("lang", rdb.String(5), primary_key=True, nullable=False),
    rdb.Column("field_name", rdb.String(50), primary_key=True, nullable=False),
    rdb.Column("field_text", rdb.UnicodeText),
)
translation_lookup_index = rdb.Index("translation_lookup_index",
    translations.c.object_id,
    translations.c.object_type,
    translations.c.lang
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
    db = rdb.create_engine(db_uri, echo=True)
    metadata.bind = db

    try:
        metadata.drop_all()
        metadata.create_all()
    except:
        import pdb, traceback, sys
        traceback.print_exc()
        pdb.post_mortem(sys.exc_info()[-1])

