#!/usr/bin/env python
# encoding: utf-8
import sqlalchemy as rdb
from fields import FSBlob
from sqlalchemy.sql import text, functions
from datetime import datetime

metadata = rdb.MetaData()

# bills, motions, questions
ItemSequence = rdb.Sequence("item_sequence")

# users and groups because of the zope users and groups
PrincipalSequence = rdb.Sequence("principal_sequence")


def make_changes_table(table, metadata):
    """Create an object log table for an object.
    """
    table_name = table.name
    entity_name = table_name.endswith("s") and table_name[:-1] or table_name
    changes_name = "%s_changes" % (entity_name)
    fk_id = "%s_id" % (entity_name)
    changes_table = rdb.Table(changes_name, metadata,
        rdb.Column("change_id", rdb.Integer, primary_key=True),
        rdb.Column("content_id", rdb.Integer, rdb.ForeignKey(table.c[fk_id])),
        rdb.Column("action", rdb.Unicode(16)),
        # audit date, exclusively managed by the system
        rdb.Column("date_audit", rdb.DateTime(timezone=False),
            default=functions.current_timestamp(),
            nullable=False
        ),
        # user-modifiable effective date, defaults to same value as audit date;
        # this is the date to be used for all intents and purposes other than 
        # for data auditing
        rdb.Column("date_active", rdb.DateTime(timezone=False),
            default=functions.current_timestamp(),
            nullable=False
        ),
        rdb.Column("description", rdb.UnicodeText),
        rdb.Column("notes", rdb.UnicodeText),
        rdb.Column("user_id", rdb.Integer, rdb.ForeignKey("users.user_id")),
    )
    return changes_table


