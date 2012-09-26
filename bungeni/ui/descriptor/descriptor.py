# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Form Schemas for Domain Objects

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.descriptor")

from copy import deepcopy

from bungeni.alchemist.model import ModelDescriptor, show, hide

# We import bungeni.core.workflows.adapters to ensure that the "states"
# attribute on each "workflow" module is setup... this is to avoid an error
# when importing bungeni.ui.descriptor.descriptor from standalone scripts:
import bungeni.core.workflows.adapters # needed by standalone scripts !+review

from bungeni.ui.forms import validations
from bungeni.ui.i18n import _
from bungeni.ui import vocabulary # !+
from bungeni.ui.descriptor import constraints
from bungeni.ui.descriptor.field import F
from bungeni.utils import misc


def get_field(fields, name):
    return misc.get_keyed_item(fields, name, key="name")
def replace_field(fields, field):
    return misc.replace_keyed_item(fields, field, key="name")
def insert_field_after(fields, name, field):
    fields.insert(fields.index(get_field(fields, name)) + 1, field)
    

####
# Fields

# Notes:
#
# Field parameters, if specified, should be in the following order:
#   name, label, description, modes, localizable, property, 
#   listing_column, view_widget, edit_widget, add_widget, search_widget
#
#   !+FIELD_PERMISSIONS(mr, nov-2010) view_permission/edit_permission params
#   are deprecated -- when applied to any field (that corresponds to an
#   attribute of the domain's class), the domain.zcml setting for that same
#   class attribute will anyway take precedence.
#
# modes: !+
# - default: "view edit add"
# - all individual bool params {view, edit, add, listing, search} for each
#   supported mode are now obsolete
# - to specify a non-default mode, must redefine entire modes parameter
#   e.g. to add "listing" mode must state modes="view edit add listing"
# - use modes="" as the equivalent of OBSOLETED omit=True
#
# property
# by default, property itself is None
# if not None, then the property's default values for schema.Field init params:
#   title="", description="", __name__="",
#   required=True, readonly=False, constraint=None, default=None
#
# required
# - Field.property.required: by default required=True for all schema.Field
# - !+Field.required(mr, oct-2010) OBSOLETED.
#
# localization -- guidelines
# - [user] fields should, whenever possible, be displayable/localizable in all
#   modes, but as a minimum fields should at least be displayable/localizable
#   in "view listing".
# - [user-req] fields (e.g. primary keys) should NOT be localizable in "add"
# - [sys] fields should NOT be *displayable* in "add edit" (but, as per [user], 
#   should be displayable/localizable in "view listing")
# - [rtf] [img] [file] fields should not be *displayable* in "listing"
# - [derived] fields should only be diplsyable/localizable in "view listing"

# !+EDIT_AS_VIEW fields in "edit" mode on which user has no Edit permission? 

def LanguageField(name="language", 
        localizable=[
            show("add"), # db-not-null-ui-add
            show("view edit"), 
            hide("listing"), 
        ]
    ):
    f = F(name=name, 
        label="Language", 
        description=None, 
        required=True,
        localizable=localizable,
        value_type="language",
        render_type="single_select",
        vocabulary="language_vocabulary",
    )
    return f

def AdmissibleDateField(name="admissible_date"):
    return F(name=name, # [derived]
        label="Admissible Date", 
        description=None, 
        required=True,
        localizable=[ show("view listing"), ],
        value_type="date",
        render_type="date",
    )


####
# Descriptors

# !+ID_NAME_LABEL_TITLE(mr, oct-2010) use of "id", "name", "label", "title",
# should be conistent -- the (localized) {display, container}_name attributes
# here should really all be {display, container}_label.

# !+CHOICE_FIELDS(mr, nov-2011) for fields with a zope.schema._field.Choice
# property that uses some kind of vocabulary as source, then there should be 
# a sensible "default rendering" for view, edit, add and listing modes, that
# will display the field value appropriately (including proper translation, 
# of the value itself or of any label that may be associated with it).


class UserDescriptor(ModelDescriptor):
    order = 4 # top
    localizable = True
    sort_on = ["user_id"]
    sort_dir = "asc"
    
    fields = [
        F(name="user_id", # [sys] for linking item in listing
            label="Name",
            description=None, 
            required=True,
            localizable=[
                # "add edit" -> non-ui
                hide("view"),
                show("listing"),
            ],
            value_type="user",
            render_type="no_input",
        ),
        F(name="salutation", 
            label="Salutation", 
            description="e.g. Mr. Mrs, Prof. etc.",
            localizable=[
                show("view edit add listing"),
            ],
        ),
        F(name="title", 
            label="Title",
            description="e.g. Chief Advisor, etc.",
            localizable=[
                show("view edit add listing"),
            ],
        ),
        F(name="first_name",
            label="First Name",
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
        ),
        F(name="middle_name",
            label="Middle Name",
            localizable=[
                show("view edit add"),
                hide("listing"),
            ],
        ),
        F(name="last_name",
            label="Last Name",
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
        ),
        F(name="email",
            label="Email",
            description="Email address",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="email",
        ),
        F(name="login",
            label="Login",
            description="Must contain only letters, numbers, a period (.) "
                "and underscore (_). Should start with a letter and be "
                "between 3 and 20 characters long",
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view"),
                hide("listing"),
            ],
            value_type="login",
        ),
        F(name="_password",
            label="Initial password",
            localizable=[
                show("add"), # db-not-null-ui-add
            ],
            value_type="password",
        ),
        F(name="status",
            label="Status",
            required=True,
            localizable=[
                show("view listing"),
            ],
            value_type="status",
            render_type="single_select",
            vocabulary="workflow_states",
        ),
        F(name="national_id",
            label="National Id",
            localizable=[
                show("view edit add"),
                hide("listing"),
            ],
        ),
        F(name="gender",
            label="Gender",
            localizable=[
                show("view edit add"),
                show("listing"),
            ],
            value_type="text",
            render_type="radio",
            vocabulary="gender",
        ),
        F(name="date_of_birth",
            label="Date of Birth",
            localizable=[
                show("view edit add"),
                show("listing"),
            ],
            value_type="date",
            render_type="date",
        ),
        F(name="birth_country",
            label="Country of Birth",
            localizable=[
                show("view edit add"),
                hide("listing"),
            ],
            value_type="text",
            render_type="single_select",
            vocabulary="country",
        ),
        F(name="birth_nationality",
            label="Nationality at Birth",
            localizable=[
                show("view edit add"),
                hide("listing"),
            ],
            value_type="text",
            render_type="single_select",
            vocabulary="country",
        ),
        F(name="current_nationality",
            label="Current Nationality",
            localizable=[
                show("view edit add"),
                hide("listing"),
            ],
            value_type="text",
            render_type="single_select",
            vocabulary="country",
        ),
        F(name="marital_status",
            label="Marital Status",
            localizable=[
                show("view edit add"),
                hide("listing"),
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="marital_status",
        ),
        F(name="date_of_death",
            label="Date of Death",
            localizable=[
                show("view edit"),
                hide("listing"),
            ],
            value_type="date",
            render_type="date",
        ),
        F(name="image",
            label="Image",
            description="Picture of the person",
            # !+LISTING_IMG(mr, apr-2011) TypeError, not JSON serializable
            localizable=[
                show("view edit add"),
            ],
            value_type="image",
            render_type="image",
        ),
        LanguageField("language"), # [user-req]
        F(name="description",
            label="Biographical notes",
            localizable=[
                show("view edit add"),
            ],
            value_type="text",
            render_type="rich_text",
        ),
        F(name="remarks",
            label="Remarks",
            localizable=[
                show("view edit add"),
            ],
            value_type="text",
            render_type="rich_text",
        ),
    ]
    schema_invariants = [constraints.DeathBeforeLife]
    custom_validators = [validations.email_validator]


