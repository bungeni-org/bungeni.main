#!/usr/bin/env python
# encoding: utf-8
import sqlalchemy as rdb
from sqlalchemy.sql import text

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
            server_default=(text("now()")),
            nullable=False
        ),
        # user-modifiable effective date, defaults to same value as audit date;
        # this is the date to be used for all intents and purposes other than 
        # for data auditing
        rdb.Column("date_active", rdb.DateTime(timezone=False),
            server_default=(text("now()")),
            nullable=False
        ),
        rdb.Column("description", rdb.UnicodeText),
        rdb.Column("notes", rdb.UnicodeText),
        rdb.Column("user_id", rdb.Unicode(32)
            # Integer, rdb.ForeignKey("users.user_id")),
        )
    )
    return changes_table


def make_versions_table(table, metadata, secondarytable=None):
    """Create a versions table, requires change log table for which
    some version metadata information will be stored.
    
    A secondary table may be defined if the object mapped to this
    table consists of a join between two tables
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
    columns.extend([ c.copy() for c in table.columns if not c.primary_key ])
    if secondarytable:
        columns.extend([ c.copy() for c in secondarytable.columns
                         if not c.primary_key ])
    versions_table = rdb.Table(versions_name, metadata, *columns)
    return versions_table


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
        default="A", # activ/inactiv/deceased
    ),
    # comment out for now - will be used for user preferences
    rdb.Column("receive_notification", rdb.Boolean, default=True),
    rdb.Column("language", rdb.String(5), nullable=False),
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


# specific user classes
parliament_memberships = rdb.Table("parliament_memberships", metadata,
    rdb.Column("membership_id", rdb.Integer,
        rdb.ForeignKey("user_group_memberships.membership_id"),
        primary_key=True
    ),
    rdb.Column("constituency_id", rdb.Integer,
        rdb.ForeignKey("constituencies.constituency_id")
    ),
    # the political party of the MP as of the time he was elected
    rdb.Column("party_id", rdb.Integer,
        rdb.ForeignKey("political_parties.party_id")
    ),
    # is the MP elected, nominated, ex officio member, ...
    rdb.Column("elected_nominated", rdb.String(1),
        rdb.CheckConstraint("""elected_nominated in ('E','O','N')"""),
        nullable=False
    ),
    rdb.Column("election_nomination_date", rdb.Date), # nullable=False),
    rdb.Column("leave_reason", rdb.Unicode(40)),
)


#########################
# Constituencies
#########################

constituencies = rdb.Table("constituencies", metadata,
    rdb.Column("constituency_id", rdb.Integer, primary_key=True),
    rdb.Column("name", rdb.Unicode(256), nullable=False),
    rdb.Column("province_id", rdb.Integer,
        rdb.ForeignKey("provinces.province_id")
    ),
    rdb.Column("region_id", rdb.Integer, rdb.ForeignKey("regions.region_id")),
    rdb.Column("start_date", rdb.Date, nullable=False),
    rdb.Column("end_date", rdb.Date),
    rdb.Column("language", rdb.String(5), nullable=False),
)

provinces = rdb.Table("provinces", metadata,
    rdb.Column("province_id", rdb.Integer, primary_key=True),
    #rdb.Column("region_id", rdb.Integer, rdb.ForeignKey("regions.region_id")),
    rdb.Column("province", rdb.Unicode(256), nullable=False),
    rdb.Column("language", rdb.String(5), nullable=False),
)

regions = rdb.Table("regions", metadata,
    rdb.Column("region_id", rdb.Integer, primary_key=True),
    rdb.Column("region", rdb.Unicode(256), nullable=False),
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
    rdb.Column("short_name", rdb.Unicode(256), nullable=False),
    rdb.Column("full_name", rdb.Unicode(256)),
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
    # Speakers office or Clerks office, the members of members of
    # this group will get local roles in the parliament accordingly
    rdb.Column("office_type", rdb.String(1),
        rdb.CheckConstraint("""office_type in ('S','C', 'T','L','R')"""),
        nullable=False
    ),
)

parliaments = rdb.Table("parliaments", metadata,
    rdb.Column("parliament_id", rdb.Integer,
        rdb.ForeignKey("groups.group_id"),
        primary_key=True
    ),
   rdb.Column("election_date", rdb.Date, nullable=False),
)

committees = rdb.Table("committees", metadata,
    rdb.Column("committee_id", rdb.Integer,
        rdb.ForeignKey("groups.group_id"),
        primary_key=True
    ),
    rdb.Column("committee_type_id", rdb.Integer,
        rdb.ForeignKey("committee_types.committee_type_id")
    ),
    rdb.Column("no_members", rdb.Integer),
    rdb.Column("min_no_members", rdb.Integer),
    rdb.Column("quorum", rdb.Integer),
    rdb.Column("no_clerks", rdb.Integer),
    rdb.Column("no_researchers", rdb.Integer),
    rdb.Column("proportional_representation", rdb.Boolean),
    rdb.Column("default_chairperson", rdb.Boolean),
    rdb.Column("reinstatement_date", rdb.Date),
)

committee_type = rdb.Table("committee_types", metadata,
    rdb.Column("committee_type_id", rdb.Integer, primary_key=True),
    rdb.Column("committee_type", rdb.Unicode(256), nullable=False),
    rdb.Column("description", rdb.UnicodeText),
    rdb.Column("life_span", rdb.Unicode(16)),
    # Indicate whether this type of committees are: 
    # ‘P" - Permanent, ‘T" - Temporary
    rdb.Column("status", rdb.String(1),
        rdb.CheckConstraint("""status in ('P','T')"""),
        nullable=False
    ),
    rdb.Column("language", rdb.String(5), nullable=False),
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

user_role_types = rdb.Table("user_role_types", metadata,
    rdb.Column("user_role_type_id", rdb.Integer, primary_key=True),
    rdb.Column("user_type", rdb.String(30), nullable=False),
    rdb.Column("user_role_name", rdb.Unicode(40), nullable=False),
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

role_titles = rdb.Table("role_titles", metadata,
    rdb.Column("role_title_id", rdb.Integer, primary_key=True),
    rdb.Column("membership_id", rdb.Integer,
        rdb.ForeignKey("user_group_memberships.membership_id"),
        nullable=False
    ),
    # title of user"s group role
    rdb.Column("title_name_id", rdb.Integer,
    rdb.ForeignKey("user_role_types.user_role_type_id"), nullable=False),
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

addresses = rdb.Table("addresses", metadata,
    rdb.Column("address_id", rdb.Integer, primary_key=True),
    # official address - only one official address is allowed per title
    rdb.Column("role_title_id", rdb.Integer,
        rdb.ForeignKey("role_titles.role_title_id"),
        unique=True
    ),
    # personal address, multiple addresses are allowed for a user
    rdb.Column("user_id", rdb.Integer, rdb.ForeignKey("users.user_id")),
    rdb.Column("address_type_id", rdb.Integer,
        rdb.ForeignKey("address_types.address_type_id")
    ),
    rdb.Column("po_box", rdb.Unicode(40)),
    rdb.Column("address", rdb.Unicode(256)),
    rdb.Column("city", rdb.Unicode(256)),
    rdb.Column("zipcode", rdb.Unicode(20)),
    rdb.Column("country", rdb.String(2),
        rdb.ForeignKey("countries.country_id")
    ),
    rdb.Column("phone", rdb.Unicode(256)),
    rdb.Column("fax", rdb.Unicode(256)),
    rdb.Column("email", rdb.String(512)),
    rdb.Column("im_id", rdb.String(512)),
    # Workflow State -> determins visibility
    rdb.Column("status", rdb.Unicode(16)),
    rdb.Column("status_date", rdb.DateTime(timezone=False),
        server_default=(text("now()")),
        nullable=False
    ),
)


##################
# Activity 
# 
parliament_sessions = rdb.Table("sessions", metadata,
    rdb.Column("session_id", rdb.Integer, primary_key=True),
    rdb.Column("parliament_id", rdb.Integer,
        rdb.ForeignKey("parliaments.parliament_id"),
        nullable=False
    ),
    rdb.Column("short_name", rdb.Unicode(32), nullable=False),
    rdb.Column("full_name", rdb.Unicode(256), nullable=False),
    rdb.Column("start_date", rdb.Date, nullable=False),
    rdb.Column("end_date", rdb.Date),
    rdb.Column("notes", rdb.UnicodeText),
    rdb.Column("language", rdb.String(5), nullable=False),
)

sittings = rdb.Table("group_sittings", metadata,
    rdb.Column("sitting_id", rdb.Integer, primary_key=True),
    rdb.Column("group_id", rdb.Integer,
        rdb.ForeignKey("groups.group_id"),
        nullable=False
    ),
    rdb.Column("short_name", rdb.Unicode(32)),
    rdb.Column("start_date", rdb.DateTime(timezone=False), nullable=False),
    rdb.Column("end_date", rdb.DateTime(timezone=False), nullable=False),
    rdb.Column("sitting_type_id", rdb.Integer,
        rdb.ForeignKey("sitting_type.sitting_type_id")
    ),
    # if a sitting is recurring this is the id of the original sitting
    # there is no foreign key to the original sitting
    # like rdb.ForeignKey("group_sittings.sitting_id")
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

sitting_type = rdb.Table("sitting_type", metadata,
    rdb.Column("sitting_type_id", rdb.Integer, primary_key=True),
    rdb.Column("sitting_type", rdb.Unicode(40)),
    rdb.Column("start_time", rdb.Time, nullable=False),
    rdb.Column("end_time", rdb.Time, nullable=False),
    rdb.Column("language", rdb.String(5), nullable=False),
)

sitting_attendance = rdb.Table("sitting_attendance", metadata,
    rdb.Column("sitting_id", rdb.Integer,
        rdb.ForeignKey("group_sittings.sitting_id"),
        primary_key=True
    ),
    rdb.Column("member_id", rdb.Integer,
        rdb.ForeignKey("users.user_id"),
        primary_key=True
    ),
    rdb.Column("attendance_id", rdb.Integer,
        rdb.ForeignKey("attendance_type.attendance_id"),
        nullable=False
    ),
)

attendance_type = rdb.Table("attendance_type", metadata,
    rdb.Column("attendance_id", rdb.Integer, primary_key=True),
    rdb.Column("attendance_type", rdb.Unicode(40), nullable=False),
    rdb.Column("language", rdb.String(5), nullable=False),
)


# venues for sittings:

venues = rdb.Table("venues", metadata,
    rdb.Column("venue_id", rdb.Integer, primary_key=True),
    rdb.Column("short_name", rdb.Unicode(255), nullable=False),
    rdb.Column("description", rdb.UnicodeText),
    rdb.Column("language", rdb.String(5), nullable=False),
)


# resources for sittings like rooms ...

resource_types = rdb.Table("resource_types", metadata,
    rdb.Column("resource_type_id", rdb.Integer, primary_key=True),
    rdb.Column("short_name", rdb.Unicode(40), nullable=False),
    rdb.Column("language", rdb.String(5), nullable=False),
)

resources = rdb.Table("resources", metadata,
    rdb.Column("resource_id", rdb.Integer, primary_key=True),
    rdb.Column("resource_type_id", rdb.Integer,
        rdb.ForeignKey("resource_types.resource_type_id"),
        nullable=False
    ),
    rdb.Column("short_name", rdb.Unicode(255), nullable=False),
    rdb.Column("description", rdb.UnicodeText),
    rdb.Column("language", rdb.String(5), nullable=False),
)

resourcebookings = rdb.Table("resourcebookings", metadata,
    rdb.Column("resource_id", rdb.Integer,
        rdb.ForeignKey("resources.resource_id"),
        primary_key=True
    ),
    rdb.Column("sitting_id", rdb.Integer,
        rdb.ForeignKey("group_sittings.sitting_id"),
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

items_schedule = rdb.Table("items_schedule", metadata,
    rdb.Column("schedule_id", rdb.Integer, primary_key=True),
    rdb.Column("item_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id"),
        nullable=False
    ),
    rdb.Column("sitting_id", rdb.Integer,
        rdb.ForeignKey("group_sittings.sitting_id"),
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

item_discussion = rdb.Table("item_discussion", metadata,
    rdb.Column("schedule_id", rdb.Integer,
        rdb.ForeignKey("items_schedule.schedule_id"),
        primary_key=True),
    rdb.Column("body_text", rdb.UnicodeText),
    rdb.Column("sitting_time", rdb.Time(timezone=False)),
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
    rdb.Column("end_date", rdb.Date),
    rdb.Column("report_type", rdb.String(32), nullable=False)
)

sitting_reports = rdb.Table("sitting_reports", metadata,
    rdb.Column("report_id", rdb.Integer,
        rdb.ForeignKey("reports.report_id"), primary_key=True
    ),
    rdb.Column("sitting_id", rdb.Integer,
        rdb.ForeignKey("group_sittings.sitting_id"), primary_key=True
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

# parliamentary items contains the common fields for motions, questions,
# bills and agenda items.

attached_files = rdb.Table("attached_files", metadata,
    rdb.Column("attached_file_id", rdb.Integer, primary_key=True),
    rdb.Column("item_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id")
    ),
    rdb.Column("file_version_id", rdb.Integer),
    rdb.Column("file_title", rdb.Unicode(255), nullable=False),
    rdb.Column("file_description", rdb.UnicodeText),
    rdb.Column("file_data", rdb.Binary),
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
    # XXX it should be nullable = False, but that crashes agendaitems add
    rdb.Column("parliament_id", rdb.Integer,
        rdb.ForeignKey("parliaments.parliament_id"),
        nullable=True
    ),
    rdb.Column("owner_id", rdb.Integer,
        rdb.ForeignKey("users.user_id"),
        nullable=False
    ),
    rdb.Column("language", rdb.String(5), nullable=False),
    rdb.Column("short_name", rdb.Unicode(255), nullable=False),
    rdb.Column("full_name", rdb.Unicode(1024), nullable=True),
    rdb.Column("body_text", rdb.UnicodeText),
    rdb.Column("submission_date", rdb.Date),
    # Workflow State
    rdb.Column("status", rdb.Unicode(48)),
    rdb.Column("status_date", rdb.DateTime(timezone=False),
        server_default=(text("now()")),
        nullable=False
    ),
    rdb.Column("registry_number", rdb.Integer),
    # the reviewer may add a recommendation note
    rdb.Column("note", rdb.UnicodeText),
    # Receive  Notifications -> triggers notification on workflow change
    rdb.Column("receive_notification", rdb.Boolean,
        default=True
    ),
    # type for polymorphic_identity
    rdb.Column("type", rdb.String(30), nullable=False),
    rdb.Column("language", rdb.String(5), nullable=False),
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
    rdb.Column("approval_date", rdb.Date,),
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

questions = rdb.Table("questions", metadata,
    rdb.Column("question_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id"),
        primary_key=True
    ),
    rdb.Column("question_number", rdb.Integer),
    rdb.Column("approval_date", rdb.Date,), # date speaker approved question
    rdb.Column("ministry_submit_date", rdb.Date,),
    rdb.Column("question_type", rdb.String(1),
        rdb.CheckConstraint("""question_type in ('O', 'P')"""),
        # (O)rdinary (P)rivate Notice
        default=u"O"
    ),
    rdb.Column("response_type", rdb.String(1),
        rdb.CheckConstraint("""response_type in ('O', 'W')"""), # (O)ral (W)ritten
        default=u"O"
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
    rdb.Column("approval_date", rdb.Date), # date speaker approved question
    rdb.Column("public", rdb.Boolean),
    rdb.Column("seconder_id", rdb.Integer,
        rdb.ForeignKey("users.user_id")
    ),
    rdb.Column("entered_by_id", rdb.Integer,
        rdb.ForeignKey("users.user_id")
    ),
    # if the motion was sponsored by a party
    rdb.Column("party_id", rdb.Integer,
        rdb.ForeignKey("political_parties.party_id")
    ),
    rdb.Column("notice_date", rdb.Date),
    # Receive Notifications -> triggers notification on workflow change
    rdb.Column("receive_notification", rdb.Boolean, default=True),
)

motion_changes = make_changes_table(motions, metadata)
motion_versions = make_versions_table(motions, metadata,
    parliamentary_items
)

bill_types = rdb.Table("bill_types", metadata,
    rdb.Column("bill_type_id", rdb.Integer, primary_key=True),
    rdb.Column("bill_type_name", rdb.Unicode(256),
        nullable=False,
        unique=True
    ),
    # language?
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

consignatories = rdb.Table("consignatories", metadata,
    rdb.Column("item_id", rdb.Integer,
        rdb.ForeignKey("parliamentary_items.parliamentary_item_id"),
        nullable=False,
        primary_key=True
    ),
    rdb.Column("user_id", rdb.Integer,
        rdb.ForeignKey("users.user_id"),
        nullable=False,
        primary_key=True
    ),
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
    rdb.Column("approval_date", rdb.Date,),
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

#######################
# Hansard
#######################

rotas = rdb.Table("rotas", metadata,
    rdb.Column("rota_id", rdb.Integer, primary_key=True),
    rdb.Column("reporter_id", rdb.Integer, rdb.ForeignKey("users.user_id")),
    rdb.Column("identifier", rdb.Unicode(60)),
    rdb.Column("start_date", rdb.Date),
    rdb.Column("end_date", rdb.Date)
)

takes = rdb.Table("takes", metadata,
    rdb.Column("take_id", rdb.Integer, primary_key=True),
    rdb.Column("rota_id", rdb.Integer, rdb.ForeignKey("rotas.rota_id")),
    rdb.Column("identifier", rdb.Unicode(1)),
)

take_media = rdb.Table("take_media", metadata,
    rdb.Column("media_id", rdb.Integer, primary_key=True),
    rdb.Column("take_id", rdb.Integer, rdb.ForeignKey("takes.take_id")),
)

transcripts = rdb.Table("transcripts", metadata,
    rdb.Column("transcript_id", rdb.Integer, primary_key=True),
    rdb.Column("take_id", rdb.Integer, rdb.ForeignKey("takes.take_id")),
    rdb.Column("reporter_id", rdb.Integer, rdb.ForeignKey("users.user_id")),
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


def reset_database():
    import util
    mdset = util.cli_setup()
    for m in mdset:
        m.drop_all(checkfirst=True)
        m.create_all(checkfirst=True)


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

