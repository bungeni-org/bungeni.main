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
from bungeni.utils import naming


# column creation utilities, for better consistency and clarity
def col_language_code(name, primary_key=False, nullable=False):
    # a column for an rfc3066-compliant language code
    return sa.Column(name, sa.String(5), primary_key=primary_key, nullable=nullable)
def col_acronym(name):
    return sa.Column(name, sa.Unicode(64), nullable=True)
def col_status(name):
    #!+STATUS_NULLABLE: logically this should NOT be nullable, but for 
    # practicalities of the implementation of how an object is created 
    # (see workflow initial status and fireAutomaticTransitions) requiring 
    # that only initially a workflowed instance must have a null status.
    return sa.Column(name, sa.Unicode(64), nullable=True)
def col_status_date(name):
    return sa.Column(name, sa.DateTime(timezone=False),
        server_default=sa.sql.text("now()"), nullable=False)
def col_principal_name(name, default=None):
    # !+login_regex - principal_name should also be a valid login name
    return sa.Column(name, sa.Unicode(128), default=default,
        unique=True, nullable=False)


metadata = sa.MetaData()


# extended attributes - vertical properties

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
    col_language_code("language"),
)
vp_datetime = sa.Table("vp_datetime", metadata,
    sa.Column("object_id", sa.Integer, primary_key=True, nullable=False),
    sa.Column("object_type", sa.String(32), primary_key=True, nullable=False),
    sa.Column("name", sa.String(50), primary_key=True, nullable=False,),
    sa.Column("value", sa.DateTime(timezone=False)),
)
vp_binary = sa.Table("vp_binary", metadata,
    sa.Column("object_id", sa.Integer, primary_key=True, nullable=False),
    sa.Column("object_type", sa.String(32), primary_key=True, nullable=False),    
    sa.Column("name", sa.String(50), primary_key=True, nullable=False,),
    sa.Column("value", sa.Binary),
)
vp_integer = sa.Table("vp_integer", metadata,
    sa.Column("object_id", sa.Integer, primary_key=True, nullable=False),
    sa.Column("object_type", sa.String(32), primary_key=True, nullable=False),    
    sa.Column("name", sa.String(50), primary_key=True, nullable=False,),
    sa.Column("value", sa.Integer),
)


# change, audit, version

# generic change information -- visibility of a change record depends
# the permissions of the parent object "at the time" of the change
change = sa.Table("change", metadata,
    sa.Column("audit_id", sa.Integer, 
        sa.ForeignKey("audit.audit_id"),
        primary_key=True),
    sa.Column("user_id", sa.Integer, sa.ForeignKey("user.user_id"), 
        nullable=False),
    # the type of change, also the change polymorphic identity
    sa.Column("action", sa.Unicode(128), nullable=False),
    # accumulative count, per (change.audit.audit_head_id, change.action) 
    # e.g default: 1 + max(seq(head, "version")), see core.audit _get_seq()
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
    sa.Column("audit_type", sa.Unicode(128), nullable=False),
)


def make_audit_table(table, metadata):
    """Create an audit log table for an archetype.
    """
    audit_tbl_name = naming.audit_table_name(table.name)
    audit_columns = get_audit_table_columns(table)
    audit_tbl = sa.Table(audit_tbl_name, metadata, *audit_columns,
        useexisting=False
    )
    return audit_tbl