class UserDelegationDescriptor(ModelDescriptor):
    """Delegate rights to act on behalf of that user."""
    order = 3 # top
    localizable = True
    #display_name = "Delegate to user"
    #container_name = "Delegations"
    
    fields = [
        F(name="delegation_id",
            label="User",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="user",
            render_type="single_select",
            vocabulary="user",
        ),
    ]

class GroupMembershipRoleDescriptor(ModelDescriptor):
    """Role associated with a group membership
    """
    localizable = False
    #display_name = "sub roles"
    #container_name = "sub roles"
    fields = [
        F(name="role_id",
          label="sub role",
          description="the sub role this member will get",
          required=True,
          value_type="text",
          render_type="single_select",
          vocabulary="group_sub_role"
          ),
        F(name="is_global",
          label="is global",
          description="whether or not this role is granted globally",
          required=True,
          value_type="bool",
          render_type="bool",
          )
        ]

class GroupMembershipDescriptor(ModelDescriptor):
    localizable = False
    sort_on = ["user_id"]
    sort_dir = "asc"
    
    fields = [
        F(name="start_date",
            label="Start Date",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="date",
            render_type="date",
        ),
        F(name="end_date",
            label="End Date",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="date",
            render_type="date",
        ),
        F(name="active_p",
            label="Active",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="bool",
            render_type="bool",
        ),
        LanguageField("language"), # [user-req]
        F(name="substitution_type", #!+UNUSED? string100
            label="Type of Substitution",
            localizable=[
                show("view edit listing"),
            ],
        ),
        F(name="replaced_id", #!+UNUSED? fk to a membership
            label="Substituted by",
            localizable=[
                show("view edit listing"),
            ],
            value_type="text",
            render_type="single_select",
            vocabulary="substitution",
        ),
        F(name="status",
            label="Status",
            required=True,
            localizable=[
                show("view listing"),
            ],
            value_type="status",
            render_type="single_select",
            vocabulary="workflow_states",
        ),
        F(name="status_date",
            label="Status Date",
            required=True,
            localizable=[
                show("view listing"),
            ],
            value_type="date",
            render_type="date",
        ),
    ]
    schema_invariants = [
        constraints.EndAfterStart,
        constraints.ActiveAndSubstituted,
        constraints.SubstitudedEndDate,
        constraints.InactiveNoEndDate
    ]
    custom_validators = [
        validations.validate_date_range_within_parent,
        validations.validate_group_membership_dates
    ]


# !+bungeni_custom, as part of descriptor config?
_ORDER_BY_CONTAINER_NAMES = [
    0, 1, 2, 3, 4, 5, 6, 7, 8 , 9, # occupy first 10, start this batch from 10
    "agendaitems",
    "bills",
    "motions",
    "questions",
    "tableddocuments",
    "preports",
    "sessions",
    "sittings",
    "parliamentmembers",
    "politicalgroups",
    "committees",
    "governments",
    "title_types",
]

# !+naming
class MemberOfParliamentDescriptor(GroupMembershipDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("parliamentmembers")
    localizable = True
    display_name = "Member of parliament" # !+Parliament Member
    container_name = "Members of parliament" # !+Parliament Members
    sort_on = ["user_id"]
    fields = [
        F(name="user_id",
            label="Name",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view listing"),
            ],
            value_type="user",
            render_type="single_select",
            vocabulary="member",
        ),
        F(name="member_election_type",
            label="Election Type",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="member_election_type",
        ),
        F(name="election_nomination_date",
            label="Election/Nomination Date",
            required=False,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="date",
            render_type="date",
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        F(name="representation",
            label="Representation",
            description="Select Representation",
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit"),
                hide("listing"),
            ],
            value_type="text",
            render_type="tree_text",
            vocabulary="representation",
        ),
        F(name="party",
            label="Political Party",
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="party",
        ),
        F(name="leave_reason",
            label="Leave Reason",
            localizable=[
                show("view edit add"),
                hide("listing"),
            ],
        ),
        F(name="notes",
            label="Notes",
            localizable=[
                show("view edit add"),
            ],
            value_type="text",
            render_type="rich_text",
        ),
    ])
    schema_invariants = GroupMembershipDescriptor.schema_invariants + [
       constraints.MpStartBeforeElection]


class PoliticalGroupMemberDescriptor(GroupMembershipDescriptor):
    """Membership of a user in a political group."""
    localizable = True
    
    fields = [
        F(name="user_id",
            label="Name",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view listing"),
            ],
            value_type="member", # !+user: constrained by "parent group" OR vocabulary
            render_type="single_select",
            vocabulary="parliament_member",
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        F(name="notes",
            label="Notes",
            localizable=[
                show("view edit add"),
            ],
            value_type="text",
            render_type="rich_text",
        ),
    ])


