# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Form Schemas for Domain Objects

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.descriptor")

from copy import deepcopy
from zope import schema
import zope.formlib

from bungeni.alchemist.model import ModelDescriptor, Field, show, hide

from bungeni.models import domain
import bungeni.models.interfaces

# We import bungeni.core.workflows.adapters to ensure that the "states"
# attribute on each "workflow" module is setup... this is to avoid an error
# when importing bungeni.ui.descriptor.descriptor from standalone scripts:
import bungeni.core.workflows.adapters # needed by standalone scripts !+review

#from bungeni.core import translation

from bungeni.ui import widgets
from bungeni.ui.fields import VocabularyTextField
from bungeni.ui.forms import validations
from bungeni.ui.i18n import _
from bungeni.ui import vocabulary
from bungeni.ui.descriptor import listing, constraints
from bungeni.ui.descriptor.field import F
from bungeni.utils import misc


def get_field(fields, name):
    return misc.get_keyed_item(fields, name, key="name")
    

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
    display_name = _("User")
    container_name = _("Users")
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
    display_name = _("Delegate to user")
    container_name = _("Delegations")
    
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
    display_name = _("sub roles")
    container_name = _("sub roles")
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

class MemberOfParliamentDescriptor(GroupMembershipDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("parliamentmembers")
    localizable = True
    display_name = _("Member of parliament")
    container_name = _("Members of parliament")
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
    display_name = _("member")
    container_name = _("members")
    
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
    display_name = _("Group")
    container_name = _("Groups")
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
    display_name = _("Parliament")
    container_name = _("Parliaments")
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
    display_name = _("Profile")
    container_name = _("Committees")
    
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
    display_name = _("Member")
    container_name = _("Members")

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
    display_name = _("Address")
    container_name = _("Addresses")
    
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
    display_name = _("Title types")
    container_name = _("Title types")
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
    display_name = _("Title")
    container_name = _("Titles")
    
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
    display_name = _("Staff")
    container_name = _("Staff")

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
    display_name = _("political group")
    container_name = _("political groups")
    
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
    display_name = _("Office")
    container_name = _("Offices")
    
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
    display_name = _("Office Member")
    container_name = _("Office Members")
    
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
    display_name = _("Ministry")
    container_name = _("Ministries")

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
    display_name = _("Minister")
    container_name = _("Ministers")

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
    display_name = _("Government")
    container_name = _("Governments")
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
    display_name = _("Attachment")
    container_name = _("Attachments")
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
    display_name = _("Attached file version")
    container_name = _("Versions")
    
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
        "body",
        #"admissable_date",
        #"signatories", 
        #"attachments",
        #"events",
        # subject
        # coverage
        # geolocation
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
        #Field(name="group_id", # [user]
        #    modes="view edit add listing",
        #    localizable=[ 
        #        show("view edit listing"), 
        #    ],
        #    property=schema.Choice(title=_("Group"),
        #        source=vocabulary.MinistrySource("ministry_id"), # !+PLACEHOLDER_GROUP_SOURCE
        #        required=False
        #    ),
        #),
        # subject
        # coverage
        # geolocation
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
    display_name = _("Event")
    container_name = _("Events")
    
    fields = deepcopy(DocDescriptor.fields)
    fields.append(
        Field(name="group_id", # [user]
            modes="view edit add listing",
            localizable=[ 
                show("view edit add listing"), 
            ],
            property=schema.Choice(title=_("Group"),
                source=vocabulary.GroupSource( 
                    token_field="group_id",
                    title_field="short_name",
                    value_field="group_id",
                ),
                required=False,
            ),
        ),
    )
    with get_field(fields, "owner_id") as f:
        # "non-legal" parliamentary documents may be added by any user
        f.property = schema.Choice(title=_("Owner"), 
            # !+GROUP_AS_OWNER(mr, apr-2012) for Event, a common case would be
            # to be able to set a group (of the office/group member creating the 
            # event) as the owner (but Group is not yet polymorphic with User). 
            # For now we limit the owner of an Event to be simply the current 
            # logged in user:
            source=vocabulary.OwnerOrLoggedInUserSource(
                token_field="user_id",
                title_field="fullname",
                value_field="user_id",
            )
        )
        # !+f.localizable changing localizable modes AFTER Field is initialized
        # gives mismatch error when descriptors are (re-)loaded, e.g. 
        #f.localizable = [ hide("view edit add listing"), ]
        f.listing_column = listing.related_user_name_column("owner_id", _("Name"))
        f.listing_column_filter = listing.related_user_name_column_filter
        f.view_widget = None
        # !+ select or autocomplete... ?
        #f.edit_widget=widgets.AutoCompleteWidget(remote_data=True,
        #        yui_maxResultsDisplayed=5),
        #f.add_widget=widgets.AutoCompleteWidget()
    with get_field(fields, "doc_type") as f:
        # "non-legal" parliamentary documents may be added by any user
        f.property = schema.Choice(title=_("Event Type"),
                source=vocabulary.event_type,
        )
        listing_column = listing.vocabulary_column("event_type",
            _("Event Type"),
            vocabulary.event_type
        )
    del f # remove f from class namespace


# !+AuditLogView(mr, nov-2011) change listings do not respect this
class ChangeDescriptor(ModelDescriptor):
    localizable = False
    fields = [
        Field(name="audit_id", # [sys]
            modes="view listing",
            localizable=[ hide("view listing"), ],
        ),
        Field(name="user_id",
            modes="view listing",
            localizable=[ show("view listing"), ],
            property=schema.Choice(title=_("User"), vocabulary="user"),
            view_widget=None,
            listing_column=listing.related_user_name_column("user_id", _("Name")),
            # !+ audit listing column filtering currently disabled
            #listing_column_filter=listing.related_user_name_column_filter,
        ),
        Field(name="action",
            modes="view listing",
            localizable=[ show("view listing"), ],
        ),
        Field(name="seq",
            modes="view listing",
            localizable=[ show("view listing"), ],
        ), 
        Field(name="procedure",
            modes="view listing",
            localizable=[ show("view listing"), ],
        ),
        Field(name="date_audit", # [sys]
            modes="view listing",
            localizable=[ hide("view listing"), ],
            property=schema.Date(title=u"Audit Date", required=True),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget,
            listing_column=listing.datetime_column("date_audit", _("Date Audit")),
            search_widget=widgets.date_input_search_widget
        ),
        Field(name="date_active", # [user]
            modes="view listing",
            localizable=[ show("view listing"), ],
            property=schema.Date(title=u"Active Date", required=True),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget,
            listing_column=listing.datetime_column("date_active", 
                _("Date Active")),
            search_widget=widgets.date_input_search_widget
        ),
    ]
    default_field_order = [
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
        deepcopy(VersionDescriptor.default_field_order) + \
        deepcopy(DocDescriptor.default_field_order)
    fields = \
        deepcopy(VersionDescriptor.fields) + \
        deepcopy(DocDescriptor.fields)
    with get_field(fields, "status") as f:
        f.modes = "view listing"
        f.localizable = [ show("view listing"), ]
        f.property = schema.Text(title=_("Status"))
    del f # remove f from class namespace

class AttachmentVersionDescriptor(VersionDescriptor):
    """UI Descriptor for Attachment archetype."""
    localizable = True
    default_field_order = \
        deepcopy(VersionDescriptor.default_field_order) + \
        list(deepcopy(AttachmentDescriptor.default_field_order))
    fields = \
        deepcopy(VersionDescriptor.fields) + \
        deepcopy(AttachmentDescriptor.fields)
    with get_field(fields, "status") as f:
        f.modes = "view listing"
        f.localizable = [ show("view listing"), ]
        f.property = schema.Text(title=_("Status"))
    del f # remove f from class namespace


class HeadingDescriptor(ModelDescriptor):
    order = 3 # top
    localizable = True
    display_name = _("Heading")
    container_name = _("Headings")
    
    fields = [
        Field(name="text", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.TextLine(title=_("Title")),
            edit_widget=widgets.TextWidget,
            add_widget=widgets.TextWidget,
        ),
        LanguageField("language"), # [user-req]
    ]


class AgendaItemDescriptor(DocDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("agendaitems")
    localizable = True
    display_name = _("Agenda item")
    container_name = _("Agenda items")
    
    fields = deepcopy(DocDescriptor.fields)
    fields.append(AdmissibleDateField()) # [sys]
    get_field(fields, "admissible_date").localizable = [
        show("view"),
        hide("listing"),
    ]
    default_field_order= DocDescriptor.default_field_order[:]
    default_field_order.insert(
        default_field_order.index("submission_date") + 1, "admissible_date")


''' !+VERSION_CLASS_PER_TYPE
class AgendaItemVersionDescriptor(VersionDescriptor):
    localizable = True
    display_name = _("Agenda Item version")
    container_name = _("Versions")
    fields = deepcopy(VersionDescriptor.fields)
'''

class MotionDescriptor(DocDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("motions")
    localizable = True
    display_name = _("Motion")
    container_name = _("Motions")
    fields = deepcopy(DocDescriptor.fields)
    fields.extend([
        AdmissibleDateField(),
        Field(name="notice_date", # [sys]
            modes="view listing",
            localizable=[ 
                show("view"),
                hide("listing"),
            ],
            property=schema.Date(title=_("Notice Date"), required=False),
        ),
    ])
    get_field(fields, "admissible_date").localizable = [
        show("view"),
        hide("listing"),
    ]
    default_field_order= DocDescriptor.default_field_order[:]
    default_field_order.insert(
        default_field_order.index("submission_date") + 1, "admissible_date")
    default_field_order.insert(
        default_field_order.index("submission_date") + 2, "notice_date")


''' !+VERSION_CLASS_PER_TYPE
class MotionVersionDescriptor(VersionDescriptor):
    localizable = True
    display_name = _("Motion version")
    container_name = _("Versions")
    fields = deepcopy(VersionDescriptor.fields)
'''

''' !+AuditLogView(mr, nov-2011)
class MotionChangeDescriptor(ChangeDescriptor):
    localizable = True
    display_name = "Changes changes"
    container_name = "Changes"
    fields = deepcopy(ChangeDescriptor.fields)
'''


class BillDescriptor(DocDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("bills")
    localizable = True
    display_name = _("Bill")
    container_name = _("Bills")

    fields = deepcopy(DocDescriptor.fields)
    # remove "doc_type"
    fields[:] = [ f for f in fields if f.name not in ("doc_type",) ]
    # tweak...
    with get_field(fields, "body") as f:
        f.label = _("Statement of Purpose")
        f.property = schema.Text(title=_("Statement of Purpose"), required=False)
    del f # remove f from class namespace
    
    fields.extend([
        Field(name="short_title", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit add"),
                hide("listing"),
            ],
            property=schema.TextLine(title=_("Short Title")),
            #!+view_widget=widgets.ComputedTitleWidget,
            edit_widget=widgets.TextWidget,
            add_widget=widgets.TextWidget,
        ),
        Field(name="doc_type", # [user-req]
            modes="view edit add listing",
            localizable=[ 
                show("view edit listing"), 
            ],
            property=schema.Choice(title=_("Bill Type"),
                source=vocabulary.bill_type,
            ),
            listing_column=listing.vocabulary_column("doc_type",
                _("Bill Type"),
                vocabulary.bill_type
            ),
        ),
        Field(name="group_id", # [user]
            modes="view edit add listing",
            localizable=[ 
                show("view edit add"),
                hide("listing"),
            ],
            property=schema.Choice(title=_("Ministry"),
                source=vocabulary.MinistrySource("ministry_id"),
                required=False
            ),
            listing_column_filter=listing.ministry_column_filter
        ),
        F(name="publication_date",
            label="Publication Date",
            localizable=[
                show("view listing"),
            ],
            value_type="date",
            render_type="date",
        ),
    ])
    default_field_order= DocDescriptor.default_field_order[:]
    default_field_order.insert(
        default_field_order.index("submission_date") + 1, "publication_date")


''' !+VERSION_CLASS_PER_TYPE
class BillVersionDescriptor(VersionDescriptor):
    localizable = True
    display_name = _("Bill version")
    container_name = _("Versions")
    fields = deepcopy(VersionDescriptor.fields)
'''


class QuestionDescriptor(DocDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("questions")
    localizable = True
    display_name = _("Question")
    container_name = _("Questions")
    
    fields = deepcopy(DocDescriptor.fields)
    # remove "doc_type"
    fields[:] = [ f for f in fields if f.name not in ("doc_type",) ]
    fields.extend([
        #Field(name="supplement_parent_id",
        #    label=_("Initial/supplementary question"),
        #    modes="",
        #    view_widget=widgets.SupplementaryQuestionDisplay,
        #),
        Field(name="group_id", # [user-req]
            modes="view edit add listing",
            localizable=[ 
                show("view edit listing"), 
            ],
            property=schema.Choice(title=_("Ministry"),
                source=vocabulary.MinistrySource("ministry_id"),
            ),
            listing_column=listing.ministry_column("ministry_id" , _("Ministry")),
            listing_column_filter=listing.ministry_column_filter
        ),
        AdmissibleDateField(), # [sys]
        Field(name="ministry_submit_date", # [user]
            modes="view listing",
            localizable=[ 
                show("view"),
                hide("listing"),
            ],
            property=schema.Date(title=_("Submitted to ministry"),
                required=False
            ),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget,
            search_widget=widgets.date_input_search_widget
        ),
        Field(name="doc_type", # [user-req]
            modes="view edit add listing",
            localizable=[ 
                show("view edit listing"),
            ],
            property=schema.Choice(title=_("Question Type"),
                description=_("Choose the type of question"),
                source=vocabulary.question_type,
            ),
            listing_column=listing.vocabulary_column("doc_type",
                _("Question Type"),
                vocabulary.question_type
            ),
        ),
        Field(name="response_type", # [user-req]
            modes="view edit add listing",
            localizable=[ 
                show("view edit"),
                show("listing")
            ],
            property=schema.Choice(title=_("Response Type"),
                description=_(
                    "Choose the type of response expected for this question"),
                source=vocabulary.response_type
            ),
            listing_column=listing.vocabulary_column("response_type",
                _("Response Type"),
                vocabulary.response_type
            ),
        ),
        F(name="response_text",
            label="Response",
            localizable=[
                show("view edit"),
            ],
            value_type="text",
            render_type="rich_text",
        ),
        F(name="subject",
            label="Subject Terms",
            description="Select Subjects",
            localizable=[
                show("view edit add"),
                hide("listing"),
            ],
            value_type="text",
            render_type="tree_text",
            vocabulary="subject-terms", # !+naming
        ),
    ])
    get_field(fields, "admissible_date").localizable = [
        show("view"),
        hide("listing"),
    ]
    default_field_order = DocDescriptor.default_field_order[:]
    default_field_order.insert(0, "response_text")
    default_field_order.insert(
        default_field_order.index("language"), "response_type")
    default_field_order.insert(
        default_field_order.index("submission_date") + 1, "admissible_date")
    default_field_order.insert(
        default_field_order.index("submission_date") + 2, "ministry_submit_date")
    custom_validators = []

''' !+VERSION_CLASS_PER_TYPE
class QuestionVersionDescriptor(VersionDescriptor):
    localizable = True
    display_name = _("Question version")
    container_name = _("Versions")
    fields = deepcopy(VersionDescriptor.fields)
'''

class TabledDocumentDescriptor(DocDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("tableddocuments")
    localizable = True
    display_name = _("Tabled document")
    container_name = _("Tabled documents")
    fields = deepcopy(DocDescriptor.fields)
    fields.extend([
        AdmissibleDateField(), # [sys]
    ])
    get_field(fields, "admissible_date").localizable = [
        show("view"),
        hide("listing"),
    ]
    default_field_order = DocDescriptor.default_field_order[:]
    default_field_order.insert(
        default_field_order.index("submission_date") + 1, "admissible_date")


''' !+VERSION_CLASS_PER_TYPE
class TabledDocumentVersionDescriptor(VersionDescriptor):
    localizable = True
    display_name = _("Tabled Document version")
    container_name = _("Versions")
    fields = deepcopy(VersionDescriptor.fields)
'''

class VenueDescriptor(ModelDescriptor):
    localizable = False
    display_name = _("Venue")
    container_name = _("Venues")
    fields = [
        Field(name="short_name", # [user-req]
            modes="view edit add listing",
            localizable=[ 
                show("view edit listing"),
            ],
            property=schema.TextLine(title=_("Title")),
        ),
        Field(name="description", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit"),
                hide("listing"),
            ],
            property=schema.Text(title=_("description"))
        ),
        LanguageField("language"),
    ]

class SittingDescriptor(ModelDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("sittings")
    localizable = True
    display_name = _("Sitting")
    container_name = _("Sittings")
    fields = [
        Field(name="short_name",
            modes="view edit add listing",
            localizable=[
                show("view edit listing")
            ],
            property=schema.TextLine(title=_(u"Name of activity")),
        ),
        LanguageField("language"),
        Field(name="start_date", # [user-req]
            modes="view add listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Datetime(title=_("Date")),
            listing_column=listing.date_from_to_column("start_date", _("Start")),
            # !+CustomListingURL(mr, oct-2010) the listing of this type has
            # been replaced by the custom SittingsViewlet -- but it
            # should still be possible use the generic container listing in
            # combination with a further customized listing_column -- for an
            # example of this see how the listing of the column "owner_id"
            # is configured in: descriptor.DocDescriptor
            
            # !+CustomListingURL(miano, nov-2010)
            # Since the custom listing column function was missing
            # the sitting listing was broken in archive.
            # Reverted to fix the issue.
            # This listing does not need to be customised because it is
            # only used in the archive.
            edit_widget=widgets.DateTimeWidget,
            add_widget=widgets.DateTimeWidget,
            search_widget=widgets.date_input_search_widget
        ),
        Field(name="end_date", # [user-req]
            modes="view add listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Datetime(title=_("End")),
            #listing_column=time_column("end_date", _("End Date")),
            edit_widget=widgets.DateTimeWidget,
            add_widget=widgets.DateTimeWidget,
        ),
        Field(name="venue_id", # [user]
            modes="view edit add listing",
            localizable=[
                show("view edit add listing"),
            ],
            property=schema.Choice(title=_("Venue"),
                source=vocabulary.DatabaseSource(domain.Venue,
                    token_field="venue_id",
                    title_field="short_name",
                    value_field="venue_id"
                ),
                required=False
            ),
            listing_column=listing.dc_property_column("venue", _(u"Venue")),
        ),
        Field(name="activity_type",
            modes="view edit add",
            localizable=[
                show("view edit add")
            ],
            property=schema.Choice(title=_(u"Activity Type"),
                description=_(u"Sitting Activity Type"),
                vocabulary=vocabulary.sitting_activity_types,
                required=False
            ),
        ),
        Field(name="meeting_type",
            modes="view edit add",
            localizable=[
                show("view edit add")
            ],
            property=schema.Choice(title=_(u"Meeting Type"),
                description=_(u"Sitting Meeting Type"),
                vocabulary=vocabulary.sitting_meeting_types,
                required=False
            ),
        ),
        Field(name="convocation_type",
            modes="view edit add",
            localizable=[
                show("view edit add")
            ],
            property=schema.Choice(title=_(u"Convocation Type"),
                description=_(u"Sitting Convocation Type"),
                vocabulary=vocabulary.sitting_convocation_types,
                required=False
            ),
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
    display_name = _("Parliamentary session")
    container_name = _("Parliamentary sessions")
    sort_on = ["start_date", ]
    sort_dir = "desc"
    fields = [
        Field(name="short_name", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.TextLine(title=_("Short Name")),
        ),
        Field(name="full_name", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit"),
                hide("listing"),
            ],
            property=schema.TextLine(title=_("Full Name"))
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
    display_name = _("Sitting attendance")
    container_name = _("Sitting attendances")
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
    display_name = _("Signatory")
    container_name = _("Signatories")
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
    display_name = _("Country")
    container_name = _("Countries")
    fields = [
        LanguageField("language"),
        Field(name="country_id", # [user-req]
            modes="view edit add",
            localizable=[
                show("view edit"),
            ],
            property=schema.TextLine(title=_("Country Code"),
                description=_(
                    "Two letter ISO Code for this country e.g. DZ for Algeria")
            )
        ),
        Field(name="country_name", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.TextLine(title=_("Country"),
                description=_("Name of the Country")
            ),
        ),
    ]


class ItemScheduleDescriptor(ModelDescriptor):
    localizable = True
    display_name = _("Scheduling")
    container_name = _("Schedulings")
    sort_on = ["planned_order", ]
    sort_dir = "asc"
    #!+VOCABULARY(mb, nov-2010) item_id references a variety of content
    # types identified by the type field. Scheduling 'add items' view suffices
    # for now providing viewlets with a list of addable objects. TODO:
    # TODO: validate scheduled items
    fields = [
        Field(name="item_id", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Int(title=_("Item")),
        ),
        Field(name="item_title", # [derived]
            modes="view listing",
            localizable=[
                show("view listing")
            ],
            property=schema.TextLine(title=_("Title"), required=False),
            listing_column=listing.scheduled_item_title_column("title", _(u"Title"))
        ),
        Field(name="item_mover", # [derived]
            modes="view listing",
            localizable=[
                show("view listing")
            ],
            property=schema.TextLine(title=_("Mover"), required=False),
            listing_column=listing.scheduled_item_mover_column("mover", _(u"Mover"))
        ),
        Field(name="item_type",
            modes="view edit add listing",
            localizable=[
                show("view listing")
            ],
            property=schema.TextLine(title=_("Item Type")),
        ),
        Field(name="item_uri", # [derived]
            modes="view listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.TextLine(title=_("uri"), required=False),
            listing_column=listing.scheduled_item_uri_column("uri", _(u"Item URI"))
        ),
    ]

class EditorialNoteDescriptor(ModelDescriptor):
    localizable = True
    display_name = _("Editorial Note")
    container_name = "Editorial Notes"
    fields = [
        Field(name="editorial_note_id",
            modes="view edit add listing",
            localizable=[
                show("view listing")
            ],
            property=schema.Int(title=_("Item"))
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
    display_name = _("Discussion")
    container_name = _("Discussions")
    
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
    display_name = _("Report")
    container_name = _("Reports")
    sort_on = ["end_date"] + DocDescriptor.sort_on
    fields = [
        LanguageField("language"),
        Field(name="title", label=_("Publications type"), # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
        ),
        Field(name="status_date", label=_("Published Date"), # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            listing_column=listing.datetime_column("status_date", _("Published Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget,
            search_widget=widgets.date_input_search_widget
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