def get_audit_table_columns(table):
    """Derive the columns of the audit table from the table being audited.
    """
    entity_name = table.name
    audit_tbl_name = naming.audit_table_name(entity_name)
    # audit-specific columns -- prefix with "audit_" to avoid potential 
    # clashing of column names from table being audited.
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
            if c.primary_key:
                # PK columns on auditable table become FK columns on audit table
                if len(table.primary_key) == 1:
                    # single-column PK - the id column of the "owning" object for
                    # which the change is being logged; we always retain the same
                    # original column name i.e. doc_id for case of "doc", and have
                    # the audit_head_id property always read and write to this.
                    assert c.name == "%s_id" % (entity_name), \
                        "Inconsistent PK column naming [%s != %s]" % (
                            "%s_id" % (entity_name), c.name)
                else:
                    # composite PK
                    log.debug("Table %r -> skipping pk column %r name "
                            "constraint check for multi-column PK: %s", 
                                audit_tbl_name, c.name, table.primary_key.columns)
                # add the column, corresponding ForeignKeyConstraint added at end
                cols.append(sa.Column(c.name, c.type, nullable=False, index=True))
                # !+FK columns may specify type as None (not c.type), to let 
                # auto detection of the type from that of the FK col
            else:
                # !+ should special ext col constraints NOT be carried over
                # e.g. default value on ext, not/nullable on ext...?
                cols.append(c.copy())
                # auditable "unique" columns may NOT be unique in the audit table!
                if cols[-1].unique:
                    cols[-1].unique = False
    
    extend_cols(columns, table.columns)
    # add ForeignKeyConstraint corresponding to original PK
    pk_col_names = [ c.name for c in table.primary_key.columns ]
    columns.append(
        sa.ForeignKeyConstraint(pk_col_names, 
            [ "%s.%s" % (entity_name, name) for name in pk_col_names ]))
    # !+additional tables...
    return columns


# ARCHETYPES