class GroupDescriptor(ModelDescriptor):
    localizable = True # !+ARCHETYPE_LOCALIZATION
    sort_on = ["group_id"]
    sort_dir = "asc"
    _combined_name_title = "%s [%s]" % (_("Full Name"), _("Short Name"))
    default_field_order = [
        "full_name",
        "short_name",
        "acronym",
        "combined_name",
        "language",
        "start_date",
        "end_date",
        "status",
        "description",
    ]
    fields = [
        F(name="full_name",
            label="Full Name",
            localizable=[
                show("view edit add listing"),
            ],
        ),
        F(name="short_name",
            label="Short Name",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
        ),
        F(name="acronym",
            label="Acronym",
            localizable=[
                show("view edit add listing"),
            ],
        ),
        F(name="combined_name", # [derived]
            label="Full Name [Short Name]",
            localizable=[
                show("listing"),
            ],
            value_type="combined_name",
        ),
        LanguageField("language"), # [user-req]
        F(name="description",
            label="Description",
            localizable=[
                show("view edit add"),
            ],
            value_type="text",
            render_type="rich_text",
        ),
        F(name="start_date",
            label="Start Date",
            required=True,
            localizable=[
                show("view edit add listing"),
            ],
            value_type="date",
            render_type="date",
        ),
        F(name="end_date",
            label="End Date",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="date",
            render_type="date",
        ),
        F(name="status",
            label="Status",
            required=True,
            localizable=[
                show("view listing"),
            ],
            value_type="status",
            render_type="single_select",
            vocabulary="workflow_states",
        ),
    ]
    schema_invariants = [constraints.EndAfterStart]
    custom_validators = [validations.validate_date_range_within_parent]


class ParliamentDescriptor(GroupDescriptor):
    order = 1 # top
    localizable = True
    sort_on = ["start_date"]
    default_field_order = [
        "full_name",
        "short_name",
        "identifier", #"acronym",
        #"combined_name",
        "language",
        "election_date",
        "start_date",
        "end_date",
        #"status",
        "description",
    ]
    fields = [
        F(name="full_name",
            label="Parliament Name",
            localizable=[
                show("view edit add listing"),
            ],
        ),
        F(name="short_name",
            label="Short Name",
            description="Shorter name for the parliament",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
        ),
        F(name="identifier",
            label="Parliament Identifier",
            description="Unique identifier or number for this Parliament",
            localizable=[
                show("view edit add listing"),
            ],
        ),
        LanguageField("language"), # [user-req]
        F(name="description",
            label="Description",
            localizable=[
                show("view edit add"),
            ],
            value_type="text",
            render_type="rich_text",
        ),
        F(name="election_date",
            label="Election Date",
            description="Date of the election",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="date",
            render_type="date",
        ),
        F(name="start_date",
            label="In power from",
            description="Date of the swearing in",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="date",
            render_type="date",
        ),
        F(name="end_date",
            label="In power till",
            description="Date of the dissolution",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="date",
            render_type="date",
        ),
    ]
    schema_invariants = [
        constraints.EndAfterStart,
        constraints.ElectionAfterStart
    ]
    custom_validators = [validations.validate_parliament_dates]


class CommitteeDescriptor(GroupDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("committees")
    localizable = True
    
    fields = deepcopy(GroupDescriptor.fields)
    get_field(fields, "start_date").localizable = [
        show("view edit add"),
        hide("listing")
    ]
    get_field(fields, "end_date").localizable = [
        show("view edit add"),
        hide("listing")
    ]
    
    fields.extend([
        F(name="identifier",
            label="Committee Identifier",
            description="Unique identifier or number for this Committee",
            localizable=[
                show("view edit add"),
            ],
        ),
        F(name="sub_type", # group field, only used in committee
            label="Committee Type",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="committee_type",
        ),
        F(name="group_continuity",
            label="Committee Status Type",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="committee_continuity",
        ),
        F(name="num_members",
            label="Number of members",
            localizable=[
                show("view edit add"),
                hide("listing")
            ],
            value_type="number",
            render_type="number",
        ),
        F(name="min_num_members",
            label="Minimum Number of members",
            localizable=[
                show("view edit add"),
                hide("listing")
            ],
            value_type="number",
            render_type="number",
        ),
        F(name="quorum",
            label="Quorum",
            localizable=[
                show("view edit add"),
                hide("listing")
            ],
            value_type="number",
            render_type="number",
        ),
        F(name="num_clerks",
            label="Number of clerks",
            localizable=[
                show("view edit add"),
                hide("listing")
            ],
            value_type="number",
            render_type="number",
        ),
        F(name="num_researchers",
            label="Number of researchers",
            localizable=[
                show("view edit add"),
                hide("listing")
            ],
            value_type="number",
            render_type="number",
        ),
        F(name="proportional_representation",
            label="Proportional representation",
            localizable=[
                show("view edit add"),
                hide("listing")
            ],
            value_type="bool",
            render_type="bool",
        ),
        F(name="reinstatement_date",
            label="Reinstatement Date",
            localizable=[
                show("view edit add"),
                hide("listing")
            ],
            value_type="date",
            render_type="date",
        ),
    ])
    schema_invariants = [
        constraints.EndAfterStart,
        #DissolutionAfterReinstatement
    ]
    custom_validators = [validations.validate_date_range_within_parent]


class CommitteeMemberDescriptor(GroupMembershipDescriptor):
    localizable = True
    
    fields = [
        F(name="user_id",
            label="Name",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view listing"),
            ],
            value_type="user",
            render_type="single_select",
            vocabulary="parliament_member",
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        F(name="notes",
            label="Notes",
            localizable=[
                show("view edit add"),
            ],
            value_type="text",
            render_type="rich_text",
        ),
    ])