def make_versions_table(table, metadata, secondarytable=None):
    """Create a versions table, requires change log table for which
    some version metadata information will be stored.
    
    A secondary table may be defined if the object mapped to this
    table consists of a join between two tables.
    
    Assumption: table and secondarytable both have only a single surrogate pk.
    """
    table_name = table.name
    entity_name = table_name.endswith("s") and table_name[:-1] or table_name
    versions_name = "%s_versions" % (entity_name)
    fk_id = "%s_id" % (entity_name)
    columns = [
        rdb.Column("version_id", rdb.Integer, primary_key=True),
        rdb.Column("content_id", rdb.Integer, rdb.ForeignKey(table.c[fk_id])),
        rdb.Column("change_id", rdb.Integer,
            rdb.ForeignKey("%s_changes.change_id" % entity_name)
        ),
        rdb.Column("manual", rdb.Boolean, nullable=False, default=False),
    ]
    def extend_cols(cols, ext_cols):
        names = [ c.name for c in cols ]
        for c in ext_cols:
            if not c.primary_key:
                assert c.name not in names, "Duplicate column."
                names.append(c.name)
                cols.append(c.copy())
    extend_cols(columns, table.columns)
    if secondarytable:
        extend_cols(columns, secondarytable.columns)
    versions_table = rdb.Table(versions_name, metadata, *columns)
    return versions_table

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
    rdb.Column("uri", rdb.String(120), unique=True),
    rdb.Column("date_of_death", rdb.Date),
    rdb.Column("type_of_id", rdb.String(1)),
    rdb.Column("national_id", rdb.Unicode(32)),
    rdb.Column("password", rdb.String(36)
        # we store salted md5 hash hexdigests
    ),
    rdb.Column("salt", rdb.String(24)),
    rdb.Column("description", rdb.UnicodeText),
    rdb.Column("image", rdb.Binary),
    rdb.Column("active_p", rdb.String(1),
        rdb.CheckConstraint("""active_p in ('A', 'I', 'D')"""),
        default="A", # active/inactive/deceased
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

# associations table for many-to-many relation between user and 
# parliamentary item
users_parliamentary_items = rdb.Table("users_parliamentary_items", metadata,
    rdb.Column("users_id", rdb.Integer,
        rdb.ForeignKey("users.user_id")
    ),
    rdb.Column("parliamentary_items_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id")
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

# user subscriptions table

member_election_types = make_vocabulary_table("member_election", metadata)

# specific user classes
parliament_memberships = rdb.Table("parliament_memberships", metadata,
    rdb.Column("membership_id", rdb.Integer,
        rdb.ForeignKey("user_group_memberships.membership_id"),
        primary_key=True
    ),
    # the constituency/province/region of the MP as of the time he was elected
    rdb.Column("constituency_id", rdb.Integer,
        rdb.ForeignKey("constituencies.constituency_id")
    ),
    rdb.Column("province_id", rdb.Integer,
        rdb.ForeignKey("provinces.province_id")
    ),
    rdb.Column("region_id", rdb.Integer,
        rdb.ForeignKey("regions.region_id")
    ),
    # the political party of the MP as of the time he was elected
    rdb.Column("party_id", rdb.Integer,
        rdb.ForeignKey("political_parties.party_id")
    ),
    # is the MP elected, nominated, ex officio member, ...
    rdb.Column("member_election_type_id", rdb.Integer,
        rdb.ForeignKey("member_election_types.member_election_type_id"),
        nullable=False
    ),
    rdb.Column("election_nomination_date", rdb.Date), # nullable=False),
    rdb.Column("leave_reason", rdb.Unicode(40)),
)


#########################
# Geo Localities
#########################

# !+GEO_LOCALITIES(mr, aug-2010) there is no longer any conceptual differences
# between constituency/region/province entities -- maybe should be reduced to
# a single table "geo_localities" plus a (parametrizable) type qualifier column.
# This implies reworking: db schema, "add mp" form, core/ dc.py app.py, etc.

# !+GEO_LOCALITIES(mr, aug-2010) all geo_localities should have start/end dates
# as well as additional extra (dated) details.

constituencies = rdb.Table("constituencies", metadata,
    rdb.Column("constituency_id", rdb.Integer, primary_key=True),
    rdb.Column("name", rdb.Unicode(256), nullable=False),
    rdb.Column("start_date", rdb.Date, nullable=False),
    rdb.Column("end_date", rdb.Date),
    rdb.Column("language", rdb.String(5), nullable=False),
)
provinces = rdb.Table("provinces", metadata,
    rdb.Column("province_id", rdb.Integer, primary_key=True),
    rdb.Column("province", rdb.Unicode(256), nullable=False), # !+name
    rdb.Column("language", rdb.String(5), nullable=False),
)
regions = rdb.Table("regions", metadata,
    rdb.Column("region_id", rdb.Integer, primary_key=True),
    rdb.Column("region", rdb.Unicode(256), nullable=False), # !+name
    rdb.Column("language", rdb.String(5), nullable=False),
)

countries = rdb.Table("countries", metadata,
    rdb.Column("country_id", rdb.String(2), primary_key=True),
    rdb.Column("iso_name", rdb.Unicode(80), nullable=False),
    rdb.Column("country_name", rdb.Unicode(80), nullable=False),
    rdb.Column("iso3", rdb.String(3)),
    rdb.Column("numcode", rdb.Integer),
    rdb.Column("language", rdb.String(5), nullable=False),
)

# !+GEO_LOCALITIES_DETAILS(mr, aug-2010) generalize/apply to all geo_localities
constituency_details = rdb.Table("constituency_details", metadata,
    rdb.Column("constituency_detail_id", rdb.Integer, primary_key=True),
    rdb.Column("constituency_id", rdb.Integer,
        rdb.ForeignKey("constituencies.constituency_id")),
    rdb.Column("date", rdb.Date, nullable=False),
    rdb.Column("population", rdb.Integer, nullable=False),
    rdb.Column("voters", rdb.Integer, nullable=False),
)


#######################
# Groups
#######################
# we"re using a very normalized form here to represent all kinds of
# groups and their relations to other things in the system.

groups = rdb.Table("groups", metadata,
    rdb.Column("group_id", rdb.Integer, PrincipalSequence, primary_key=True),
    rdb.Column("short_name", rdb.Unicode(32), nullable=False), #!+ACRONYM
    rdb.Column("full_name", rdb.Unicode(256)), #!+NAME
    rdb.Column("description", rdb.UnicodeText),
    rdb.Column("status", rdb.Unicode(32)), # workflow for groups
    rdb.Column("status_date", rdb.DateTime(timezone=False),
        server_default=(text("now()")),
        nullable=False
    ),
    rdb.Column("start_date", rdb.Date, nullable=False),
    rdb.Column("end_date", rdb.Date),
    rdb.Column("type", rdb.String(30), nullable=False),
    rdb.Column("parent_group_id", rdb.Integer,
        rdb.ForeignKey("groups.group_id")
     ),
    rdb.Column("language", rdb.String(5), nullable=False),
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

committees = rdb.Table("committees", metadata,
    rdb.Column("committee_id", rdb.Integer,
        rdb.ForeignKey("groups.group_id"),
        primary_key=True
    ),
    rdb.Column("committee_type_id", rdb.Integer,
        rdb.ForeignKey("committee_types.committee_type_id")
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

# political parties (outside the parliament) and 
# political groups (inside the parliament)
political_parties = rdb.Table("political_parties", metadata,
    rdb.Column("party_id", rdb.Integer,
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

# a bill assigned to a committee, a question assigned to a ministry
group_item_assignments = rdb.Table("group_assignments", metadata,
    rdb.Column("assignment_id", rdb.Integer,
        primary_key=True,
        nullable=False
    ),
    rdb.Column("item_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id"),
        nullable=False),
    #rdb.Column("object_type", rdb.String(128), nullable=False),
    rdb.Column("group_id", rdb.Integer,
        rdb.ForeignKey("groups.group_id"),
        nullable=False
    ),
    rdb.Column("start_date", rdb.Date, default=datetime.now, nullable=False),
    rdb.Column("end_date", rdb.Date),
    rdb.Column("due_date", rdb.Date),
    rdb.Column("status", rdb.String(16)),
    rdb.Column("status_date", rdb.DateTime(timezone=False),
        server_default=(text("now()")),
        nullable=False
    ),
    rdb.Column("notes", rdb.UnicodeText),
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
# Adresses can be attached to a user or to a role title 
# as the official address for this function

address_types = rdb.Table("address_types", metadata,
    rdb.Column("address_type_id", rdb.Integer, primary_key=True),
    rdb.Column("address_type_name", rdb.Unicode(40)),
    rdb.Column("language", rdb.String(5), nullable=False),
)

postal_address_types = make_vocabulary_table("postal_address", metadata)

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
        rdb.Column("address_type_id", rdb.Integer,
            rdb.ForeignKey("address_types.address_type_id"),
            nullable=False
        ),
        rdb.Column("postal_address_type_id", rdb.Integer,
            rdb.ForeignKey("postal_address_types.postal_address_type_id"),
            nullable=False
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
            server_default=(text("now()")),
            nullable=False
        ),
    )
group_addresses = _make_address_table(metadata, "group")
user_addresses = _make_address_table(metadata, "user")


##################
# Activity 
#

parliament_sessions = rdb.Table("sessions", metadata,
    rdb.Column("session_id", rdb.Integer, primary_key=True),
    rdb.Column("parliament_id", rdb.Integer,
        rdb.ForeignKey("parliaments.parliament_id"),
        nullable=False
    ),
    rdb.Column("short_name", rdb.Unicode(32), nullable=False), #!+ACRONYM
    rdb.Column("full_name", rdb.Unicode(256), nullable=False), #!+NAME
    rdb.Column("start_date", rdb.Date, nullable=False),
    rdb.Column("end_date", rdb.Date),
    rdb.Column("notes", rdb.UnicodeText),
    rdb.Column("language", rdb.String(5), nullable=False),
)

group_sittings = rdb.Table("group_sittings", metadata,
    rdb.Column("group_sitting_id", rdb.Integer, primary_key=True),
    rdb.Column("group_id", rdb.Integer,
        rdb.ForeignKey("groups.group_id"),
        nullable=False
    ),
    rdb.Column("short_name", rdb.Unicode(32)), #!+ACRONYM
    rdb.Column("start_date", rdb.DateTime(timezone=False), nullable=False),
    rdb.Column("end_date", rdb.DateTime(timezone=False), nullable=False),
    rdb.Column("group_sitting_type_id", rdb.Integer,
        rdb.ForeignKey("group_sitting_types.group_sitting_type_id")
    ),
    # if a sitting is recurring this is the id of the original sitting
    # there is no foreign key to the original sitting
    # like rdb.ForeignKey("group_sittings.group_sitting_id")
    # to make it possible to delete the original sitting
    rdb.Column("recurring_id", rdb.Integer),
    rdb.Column("status", rdb.Unicode(48)),
    rdb.Column("status_date", rdb.DateTime(timezone=False),
        server_default=(text("now()")),
        nullable=False
    ),
    # venues for sittings
    rdb.Column("venue_id", rdb.Integer, rdb.ForeignKey("venues.venue_id")),
    rdb.Column("language", rdb.String(5), nullable=False),
)

group_sitting_changes = make_changes_table(group_sittings, metadata)

# Currently not used
group_sitting_types = rdb.Table("group_sitting_types", metadata,
    rdb.Column("group_sitting_type_id", rdb.Integer, primary_key=True),
    rdb.Column("group_sitting_type", rdb.Unicode(40)),
    rdb.Column("start_time", rdb.Time, nullable=False),
    rdb.Column("end_time", rdb.Time, nullable=False),
    rdb.Column("language", rdb.String(5), nullable=False),
)

group_sitting_attendance = rdb.Table("group_sitting_attendance", metadata,
    rdb.Column("group_sitting_id", rdb.Integer,
        rdb.ForeignKey("group_sittings.group_sitting_id"),
        primary_key=True
    ),
    rdb.Column("member_id", rdb.Integer,
        rdb.ForeignKey("users.user_id"),
        primary_key=True
    ),
    rdb.Column("attendance_type_id", rdb.Integer,
        rdb.ForeignKey("attendance_types.attendance_type_id"),
        nullable=False
    ),
)

attendance_types = rdb.Table("attendance_types", metadata,
    rdb.Column("attendance_type_id", rdb.Integer, primary_key=True),
    rdb.Column("attendance_type", rdb.Unicode(40), nullable=False),
    rdb.Column("language", rdb.String(5), nullable=False),
)


# venues for sittings:

venues = rdb.Table("venues", metadata,
    rdb.Column("venue_id", rdb.Integer, primary_key=True),
    rdb.Column("short_name", rdb.Unicode(128), nullable=False),
    rdb.Column("description", rdb.UnicodeText),
    rdb.Column("language", rdb.String(5), nullable=False),
)


# resources for sittings like rooms ...

resource_types = rdb.Table("resource_types", metadata,
    rdb.Column("resource_type_id", rdb.Integer, primary_key=True),
    rdb.Column("short_name", rdb.Unicode(32), nullable=False), #!+ACRONYM
    rdb.Column("language", rdb.String(5), nullable=False),
)

resources = rdb.Table("resources", metadata,
    rdb.Column("resource_id", rdb.Integer, primary_key=True),
    rdb.Column("resource_type_id", rdb.Integer,
        rdb.ForeignKey("resource_types.resource_type_id"),
        nullable=False
    ),
    rdb.Column("short_name", rdb.Unicode(128), nullable=False),
    rdb.Column("description", rdb.UnicodeText),
    rdb.Column("language", rdb.String(5), nullable=False),
)

resourcebookings = rdb.Table("resourcebookings", metadata,
    rdb.Column("resource_id", rdb.Integer,
        rdb.ForeignKey("resources.resource_id"),
        primary_key=True
    ),
    rdb.Column("group_sitting_id", rdb.Integer,
        rdb.ForeignKey("group_sittings.group_sitting_id"),
        primary_key=True
    ),
)

#######################
# Parliament
#######################
# Parliamentary Items

item_votes = rdb.Table("item_votes", metadata,
    rdb.Column("vote_id", rdb.Integer, primary_key=True),
    rdb.Column("item_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id"),
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
    rdb.Column("item_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id"),
        nullable=False
    ),
    rdb.Column("group_sitting_id", rdb.Integer,
        rdb.ForeignKey("group_sittings.group_sitting_id"),
        nullable=False
    ),
    rdb.Column("planned_order", rdb.Integer,
        rdb.Sequence("planned_order", 0, 1)
    ),
    rdb.Column("real_order", rdb.Integer),
    # item was discussed on this sitting sitting
    rdb.Column("active", rdb.Boolean, default=True),
    # workflow status of the item for this schedule
    # NOT workflow status of this item_schedule!
    rdb.Column("item_status", rdb.Unicode(64),)
)

# to produce the proceedings:
# capture the discussion on this item

item_schedule_discussions = rdb.Table("item_schedule_discussions", metadata,
    rdb.Column("schedule_id", rdb.Integer,
        rdb.ForeignKey("item_schedules.schedule_id"),
        primary_key=True),
    rdb.Column("body_text", rdb.UnicodeText),
    rdb.Column("group_sitting_time", rdb.Time(timezone=False)),
    rdb.Column("language", rdb.String(5),
        nullable=False,
        default="en"
    ),
)

reports = rdb.Table("reports", metadata,
    rdb.Column("report_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id"),
        primary_key=True
    ),
    rdb.Column("group_id", rdb.Integer, rdb.ForeignKey("groups.group_id")),
    rdb.Column("start_date", rdb.Date, nullable=False),
    rdb.Column("end_date", rdb.Date)
)

sitting_reports = rdb.Table("sitting_reports", metadata,
    rdb.Column("report_id", rdb.Integer,
        rdb.ForeignKey("reports.report_id"), primary_key=True
    ),
    rdb.Column("group_sitting_id", rdb.Integer,
        rdb.ForeignKey("group_sittings.group_sitting_id"), primary_key=True
    ),
)

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

attached_file_types = rdb.Table("attached_file_types", metadata,
    rdb.Column("attached_file_type_id", rdb.Integer, primary_key=True),
    rdb.Column("attached_file_type_name", rdb.Unicode(40)),
    rdb.Column("language", rdb.String(5), nullable=False),
)

# parliamentary items contains the common fields for motions, questions,
# bills and agenda items.
attached_files = rdb.Table("attached_files", metadata,
    rdb.Column("attached_file_id", rdb.Integer, primary_key=True),
    rdb.Column("item_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id")
    ),
    rdb.Column("attached_file_type_id", rdb.Integer,
        rdb.ForeignKey("attached_file_types.attached_file_type_id"),
        nullable=False
    ),
    rdb.Column("file_version_id", rdb.Integer),
    rdb.Column("file_title", rdb.Unicode(255), nullable=False),
    rdb.Column("file_description", rdb.UnicodeText),
    rdb.Column("file_data", FSBlob(32)),
    rdb.Column("file_name", rdb.String(127)),
    rdb.Column("file_mimetype", rdb.String(127)),
    # Workflow State
    rdb.Column("status", rdb.Unicode(48)),
    rdb.Column("status_date", rdb.DateTime(timezone=False),
        server_default=(text("now()")),
        nullable=False
    ),
    rdb.Column("language", rdb.String(5), nullable=False),
)

attached_file_changes = make_changes_table(attached_files, metadata)
attached_file_versions = make_versions_table(attached_files, metadata)

registrySequence = rdb.Sequence("registry_number_sequence", metadata)

parliamentary_items = rdb.Table("parliamentary_items", metadata,
    rdb.Column("parliamentary_item_id", rdb.Integer,
        ItemSequence,
        primary_key=True
    ),
    # parliament <=> dc:Publisher
    # The entity responsible for making the resource available. 
    # Examples of a Publisher include a person, an organization, or a service.
    # Typically, the name of a Publisher should be used to indicate the entity.
    # !+ XXX it should be nullable=False, but that crashes agendaitems add
    rdb.Column("parliament_id", rdb.Integer,
        rdb.ForeignKey("parliaments.parliament_id"),
        nullable=True
    ),
    # owner <=> no dc equivalent
    # The bungeni user that submits (either directly, or someone else submits 
    # on his/her behalf) the document to Parliament. This is the "data owner" 
    # of the item (and not necessarily the conceptual owner, that may be an 
    # entity outside of Parliament). 
    rdb.Column("owner_id", rdb.Integer,
        rdb.ForeignKey("users.user_id"),
        nullable=False
    ),
    rdb.Column("language", rdb.String(5), nullable=False),
    # !+ACRONYM(mr, jan-2011) also add an acronym/label (e.g. for link text)?
    # short_name <=> dc:Title !+DescriptiveProperties(mr, jan-2011)
    # The name given to the resource. Typically, a Title will be a name
    # by which the resource is formally known.
    rdb.Column("short_name", rdb.Unicode(128), nullable=False), 
    # full_name <=> no dc equivalent
    rdb.Column("full_name", rdb.Unicode(1024), nullable=True),
    rdb.Column("body_text", rdb.UnicodeText),
    # description <=> dc:Description !+DescriptiveProperties(mr, jan-2011)
    # An account of the content of the resource. Description may include but is
    # not limited to: an abstract, table of contents, reference to a graphical
    # representation of content or a free-text account of the content.
    rdb.Column("description", rdb.UnicodeText, nullable=True),
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
    # Workflow State
    rdb.Column("status", rdb.Unicode(48)),
    rdb.Column("status_date", rdb.DateTime(timezone=False),
        server_default=(text("now()")),
        nullable=False
    ),
    # registry_number <=> dc:Identifier
    # An unambiguous reference to the resource within a given context. 
    # Recommended best practice is to identify the resource by means of a 
    # string or number conforming to a formal identification system. 
    rdb.Column("registry_number", rdb.Unicode(128)),
    # uri, Akoma Ntoso <=> dc:Source
    # A Reference to a resource from which the present resource is derived. 
    # The present resource may be derived from the Source resource in whole or 
    # part.
    rdb.Column("uri", rdb.Unicode(128), nullable=True), 
    # the reviewer may add a recommendation note
    rdb.Column("note", rdb.UnicodeText),
    # Receive  Notifications -> triggers notification on workflow change
    rdb.Column("receive_notification", rdb.Boolean,
        default=True
    ),
    # type, for polymorphic_identity <=> dc:Type
    rdb.Column("type", rdb.String(30), nullable=False),
    # !+DC(mr, jan-2011) consider addition of:
    # - Creator/Author
    # - Contributor
    # - Format
    # - Date, auto derive from workflow audit log
    # - Rights
    # - Reference, citations of other resources, implied from body content? 
    # - Relation, e.g. assigned to a Committee
    
)

# Agenda Items:
# generic items to be put on the agenda for a certain group
# they can be scheduled for a sitting

agenda_items = rdb.Table("agenda_items", metadata,
    rdb.Column("agenda_item_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id"),
        primary_key=True
    ),
    rdb.Column("group_id", rdb.Integer,
        rdb.ForeignKey("groups.group_id"),
        nullable=False
    ),
)

agenda_item_changes = make_changes_table(agenda_items, metadata)
agenda_item_versions = make_versions_table(agenda_items, metadata,
    parliamentary_items
)

QuestionSequence = rdb.Sequence("question_number_sequence", metadata)
# Approved questions are given a serial number enabling the clerks office
# to record the order in which questions are received and hence enforce 
# a first come first served policy in placing the questions on the order
# paper. The serial number is re-initialized at the start of each session
question_types = make_vocabulary_table("question", metadata)
response_types = make_vocabulary_table("response", metadata)

questions = rdb.Table("questions", metadata,
    rdb.Column("question_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id"),
        primary_key=True
    ),
    rdb.Column("question_number", rdb.Integer),
    rdb.Column("ministry_submit_date", rdb.Date,),
    rdb.Column("question_type_id", rdb.Integer,
        rdb.ForeignKey("question_types.question_type_id")
    ),
    rdb.Column("response_type_id", rdb.Integer,
        rdb.ForeignKey("response_types.response_type_id")
    ),
    # if supplementary question, this is the original/previous question
    rdb.Column("supplement_parent_id", rdb.Integer,
        rdb.ForeignKey("questions.question_id")
    ),
    rdb.Column("sitting_time", rdb.DateTime(timezone=False)),
    rdb.Column("ministry_id", rdb.Integer, rdb.ForeignKey("groups.group_id")),
    rdb.Column("response_text", rdb.UnicodeText),
)
question_changes = make_changes_table(questions, metadata)
question_versions = make_versions_table(questions, metadata,
    parliamentary_items
)

MotionSequence = rdb.Sequence("motion_number_sequence", metadata)
# Number that indicate the order in which motions have been approved 
# by the Speaker. The Number is reset at the start of each new session
# with the first motion assigned the number 1

motions = rdb.Table("motions", metadata,
    rdb.Column("motion_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id"),
        primary_key=True
    ),
    rdb.Column("motion_number", rdb.Integer),
    # !+USAGE(mr, jan-2011) determine usage, document or remove
    rdb.Column("public", rdb.Boolean),
    # !+USAGE(mr, jan-2011) determine usage, document or remove 
    # - overlap with parliamentary_items.signatories ?
    rdb.Column("seconder_id", rdb.Integer,
        rdb.ForeignKey("users.user_id")
    ),
    # !+USAGE(mr, jan-2011) determine usage, document or remove
    # - if the motion was sponsored by a *political group* (NOT *party*) 
    # - obsoleted by each group's "virtual user" idea?
    rdb.Column("party_id", rdb.Integer,
        rdb.ForeignKey("political_parties.party_id")
    ),
)
motion_changes = make_changes_table(motions, metadata)
motion_versions = make_versions_table(motions, metadata, parliamentary_items)

