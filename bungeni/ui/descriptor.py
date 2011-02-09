# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Form Schemas for Domain Objects

$Id$
"""

import datetime
from copy import deepcopy
from zope import schema, interface

from zope.security.management import getInteraction
from zope.publisher.interfaces import IRequest
import zope.app.form.browser
from zope.i18n import translate
from zc.table import column

from bungeni.alchemist import Session
from bungeni.alchemist.model import ModelDescriptor, Field, show, hide

from bungeni.models import domain

from bungeni.core.translation import get_default_language
from bungeni.core.workflows.groups import states as group_wf_state
from bungeni.core.workflows.attachedfile import states as af_wf_state
from bungeni.core.workflows.address import states as address_wf_state
from bungeni.core.workflows.event import states as event_wf_state
from bungeni.core.workflows.heading import states as heading_wf_state
from bungeni.core.workflows.committee import states as committee_wf_state
from bungeni.core.workflows.parliament import states as parliament_wf_state
from bungeni.core.workflows.version import states as version_wf_state
from bungeni.core import translation

from bungeni.ui import widgets

from bungeni.ui import constraints
from bungeni.ui.forms import validations
from bungeni.ui.i18n import _
from bungeni.ui.utils import common, date, misc
from bungeni.ui import vocabulary
from bungeni.ui.tagged import get_states
from bungeni.ui.interfaces import IBusinessSectionLayer

###
# Listing Columns 
#

def _column(name, title, renderer, default=""):
    def getter(item, formatter):
        # item.__parent__.request
        value = getattr(item, name)
        if value:
            return renderer(value)
        return default
    return column.GetterColumn(title, getter)

def localized_datetime_column(name, title, default="",
        category="date", # "date" | "time" | "dateTime"
        length="medium"     # "short" | "medium" | "long" | "full" | None
    ):
    def getter(item, formatter):
        value = getattr(item, name)
        if value:
            request = item.__parent__.request
            date_formatter = date.getLocaleFormatter(request, category, length)
            return date_formatter.format(value)
        return default
    return column.GetterColumn(title, getter)
def day_column(name, title, default=""):
    return localized_datetime_column(name, title, default, "date", "medium")
def datetime_column(name, title, default=""):
    return localized_datetime_column(name, title, default, "dateTime", "medium")
#def time_column(name, title, default=""):
#    return localized_datetime_column(name, title, default, "time", "long")



def date_from_to_column(name, title, default=""):
    format_length = "medium"
    def getter(item, formatter):
        request = item.__parent__.request
        start = getattr(item, "start_date")
        if start:
            start = date.getLocaleFormatter(request,
                "dateTime", format_length).format(start)
        end = getattr(item, "end_date")
        if end:
            end = date.getLocaleFormatter(request,
                "time", format_length).format(end)
        return u"%s - %s" % (start, end)
    return column.GetterColumn(title, getter)


def name_column(name, title, default=""):
    def renderer(value, size=50):
        if len(value) > size:
            return "%s..." % value[:size]
        return value
    return _column(name, title, renderer, default)

def combined_name_column(name, title, default=""):
    """An extended name, combining full_name (localized) and short_name columns.
    
    For types that have both a full_name and a short_name attribute:
    Group, ParliamentaryItem, ParliamentarySession
    """
    def getter(item, formatter):
        return "%s [%s]" % (_(item.full_name), item.short_name)
    return column.GetterColumn(title, getter)


def _get_related_user(item_user, attr):
    """Get trhe user instance that is related to this item via <attr>, 
    or if <attr> is None, return the item_user itself. 
    """
    if attr:
        item_user = getattr(item_user, attr, None)
        assert item_user is not None, \
            "Item [%s] may not have None as [%s]" % (item_user, attr)
    else:
        assert item_user is not None, \
            "Item User [%s] may not be None" % (item_user)
    return item_user

def user_name_column(name, title, attr):
    def getter(item_user, formatter):
        item_user = _get_related_user(item_user, attr)
        return item_user.fullname # User.fullname property 
    return column.GetterColumn(title, getter)

def linked_mp_name_column(name, title, attr):
    """This may be used to customize the default URL generated as part of the 
    container listing. 
    
    E.g. instead of the URL to the association view between a cosignatory (MP) 
    and a bill:
        /business/bills/obj-169/cosignatory/obj-169-61/
    the direct URL for the MP's "home" view is used instead:
        /members/current/obj-55/
    """
    def get_member_of_parliament(user_id):
        """Get the MemberOfParliament instance for user_id."""
        return Session().query(domain.MemberOfParliament).filter(
            domain.MemberOfParliament.user_id == user_id).one()
    def getter(item_user, formatter):
        item_user = _get_related_user(item_user, attr)
        mp = get_member_of_parliament(item_user.user_id)
        return zope.app.form.browser.widget.renderElement("a",
            contents=item_user.fullname, # User.fullname derived property 
            href="/members/current/obj-%s/" % (mp.membership_id)
        )
    return column.GetterColumn(title, getter)

''' !+ replaced with linked_assignment_column()
def item_name_column(name, title, default=u""):
    def getter(item, formatter):
        return u"%s %s" % (item.item.type, item.item.short_name)
    return column.GetterColumn(title, getter)
def group_name_column(name, title, default=u""):
    def getter(item, formatter):
        obj = translation.translate_obj(item)
        #TODO: translate group.type
        return u"%s %s" % (item.group.type, obj.group.short_name)
    return column.GetterColumn(title, getter)
'''
def linked_assignment_column(title, assigned_kind="item"):
    """To customize the default URL generated as part of the container listing. 
    
    E.g. instead of the URL to the association view between a committee and an 
    assigned bill or between a bill and a committe it is assigned to:
        /business/committees/obj-46/assigneditems/obj-1/
        /business/bills/obj-70/assignedgroups/obj-2/
    the direct URL for the bill's or committee's "home" view is used instead:
        /business/bills/obj-37/
        /business/committees/obj-15/
    """
    assert assigned_kind in ("item", "group")
    assigned_id_attr_name = {
        "item": "parliamentary_item_id", "group": "group_id" 
    }[assigned_kind]
    acn = assigned_container_name = "assigned%ss" % (assigned_kind)
    acn_len = len(acn)
    def getter(assignment, formatter):
        """(assignment:either(ItemGroupItemAssignment, GroupGroupItemAssignment), 
            formatter:? ) -> str
        """
        r = common.get_request()
        assigned = getattr(assignment, assigned_kind)
        assigned = translation.translate_obj(assigned)
        link_label = "[%s] %s" % (assigned.type, assigned.short_name)
        if IBusinessSectionLayer.providedBy(r):
            # Within the business/ section use a direct and absolute link to 
            # the related PI's public "home view".
            # The absolute URL path is of the form: 
            # /business/{ASSIGNED.TYPE}s/obj-{ASSIGNED.ID}/
            return zope.app.form.browser.widget.renderElement("a",
                contents=link_label,
                href="/business/%ss/obj-%s/" % (
                    assigned.type, getattr(assigned, assigned_id_attr_name))
            )
        else:
            # All other sections use a *relative* link to association view of 
            # the assigned item and the group it is assigned to (thus following
            # the link will keep the user within the same section). This is 
            # because under other sections, e.g. /admin or /workspace, this
            # association view makes it possible for an appropriately-privileged
            # user to modify properties of the assignment of the item to this 
            # group. The relative URL path is of the form: 
            # .../{ASSIGNED_CONTAINER_NAME}/obj-{ASSIGNMENT.ID}/
            #
            # We explicitly determine the absolute url path because 
            # concatenating to a relative path gives different results in 
            # different contexts e.g. when this is loaded as a json_listing of 
            # a *page view* or as a json_listing within a viewlet tab.
            url_path = acn
            if r:
                url = r.getURL()
                url_path = url[0: url.index(acn) + acn_len]
            return zope.app.form.browser.widget.renderElement("a",
                contents=link_label,
                href="%s/obj-%s/" % (url_path, assignment.assignment_id)
            )
    return column.GetterColumn(title, getter)


def member_title_column(name, title, default=u""):
    def getter(item, formatter):
        return item.title_name.user_role_name
    return column.GetterColumn(title, getter)

'''
def current_titles_in_group_column(name, title, default=u""):
    def getter(item, formatter):
        value = getattr(item, name)
        today = datetime.date.today()
        if not value:
            return default
        title_list = []
        for title in item.member_titles:
            if title.start_date <= today:
                if title.end_date:
                    if title.end_date >= today:
                        obj = translation.translate_obj(title.title_name)
                        title_list.append(obj.user_role_name)
                else:
                    obj = translation.translate_obj(title.title_name)
                    title_list.append(obj.user_role_name)
        return ", ".join(title_list)
    return column.GetterColumn(title, getter)
'''

def inActiveDead_Column(name, title, default):
    aid = { "A": _(u"active"),
        "I": _(u"inactive"),
        "D": _(u"deceased")}
    renderer = lambda x: aid[x]
    return _column(name, title, renderer, default)



def workflow_column(name, title, default=u""):
    def getter(item, formatter):
        state_title = misc.get_wf_state(item)
        interaction = getInteraction()
        for participation in interaction.participations:
            if IRequest.providedBy(participation):
                request = participation
        return translate(
            str(state_title),
            domain="bungeni.core",
            context=request)
    return column.GetterColumn(title, getter)

def constituency_column(name, title, default=u""):
    def getter(item, formatter):
        if item.constituency is None:
            return default
        obj = translation.translate_obj(item.constituency)
        return obj.name
    return column.GetterColumn(title, getter)
def province_column(name, title, default=u""):
    def getter(item, formatter):
        if item.province is None:
            return default
        obj = translation.translate_obj(item.province)
        return obj.province
    return column.GetterColumn(title, getter)
def region_column(name, title, default=u""):
    def getter(item, formatter):
        if item.region is None:
            return default
        obj = translation.translate_obj(item.region)
        return obj.region
    return column.GetterColumn(title, getter)

def party_column(name, title, default=u""):
    def getter(item, formatter):
        obj = item.party
        if obj is not None:
            return translation.translate_obj(obj).full_name
        return u"-"
    return column.GetterColumn(title, getter)

def ministry_column(name, title, default=u""):
    def getter(item, formatter):
        # !+TRANSLATE_ATTR(mr, sep-2010)
        #m = item.ministry
        #return translation.translate_attr(m, m.group_id, "short_name")
        obj = translation.translate_obj(item.ministry)
        return obj.short_name
    return column.GetterColumn(title, getter)

def enumeration_column(name, title,
    item_reference_attr=None, # parent item attribute, for enum 
    enum_value_attr=None, # enum attribute, for desired value
    ):
    """Get getter for the enum-value of an enumerated column.
    """
    if enum_value_attr is None:
        # then assume that value-attr on enum is same as enum-attr on parent
        enum_value_attr = item_reference_attr
    assert item_reference_attr is not None
    assert enum_value_attr is not None
    def getter(item, formatter):
        enum_obj = getattr(item, item_reference_attr)
        enum_obj = translation.translate_obj(enum_obj)
        return getattr(enum_obj, enum_value_attr)
    return column.GetterColumn(title, getter)

####
#  Constraints / Invariants
#

def ElectionAfterStart(obj):
    """Start Date must be after Election Date."""
    if obj.election_date >= obj.start_date:
        raise interface.Invalid(
            _("A parliament has to be elected before it can be sworn in"),
            "election_date",
            "start_date"
        )

def EndAfterStart(obj):
    """End Date must be after Start Date."""
    if obj.end_date is None: return
    if obj.end_date <= obj.start_date:
        raise interface.Invalid(
            _("End Date must be after Start Date"),
            "start_date",
            "end_date"
        )

def DissolutionAfterReinstatement(obj):
    """A committee must be disolved before it can be reinstated."""
    if (obj.dissolution_date is None) or (obj.reinstatement_date is None):
        return
    if obj.dissolution_date > obj.reinstatement_date:
        raise interface.Invalid(
            _("A committee must be disolved before it can be reinstated"),
            "dissolution_date",
            "reinstatement_date"
        )

def ActiveAndSubstituted(obj):
    """A person cannot be active and substituted at the same time."""
    if obj.active_p and obj.replaced_id:
        raise interface.Invalid(
            _("A person cannot be active and substituted at the same time"),
            "active_p",
            "replaced_id"
        )

def SubstitudedEndDate(obj):
    """If a person is substituted he must have an end date."""
    if not obj.end_date and obj.replaced_id:
        raise interface.Invalid(
            _("If a person is substituted End Date must be set"),
            "replaced_id",
            "end_date"
        )

def InactiveNoEndDate(obj):
    """If you set a person inactive you must provide an end date."""
    if not obj.active_p:
        if not (obj.end_date):
            raise interface.Invalid(
                _("If a person is inactive End Date must be set"),
                "end_date",
                "active_p"
            )

def MpStartBeforeElection(obj):
    """For members of parliament start date must be after election."""
    if obj.election_nomination_date > obj.start_date:
        raise interface.Invalid(_("A parliament member has to be "
                "elected/nominated before she/he can be sworn in"),
            "election_nomination_date",
            "start_date"
        )

def DeathBeforeLife(User):
    """Check if date of death is after date of birth."""
    if User.date_of_death is None: return
    if User.date_of_death < User.date_of_birth:
        raise interface.Invalid(_(u"One cannot die before being born"),
            "date_of_death",
            "date_of_birth"
        )

####
# Fields

# Notes:
#
# Field parameters, if specified, should be in the following order:
#   name, label, description, modes, property, listing_column, 
#   view_widget, edit_widget, add_widget, search_widget
#   
#   !+FIELD_PERMISSIONS(mr, nov-2010) view_permission/edit_permission params 
#   are deprecated -- when applied to any field (that corresponds to an 
#   attribute of the domain's class), the domain.zcml setting for that same 
#   class attribute will anyway take precedence.
#
# modes:
# - default: "view edit add"
# - all individual bool params {view, edit, add, listing, search} for each 
#   supported mode are now obsolete
# - to specify a non-default mode, must redefine entire modes parameter
#   e.g. to add "listing" mode must state modes="view edit add listing"
# - use modes="" as the equivalent of OBSOLETED omit=True
#
# property
# default values for schema.Field init parameters
#   title=u'', description=u'', __name__='', 
#   required=True, readonly=False, constraint=None, default=None
#
# required
# - Field.property.required: by default required=True for all schema.Field 
# - !+Field.required(mr, oct-2010) OBSOLETED.


def LanguageField(name="language"):
    return Field(name=name,
        label=_(u"Language"),
        modes="edit add",
        property=schema.Choice(title=_(u"Language"),
            default=get_default_language(),
            vocabulary="language_vocabulary"
        ),
    )

def AdmissibleDateField(name="admissible_date"):
    return Field(name=name,
        modes="view listing",
        localizable=[ show("view listing"), ],
        property=schema.Date(title=_(u"Admissible Date"), required=False),
    )

####
# Descriptors

# !+ID_NAME_LABEL_TITLE(mr, oct-2010) use of "id", "name", "label", "title", 
# should be conistent -- the (localized) {display, container}_name attributes 
# here should really all be {display, container}_label.

class UserDescriptor(ModelDescriptor):
    display_name = _(u"User")
    container_name = _(u"Users")

    fields = [
        Field(name="user_id",
            label="Name",
            modes="listing",
            listing_column=user_name_column("user_id", _(u"Name"), None),
        ),
        Field(name="titles",
            property=schema.TextLine(title=_(u"Salutation"),
                description=_(u"e.g. Mr. Mrs, Prof. etc."),
            ),
        ),
        Field(name="first_name",
            property=schema.TextLine(title=_(u"First Name"))
        ),
        Field(name="middle_name",
            property=schema.TextLine(title=_(u"Middle Name"), required=False)
        ),
        Field(name="last_name",
            property=schema.TextLine(title=_(u"Last Name"))
        ),
        Field(name="email",
            property=schema.TextLine(title=_(u"Email"),
                description=_(u"Email address"),
                constraint=constraints.check_email,
            ),
        ),
        Field(name="login",
            modes="view add",
            property=schema.TextLine(title=_(u"Login")),
        ),
        Field(name="_password",
            modes="add",
            property=schema.TextLine(title=_(u"Initial password")),
        ),
        Field(name="national_id",
            property=schema.TextLine(title=_(u"National Id"), required=False)
        ),
        Field(name="gender",
            property=schema.Choice(title=_(u"Gender"),
                source=vocabulary.Gender
            ),
            edit_widget=widgets.CustomRadioWidget,
            add_widget=widgets.CustomRadioWidget
        ),
        Field(name="date_of_birth",
            property=schema.Date(title=_(u"Date of Birth")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="birth_country",
            property=schema.Choice(title=_(u"Country of Birth"),
                source=vocabulary.DatabaseSource(domain.Country,
                    token_field="country_id",
                    title_field="country_name",
                    value_field="country_id"
                ),
            )
        ),
        Field(name="birth_nationality",
            property=schema.Choice(title=_(u"Nationality at Birth"),
                source=vocabulary.DatabaseSource(domain.Country,
                    token_field="country_id",
                    title_field="country_name",
                    value_field="country_id"
                ),
            ),
        ),
        Field(name="current_nationality",
            property=schema.Choice(title=_(u"Current Nationality"),
                source=vocabulary.DatabaseSource(domain.Country,
                    token_field="country_id",
                    title_field="country_name",
                    value_field="country_id"
                ),
            ),
        ),
        Field(name="date_of_death",
            property=schema.Date(title=_(u"Date of Death"), required=False),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        LanguageField("language"),
        Field(name="description",
            property=schema.Text(title=_(u"Biographical notes"),
                required=False
            ),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor
        ),
        Field(name="image",
            property=schema.Bytes(title=_(u"Image"),
                description=_(u"Picture of the person"),
                required=False
            ),
            view_widget=widgets.ImageDisplayWidget,
            edit_widget=widgets.ImageInputWidget,
        ),
    ]
    schema_invariants = [DeathBeforeLife]
    custom_validators = []


class UserDelegationDescriptor(ModelDescriptor):
    """Delegate rights to act on behalf of that user."""
    display_name = _(u"Delegate to user")
    container_name = _(u"Delegations")
    fields = [
        Field(name="delegation_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"User"),
                source=vocabulary.DatabaseSource(domain.User,
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id"
                )
            ),
            listing_column=user_name_column("delegation_id", _(u"User"),
                "delegation"),
        ),
    ]


class GroupMembershipDescriptor(ModelDescriptor):

    SubstitutionSource = vocabulary.SubstitutionSource(
        token_field="user_id",
        title_field="fullname",
        value_field="user_id"
    )

    fields = [
        Field(name="start_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"Start Date")),
            listing_column=day_column("start_date", _(u"Start Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="end_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"End Date"), required=False),
            listing_column=day_column("end_date", _(u"End Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="active_p",
            modes="edit add",
            property=schema.Bool(title=_(u"Active"), default=True),
        ),
        LanguageField("language"),
        Field(name="substitution_type",
            modes="edit view",
            property=schema.TextLine(
                title=_(u"Type of Substitution"),
                required=False
            ),
        ),
        Field(name="replaced_id",
            modes="edit view",
            property=schema.Choice(
                title=_(u"Substituted by"),
                source=SubstitutionSource,
                required=False
            ),
        ),
        #Field(name="membership_id", 
        #    label=_(u"Roles/Titles"),
        #    modes="",
        #    listing_column=current_titles_in_group_column("membership_id", 
        #        _(u"Roles/Titles")
        #    )
        #),
    ]
    schema_invariants = [
        EndAfterStart,
        ActiveAndSubstituted,
        SubstitudedEndDate,
        InactiveNoEndDate
    ]
    custom_validators = [
        validations.validate_date_range_within_parent,
        validations.validate_group_membership_dates
    ]


class MpDescriptor(GroupMembershipDescriptor):
    display_name = _(u"Member of parliament")
    container_name = _(u"Members of parliament")

    fields = [
        Field(name="user_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Name"),
                source=vocabulary.UserSource(
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id"
                )
            ),
            listing_column=user_name_column("user_id", _(u"Name"), "user"),
            #edit_widget=AutocompleteWidget,
            #add_widget=AutocompleteWidget,
            # !+AUTOCOMPLETE(mr, oct-2010) not working with the current 
            # field.vocabulary being passed to AutocompleteWidget 
        ),
        Field(name="elected_nominated",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"elected/nominated"),
                source=vocabulary.ElectedNominated
            ),
        ),
        Field(name="election_nomination_date",
            modes="view edit add",
            property=schema.Date(title=_("Election/Nomination Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))

    constituencySource = vocabulary.DatabaseSource(domain.Constituency,
        token_field="constituency_id",
        title_field="name",
        value_field="constituency_id"
    )
    provinceSource = vocabulary.DatabaseSource(domain.Province,
        token_field="province_id",
        title_field="province",
        value_field="province_id"
    )
    regionSource = vocabulary.DatabaseSource(domain.Region,
        token_field="region_id",
        title_field="region",
        value_field="region_id"
    )
    partySource = vocabulary.DatabaseSource(domain.PoliticalParty,
        token_field="party_id",
        title_field="full_name",
        value_field="party_id"
    )

    fields.extend([
        Field(name="constituency_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Constituency"),
                source=constituencySource,
                required=False
            ),
            listing_column=constituency_column("constituency_id",
                "Constituency"
            ),
        ),
        Field(name="province_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Province"),
                source=provinceSource,
                required=False
            ),
            listing_column=province_column("province_id", "Province"),
        ),
        Field(name="region_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"region"),
                source=regionSource,
                required=False
            ),
            listing_column=region_column("region_id", "region"),
        ),
        Field(name="party_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Political Party"),
                source=partySource,
                required=False
            ),
            listing_column=party_column("party_id", "Party"),
        ),
        Field(name="leave_reason",
            property=schema.Text(title=_("Leave Reason"), required=False)
        ),
        Field(name="notes",
            property=schema.Text(title=_(u"Notes"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor
        ),
    ])
    schema_invariants = GroupMembershipDescriptor.schema_invariants + [
        MpStartBeforeElection]


class PartyMemberDescriptor(GroupMembershipDescriptor):
    """Membership of a user in a party."""
    display_name = _(u"member")
    container_name = _(u"members")

    fields = [
        Field(name="user_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Name"),
                source=vocabulary.MemberOfParliamentSource("user_id",)
            ),
            listing_column=linked_mp_name_column("user_id", _(u"Name"), "user"),
            view_widget=widgets.MemberURLDisplayWidget
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        Field(name="notes",
            property=schema.Text(title=_(u"Notes"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
    ])


''' !+UNUSED(mr, oct-2010)
class MemberOfPartyDescriptor(ModelDescriptor):
    """Partymemberships of a member of a user."""
    
    display_name = _(u"Party membership")
    container_name = _(u"Party memberships")
    
    fields = [
        Field(name="user_id", modes=""),
        Field(name="short_name",
            modes="view edit add listing",
            property=schema.Text(title=_(u"Political Party")),
        ),
        Field(name="start_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"Start Date")),
            listing_column=day_column("start_date", _(u"Start Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget,
        ),
        Field(name="end_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"End Date"), required=False),
            listing_column=day_column("end_date", _(u"End Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget,
        ),
        Field(name="active_p",
            modes="edit add",
            property=schema.Bool(title=_(u"Active"), default=True),
            #label=_(u"Active"),
        ),
        LanguageField("language"),
        Field(name="notes",
            property=schema.Text(title=_(u"Notes"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
        Field(name="substitution_type", modes=""),
        Field(name="replaced_id", modes=""),
        Field(name="membership_id", modes=""),
        Field(name="status", modes=""),
        Field(name="membership_type", modes=""),
    ]
    #schema_invariants = [EndAfterStart]
    #custom_validators =[validations.validate_date_range_within_parent,]
'''

class GroupDescriptor(ModelDescriptor):

    _combined_name_title = "%s [%s]" % (_(u"Name"), _(u"Acronym"))
    fields = [
        Field(name="full_name",
            modes="view edit add",
            property=schema.TextLine(title=_(u"Name")),
            #listing_column=name_column("full_name", _(u"Full Name"))
        ),
        Field(name="short_name",
            modes="view edit add",
            property=schema.TextLine(title=_(U"Acronym")),
            #listing_column=name_column("short_name", _(u"Name"))
        ),
        Field(name="combined_name",
            modes="listing",
            property=schema.TextLine(title=_combined_name_title),
            listing_column=combined_name_column("full_name",
                _combined_name_title)
        ),
        LanguageField("language"),
        Field(name="description",
            property=schema.Text(title=_(u"Description") , required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
        Field(name="start_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"Start Date")),
            listing_column=day_column("start_date", _(u"Start Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="end_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"End Date"), required=False),
            listing_column=day_column("end_date", _(u"End Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
    ]
    schema_invariants = [EndAfterStart]
    custom_validators = [validations.validate_date_range_within_parent]
    public_wfstates = [
        group_wf_state[u"active"].id,
        group_wf_state[u"dissolved"].id
    ]


class ParliamentDescriptor(GroupDescriptor):
    display_name = _(u"Parliament")
    container_name = _(u"Parliaments")
    custom_validators = validations.validate_parliament_dates,

    fields = [
        Field(name="full_name",
            description=_(u"Parliament name"),
            modes="view edit add listing",
            property=schema.TextLine(title=_(u"Name")),
            listing_column=name_column("full_name", "Name"),
        ),
        Field(name="short_name",
            modes="view edit add listing",
            property=schema.TextLine(title=_(u"Parliament Identifier"),
                description=_("Unique identifier of each Parliament "
                    "(e.g. IX Parliament)"),
            ),
        ),
        LanguageField("language"),
        Field(name="description",
            property=schema.Text(title=_(u"Description"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
        Field(name="election_date",
            property=schema.Date(title=_(u"Election Date"),
                description=_(u"Date of the election"),
            ),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="start_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"In power from"),
                description=_(u"Date of the swearing in"),
            ),
            listing_column=day_column("start_date", _(u"In power from")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="end_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"In power till"),
                description=_(u"Date of the dissolution"),
                required=False
            ),
            listing_column=day_column("end_date", _(u"In power till")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
    ]
    schema_invariants = [
        EndAfterStart,
        ElectionAfterStart
    ]
    public_wfstates = [
        parliament_wf_state[u"active"].id,
        parliament_wf_state[u"dissolved"].id
    ]


class CommitteeDescriptor(GroupDescriptor):
    display_name = _(u"Profile")
    container_name = _(u"Committees")
    custom_validators = [validations.validate_date_range_within_parent, ]

    fields = deepcopy(GroupDescriptor.fields)
    fields.extend([
        Field(name="committee_type_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Type of committee"),
                source=vocabulary.DatabaseSource(domain.CommitteeType,
                    token_field="committee_type_id",
                    title_field="committee_type",
                    value_field="committee_type_id"
                )
            ),
            listing_column=enumeration_column("committee_type_id",
                _(u"Type"),
                item_reference_attr="committee_type"
            ),
        ),
        Field(name="num_members",
            property=schema.Int(title=_(u"Number of members"), required=False),
        ),
        Field(name="min_num_members",
            property=schema.Int(title=_(u"Minimum Number of Members"),
                required=False
            )
        ),
        Field(name="quorum",
            property=schema.Int(title=_(u"Quorum"), required=False)
        ),
        Field(name="num_clerks",
            property=schema.Int(title=_(u"Number of clerks"), required=False)
        ),
        Field(name="num_researchers",
            property=schema.Int(title=_(u"Number of researchers"),
                required=False
            )
        ),
        Field(name="proportional_representation",
            property=schema.Bool(title=_(u"Proportional representation"),
                default=True,
                required=False
            )
        ),
        Field(name="reinstatement_date",
            property=schema.Date(title=_(u"Reinstatement Date"),
                required=False
            ),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
    ])
    schema_invariants = [
        EndAfterStart,
        #DissolutionAfterReinstatement
    ]
    public_wfstates = [
        committee_wf_state[u"active"].id,
        committee_wf_state[u"dissolved"].id
    ]


class CommitteeMemberDescriptor(GroupMembershipDescriptor):
    display_name = _(u"Member")
    container_name = _(u"Members")
    fields = [
        Field(name="user_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Name"),
                source=vocabulary.MemberOfParliamentSource("user_id")
            ),
            listing_column=user_name_column("user_id", _(u"Name"), "user"),
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        Field(name="notes",
            property=schema.TextLine(title=_(u"Notes"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
    ])


class AddressTypeDescriptor(ModelDescriptor):
    display_name = _(u"Address type")
    container_name = _(u"Address types")

    fields = [
        Field(name="address_type_name",
            property=schema.TextLine(title=_(u"Address Type"))
        ),
    ]


class AddressDescriptor(ModelDescriptor):
    display_name = _(u"Address")
    container_name = _(u"Addresses")

    fields = [
        Field(name="address_type_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Address Type"),
                source=vocabulary.DatabaseSource(domain.AddressType,
                    token_field="address_type_id",
                    title_field="address_type_name",
                    value_field="address_type_id"
                ),
            ),
            listing_column=enumeration_column("address_type_id",
                _(u"Type"),
                item_reference_attr="address_type",
                enum_value_attr="address_type_name"
            ),
        ),
        Field(name="postal_type",
            property=schema.Choice(title=_(u"Postal Type"),
                source=vocabulary.AddressPostalType,
                required=True
            ),
        ),
        Field(name="street",
            property=schema.Text(title=_(u"Street"), required=True),
            edit_widget=zope.app.form.browser.TextAreaWidget,
            add_widget=zope.app.form.browser.TextAreaWidget,
        ),
        Field(name="city",
            modes="view edit add listing",
            property=schema.TextLine(title=_(u"City"), required=True)
        ),
        Field(name="zipcode", label=_(u"Zip Code")),
        Field(name="country",
            property=schema.Choice(title=_(u"Country"),
                source=vocabulary.DatabaseSource(domain.Country,
                    token_field="country_id",
                    title_field="country_name",
                    value_field="country_id"
                ),
                required=True
            ),
        ),
        Field(name="phone",
            property=schema.Text(title=_(u"Phone Number(s)"),
                description=_(u"Enter one phone number per line"),
                required=False
            ),
            edit_widget=zope.app.form.browser.TextAreaWidget,
            add_widget=zope.app.form.browser.TextAreaWidget,
            #view_widget=zope.app.form.browser.ListDisplayWidget,
        ),
        Field(name="fax",
            property=schema.Text(title=_(u"Fax Number(s)"),
                description=_(u"Enter one fax number per line"),
                required=False
            ),
            edit_widget=zope.app.form.browser.TextAreaWidget,
            add_widget=zope.app.form.browser.TextAreaWidget,
        ),
        Field(name="email",
            modes="view edit add listing",
            property=schema.TextLine(title=_(u"Email"),
                description=_(u"Email address"),
                constraint=constraints.check_email,
                required=False
            ),
        ),
        #Field(name="im_id",
        #    property=schema.TextLine(title=_(u"Instant Messenger Id"),
        #        description=_(u"ICQ, AOL IM, GoogleTalk..."), 
        #        required=False
        #    )
        #), !+IM(mr, oct-2010) morph to some "extra_info" on User
    ]
    public_wfstates = [address_wf_state[u"public"].id]

class GroupAddressDescriptor(AddressDescriptor):
    fields = deepcopy(AddressDescriptor.fields)
class UserAddressDescriptor(AddressDescriptor):
    fields = deepcopy(AddressDescriptor.fields)


class MemberRoleTitleDescriptor(ModelDescriptor):
    display_name = _(u"Title")
    container_name = _(u"Titles")

    fields = [
        Field(name="title_name_id", label=_(u"Title"),
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Title"),
                source=vocabulary.MemberTitleSource("title_name_id"),
            ),
            listing_column=member_title_column("title_name_id", _(u"Title")),
        ),
        Field(name="start_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"Start Date"), required=True),
            listing_column=day_column("start_date", _(u"Start Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="end_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"End Date"), required=False),
            listing_column=day_column("end_date", _(u"End Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        LanguageField("language"),
    ]
    #] + [ deepcopy(f) for f in AddressDescriptor.fields 
    #      if f["name"] not in ("role_title_id",) ]

    schema_invariants = [
        EndAfterStart,
    ]
    custom_validators = [
        validations.validate_date_range_within_parent,
        validations.validate_member_titles
    ]


class CommitteeStaffDescriptor(GroupMembershipDescriptor):
    display_name = _(u"Staff")
    container_name = _(u"Staff")
    fields = [
        Field(name="user_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Name"),
                source=vocabulary.UserNotMPSource(
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id"
                )
            ),
            listing_column=user_name_column("user_id", _(u"Name"), "user"),
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        Field(name="notes",
            property=schema.Text(title=_(u"Notes"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
    ])


class PoliticalPartyDescriptor(GroupDescriptor):
    display_name = _(u"political party")
    container_name = _(u"political parties")
    custom_validators = [validations.validate_date_range_within_parent, ]

    fields = deepcopy(GroupDescriptor.fields)
    fields.extend([
        Field(name="logo_data",
            property=schema.Bytes(title=_(u"Logo"), required=False),
            view_widget=widgets.ImageDisplayWidget,
            edit_widget=widgets.ImageInputWidget
        ),
    ])
    schema_invariants = [EndAfterStart]


class PoliticalGroupDescriptor(PoliticalPartyDescriptor):
    display_name = _(u"political group")
    container_name = _(u"political groups")

    fields = deepcopy(PoliticalPartyDescriptor.fields)


class OfficeDescriptor(GroupDescriptor):
    display_name = _(u"Office")
    container_name = _(u"Offices")

    fields = [
        Field(name="office_type",
            property=schema.Choice(title=_(u"Type"),
                description=_(u"Type of Office"),
                source=vocabulary.OfficeType
            ),
        )
    ]
    fields.extend(deepcopy(GroupDescriptor.fields))
    custom_validators = [validations.validate_date_range_within_parent]


class OfficeMemberDescriptor(GroupMembershipDescriptor):
    display_name = _(u"Office Member")
    container_name = _(u"Office Members")
    fields = [
        Field(name="user_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Name"),
                source=vocabulary.UserNotMPSource(
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id"
                )
            ),
            listing_column=user_name_column("user_id", _(u"Name"), "user"),
        )
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        Field(name="notes",
              property=schema.Text(title=_(u"Notes"), required=False),
              view_widget=widgets.HTMLDisplay,
              edit_widget=widgets.RichTextEditor,
              add_widget=widgets.RichTextEditor,
        ),
    ])


class MinistryDescriptor(GroupDescriptor):
    display_name = _(u"Ministry")
    container_name = _(u"Ministries")

    fields = deepcopy(GroupDescriptor.fields)
    schema_invariants = [EndAfterStart]
    custom_validators = [validations.validate_date_range_within_parent]


class MinisterDescriptor(GroupMembershipDescriptor):
    display_name = _(u"Minister")
    container_name = _(u"Ministers")

    fields = [
        Field(name="user_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Name"),
                source=vocabulary.UserSource(
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id"
                )
            ),
            listing_column=user_name_column("user_id", _(u"Name"), "user"),
        )
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        Field(name="notes",
            property=schema.Text(title=_(u"Notes"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
    ])


class GovernmentDescriptor(GroupDescriptor):
    display_name = _(u"Government")
    container_name = _(u"Governments")

    fields = [
        Field(name="short_name",
            modes="view edit add listing",
            property=schema.TextLine(title=_(u"Name"),
                description=_(u"Name"),
                required=False
            ),
        ),
        Field(name="full_name", label=_(u"Number")),
        Field(name="start_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"In power from")),
            listing_column=day_column("start_date", _(u"In power from")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="end_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"In power till"), required=False),
            listing_column=day_column("end_date", _(u"In power till")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        LanguageField("language"),
        Field(name="description",
            property=schema.Text(title=_(u"Notes"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
    ]
    schema_invariants = [EndAfterStart]
    custom_validators = [validations.validate_government_dates]


class GroupItemAssignmentDescriptor(ModelDescriptor):
    fields = [
        Field(name="start_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"Start Date")),
            listing_column=day_column("start_date", _(u"Start Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="end_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"End Date"), required=False),
            listing_column=day_column("end_date", _(u"End Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="due_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"Due Date"), required=False),
            listing_column=day_column("due_date", _(u"Due Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        #Field(name="status_date", 
        #    label=_(u"Status date"),
        #    modes="",
        #    listing_column=day_column("status_date", _(u"Status date")),
        #),
        Field(name="notes",
            property=schema.Text(title=_(u"Notes") , required=False),
                view_widget=widgets.HTMLDisplay,
                edit_widget=widgets.RichTextEditor,
                add_widget=widgets.RichTextEditor,
        ),
        LanguageField("language"),
    ]

class ItemGroupItemAssignmentDescriptor(GroupItemAssignmentDescriptor):
    """The Bills assigned to a Committee.
    """
    display_name = _(u"Assigned bill")
    container_name = _(u"Assigned bills")
    fields = [
        Field(name="item_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Bill"),
                source=vocabulary.BillSource(
                    token_field="parliamentary_item_id",
                    title_field="short_name",
                    value_field="parliamentary_item_id"
                ),
            ),
            listing_column=linked_assignment_column(_(u"Bill"), "item"),
        ),
    ]
    fields.extend(deepcopy(GroupItemAssignmentDescriptor.fields))

class GroupGroupItemAssignmentDescriptor(GroupItemAssignmentDescriptor):
    """The Committees a Bill is assigned to.
    """
    display_name = _(u"Assigned committee")
    container_name = _(u"Assigned committees")
    fields = [
        Field(name="group_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Committee"),
                source=vocabulary.CommitteeSource(
                    token_field="group_id",
                    title_field="short_name",
                    value_field="group_id"
                ),
            ),
            listing_column=linked_assignment_column(_(u"Committee"), "group"),
        ),
    ]
    fields.extend(deepcopy(GroupItemAssignmentDescriptor.fields))


class AttachedFileDescriptor(ModelDescriptor):
    display_name = _(u"File")
    container_name = _(u"Files")
    fields = [
        LanguageField("language"),
        Field(name="file_title",
            modes="view edit add listing",
            property=schema.TextLine(title=_(u"Title")),
            edit_widget=widgets.TextWidget,
            add_widget=widgets.TextWidget,
        ),
        Field(name="file_description",
            property=schema.Text(title=_(u"Description"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
        Field(name="file_data",
            property=schema.Bytes(title=_(u"File")),
            description=_(u"Upload a file"),
            edit_widget=widgets.FileEditWidget,
            add_widget=widgets.FileAddWidget,
            view_widget=widgets.FileDisplayWidget,
        ),
        Field(name="attached_file_type_id",
            property=schema.Choice(title=_(u"File type"),
                source=vocabulary.DatabaseSource(domain.AttachedFileType,
                    token_field="attached_file_type_id",
                    title_field="attached_file_type_name",
                    value_field="attached_file_type_id"
                ),
            ),
        ),
        Field(name="file_name",
            label=u"",
            modes="edit add",
            edit_widget=widgets.NoInputWidget,
            add_widget=widgets.NoInputWidget,
        ),
        Field(name="file_mimetype",
            label=u"",
            modes="edit add",
            edit_widget=widgets.NoInputWidget,
            add_widget=widgets.NoInputWidget,
        ),
        Field(name="status",
            label=_(u"Status"),
            modes="edit view listing",
            property=schema.Choice(title=_(u"Status"),
                 vocabulary="bungeni.vocabulary.workflow",
            ),
            listing_column=workflow_column("status", "Workflow status"),
        ),
        Field(name="status_date",
            label=_(u"Status date"),
            modes="view listing",
            listing_column=day_column("status_date", _(u"Status date")),
        ),
    ]
    public_wfstates = [af_wf_state[u"public"].id]


class AttachedFileVersionDescriptor(ModelDescriptor):
    display_name = _(u"Attached file version")
    container_name = _(u"Versions")
    fields = deepcopy(AttachedFileDescriptor.fields)


class ParliamentaryItemDescriptor(ModelDescriptor):

    fields = [
        Field(name="parliament_id",
            modes="view edit",
            localizable=[ hide("view"), ],
            property=schema.Choice(title=_(u"Parliament"),
                source=vocabulary.DatabaseSource(domain.Parliament,
                    token_field="parliament_id",
                    title_field="short_name",
                    value_field="parliament_id"
                ),
            ),
        ),
        Field(name="short_name",
            modes="view edit add listing",
            localizable=[ show("view listing"), ],
            property=schema.TextLine(title=_(u"Title")),
            edit_widget=widgets.TextWidget,
            add_widget=widgets.TextWidget,
        ),
        Field(name="full_name",
            modes="view edit add",
            localizable=[ show(), ],
            property=schema.TextLine(title=_(u"Summary"), required=False),
            edit_widget=widgets.LongTextWidget,
            add_widget=widgets.LongTextWidget,
        ),
        Field(name="registry_number",
            modes="edit view",
            localizable=[ show("view"), ],
            property=schema.Int(title=_(u"Registry number"), required=False),
        ),
        Field(name="owner_id",
            modes="view edit add listing",
            localizable=[
                hide("view listing", "bungeni.Anybody"),
            ],
            property=schema.Choice(title=_(u"Moved by"),
                description=_(u"Select the user who moved the document"),
                source=vocabulary.MemberOfParliamentDelegationSource("owner_id"),
            ),
            listing_column=linked_mp_name_column("owner_id", _(u"Name"), "owner"),
            view_widget=widgets.MemberURLDisplayWidget
        ),
        #LanguageField("language"),
        Field(name="language",
            modes="view edit add",
            localizable=[ show("view"), ],
            property=schema.Choice(title=_(u"Language"),
                default=get_default_language(),
                vocabulary="language_vocabulary",
            ),
        ),
        Field(name="body_text",
            modes="view edit add",
            localizable=[ show("view"), ],
            property=schema.Text(title=_(u"Text")),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
        Field(name="submission_date",
            modes="view listing",
            localizable=[ show("view listing"), ],
            property=schema.Date(title=_(u"Submission Date"), required=False),
            listing_column=day_column("submission_date", _(u"Submission Date")),
        ),
        Field(name="status",
            label=_(u"Status"),
            modes="edit view listing",
            property=schema.Choice(title=_(u"Status"),
                vocabulary="bungeni.vocabulary.workflow",
            ),
            listing_column=workflow_column("status", "Workflow status"),
        ),
        Field(name="status_date",
            label=_(u"Status date"),
            modes="view listing",
            localizable=[ show("view listing"), ],
            listing_column=day_column("status_date", _(u"Status date")),
        ),
        Field(name="note",
            label=_(u"Notes"),
            description="Recommendation note",
            modes="edit add",
            property=schema.Text(title=_(u"Notes"),
                description=_(u"Recommendation note"),
                required=False
            ),
            add_widget=widgets.OneTimeEditWidget,
            edit_widget=widgets.OneTimeEditWidget,
        ),
        Field(name="receive_notification",
            modes="view edit add",
            localizable=[ show("view"), ],
            property=schema.Choice(title=_(u"Receive notification"),
                description=_("Select this option to receive notifications "
                    "for this item"),
                source=vocabulary.YesNoSource
            ),
            edit_widget=widgets.CustomRadioWidget,
            add_widget=widgets.CustomRadioWidget,
        ),
    ]


class VersionDescriptor(ModelDescriptor):
    fields = [
        Field(name="short_name",
            modes="view edit add listing",
            property=schema.TextLine(title=_(u"Title")),
            edit_widget=widgets.TextWidget,
            add_widget=widgets.TextWidget,
        ),
        Field(name="full_name",
            property=schema.TextLine(title=_(u"Summary")),
            edit_widget=widgets.LongTextWidget,
            add_widget=widgets.LongTextWidget,
        ),
        #LanguageField("language"),
        Field(name="language",
            modes="view add listing",
            property=schema.Choice(title=_(u"Language"),
                default=get_default_language(),
                vocabulary="language_vocabulary",
            ),
        ),
        Field(name="body_text",
            property=schema.Text(title=_(u"Text")),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
        Field(name="note",
            description="Recommendation note",
            modes="edit add",
            property=schema.Text(title=_(u"Notes"),
                description=_(u"Recommendation note"),
                required=False
            ),
            edit_widget=widgets.OneTimeEditWidget,
        ),
    ]
    public_wfstates = [version_wf_state[u"archived"].id]


class HeadingDescriptor(ParliamentaryItemDescriptor):
    display_name = _(u"Heading")
    container_name = _(u"Headings")
    fields = [
        Field(name="short_name",
            modes="view edit add listing",
            localizable=[ show("view listing"), ],
            property=schema.TextLine(title=_(u"Title")),
            edit_widget=widgets.TextWidget,
            add_widget=widgets.TextWidget,
        ),
        Field(name="owner_id",
            modes="view edit add",
            localizable=[
                hide("view", "bungeni.Anybody"),
            ],
            property=schema.Choice(title=_(u"Owner"),
                source=vocabulary.DatabaseSource(domain.User,
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id")
            ),
        ),
        #LanguageField("language"),
        Field(name="language",
            modes="view edit add",
            localizable=[ show("view"), ],
            property=schema.Choice(title=_(u"Language"),
                default=get_default_language(),
                vocabulary="language_vocabulary",
            ),
        ),
        Field(name="body_text",
            modes="view edit add",
            localizable=[ show("view"), ],
            property=schema.Text(title=_(u"Text")),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        )
    ]
    public_wfstates = [heading_wf_state[u"public"].id]


class AgendaItemDescriptor(ParliamentaryItemDescriptor):
    display_name = _(u"Agenda item")
    container_name = _(u"Agenda items")
    fields = deepcopy(ParliamentaryItemDescriptor.fields)
    fields.append(AdmissibleDateField())
    public_wfstates = get_states("agendaitem", tagged=["public"])


class AgendaItemVersionDescriptor(VersionDescriptor):
    display_name = _(u"Agenda Item version")
    container_name = _(u"Versions")
    fields = deepcopy(VersionDescriptor.fields)


class MotionDescriptor(ParliamentaryItemDescriptor):
    display_name = _(u"Motion")
    container_name = _(u"Motions")
    fields = deepcopy(ParliamentaryItemDescriptor.fields)
    fields.extend([
        AdmissibleDateField(),
        Field(name="notice_date",
            modes="view listing",
            localizable=[ show("view listing"), ],
            property=schema.Date(title=_(u"Notice Date"), required=False),
        ),
        Field(name="motion_number",
            modes="view listing",
            localizable=[ show("view listing"), ],
            property=schema.Int(title=_(u"Identifier"), required=False),
        ),
        #Field(name="party_id", modes="",
        #    #property = schema.Choice(title=_(u"Political Party"), 
        #    #   source=vocabulary.MotionPartySource(
        #    #     token_field="party_id", 
        #    #     title_field="short_name", 
        #    #     value_field = "party_id"), 
        #    #   required=False),
        #),
    ])
    public_wfstates = get_states("motion", tagged=["public"])


class MotionVersionDescriptor(VersionDescriptor):
    display_name = _(u"Motion version")
    container_name = _(u"Versions")
    fields = deepcopy(VersionDescriptor.fields)


class BillDescriptor(ParliamentaryItemDescriptor):
    display_name = _(u"Bill")
    container_name = _(u"Bills")
    fields = deepcopy(ParliamentaryItemDescriptor.fields)
    _bt = misc.get_keyed_item(fields, "body_text", key="name") # !+
    _bt.label = _(u"Statement of Purpose")
    _bt.property = schema.Text(
        title=_(u"Statement of Purpose"), required=False)

    fields.extend([
        Field(name="bill_type_id",
            property=schema.Choice(title=_(u"Bill Type"),
                source=vocabulary.DatabaseSource(domain.BillType,
                    token_field="bill_type_id",
                    title_field="bill_type_name",
                    value_field="bill_type_id"
                ),
            ),
        ),
        Field(name="ministry_id",
            property=schema.Choice(title=_(u"Ministry"),
                source=vocabulary.MinistrySource("ministry_id"),
                required=False
            ),
        ),
        Field(name="identifier",
            modes="edit view",
            property=schema.Text(title=_(u"Identifier"), required=False),
        ),
        Field(name="publication_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"Publication Date"), required=False),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget ,
            listing_column=day_column("publication_date",
                _(u"Publication Date")
            ),
        ),
    ])
    public_wfstates = get_states("bill", not_tagged=["private"])

class BillVersionDescriptor(VersionDescriptor):
    display_name = _(u"Bill version")
    container_name = _(u"Versions")
    fields = deepcopy(VersionDescriptor.fields)


class QuestionDescriptor(ParliamentaryItemDescriptor):
    display_name = _(u"Question")
    container_name = _(u"Questions")
    custom_validators = ()

    fields = deepcopy(ParliamentaryItemDescriptor.fields)
    fields.extend([
        Field(name="question_number",
            modes="view listing",
            property=schema.Int(title=_(u"Question Number"), required=False),
        ),
        #Field(name="supplement_parent_id",
        #    label=_(u"Initial/supplementary question"),
        #    modes="",
        #    view_widget=widgets.SupplementaryQuestionDisplay,
        #),
        Field(name="ministry_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Ministry"),
                source=vocabulary.MinistrySource("ministry_id"),
            ),
            listing_column=ministry_column("ministry_id" , _(u"Ministry")),
        ),
        AdmissibleDateField(),
        Field(name="ministry_submit_date",
            modes="edit view",
            localizable=[ show("view") ],
            property=schema.Date(title=_(u"Submitted to ministry"),
                required=False
            ),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget,
        ),
        Field(name="question_type",
            property=schema.Choice(title=_(u"Question Type"),
                description=_("Ordinary or Private Notice"),
                vocabulary=vocabulary.QuestionType
            ),
        ),
        Field(name="response_type",
            property=schema.Choice(title=_(u"Response Type"),
                description=_("Oral or Written"),
                vocabulary=vocabulary.ResponseType
            ),
        ),
        Field(name="response_text",
            modes="edit",
            property=schema.TextLine(title=_(u"Response"),
                description=_(u"Response to the Question"),
                required=False
            ),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
        ),
    ])
    public_wfstates = get_states("question", tagged=["public"])


class QuestionVersionDescriptor(VersionDescriptor):
    display_name = _(u"Question version")
    container_name = _(u"Versions")
    fields = deepcopy(VersionDescriptor.fields)


class EventItemDescriptor(ParliamentaryItemDescriptor):
    display_name = _(u"Event")
    container_name = _(u"Events")
    fields = [
        Field(name="short_name",
            modes="view edit add listing",
            localizable=[ show("view listing"), ],
            property=schema.TextLine(title=_(u"Title")),
            edit_widget=widgets.TextWidget,
            add_widget=widgets.TextWidget,
        ),
        Field(name="owner_id",
            modes="view edit add",
            localizable=[
                hide("view", "bungeni.Anybody"),
            ],
            property=schema.Choice(title=_(u"Owner"),
                source=vocabulary.DatabaseSource(domain.User,
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id")
            ),
         ),
        #LanguageField("language"),
        Field(name="language",
            modes="view edit add",
            localizable=[ show("view"), ],
            property=schema.Choice(title=_(u"Language"),
                default=get_default_language(),
                vocabulary="language_vocabulary",
            ),
        ),
        Field(name="body_text",
            modes="view edit add",
            localizable=[ show("view"), ],
            property=schema.Text(title=_(u"Text")),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
        Field(name="event_date",
            modes="view edit add listing",
            property=schema.Datetime(title=_(u"Date")),
            listing_column=day_column("event_date", _(u"Date")),
            edit_widget=widgets.DateTimeWidget,
            add_widget=widgets.DateTimeWidget,
        ),
    ]
    public_wfstates = [event_wf_state[u"public"].id]


class TabledDocumentDescriptor(ParliamentaryItemDescriptor):
    display_name = _(u"Tabled document")
    container_name = _(u"Tabled documents")
    fields = deepcopy(ParliamentaryItemDescriptor.fields)
    fields.extend([
        Field(name="tabled_document_number",
            modes="view listing",
            property=schema.Int(title=_(u"Tabled document Number")),
        ),
        AdmissibleDateField(),
    ])
    public_wfstates = get_states("tableddocument", tagged=["public"])


class TabledDocumentVersionDescriptor(VersionDescriptor):
    display_name = _(u"Tabled Document version")
    container_name = _(u"Versions")
    fields = deepcopy(VersionDescriptor.fields)


class SittingDescriptor(ModelDescriptor):
    display_name = _(u"Sitting")
    container_name = _(u"Sittings")

    fields = [
        LanguageField("language"),
        #Sitting type is commented out below because it is not set during
        #creation of a sitting but is left here because it may be used in the
        #future related to r7243

        #Field(name="sitting_type_id",
        #    modes="view edit add listing",
        #    listing_column=enumeration_column("sitting_type_id",
        #        _(u"Sitting Type"),
        #        item_reference_attr="sitting_type"
        #    ),
        #    property=schema.Choice(title=_(u"Sitting Type"),
        #        source=vocabulary.SittingTypes(
        #            token_field="sitting_type_id",
        #            title_field="sitting_type",
        #            value_field="sitting_type_id"
        #        ),
        #    ),
        #),
        Field(name="start_date",
            modes="add view listing",
            property=schema.Datetime(title=_(u"Date")),
            listing_column=date_from_to_column("start_date", _(u"Start")),
            # !+CustomListingURL(mr, oct-2010) the listing of this type has 
            # been replaced by the custom GroupSittingsViewlet -- but it 
            # should still be possible use the generic container listing in
            # combination with a further customized listing_column -- for an
            # example of this see how the listing of the column "owner_id" 
            # is configured in: descriptor.ParliamentaryItemDescriptor

            # !+CustomListingURL(miano, nov-2010) 
            # Since the custom listing column function was missing
            # the sitting listing was broken in archive.
            # Reverted to fix the issue.
            # This listing does not need to be customised because it is
            # only used in the archive.
            edit_widget=widgets.DateTimeWidget,
            add_widget=widgets.DateTimeWidget,
        ),
        Field(name="end_date",
            modes="add view listing",
            property=schema.Datetime(title=_(u"End")),
            #listing_column=time_column("end_date", _(u"End Date")),
            edit_widget=widgets.DateTimeWidget,
            add_widget=widgets.DateTimeWidget,
        ),
        Field(name="venue_id",
            property=schema.Choice(title=_(u"Venue"),
                source=vocabulary.DatabaseSource(domain.Venue,
                    token_field="venue_id",
                    title_field="short_name",
                    value_field="venue_id"
                ),
                required=False
            ),
        )
    ]
    schema_invariants = [EndAfterStart]
    custom_validators = [
        validations.validate_date_range_within_parent,
        validations.validate_start_date_equals_end_date,
        validations.validate_venues,
        #validations.validate_non_overlapping_sitting
    ]
    public_wfstates = get_states("groupsitting", tagged=["public"])


class GroupSittingTypeDescriptor(ModelDescriptor):
    display_name = _(u"Type")
    container_name = _(u"Types")


class SessionDescriptor(ModelDescriptor):
    display_name = _(u"Parliamentary session")
    container_name = _(u"Parliamentary sessions")

    fields = [
        Field(name="short_name",
            modes="view edit add listing",
            property=schema.TextLine(title=_(u"Short Name")),
        ),
        Field(name="full_name",
            property=schema.TextLine(title=_(u"Full Name"))
        ),
        Field(name="start_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"Start Date")),
            listing_column=day_column("start_date", _(u"Start Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="end_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"End Date")),
            listing_column=day_column("end_date", _(u"End Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        LanguageField("language"),
        Field(name="notes", label=_(u"Notes"))
    ]
    schema_invariants = [EndAfterStart]
    custom_validators = [validations.validate_date_range_within_parent]


#class DebateDescriptor (ModelDescriptor):
#    display_name = _(u"Debate")
#    container_name = _(u"Debate")

#    fields = [
#        Field(name="sitting_id", modes=""), 
#        Field(name="debate_id", modes=""),
#        Field(name="short_name", 
#                label=_(u"Short Name"), 
#                modes="view edit add listing",
#                listing_column=name_column("short_name", 
#                    _(u"Name"))), 
#        Field(name="body_text", label=_(u"Transcript"),
#              property = schema.Text(title=u"Transcript"),
#              view_widget=widgets.HTMLDisplay,
#              edit_widget=widgets.RichTextEditor, 
#              add_widget=widgets.RichTextEditor,
#             ),
#        ]


class AttendanceDescriptor(ModelDescriptor):
    display_name = _(u"Sitting attendance")
    container_name = _(u"Sitting attendances")

    fields = [
        Field(name="member_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Attendance"),
                source=vocabulary.SittingAttendanceSource(
                    token_field="user_id",
                    title_field="fullname",
                    value_field="member_id"
                )
            ),
            listing_column=user_name_column("member_id", _(u"Name"), "user")
        ),
        Field(name="attendance_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Attendance"),
                source=vocabulary.DatabaseSource(
                    domain.AttendanceType,
                    token_field="attendance_id",
                    title_field="attendance_type",
                    value_field="attendance_id"
                )
            ),
            listing_column=enumeration_column("attendance_id",
                _(u"Attendance"),
                item_reference_attr="attendance_type"
            ),
        ),
    ]


class AttendanceTypeDescriptor(ModelDescriptor):
    display_name = _(u"Sitting attendance")
    container_name = _(u"Sitting attendances")

    fields = [
        Field(name="attendance_type",
            property=schema.TextLine(title=_(u"Attendance type"))
        ),
        LanguageField("language"),
    ]


class CosignatoryDescriptor(ModelDescriptor):
    display_name = _(u"Cosignatory")
    container_name = _(u"Cosignatories")

    fields = [
        Field(name="user_id",
            modes="view edit add listing",
            property=schema.Choice(title=_(u"Cosignatory"),
                source=vocabulary.MemberOfParliamentDelegationSource("user_id"),
            ),
            listing_column=linked_mp_name_column("user_id",
                _(u"Cosignatory"),
                "user"
            ),
            view_widget=widgets.MemberURLDisplayWidget
        ),
    ]


class ConstituencyDescriptor(ModelDescriptor):
    display_name = _(u"Constituency")
    container_name = _(u"Constituencies")

    fields = [
        LanguageField("language"),
        Field(name="name",
            modes="view edit add listing",
            property=schema.TextLine(title=_(u"Name"),
                description=_("Name of the constituency"),
            ),
        ),
        Field(name="start_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"Start Date")),
            listing_column=day_column("start_date", _(u"Start Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="end_date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"End Date"), required=False),
            listing_column=day_column("end_date", _(u"End Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
    ]
    schema_invariants = [EndAfterStart]


class ProvinceDescriptor(ModelDescriptor):
    display_name = _(u"Province")
    container_name = _(u"Provinces")
    fields = [
        LanguageField("language"),
        Field(name="province",
            modes="view edit add listing",
            property=schema.TextLine(title=_(u"Province"),
                description=_(u"Name of the Province"),
            ),
        ),
    ]


class RegionDescriptor(ModelDescriptor):
    display_name = _(u"Region")
    container_name = _(u"Regions")
    fields = [
        LanguageField("language"),
        Field(name="region",
            modes="view edit add listing",
            property=schema.TextLine(title=_(u"Region"),
                description=_(u"Name of the Region"),
            ),
        ),
    ]


class CountryDescriptor(ModelDescriptor):
    fields = [
        LanguageField("language"),
        Field(name="country_id",
            property=schema.TextLine(title=_(u"Country Code"),
                description=_(u"ISO Code of the  country")
            )
        ),
        Field(name="country_name",
            modes="view edit add listing",
            property=schema.TextLine(title=_(u"Country"),
                description=_(u"Name of the Country")
            ),
        ),
    ]


class ConstituencyDetailDescriptor(ModelDescriptor):
    display_name = _(u"Constituency details")
    container_name = _(u"Details")
    fields = [
        Field(name="date",
            modes="view edit add listing",
            property=schema.Date(title=_(u"Date"),
                description=_("Date the data was submitted from the "
                    "Constituency"),
            ),
            listing_column=day_column("date", "Date"),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="population",
            modes="view edit add listing",
            property=schema.Int(title=_(u"Population"),
                description=_(u"Total Number of People living in this "
                    "Constituency"),
            ),
        ),
        Field(name="voters",
            modes="view edit add listing",
            property=schema.Int(title=_(u"Voters"),
                description=_(u"Number of Voters registered in this "
                    "Constituency"),
            ),
        ),
    ]


################
# Hansard
################

class RotaDescriptor(ModelDescriptor):
    fields = [
        # !+ Field(name="reporter_id") ??
        Field(name="identifier",
            modes="view edit add listing",
        ), # !+ title=_("Rota Identifier"), 
        Field(name="start_date",
            modes="view edit add listing",
            label=_(u"Start Date"),
            listing_column=day_column("start_date", _(u"Start Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="end_date",
            modes="view edit add listing",
            label=_(u"End Date"),
            listing_column=day_column("end_date", _(u"End Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
    ]
    schema_invariants = [EndAfterStart]


class DocumentSourceDescriptor(ModelDescriptor):
    display_name = _(u"Document source")
    container_name = _(u"Document sources")

    fields = [
        Field(name="document_source", label=_(u"Document Source")),
    ]


class ItemScheduleDescriptor(ModelDescriptor):
    display_name = _(u"Scheduling")
    container_name = _(u"Schedulings")

    fields = [
        Field(name="item_id",
            property=schema.Choice(title=_(u"Item"),
                source=vocabulary.DatabaseSource(domain.ParliamentaryItem,
                    token_field="parliamentary_item_id",
                    value_field="parliamentary_item_id",
                    title_getter=lambda obj: "%s - %s" % (
                        type(obj).__name__, obj.short_name)
                )
            ),
        ),
    ]


class ItemScheduleDiscussionDescriptor(ModelDescriptor):
    display_name = _(u"Discussion")
    container_name = _(u"Discussions")

    fields = [
        LanguageField("language"),
        Field(name="body_text",
            label=_(u"Minutes"),
            property=schema.Text(title=_(u"Minutes")),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
        #Field(name="sitting_time", 
        #    label=_(u"Sitting time"), 
        #    description=_(u"The time at which the discussion took place."), 
        #    modes="view edit add listing",
        #),
    ]


class ReportDescriptor(ParliamentaryItemDescriptor):
    display_name = _(u"Report")
    container_name = _(u"Reports")

    fields = [
        #LanguageField("language"),
        Field(name="language",
            label=_(u"Language"),
            modes="edit add",
            property=schema.Choice(title=_(u"Language"),
                default=get_default_language(),
                vocabulary="language_vocabulary",
            ),
        ),
        Field(name="short_name",
            label=_(u"Publications type"),
            modes="edit add listing",
        ),
        Field(name="start_date",
            label=_(u"Sitting Date"),
            modes="edit add listing",
            listing_column=datetime_column("start_date", _(u"Sitting Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget,
        ),
        # reports do not go through the workflow so the status date
        # is the published date ie. they are created and immediately
        # published
        Field(name="status_date",
            label=_(u"Published Date"),
            modes="edit add listing",
            listing_column=datetime_column("status_date", _(u"Published Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget,
        ),
        Field(name="note",
            modes="edit add listing",
            label=_(u"Note"),
        ),
        Field(name="body_text",
            label=_(u"Text"),
            property=schema.Text(title=_(u"Text")),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
    ]


class Report4SittingDescriptor(ReportDescriptor):
    fields = deepcopy(ReportDescriptor.fields)