class AddressDescriptor(ModelDescriptor):
    localizable = False
    display_name = "Address" # !+
    container_name = "Addresses" # !+
    fields = [
        F(name="logical_address_type",
            label="Address Type",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="logical_address_type",
        ),
        F(name="postal_address_type",
            label="Postal Address Type",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="postal_address_type",
        ),
        F(name="street",
            label="Street",
            localizable=[
                show("view edit add"),
                hide("listing"),
            ],
            value_type="text",
            render_type="text_box",
        ),
        F(name="city",
            label="City",
            localizable=[
                show("view edit add listing"),
            ],
        ),
        F(name="zipcode",
            label="Zip Code",
            localizable=[
                show("view edit add listing"),
            ],
        ),
        F(name="country_id",
            label="Country",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="text",
            render_type="single_select",
            vocabulary="country",
        ),
        F(name="phone",
            label="Phone Number(s)",
            description="Enter one phone number per line",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="text", # !+ phone ?
            render_type="text_box",
        ),
        F(name="fax",
            label="Fax Number(s)",
            description="Enter one fax number per line",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="text", # !+ phone ?
            render_type="text_box",
        ),
        F(name="email",
            label="Email",
            description="Email address",
            localizable=[
                show("view edit add listing"),
            ],
        ),
        #Field(name="im_id",
        #    property=schema.TextLine(title=_("Instant Messenger Id"),
        #        description=_("ICQ, AOL IM, GoogleTalk..."),
        #        required=False
        #    )
        #), !+IM(mr, oct-2010) morph to some "extra_info" on User
    ]

class GroupAddressDescriptor(AddressDescriptor):
    localizable = True
    fields = deepcopy(AddressDescriptor.fields)
class UserAddressDescriptor(AddressDescriptor):
    localizable = True
    fields = deepcopy(AddressDescriptor.fields)

class TitleTypeDescriptor(ModelDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("title_types")
    localizable = True
    display_name = "Title types" # !+
    container_name = "Title types" # !+
    fields = [
        F(name="title_name",
            label="Name",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
        ),
        F(name="user_unique",
            label="Only one user may have this title",
            description="Limits persons with this title to one",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="text", # in schema bool w. default=False
            render_type="single_select",
            vocabulary="yes_no", 
        ),
        F(name="sort_order",
            label="Sort Order",
            description="The order in which members with this title " \
                "will appear relative to other members",
            required=True,
            localizable=[
                show("view edit add listing"),
            ],
            value_type="number",
            render_type="number",
        ),
        LanguageField("language"), # [user-req]
    ]
    #custom_validators = [ validations.validate_sub_role_unique ]

class MemberTitleDescriptor(ModelDescriptor):
    localizable = True
    display_name = "Title"
    container_name = "Titles"
    fields = [
        F(name="title_type_id",
            label="Title",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="group_title_types",
        ),
        F(name="start_date",
            label="Start Date",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="date",
            render_type="date",
        ),
        F(name="end_date",
            label="End Date",
            description="Date of the dissolution",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="date",
            render_type="date",
        ),
        LanguageField("language"), # [user-req]
    ]
    #] + [ deepcopy(f) for f in AddressDescriptor.fields
    #      if f["name"] not in ("role_title_id",) ]

    schema_invariants = [
        constraints.EndAfterStart,
    ]
    custom_validators = [
        validations.validate_date_range_within_parent,
        validations.validate_member_titles
    ]


class CommitteeStaffDescriptor(GroupMembershipDescriptor):
    localizable = True
    
    fields = [
        F(name="user_id",
            label="Name",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view listing"),
            ],
            value_type="user",
            render_type="single_select",
            vocabulary="user_not_mp",
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        F(name="notes",
            label="Notes",
            localizable=[
                show("view edit add"),
            ],
            value_type="text",
            render_type="rich_text",
        ),
    ])


class PoliticalGroupDescriptor(GroupDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("politicalgroups")
    localizable = True
    
    fields = deepcopy(GroupDescriptor.fields)
    fields.extend([
        F(name="identifier",
            label="Identifier",
            description="Unique identifier or number for this political group",
            localizable=[
                show("view edit add"),
            ],
        ),
        F(name="logo_data",
            label="Logo",
            # !+LISTING_IMG(mr, apr-2011) TypeError, not JSON serializable
            localizable=[
                show("view edit add"),
            ],
            value_type="image",
            render_type="image",
        ),
    ])
    schema_invariants = [constraints.EndAfterStart]
    custom_validators = [validations.validate_date_range_within_parent]


class OfficeDescriptor(GroupDescriptor):
    order = 2 # top
    localizable = True
    
    fields = [
        F(name="identifier",
            label="Office Identifier",
            description="Unique identifier or number for this Office",
            localizable=[
                show("view edit add"),
            ],
        ),
        F(name="office_role",
            label="Role",
            description="Role given to members of this office",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="text",
            render_type="single_select",
            vocabulary="office_role",
        ),

    ]
    fields.extend(deepcopy(GroupDescriptor.fields))
    custom_validators = [validations.validate_date_range_within_parent]


class OfficeMemberDescriptor(GroupMembershipDescriptor):
    localizable = True
    
    fields = [
        F(name="user_id",
            label="Name",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view listing"),
            ],
            value_type="user",
            render_type="single_select",
            vocabulary="user_not_mp",
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        F(name="notes",
            label="Notes",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="text",
            render_type="rich_text",
        ),
    ])


class MinistryDescriptor(GroupDescriptor):
    localizable = True
    
    fields = deepcopy(GroupDescriptor.fields)
    fields.extend([
        F(name="identifier",
            label="Ministry Identifier",
            description="Unique identifier or number for this Ministry",
            localizable=[
                show("view edit add"),
            ],
        ),
    ])
    schema_invariants = [constraints.EndAfterStart]
    custom_validators = [validations.validate_date_range_within_parent]


class MinisterDescriptor(GroupMembershipDescriptor):
    localizable = True
    
    fields = [
        F(name="user_id",
            label="Name",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view listing"),
            ],
            value_type="user",
            render_type="single_select",
            vocabulary="user",
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        F(name="notes",
            label="Notes",
            localizable=[
                show("view edit add"),
            ],
            value_type="text",
            render_type="rich_text",
        ),
    ])