bill_types = rdb.Table("bill_types", metadata,
    rdb.Column("bill_type_id", rdb.Integer, primary_key=True),
    rdb.Column("bill_type_name", rdb.Unicode(256),
        nullable=False,
        unique=True
    ),
    rdb.Column("language", rdb.String(5), nullable=False),
)

bills = rdb.Table("bills", metadata,
    rdb.Column("bill_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id"),
        primary_key=True
    ),
    rdb.Column("bill_type_id", rdb.Integer,
        rdb.ForeignKey("bill_types.bill_type_id"),
        nullable=False
    ),
    rdb.Column("ministry_id", rdb.Integer, rdb.ForeignKey("groups.group_id")),
    rdb.Column("identifier", rdb.Integer),
    rdb.Column("publication_date", rdb.Date),
)
bill_changes = make_changes_table(bills, metadata)
bill_versions = make_versions_table(bills, metadata, parliamentary_items)

committee_reports = ()

signatories = rdb.Table("signatories", metadata,
    rdb.Column("signatory_id", rdb.Integer,
        primary_key=True
    ),
    rdb.Column("item_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id"),
        nullable=False,
    ),
    rdb.Column("user_id", rdb.Integer,
        rdb.ForeignKey("users.user_id"),
        nullable=False,
    ),
    rdb.Column("status", rdb.Unicode(32)),
    rdb.UniqueConstraint("item_id", "user_id")
)

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