# doc - base table for a workflowed parliamentary document
doc_sequence = sa.Sequence("doc_sequence")
doc = sa.Table("doc", metadata,
    # DB id
    sa.Column("doc_id", sa.Integer, doc_sequence, primary_key=True),
    
    # CHAMBER
    # chamber <=> dc:Publisher
    # The entity responsible for making the resource available. 
    # Examples of a Publisher include a person, an organization, or a service.
    # Typically, the name of a Publisher should be used to indicate the entity.
    # !+CONTAINER_CUSTODIAN_GROUPS(mr, apr-2011) chamber_id and group_id are
    # conceptually distinct while still being related:
    # - the general sense of chamber_id seems to be that of the 
    # "root_container" group (currently this may only be a chamber) in 
    # which the doc "exists"
    # - while the general sense of group_id seems to be that of a kind of
    # "custodian" group, to which the doc is "assigned to" for handling.
    # !+CHAMBER_ID should be nullable=False, but fails on creating an Event...
    sa.Column("chamber_id", sa.Integer,
        sa.ForeignKey("group.group_id"),
        nullable=True
    ),
    #sa.Column("origin_chamber_id", sa.Integer,
    #    sa.ForeignKey("groups.group_id"), # !+ group (singular), chamber
    #    nullable=True
    #),
    
    # OWNERSHIP
    # owner <=> no dc equivalent
    # The bungeni user that submits (either directly, as the conceptual/legal 
    # "Owner" or someone else submits on his/her behalf as the "Drafter") the 
    # document to the chamber in Parliament. This is the Bungeni user/group who
    # is the conceptual owner of the document.
    # Note: an "external" Owner, an entity that is outside of Parliament, 
    # should also be supported.
    sa.Column("owner_id", sa.Integer,
        sa.ForeignKey("user.user_id"), #!+principal
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
    col_acronym("acronym"),
    # !+LABEL(mr, jan-2011) display label e.g. for link text?
    # title <=> dc:Title !+DescriptiveProperties(mr, jan-2011)
    # The name given to the resource. Typically, a Title will be a name
    # by which the resource is formally known.
    sa.Column("title", sa.Unicode(1024), nullable=False),
    sa.Column("sub_title", sa.Unicode(1024), nullable=True),
    # description <=> dc:Description !+DescriptiveProperties(mr, jan-2011)
    # An account of the content of the resource. Description may include but is
    # not limited to: an abstract, table of contents, reference to a graphical
    # representation of content or a free-text account of the content.
    sa.Column("description", sa.UnicodeText, nullable=True),
    sa.Column("summary", sa.UnicodeText, nullable=True),
    # original language of the document
    col_language_code("language"),
    sa.Column("body", sa.UnicodeText),
    
    # WORKFLOW
    col_status("status"),
    col_status_date("status_date"),
    sa.Column("doc_date", sa.DateTime(timezone=False), nullable=True),
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
    sa.Column("doc_urgency", sa.Unicode(length=128), nullable=True),
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
    
    # Dublin Core Metadata Fields
    sa.Column("source_title", sa.Unicode(1024), nullable=True),
    sa.Column("source_creator", sa.Unicode(1024), nullable=True),
    sa.Column("source_subject", sa.UnicodeText, nullable=True),
    sa.Column("source_description", sa.UnicodeText, nullable=True),
    sa.Column("source_publisher", sa.UnicodeText, nullable=True),
    sa.Column("source_publisher_address", sa.UnicodeText, nullable=True),
    sa.Column("source_contributors", sa.UnicodeText, nullable=True),
    sa.Column("source_date", sa.DateTime(timezone=False), nullable=True),
    sa.Column("source_type", sa.Unicode(128), nullable=True),
    sa.Column("source_format", sa.Unicode(128), nullable=True),
    sa.Column("source_doc_source", sa.UnicodeText, nullable=True),
    col_language_code("source_language", nullable=True),
    sa.Column("source_relation", sa.UnicodeText, nullable=True),
    sa.Column("source_coverage", sa.UnicodeText, nullable=True),
    sa.Column("source_rights", sa.UnicodeText, nullable=True),
)
doc_index = sa.Index("doc_status_idx", doc.c["status"])
doc_audit = make_audit_table(doc, metadata)


# principal: user, group

PrincipalSequence = sa.Sequence("principal_sequence")

principal = sa.Table("principal", metadata,
    sa.Column("principal_id", sa.Integer, PrincipalSequence, primary_key=True),
    # !+PRINCIPAL_NAME(mr, mar-2013) should really be THE (natural) primary key,
    # and replace principal_id altogether! Move col_principal_name to here.
    # for polymorphic_identity
    sa.Column("type", sa.Unicode(128), nullable=False),
)

user = sa.Table("user", metadata,
    # !+principal_name sa.ForeignKey("principal.principal_name")
    sa.Column("user_id", sa.Integer, 
        sa.ForeignKey("principal.principal_id"),
        primary_key=True),
    # !+principal_name(mr, feb-2013) "login" should really be "principal_name" here
    col_principal_name("login"),
    sa.Column("salutation", sa.Unicode(128)), # !+vocabulary?
    sa.Column("title", sa.Unicode(128)), # !+vocabulary?
    sa.Column("first_name", sa.Unicode(256), nullable=False),
    sa.Column("last_name", sa.Unicode(256), nullable=False),
    sa.Column("middle_name", sa.Unicode(256)),
    sa.Column("email", sa.String(512), nullable=False),
    # !+FLAVIO: let's think beyond M and F and beyond male and female
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
    sa.Column("national_id", sa.Unicode(256)),
    sa.Column("password", sa.String(36)), # store salted md5 hash hexdigests
    sa.Column("salt", sa.String(24)),
    sa.Column("description", sa.UnicodeText),
    sa.Column("remarks", sa.UnicodeText),
    sa.Column("image", sa.Binary),
    # !+active_p(mr, sep-2011) why is this "workflow status" column named
    # "active_p" and not "status"? Rename...
    # !+active_p(mr, sep-2011) why have identically named columns here and on 
    # member, with one being a string and other a bool?
    # !+FLAVIO: we have the "odd" issues that a "state" is not reached through 
    # workflow but using "the field "active" ... see also notes below.
    # Get rid of it?
    sa.Column("active_p", sa.String(1),
        sa.CheckConstraint("""active_p in ('A', 'I', 'D')"""),
        # !+active_p(mr, sep-2011) workflow status columns MUST not have a
        # default value--it is up to the workflow to decide what this should be!
        #default="A", # active/inactive/deceased
    ),
    #!+receive_notification comment out for now - will be used for user preferences
    sa.Column("receive_notification", sa.Boolean, default=True),
    col_language_code("language"),
    col_language_code("home_language", nullable=True),
)

admin_user = sa.Table("admin_user", metadata,
    sa.Column("user_id", sa.Integer,
        sa.ForeignKey("user.user_id"),
        primary_key=True,
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

# password restore links
password_restore_link = sa.Table("password_restore_link", metadata,
    sa.Column("user_id", sa.Integer,
        sa.ForeignKey("user.user_id"),
        primary_key=True
    ),
    sa.Column("hash", sa.Unicode(256), nullable=False),
    sa.Column("expiration_date", sa.DateTime(timezone=False), nullable=False) 
) 


def _group_principal_name(context):
    """Derive the group principal_name (from conceptual_name, group_id)
    """
    params = context.current_parameters
    return u"{0}.g{1}".format(params["conceptual_name"], params["group_id"])


# group - we use a very normalized form here to represent all kinds of
# groups and their relations to other things in the system.
group = sa.Table("group", metadata,
    # !+principal_name sa.ForeignKey("principal.principal_name"),
    sa.Column("group_id", sa.Integer,
        sa.ForeignKey("principal.principal_id"),
        primary_key=True),
    sa.Column("short_name", sa.Unicode(512), nullable=False),
    sa.Column("full_name", sa.Unicode(1024)),
    col_acronym("acronym"),
    # conceptual_name - user-selected conceptual name for the group:
    # - used to automatically derive the principal_name (login) for the group
    #   and for this reason is limited to half the size of that
    # - there may only be one *active* group per (conceptual_name, principal.type)
    sa.Column("conceptual_name", sa.Unicode(64), nullable=False),
    col_principal_name("principal_name", default=_group_principal_name),
    sa.Column("description", sa.UnicodeText),
    sa.Column("body", sa.UnicodeText),
    col_status("status"),
    col_status_date("status_date"),
    sa.Column("start_date", sa.Date, nullable=False),
    sa.Column("end_date", sa.Date),
    # !+ rename to "group_type" (consistent with doc table: type/doc_type?
    # or rename doc.doc_type to doc.sub_type?
    sa.Column("sub_type", sa.Unicode(128), nullable=True),
    # !+ should we add a constraint such as chamber.sub_type must be unique?
    # i.e. can only have one "active" chamber of any given type
    sa.Column("parent_group_id", sa.Integer,
        sa.ForeignKey("group.group_id")
     ),
    col_language_code("language"),
    # the role gained by being a member of this group
    sa.Column("group_role", sa.Unicode(256), nullable=False),
    # is the group "permament", "temporary", ... ?
    sa.Column("group_mandate_type", sa.Unicode(128)),
)
group_audit = make_audit_table(group, metadata)


# member 

# group memberships encompasses any user participation in a group, including
# substitutions.
member = sa.Table("member", metadata,
    sa.Column("member_id", sa.Integer, primary_key=True),
    sa.Column("user_id", sa.Integer,
        sa.ForeignKey("user.user_id"),
        nullable=False
    ),
    sa.Column("group_id", sa.Integer,
        sa.ForeignKey("group.group_id"),
        nullable=False
    ),
    col_status("status"),
    col_status_date("status_date"),
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
        sa.ForeignKey("member.member_id"),
        unique=True
    ),
    sa.Column("substitution_type", sa.Unicode(100)),
    # the type of membership, polymorphic identity
    sa.Column("member_type", sa.Unicode(128), default="member", nullable=False),
    col_language_code("language"),
    # Representation of this member (in a chamber or any other group):
    # - geo: the region/province/constituency (divisions and order may be in any
    # way as appropriate for the given parliamentary territory)
    # - sig: represented Special Interest Group (s)
    # Values should be a Hierarchical Controlled Vocabulary Micro Data Format: 
    # a triple-colon ":::" separated sequence of *key phrase paths*, each of 
    # which is a double-colon "::" separated sequence of *key phrases*.
    sa.Column("representation_geo", sa.UnicodeText, nullable=True),
    sa.Column("representation_sig", sa.UnicodeText, nullable=True),
    # how the user became a member of this group
    sa.Column("election_type", sa.Unicode(128),
        default="elected", # elected, nominated, ex officio, co-opted, ...
        nullable=True),
    sa.Column("election_date", sa.Date, 
        server_default=sa.sql.text("now()::date"),
        nullable=True),
    sa.Column("leave_reason", sa.Unicode(128)),
    sa.schema.UniqueConstraint("user_id", "group_id"),
)
member_audit = make_audit_table(member, metadata)

# sub roles to be granted when a document is assigned to a user
member_role = sa.Table("member_role", metadata,
    sa.Column("member_id", sa.Integer,
        sa.ForeignKey("member.member_id"),
        primary_key=True),
    sa.Column("role_id", sa.Unicode(256), nullable=False,
        primary_key=True),
    # !+IS_GLOBAL(mr, jul-2014) what is the exact intention for this column?
    sa.Column("is_global", sa.Boolean, default=False),
)

# title - to indicate the title a person has in a specific context (Ministry, 
# Committee, Chamber, ...) and for what period (from - to)
member_title = sa.Table("member_title", metadata,
    sa.Column("member_title_id", sa.Integer, primary_key=True),
    sa.Column("member_id", sa.Integer,
        sa.ForeignKey("member.member_id"),
        nullable=False
    ),
    # title of user"s group role
    sa.Column("title_type_id", sa.Integer,
        sa.ForeignKey("title_type.title_type_id"),
        nullable=False
    ),
    sa.Column("start_date", sa.Date, default=datetime.now, nullable=False),
    sa.Column("end_date", sa.Date),
    col_language_code("language"),
    sa.schema.UniqueConstraint("member_id", "title_type_id")
)

# the personal role of a user in terms of their membership in this group:
# The personal roles a person may have varies with the context 
# e.g. in a party one may have the role spokesperson, member, ...
title_type = sa.Table("title_type", metadata,
    sa.Column("title_type_id", sa.Integer, primary_key=True),
    sa.Column("group_id", sa.Integer, 
                sa.ForeignKey("group.group_id"), nullable=False),
    sa.Column("title_name", sa.Unicode(128), nullable=False),
    sa.Column("user_unique", sa.Boolean, default=False,), # nullable=False),
    sa.Column("sort_order", sa.Integer, nullable=False),
    col_language_code("language"),
)



# SUPPORT TYPES

# doc_principal - !+VP composite-PK means no VP support for doc_principal

doc_principal = sa.Table("doc_principal", metadata,
    sa.Column("doc_id", sa.Integer,
        sa.ForeignKey("doc.doc_id"),
        primary_key=True),
    sa.Column("principal_id", sa.Integer, 
        sa.ForeignKey("principal.principal_id"),
        primary_key=True),
    # relationship qualifier, also the item's polymorphic identity
    sa.Column("activity", sa.Unicode(128), primary_key=True, nullable=False),
    sa.Column("date", sa.DateTime(timezone=False), 
        server_default=sa.sql.text("now()"),
        nullable=False),
)
doc_principal_audit = make_audit_table(doc_principal, metadata)


# sitting, session

session = sa.Table("session", metadata,
    sa.Column("session_id", sa.Integer, primary_key=True),
    sa.Column("chamber_id", sa.Integer, # group_id
        sa.ForeignKey("group.group_id"),
        nullable=False
    ),
    sa.Column("short_name", sa.Unicode(512), nullable=False), #!+ACRONYM
    sa.Column("full_name", sa.Unicode(1024), nullable=False), #!+NAME
    sa.Column("start_date", sa.Date, nullable=False),
    sa.Column("end_date", sa.Date),
    sa.Column("notes", sa.UnicodeText),
    col_language_code("language"),
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
    sa.Column("recurring_type", sa.Unicode(64)),
    sa.Column("recurring_end_date", sa.DateTime(timezone=False), 
        nullable=True),
    col_status("status"),
    col_status_date("status_date"),
    # venue for the sitting
    sa.Column("venue_id", sa.Integer, sa.ForeignKey("venue.venue_id")),
    col_language_code("language"),
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
    col_status("status"),
    col_language_code("language"),
    sa.Column("group_id", sa.Integer, sa.ForeignKey("group.group_id"))
)


# venues for sittings:

venue = sa.Table("venue", metadata,
    sa.Column("venue_id", sa.Integer, primary_key=True),
    sa.Column("short_name", sa.Unicode(512), nullable=False),
    sa.Column("description", sa.UnicodeText),
    sa.Column("body", sa.UnicodeText),
    col_language_code("language"),
    # !+ app assumption: the referenced group here is *always* a chamber?
    sa.Column("group_id", sa.Integer, sa.ForeignKey("group.group_id"))
)


''' !+BookedResources
# resources for sittings like rooms ...

resource_types = sa.Table("resource_types", metadata,
    sa.Column("resource_type_id", sa.Integer, primary_key=True),
    sa.Column("short_name", sa.Unicode(512), nullable=False), #!+ACRONYM
    col_language_code("language"),
)

resources = sa.Table("resources", metadata,
    sa.Column("resource_id", sa.Integer, primary_key=True),
    sa.Column("resource_type_id", sa.Integer,
        sa.ForeignKey("resource_types.resource_type_id"),
        nullable=False
    ),
    sa.Column("short_name", sa.Unicode(512), nullable=False),
    sa.Column("description", sa.UnicodeText),
    col_language_code("language"),
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


# address 

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
    # !+FLAVIO: see my note above regarding country ids
    sa.Column("country_id", sa.String(2),
        sa.ForeignKey("country.country_id"),
        nullable=True
    ),
    sa.Column("phone", sa.Unicode(256)),
    sa.Column("fax", sa.Unicode(256)),
    sa.Column("email", sa.String(512)),
    col_status("status"),
    col_status_date("status_date"),
)


# country - 2-letter and 3-letter codes, see:
# http://www.nationsonline.org/oneworld/country_code_list.htm
country = sa.Table("country", metadata,
    sa.Column("country_id", sa.String(2), primary_key=True), # ISO alpha-2
    sa.Column("iso_name", sa.Unicode(80), nullable=False),
    sa.Column("country_name", sa.Unicode(80), nullable=False),
    sa.Column("iso3", sa.String(3)), # ISO alpha-3
    sa.Column("numcode", sa.Integer), # ISO UN M49
    col_language_code("language"),
)


item_schedule = sa.Table("item_schedule", metadata,
    sa.Column("schedule_id", sa.Integer, primary_key=True),
    # !+object_id/object_type - use object_id/object_type as elsewhere
    sa.Column("item_id", sa.Integer, nullable=False),
    sa.Column("item_type", sa.Unicode(128), nullable=False),
    sa.Column("sitting_id", sa.Integer,
        sa.ForeignKey("sitting.sitting_id"),
        nullable=False
    ),
    sa.Column("planned_order", sa.Integer),
    sa.Column("real_order", sa.Integer),
    # item was discussed on this sitting
    sa.Column("active", sa.Boolean, default=True),
    # workflow status of the item for this schedule
    # NOT workflow status of this item_schedule!
    sa.Column("item_status", sa.Unicode(128)),
)

editorial_note = sa.Table("editorial_note", metadata,
    sa.Column("editorial_note_id", sa.Integer, primary_key=True),
    sa.Column("text", sa.UnicodeText, nullable=True),
    sa.Column("group_id", sa.Integer, sa.ForeignKey("group.group_id"),
        nullable=True
    ),
    col_language_code("language"),
)

# store text record for a sitting or 
agenda_text_record = sa.Table("agenda_text_record", metadata,
    sa.Column("text_record_id", sa.Integer, primary_key=True),
    sa.Column("text", sa.UnicodeText, nullable=False),
    sa.Column("record_type", sa.Unicode(128), nullable=False),
    col_language_code("language"),
)

# to produce the proceedings:
# capture the discussion on this item

item_schedule_discussion = sa.Table("item_schedule_discussion", metadata,
    sa.Column("discussion_id", sa.Integer, primary_key=True),
    sa.Column("schedule_id", sa.Integer,
        sa.ForeignKey("item_schedule.schedule_id")),
    sa.Column("body", sa.UnicodeText),
    sa.Column("sitting_time", sa.Time(timezone=False)),
    col_language_code("language"), #!+ default="en"
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
    sa.Column("roll_call", FSBlob(128)),
    sa.Column("mimetype", sa.Unicode(128)),
    col_language_code("language"), #!+ default="en"
)

sitting_report = sa.Table("sitting_report", metadata,
    sa.Column("report_id", sa.Integer,
        sa.ForeignKey("doc.doc_id"), primary_key=True
    ),
    sa.Column("sitting_id", sa.Integer,
        sa.ForeignKey("sitting.sitting_id"), primary_key=True
    ),
)


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
    sa.Column("body", sa.UnicodeText),
    sa.Column("data", FSBlob(32)), #!+file
    sa.Column("name", sa.String(256)), #!+file
    sa.Column("mimetype", sa.String(128)), #!+file
    col_status("status"),
    col_status_date("status_date"),
    col_language_code("language"),
)
attachment_index = sa.Index("attachment_head_id_idx", attachment.c["head_id"])
attachment_audit = make_audit_table(attachment, metadata)




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
    col_status("status"),
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
    col_language_code("language"),
)


translation = sa.Table("translation", metadata,
    sa.Column("object_id", sa.Integer, primary_key=True, nullable=False),
    sa.Column("object_type", sa.Unicode(128), primary_key=True, nullable=False),
    col_language_code("lang", primary_key=True),
    sa.Column("field_name", sa.Unicode(128), primary_key=True, nullable=False),
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
    sa.Column("object_type", sa.Unicode(128),
        primary_key=True, nullable=False),
    col_status("object_status"),
    sa.Column("time_string", sa.String(64),
        primary_key=True, nullable=False),
    sa.Column("notification_date_time", sa.DateTime(timezone=False),
        nullable=False)
)

debate_record = sa.Table("debate_record", metadata,
    sa.Column("debate_record_id", sa.Integer, primary_key=True),
    sa.Column("sitting_id", sa.Integer, sa.ForeignKey("sitting.sitting_id"),
        unique=True),
    col_status("status"),
    col_status_date("status_date"),
)
debate_record_audit = make_audit_table(debate_record, metadata)

debate_record_item = sa.Table("debate_record_item", metadata,
    sa.Column("debate_record_item_id", sa.Integer, primary_key=True),
    sa.Column("debate_record_id", sa.Integer,
        sa.ForeignKey("debate_record.debate_record_id")),
    sa.Column("type", sa.String(128), nullable=False),
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
    col_status("status"),
    col_status_date("status_date"),
    col_language_code("language"),
)

debate_media = sa.Table("debate_media", metadata,
    sa.Column("debate_record_id", sa.Integer,
        sa.ForeignKey("debate_record.debate_record_id"), primary_key=True),
    sa.Column("media_id", sa.Integer, primary_key=True),
    sa.Column("media_path", sa.UnicodeText, nullable=False),
    sa.Column("media_type", sa.Unicode(128), nullable=False)
)

debate_take = sa.Table("debate_take", metadata,
    sa.Column("debate_record_id", sa.Integer,
        sa.ForeignKey("debate_record.debate_record_id"), primary_key=True),
    sa.Column("debate_take_id", sa.Integer, primary_key=True),
    sa.Column("start_date", sa.DateTime(timezone=False), nullable=False),
    sa.Column("end_date", sa.DateTime(timezone=False), nullable=False),
    sa.Column("transcriber_id", sa.Integer, 
        sa.ForeignKey("user.user_id")),
    sa.Column("debate_take_name", sa.String(128), nullable=False)
)


# OAuth

oauth_application = sa.Table("oauth_application", metadata,
    sa.Column("application_id", sa.Integer, primary_key=True),
    sa.Column("identifier", sa.UnicodeText, nullable=False, 
        unique=True),
    sa.Column("name", sa.UnicodeText, nullable=False),
    sa.Column("secret", sa.String(128), nullable=False),
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
    sa.Column("authorization_code", sa.Unicode(128), nullable=False),
    sa.Column("expiry", sa.DateTime(timezone=False), nullable=False),
    sa.Column("refresh_token", sa.Unicode(128), nullable=False),
)

oauth_access_token = sa.Table("oauth_access_token", metadata,
    sa.Column("access_token_id", sa.Integer, primary_key=True),
    sa.Column("authorization_token_id", sa.Integer,
        sa.ForeignKey("oauth_authorization_token.authorization_token_id"),
        nullable=False
    ),
    sa.Column("access_token", sa.Unicode(128), nullable=False),
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