class GovernmentDescriptor(GroupDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("governments")
    localizable = True
    sort_on = ["start_date"]
    fields = deepcopy(GroupDescriptor.fields)
    fields.extend([
        F(name="identifier",
            label="Government Identifier",
            description="Unique identifier or number for this Government",
            localizable=[
                show("view edit add"),
            ],
        ),
    ])
    schema_invariants = [constraints.EndAfterStart]
    custom_validators = [validations.validate_government_dates]


class AttachmentDescriptor(ModelDescriptor):
    localizable = True
    default_field_order = [
        #"attachment_id",
        #"head_id",
        "type",
        "title",
        "data",
        "name",
        "mimetype",
        "status",
        "status_date",
        "language",
        "description",
    ]
    fields = [
        F(name="type",
            label="Attachment Type",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="attachment_type",
        ),
        F(name="title",
            label="Title",
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
        ),
        F(name="description",
            label="Description",
            localizable=[
                show("view edit add"),
            ],
            value_type="text",
            render_type="rich_text",
        ),
        F(name="data",
            label="File",
            description="Upload a file",
            localizable=[
                show("view edit add"),
            ],
            value_type="file",
            render_type="file",
        ),
        F(name="name",
            label="Name",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="text",
            render_type="no_input",
        ),
        F(name="mimetype",
            label="MIME Type",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="text",
            render_type="no_input",
        ),
        F(name="status",
            label="Status",
            required=True,
            localizable=[
                show("view listing"),
            ],
            value_type="status",
            render_type="single_select",
            vocabulary="workflow_states",
        ),
        F(name="status_date",
            label="Status Date",
            localizable=[
                show("view listing"),
            ],
            value_type="date",
            render_type="date",
        ),
        LanguageField("language"), # [user-req]
    ]


''' !+VERSION_CLASS_PER_TYPE
class AttachedFileVersionDescriptor(ModelDescriptor):
    localizable = True
    
    fields = deepcopy(AttachmentDescriptor.fields)
    fields[fields.index(get_field(fields, "status"))] = Field(
        name="status", label=_("Status"), # [user-req]
        modes="view listing",
        localizable=[
            show("view listing"),
        ],
    )
'''

class DocDescriptor(ModelDescriptor):
    localizable = True # !+ARCHETYPE_LOCALIZATION
    
    default_field_order = [
        "title",
        "type_number",
        "acronym",
        "description",
        "language", # DB_REQUIRED
        #"type", # DB_REQUIRED
        "doc_type",
        #"doc_procedure",
        #"doc_id", # DB_REQUIRED
        "parliament_id",
        "owner_id", # DB_REQUIRED
        "registry_number",
        "uri",
        #"group_id", # !+group_id only exposed in specific custom doc types
        "status",
        "status_date", # DB_REQUIRED
        #"amc_signatories",
        #"amc_attachments",
        #"amc_events",
        "submission_date",
        "subject",
        "coverage",
        "geolocation",
        "body",
        #"admissable_date",
        #"signatories", 
        #"attachments",
        #"events",
        # head_id
        "timestamp", # DB_REQUIRED
    ]
    sort_on = ["status_date", "type_number"]
    sort_dir = "desc"
    fields = [
        # amc_signatories
        # amc_attachments
        # amc_events
        F(name="submission_date",
            label="Submission Date",
            localizable=[
                show("view"), 
                hide("listing"),
            ],
            value_type="date",
            render_type="date",
        ),

        #   admissible_date
        # owner
        # signatories
        # attachments
        # events
        # doc_id
        F(name="parliament_id",
            label="Parliament",
            required=True,
            localizable=[
                hide("view listing"),
            ],
            value_type="text",
            render_type="single_select",
            vocabulary="parliament",
        ),
        F(name="owner_id",
            label="Moved by",
            description="Select the user who moved the document",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("edit"), # !+ displayed in view-mode... how to control this from config?
                hide("view listing", "bungeni.Anonymous"),
            ],
            value_type="member", # !+user: constrained by "parent group" OR vocabulary
            render_type="single_select",
            vocabulary="parliament_member_delegation",
        ),
        # type
        F(name="doc_type",
            label="Document Type",
            required=True,
            localizable=[
                show("view edit add listing"), 
            ],
            value_type="vocabulary", # !+user: constrained by "parent group" OR vocabulary
            render_type="single_select",
            vocabulary="doc_type",
        ),
        # doc_procedure
        F(name="type_number",
            label="Number",
            localizable=[
                show("view listing"), 
            ],
            value_type="number",
            render_type="number",
        ),
        F(name="registry_number",
            label="Registry Number",
            localizable=[
                show("view listing"), 
                hide("edit"), 
            ],
        ),
        F(name="uri",
            label="URI",
            localizable=[
                show("view"), 
                hide("edit listing"), 
                # !+ should hide-in-edit mean -> if show-in-view then show in view-mode?
            ],
        ),
        F(name="acronym",
            label="Acronym",
            localizable=[
                show("view edit add"),
                hide("listing"),
            ],
        ),
        F(name="title",
            label="Title",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="text",
            render_type="text_box",
        ),
        F(name="description",
            label="Description",
            localizable=[
                show("view edit add"),
                hide("listing"),
            ],
            value_type="text",
            render_type="text_box",
        ),
        LanguageField("language"), # [user-req]
        F(name="subject",
            label="Subject Terms",
            description="Select Subjects",
            localizable=[
                hide("view edit add listing"),
            ],
        ),
        F(name="coverage",
            label="Coverage",
            description="Select Coverage",
            localizable=[
                hide("view edit add listing"),
            ],
        ),
        F(name="geolocation",
            label="Geolocation",
            description="Select Geolocation",
            localizable=[
                hide("view edit add listing"),
            ],
        ),
        F(name="body",
            label="Body",
            required=True,
            localizable=[
                show("view edit add"),
            ],
            value_type="text",
            render_type="rich_text",
        ),
        F(name="status",
            label="Status",
            required=True,
            localizable=[
                show("view listing"),
            ],
            value_type="status",
            render_type="single_select",
            vocabulary="workflow_states",
        ),
        F(name="status_date",
            label="Status Date",
            required=True,
            localizable=[
                show("view listing"),
            ],
            value_type="date",
            render_type="date",
        ),
        # !+group_id only exposed in specific custom doc types
        #F(name="group_id",
        #    label="Group",
        #    localizable=[
        #        show("view edit add listing"), 
        #    ],
        #    value_type="text",
        #    render_type="single_select",
        #    vocabulary="group",
        #),
        # head_id
        F(name="timestamp",
           label = u"", # !+ must have "empty" label... as no value is shown!
           localizable=[
                show("edit"),
            ],
            value_type="timestamp",
            render_type="datetime",
        ),
    ]