tabled_documentSequence = rdb.Sequence("tabled_document_number_sequence",
    metadata
)

tabled_documents = rdb.Table("tabled_documents", metadata,
    rdb.Column("tabled_document_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id"),
        primary_key=True
    ),
    rdb.Column("link", rdb.String(256)),
    rdb.Column("tabled_document_number", rdb.Integer),
)

tabled_document_changes = make_changes_table(tabled_documents, metadata)
tabled_document_versions = make_versions_table(tabled_documents, metadata,
    parliamentary_items
)

# Events with dates and possibility to upload files.
#
# - events are also a parliamentary_item (of type="event", via fk 
#   event_item_id) where the attributes title, description are stored
# - events are related (via fk item_id) to a parliamentary item, that must be a
#   bill, motion, question or tabled_document i.e NOT agendaitam.
# - adding event_item to a parliamentary_item is NOT audited as a change 
#   i.e. there is no record added to the *_changes table [!+ maybe
#   adding an event should be handled similar to e.g. adding an attachment]. 
#   But event_items must be included in the timeline of the 
#   parliamentary_item... so, to be consistent with other (time-stamped) 
#   timeline changes, the event_date here is defined as a DateTime field
#   (contrary to most date fields on other parliamentary items). 

event_items = rdb.Table("event_items", metadata,
    rdb.Column("event_item_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id"),
        primary_key=True
    ),
    rdb.Column("item_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id"),
        nullable=True
    ),
    rdb.Column("event_date", rdb.DateTime(timezone=False),
        nullable=False
    ),
)


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


holidays = rdb.Table("holidays", metadata,
    rdb.Column("holiday_id", rdb.Integer, primary_key=True),
    rdb.Column("holiday_date", rdb.Date, nullable=False),
    rdb.Column("holiday_name", rdb.Unicode(32)),
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

''' !+WTF(mr, oct-2010) what is this? To start, there is no .util module !
def reset_database():
    import util
    mdset = util.cli_setup()
    for m in mdset:
        m.drop_all(checkfirst=True)
        m.create_all(checkfirst=True)
'''

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