class EventDescriptor(DocDescriptor):
    
    localizable = True
    
    # !+ phase out default_field_order...
    fields = deepcopy(DocDescriptor.fields)
    insert_field_after(fields, "owner_id",
        F(name="group_id",
            label="Group",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="text",
            render_type="single_select",
            vocabulary="group",
        ))
    default_field_order = DocDescriptor.default_field_order[:]
    default_field_order.insert(
        default_field_order.index("owner_id") + 1, "group_id")
    replace_field(fields, 
        # "non-legal" parliamentary documents may be added by any user
        # !+GROUP_AS_OWNER(mr, apr-2012) for Event, a common case would be
        # to be able to set a group (of the office/group member creating the 
        # event) as the owner (but Group is not yet polymorphic with User). 
        # For now we limit the owner of an Event to be simply the current 
        # logged in user:
        F(name="owner_id",
            label="Owner",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("edit"), # !+ displayed in view-mode... how to control this from config?
                hide("view listing", "bungeni.Anonymous"),
            ],
            value_type="user", # !+user: constrained by "parent group" OR vocabulary
            render_type="single_select",
            vocabulary="owner_or_login",
        ))
    replace_field(fields, 
        F(name="doc_type",
            label="Event Type",
            required=True,
            localizable=[
                show("view edit add listing"), 
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="event_type",
        ))


# !+AuditLogView(mr, nov-2011) change listings do not respect this
class ChangeDescriptor(ModelDescriptor):
    localizable = False
    fields = [
        F(name="audit_id",
            localizable=[ hide("view listing"), ],
        ),
        F(name="user_id",
            label="User",
            required=True,
            localizable=[
                show("view listing"),
            ],
            value_type="user",
            render_type="single_select",
            vocabulary="user",
        ),
        F(name="action",
            localizable=[ show("view listing"), ],
        ),
        F(name="seq",
            localizable=[ show("view listing"), ],
        ),
        F(name="procedure",
            localizable=[ show("view listing"), ],
        ),
        F(name="date_audit",
           label="Date Audit",
           required=True,
           localizable=[
                hide("view listing"),
            ],
            value_type="datetime",
            render_type="datetime",
        ),
        F(name="date_active",
           label="Date Active",
           required=True,
           localizable=[
                show("view listing"),
            ],
            value_type="datetime",
            render_type="datetime",
        ),
    ]
    default_field_order = [
        #"audit_id",
        "user_id",
        "action",
        "seq",
        "procedure",
        "date_audit",
        "date_active",
    ]
# !+VERSION_LISTING(mr, nov-2011) version listings do not respect this
class VersionDescriptor(ChangeDescriptor):
    fields = deepcopy(ChangeDescriptor.fields)

''' !+VERSION_CLASS_PER_TYPE(mr, apr-2012)
- dynamically create a dedicated domain.TypeVersion and a corresponding 
  TypeVersionDescriptor (building on VersionDescriptor AND TypeDescriptor), for 
  each versionable domain Type.
- should have: localizable = True
- "edit add" mode should NOT be available on any of the audited fields?
- remove workflow vocabs (on status) (!+ but still display/translate as consistently)
'''
class DocVersionDescriptor(VersionDescriptor):
    """Base UI Descriptor for Doc archetype."""
    localizable = True #!+VERSION_CLASS_PER_TYPE that "inherits" UI desc?
    default_field_order = \
        VersionDescriptor.default_field_order[:] + \
        DocDescriptor.default_field_order[:]
    fields = \
        deepcopy(VersionDescriptor.fields) + \
        deepcopy(DocDescriptor.fields)


class AttachmentVersionDescriptor(VersionDescriptor):
    """UI Descriptor for Attachment archetype."""
    localizable = True
    default_field_order = \
        VersionDescriptor.default_field_order[:] + \
        AttachmentDescriptor.default_field_order[:]
    fields = \
        deepcopy(VersionDescriptor.fields) + \
        deepcopy(AttachmentDescriptor.fields)


class HeadingDescriptor(ModelDescriptor):
    order = 3 # top
    localizable = True
    
    fields = [
        F(name="text",
            label="Title",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit"),
                hide("listing"),
            ],
        ),
        LanguageField("language"), # [user-req]
    ]


class AgendaItemDescriptor(DocDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("agendaitems")
    localizable = True
    
    fields = deepcopy(DocDescriptor.fields)
    insert_field_after(fields, "submission_date", AdmissibleDateField())
    default_field_order = DocDescriptor.default_field_order[:]
    default_field_order.insert(
        default_field_order.index("submission_date") + 1, "admissible_date")


''' !+VERSION_CLASS_PER_TYPE
class AgendaItemVersionDescriptor(VersionDescriptor):
    localizable = True
    fields = deepcopy(VersionDescriptor.fields)
'''

class MotionDescriptor(DocDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("motions")
    localizable = True
    fields = deepcopy(DocDescriptor.fields)
    insert_field_after(fields, "submission_date", AdmissibleDateField())
    insert_field_after(fields, "admissible_date", 
        F(name="notice_date",
            label="Notice Date",
            localizable=[
                show("view"), 
                hide("listing"),
            ],
            value_type="date",
            render_type="date",
        ))
    default_field_order= DocDescriptor.default_field_order[:]
    default_field_order.insert(
        default_field_order.index("submission_date") + 1, "admissible_date")
    default_field_order.insert(
        default_field_order.index("submission_date") + 2, "notice_date")

''' !+VERSION_CLASS_PER_TYPE
class MotionVersionDescriptor(VersionDescriptor):
    localizable = True
    fields = deepcopy(VersionDescriptor.fields)
'''

''' !+AuditLogView(mr, nov-2011)
class MotionChangeDescriptor(ChangeDescriptor):
    localizable = True
    fields = deepcopy(ChangeDescriptor.fields)
'''


class BillDescriptor(DocDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("bills")
    localizable = True
    
    fields = deepcopy(DocDescriptor.fields)
    replace_field(fields, 
        F(name="doc_type",
            label="Bill Type",
            required=True,
            localizable=[
                show("view edit add listing"), 
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="bill_type",
        ))
    replace_field(fields, 
        F(name="body",
            label="Statement of Purpose",
            required=False,
            localizable=[
                show("view edit add"),
            ],
            value_type="text",
            render_type="rich_text",
        ))
    default_field_order = DocDescriptor.default_field_order[:]
    insert_field_after(fields, "submission_date", 
        F(name="publication_date",
            label="Publication Date",
            localizable=[
                show("view listing"),
            ],
            value_type="date",
            render_type="date",
        ))
    default_field_order.insert(
        default_field_order.index("submission_date") + 1, "publication_date")
    insert_field_after(fields, "publication_date", 
        F(name="short_title",
            label="Statement of Purpose",
            required=True,
            localizable=[
                show("view edit add listing"),
            ],
        ))
    default_field_order.insert(
        default_field_order.index("publication_date") + 1, "short_title")
    insert_field_after(fields, "short_title", 
        F(name="group_id",
            label="Ministry",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="group",
            render_type="single_select",
            vocabulary="ministry",
        ))
    default_field_order.insert(
        default_field_order.index("short_title") + 1, "group_id")


''' !+VERSION_CLASS_PER_TYPE
class BillVersionDescriptor(VersionDescriptor):
    localizable = True
    fields = deepcopy(VersionDescriptor.fields)
'''


class QuestionDescriptor(DocDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("questions")
    localizable = True
    
    fields = deepcopy(DocDescriptor.fields)
    replace_field(fields, 
        F(name="doc_type",
            label="Question Type",
            description="Choose the type of question",
            required=True,
            localizable=[
                show("view edit add listing"), 
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="question_type",
        ))
    replace_field(fields, 
        F(name="subject",
            label="Subject Terms",
            description="Select Subjects",
            localizable=[
                show("view edit add"),
                hide("listing"),
            ],
            value_type="text",
            render_type="tree_text",
            vocabulary="subject_terms",
        ))
    default_field_order = DocDescriptor.default_field_order[:]
    insert_field_after(fields, "description",
        F(name="response_type",
            label="Response Type",
            description="Choose the type of response expected for this question",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="response_type",
        ))
    default_field_order.insert(
        default_field_order.index("description") + 1, "response_type")
    insert_field_after(fields, "response_type",
        F(name="response_text",
            label="Response",
            localizable=[
                show("view edit"),
            ],
            value_type="text",
            render_type="rich_text",
        ))
    default_field_order.insert(0, "response_text")
    insert_field_after(fields, "submission_date", AdmissibleDateField())
    default_field_order.insert(
        default_field_order.index("submission_date") + 1, "admissible_date")
    insert_field_after(fields, "admissible_date",
        F(name="group_id",
            label="Ministry",
            required=True,
            localizable=[
                show("view edit add listing"),
            ],
            value_type="group",
            render_type="single_select",
            vocabulary="ministry", 
        ))
    default_field_order.insert(
        default_field_order.index("admissible_date") + 1, "group_id")
    insert_field_after(fields, "group_id",
        F(name="ministry_submit_date",
            label="Date submitted to ministry",
            localizable=[
                show("view"),
                hide("listing"),
            ],
            value_type="date",
            render_type="date",
        ))
    default_field_order.insert(
        default_field_order.index("group_id") + 1, "ministry_submit_date")
    ''' !+SUPPLEMENT
    fields.extend([
        #Field(name="supplement_parent_id",
        #    label=_("Initial/supplementary question"),
        #    modes="",
        #    view_widget=widgets.SupplementaryQuestionDisplay,
        #),
    ])
    '''
    custom_validators = []

''' !+VERSION_CLASS_PER_TYPE
class QuestionVersionDescriptor(VersionDescriptor):
    localizable = True
    fields = deepcopy(VersionDescriptor.fields)
'''

class TabledDocumentDescriptor(DocDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("tableddocuments")
    localizable = True
    fields = deepcopy(DocDescriptor.fields)
    insert_field_after(fields, "submission_date", AdmissibleDateField())
    default_field_order = DocDescriptor.default_field_order[:]
    default_field_order.insert(
        default_field_order.index("submission_date") + 1, "admissible_date")


''' !+VERSION_CLASS_PER_TYPE
class TabledDocumentVersionDescriptor(VersionDescriptor):
    localizable = True
    fields = deepcopy(VersionDescriptor.fields)
'''

class VenueDescriptor(ModelDescriptor):
    localizable = False
    fields = [
        F(name="short_name",
            label="Title",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
        ),
        F(name="description",
            label="Description",
            localizable=[
                show("view edit add"),
                hide("listing"),
            ],
            value_type="text",
            render_type="text_box",
        ),
        LanguageField("language"),
    ]


class SittingDescriptor(ModelDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("sittings")
    localizable = True
    fields = [
        F(name="short_name",
            label="Name of activity",
            required=True,
            localizable=[
                show("view edit add listing"),
            ],
        ),
        LanguageField("language"),
        # !+DURATION, should probably be a single "compound" field, with a 
        # dedicated rendering/listing logic.
        F(name="start_date",
            label="Date",
            required=True,
            localizable=[
                show("view edit add listing"),
            ],
            value_type="duration", # !+DURATION, in listing "consumes" also "end_date"
            render_type="datetime",
        ),
        F(name="end_date",
            label="End",
            required=True,
            localizable=[
                show("view edit add listing"),
            ],
            value_type="datetime", # !+DURATION, in listing "consumed" by "start_date"
            render_type="datetime",
        ),
        F(name="venue_id",
            label="Venue",
            localizable=[
                show("view edit add listing"),
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="venue", 
        ),
        F(name="activity_type",
            label="Activity Type",
            description="Sitting Activity Type",
            localizable=[
                show("view edit add"),
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="sitting_activity_types", 
        ),
        F(name="meeting_type",
            label="Meeting Type",
            description="Sitting Meeting Type",
            localizable=[
                show("view edit add"),
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="sitting_meeting_types", 
        ),
        F(name="convocation_type",
            label="Convocation Type",
            description="Sitting Convocation Type",
            localizable=[
                show("view edit add"),
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="sitting_convocation_types", 
        ),
    ]
    schema_invariants = [constraints.EndAfterStart]
    custom_validators = [
        validations.validate_date_range_within_parent,
        validations.validate_start_date_equals_end_date,
        validations.validate_venues,
        #validations.validate_non_overlapping_sitting
    ]


class SessionDescriptor(ModelDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("sessions")
    localizable = True
    display_name = "Parliamentary session"
    container_name = "Parliamentary sessions"
    sort_on = ["start_date", ]
    sort_dir = "desc"
    fields = [
        F(name="short_name",
            label="Short Name",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
        ),
        F(name="full_name",
            label="Full Name",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit"),
                hide("listing"),
            ],
        ),
        F(name="start_date",
            label="Start Date",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="date",
            render_type="date",
        ),
        F(name="end_date",
            label="End Date",
            required=True,
            localizable=[
                show("add"), # "logical" required (even if db allows null)
                show("view edit listing"),
            ],
            value_type="date",
            render_type="date",
        ),
        LanguageField("language"),
        F(name="notes",
            label="Notes",
            localizable=[
                show("view edit add"),
            ],
        ),
    ]
    schema_invariants = [constraints.EndAfterStart]
    custom_validators = [validations.validate_date_range_within_parent]


class SittingAttendanceDescriptor(ModelDescriptor):
    localizable = True
    sort_on = ["member_id"]
    fields = [
        F(name="member_id",
            label="Member of Parliament",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view listing"),
            ],
            value_type="user",
            render_type="single_select",
            vocabulary="sitting_attendance",
        ),
        F(name="attendance_type",
            label="Attendance",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="vocabulary",
            render_type="single_select",
            vocabulary="attendance_type",
        ),
    ]


class SignatoryDescriptor(ModelDescriptor):
    localizable = True
    fields = [
        F(name="status",
            label="Signature Status",
            required=True,
            localizable = [
                show("view listing", 
                    roles="bungeni.Owner bungeni.Signatory")
            ],
            value_type="status",
            render_type="single_select",
            vocabulary="workflow_states",
        ),
        F(name="user_id",
            label="Signatory",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view listing"),
            ],
            value_type="member",
            render_type="single_select",
            vocabulary="signatory",
        ),
        F(name="party", # property on domain model
            label="Political Party",
            localizable=[ show("listing"), ],
            value_type="text",
            render_type="single_select",
            vocabulary="party",
        ),
    ]


class CountryDescriptor(ModelDescriptor):
    localizable = True
    fields = [
        LanguageField("language"),
        F(name="country_id",
            label="Country Code",
            description="Two letter ISO Code for this country e.g. DZ for Algeria",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
        ),
        F(name="country_name",
            label="Country",
            description="Name of the Country",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
        ),
    ]


class ItemScheduleDescriptor(ModelDescriptor):
    localizable = True
    #display_name = "Scheduling"
    #container_name = "Schedulings"
    sort_on = ["planned_order", ]
    sort_dir = "asc"
    #!+VOCABULARY(mb, nov-2010) item_id references a variety of content
    # types identified by the type field. Scheduling 'add items' view suffices
    # for now providing viewlets with a list of addable objects. TODO:
    # TODO: validate scheduled items
    fields = [
        F(name="item_id",
            label="Item",
            required=True,
            localizable=[
                show("edit add"), # db-not-null-ui-add, pk
                show("view listing"),
            ],
            value_type="number",
            render_type="number",
        ),
        F(name="item_title", # derived @item_title
            label="Title",
            localizable=[
                show("view listing")
            ],
        ),
        F(name="item_mover", # derived @item_mover
            label="Mover",
            localizable=[
                show("view listing")
            ],
        ),
        F(name="item_type",
            label="Item Type",
            localizable=[
                show("edit add"), # db-not-null-ui-add, pk
                show("view listing"),
            ],
        ),
        F(name="item_uri", # derived @item_uri
            label="Item URI",
            localizable=[
                show("view listing")
            ],
        ),
    ]

class EditorialNoteDescriptor(ModelDescriptor):
    localizable = True
    fields = [
        F(name="editorial_note_id",
            label="Item",
            required=True,
            localizable=[
                show("edit add"), # db-not-null-ui-add, pk
                show("view listing"),
            ],
            value_type="number",
            render_type="number",
        ),
        F(name="text",
            label="Text",
            required=True,
            localizable=[
                show("view edit add listing")
            ],
            value_type="text",
            render_type="rich_text",
        ),
        LanguageField("language")
    ]

class ItemScheduleDiscussionDescriptor(ModelDescriptor):
    localizable = True
    #display_name = "Discussion"
    #container_name = "Discussions"
    
    fields = [
        LanguageField("language"),
        F(name="body",
            label="Minutes",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="text",
            render_type="rich_text",
        ),
        #Field(name="sitting_time",
        #    label=_("Sitting time"),
        #    description=_("The time at which the discussion took place."),
        #    modes="view edit add listing",
        #),
    ]


class ReportDescriptor(DocDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("preports")
    localizable = True
    sort_on = ["end_date"] + DocDescriptor.sort_on
    fields = [
        LanguageField("language"),
        F(name="title",
            label="Publications type",
            required=True,
            localizable=[
                show("add"), # db-not-null-ui-add
                show("view edit listing"),
            ],
            value_type="text",
            render_type="text_box",
        ),
        F(name="status_date",
            label="Published Date",
            required=True,
            localizable=[
                show("view listing"),
            ],
            value_type="date",
            render_type="date",
        ),
        F(name="body",
            label="Text",
            required=True,
            localizable=[
                show("view edit add"),
            ],
            value_type="text",
            render_type="rich_text",
        ),
    ]
    default_field_order = [ f.name for f in fields ]


class Report4SittingDescriptor(ReportDescriptor):
    localizable = True
    fields = deepcopy(ReportDescriptor.fields)


