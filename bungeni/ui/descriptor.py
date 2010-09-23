# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Form Schemas for Domain Objects

$Id$
"""

from copy import deepcopy
from datetime import date
from zope import schema, interface

from zope.security.management import getInteraction
from zope.publisher.interfaces import IRequest
import zope.app.form.browser
from zope.i18n import translate
from zc.table import column

from bungeni.alchemist.model import ModelDescriptor
from bungeni.alchemist.ui import widgets

from bungeni.models import domain

from bungeni.core.translation import get_default_language
from bungeni.core.translation import get_all_languages
from bungeni.core.workflows.groups import states as group_wf_state
from bungeni.core.workflows.attachedfile import states as af_wf_state
from bungeni.core.workflows.address import states as address_wf_state
from bungeni.core.workflows.event import states as event_wf_state
from bungeni.core.workflows.heading import states as heading_wf_state
from bungeni.core.workflows.committee import states as committee_wf_state
from bungeni.core.workflows.parliament import states as parliament_wf_state
from bungeni.core.workflows.version import states as version_wf_state
from bungeni.core import translation

#from bungeni.ui.widgets import SelectDateWidget, SelectDateTimeWidget
from bungeni.ui.widgets import TextDateWidget as DateWidget
from bungeni.ui.widgets import TextDateTimeWidget as DateTimeWidget

from bungeni.ui.widgets import CustomRadioWidget
from bungeni.ui.widgets import HTMLDisplay
from bungeni.ui.widgets import RichTextEditor
from bungeni.ui.widgets import ImageDisplayWidget
from bungeni.ui.widgets import ImageInputWidget
from bungeni.ui.widgets import SupplementaryQuestionDisplay
from bungeni.ui.widgets import OneTimeEditWidget
from bungeni.ui.widgets import FileEditWidget
from bungeni.ui.widgets import FileAddWidget
from bungeni.ui.widgets import FileDisplayWidget
from bungeni.ui.widgets import NoInputWidget
from bungeni.ui import constraints
from bungeni.ui.forms import validations
from bungeni.ui.i18n import _
import bungeni.ui.utils as ui_utils
from bungeni.ui import vocabulary
from bungeni.ui.tagged import get_states

###
# Listing Columns 
# 
def _column(name, title, renderer, default=""):
    def getter(item, formatter):
        value = getattr(item, name)
        if value:
            return renderer(value)
        return default
    return column.GetterColumn(title, getter)


def day_column(name, title, default=""):
    renderer = lambda x: x.strftime("%Y-%m-%d")
    return _column(name, title, renderer, default)

def date_from_to_column(name, title, default=""):
    def getter(item, formatter):
        start = getattr(item, "start_date")
        end = getattr(item, "end_date")
        if start:
            start = start.strftime("%Y-%m-%d %H:%M")
        if end:
            end = end.strftime("%H:%M")
        return u"%s - %s" % (start, end)
    return column.GetterColumn(title, getter)


def datetime_column(name, title, default=""):
    renderer = lambda x: x.strftime("%Y-%m-%d %H:%M")
    return _column(name, title, renderer, default)

def time_column(name, title, default=""):
    renderer = lambda x: x.strftime("%H:%M")
    return _column(name, title, renderer, default)

def name_column(name, title, default=""):
    def renderer(value, size=50):
        if len(value) > size:
            return "%s..." % value[:size]
        return value
    return _column(name, title, renderer, default)


def user_name_column(name, title, attr, default=u""):
    def getter(item, formatter):
        if attr:
            user = getattr(item, attr, None)
            if user:
                return u"%s %s" % (user.first_name, user.last_name)
        else:
            return u"%s %s" % (item.first_name, item.last_name)
    return column.GetterColumn(title, getter)


def member_title_column(name, title, default=u""):
    def getter(item, formatter):
        return item.title_name.user_role_name
    return column.GetterColumn(title, getter)

def current_titles_in_group_column(name, title, default=u""):
    def getter(item, formatter):
        value = getattr(item, name)
        today = date.today()
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

def inActiveDead_Column(name, title, default):
    aid = { "A": _(u"active"),
        "I": _(u"inactive"),
        "D": _(u"deceased")}
    renderer = lambda x: aid[x]
    return _column(name, title, renderer, default)

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


def workflow_column(name, title, default=u""):
    def getter(item, formatter):
        state_title = ui_utils.misc.get_wf_state(item)
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

def committee_type_column(name, title, default=u""):
    def getter(item, formatter):
        obj = translation.translate_obj(item.committee_type)
        return obj.committee_type
    return column.GetterColumn(title, getter)

def ministry_column(name, title, default=u""):
    def getter(item, formatter):
        # !+TRANSLATE_ATTR(mr, sep-2010)
        #m = item.ministry
        #return translation.translate_attr(m, m.group_id, "short_name")
        obj = translation.translate_obj(item.ministry)
        return obj.short_name
    return column.GetterColumn(title, getter)

def sitting_type_column(name, title, default=u""):
    def getter(item, formatter):
        obj = translation.translate_obj(item.sitting_type)
        return obj.sitting_type
    return column.GetterColumn(title, getter)

def attendance_column(name, title, default=u""):
    def getter(item, formatter):
        obj = translation.translate_obj(item.attendance_type)
        return obj.attendance_type
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

def POBoxOrAddress(obj):
    """
    An Address must have either an entry for a physical address or a P.O. Box
    """
    if obj.po_box is None and obj.address is None:
        raise interface.Invalid(_(u"You have to enter an Address"),
            "po_box",
            "address"
        )

####
# Fields

# Each field is described as a dict, for details see:
# bungeni.alchemist.model.Field.fromDict(dict)
# 
# NOTE: contrary to what is indicated in bungeni.alchemist.model, the "differ" 
# field descriptor dictionary key is actually ignored. 

def LanguageField(name="language"):
    return dict(name=name, 
        label=_(u"Language"),
        listing=False, 
        add=True, 
        edit=True, 
        omit=False,
        required=True,
        property=schema.Choice(title=_(u"Language"),
            default=get_default_language(),
            vocabulary="language_vocabulary"
        )
    )

####
# Descriptors

# !+bungeni.alchemist.model.Field.modes(mr, sep-2010) it seems that the 
# Field.modes attribute does not work as claimed in the code -- 
# use exclusively the boolean keyword alternative for each of the 
# following modes:
# _valid_modes = ('edit', 'view', 'read', 'add', 'listing', 'search')

class UserDescriptor(ModelDescriptor):
    display_name = _(u"User")
    container_name = _(u"Users")
    
    fields = [
        dict(name="user_id",
            label="Name",
            listing_column=user_name_column("user_id", _(u"Name"), None),
            listing=True,
            edit=False,
            add=False,
            view=False
        ),
        dict(name="titles",
            property=schema.TextLine(title=_(u"Salutation"),
                description=_(u"e.g. Mr. Mrs, Prof. etc."),
                required=True
            )
        ),
        dict(name="first_name",
            property=schema.TextLine(title=_(u"First Name"), required=True)
        ),
        dict(name="middle_name",
            property=schema.TextLine(title=_(u"Middle Name"), required=False)
        ),
        dict(name="last_name",
            property=schema.TextLine(title=_(u"Last Name"), required=True)
        ),
        dict(name="email",
            property=schema.TextLine(title=_(u"Email"),
                description=_(u"Email address"),
                constraint=constraints.check_email,
                required=True
            )
        ),
        dict(name="login",
            property=schema.TextLine(title=_(u"Login"), required=True),
            add=True, 
            edit=False, 
            view=True
        ),
        dict(name="password", omit=True),
        dict(name="_password",
            property=schema.TextLine(title=_(u"Initial password"), 
                required=True
            ),
            add=True,
            view=False,
            edit=False,
            required=True
        ),
        dict(name="national_id",
            property=schema.TextLine(title=_(u"National Id"), required=False)
        ),
        dict(name="gender",
            property=schema.Choice(title=_(u"Gender"), 
                source=vocabulary.Gender
            ),
            edit_widget=CustomRadioWidget,
            add_widget=CustomRadioWidget
        ),
        dict(name="date_of_birth",
            property=schema.Date(title=_(u"Date of Birth")),
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="birth_country", 
            property=schema.Choice(title=_(u"Country of Birth"),
                source=vocabulary.DatabaseSource(domain.Country,
                    token_field="country_id",
                    title_field="country_name",
                    value_field="country_id"
                ),
                required=True
            )
        ),
        dict(name="birth_nationality",
            property=schema.Choice(title=_(u"Nationality at Birth"),
                source=vocabulary.DatabaseSource(domain.Country,
                    token_field="country_id",
                    title_field="country_name",
                    value_field="country_id"
                ),
                required=True
            ),
        ),
        dict(name="current_nationality",
            property=schema.Choice(title=_(u"Current Nationality"),
                source=vocabulary.DatabaseSource(domain.Country,
                    token_field="country_id",
                    title_field="country_name",
                    value_field="country_id"
                ),
                required=True
            ),
        ),
        dict(name="date_of_death",
            property=schema.Date(title=_(u"Date of Death"), required=False),
            #view_permission="bungeni.user.AdminRecord",
            edit_permission="bungeni.user.AdminRecord",
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="active_p", label=_(u"Status"), omit=True),
        LanguageField("language"),
        dict(name="description",
            property=schema.Text(title=_(u"Biographical notes"), 
                required=False
            ),
            view_widget=HTMLDisplay,
            edit_widget=RichTextEditor,
            add_widget=RichTextEditor
        ),
        dict(name="image",
            property=schema.Bytes(title=_(u"Image"),
                description=_(u"Picture of the person"),
                required=False
            ),
            view_widget=ImageDisplayWidget,
            edit_widget=ImageInputWidget,
            listing=False
        ),
        dict(name="salt", omit=True),
        dict(name="type", omit=True),
    ]
    schema_invariants = [DeathBeforeLife]
    custom_validators = []


class UserDelegationDescriptor(ModelDescriptor):
    """Delegate rights to act on behalf of that user."""
    display_name = _(u"Delegate to user")
    container_name = _(u"Delegations")
    fields = [
        dict(name="user_id", omit=True),
        dict(name="delegation_id",
            property=schema.Choice(title=_(u"User"),
                source=vocabulary.DatabaseSource(domain.User,
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id"
                )
            ),
            listing_column=user_name_column("delegation_id", _(u"User"), "user"),
            listing=True,
        ),
    ]


class GroupMembershipDescriptor(ModelDescriptor):
    
    SubstitutionSource = vocabulary.SubstitutionSource(
        token_field="user_id",
        title_field="fullname",
        value_field="user_id"
    )
    
    fields = [
        dict(name="start_date",
            property=schema.Date(title=_(u"Start Date"), required=True),
            listing_column=day_column("start_date", _(u"Start Date")),
            listing=True,
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="end_date",
            property=schema.Date(title=_(u"End Date"), required=False),
            listing=False,
            listing_column=day_column("end_date", _(u"End Date")),
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="active_p",
            property=schema.Bool(title=_(u"Active"), 
                default=True, 
                required=True
            ),
            #label=_(u"Active"),
            #required=True,
            view=False
        ),
        LanguageField("language"),
        dict(name="substitution_type",
            property=schema.TextLine(
                title=_(u"Type of Substitution"), 
                required=False
            ),
            add=False
        ),
        dict(name="replaced_id",
            property=schema.Choice(
                title=_(u"Substituted by"),
                source=SubstitutionSource,
                required=False
            ),
            add=False
        ),
        dict(name="group_id", omit=True),
        dict(name="membership_id", 
            label=_(u"Roles/Titles"),
            add=False, 
            edit=False, 
            view=False, 
            listing=False,
            listing_column=current_titles_in_group_column("membership_id", 
                _(u"Roles/Titles")
            )
        ),
        dict(name="membership_type", omit=True),
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


class MpDescriptor(ModelDescriptor):
    display_name = _(u"Member of parliament")
    container_name = _(u"Members of parliament")
    
    fields = [
        dict(name="user_id",
            property=schema.Choice(title=_(u"Name"),
                source=vocabulary.UserSource(
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id"
                )
            ),
            listing_column=user_name_column("user_id", _(u"Name"), "user"),
            listing=True,
        ),
        dict(name="elected_nominated",
            property=schema.Choice(title=_(u"elected/nominated"),
                source=vocabulary.ElectedNominated
            ),
            listing=True
        ),
        dict(name="election_nomination_date",
            property=schema.Date(title=_("Election/Nomination Date"),
                required=True
            ),
            required=True,
            edit_widget=DateWidget,
            add_widget=DateWidget
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
        dict(name="constituency_id",
            property=schema.Choice(title=_(u"Constituency"),
                source=constituencySource,
                required=False
            ),
            # !+REQUIRED_FIELD(mr, aug-2010) this is not working -- what we 
            # *may* want to achieve is: to require that this field be set 
            # but without assuming any default value (that, for SELECT widgets, 
            # the first item is used as the default):
            #required=True, 
            listing_column=constituency_column("constituency_id", 
                "Constituency"
            ),
            listing=True
        ),
        dict(name="province_id",
            property=schema.Choice(title=_(u"Province"),
                source=provinceSource,
                required=False
            ),
            listing_column=province_column("province_id", "Province"),
            listing=True
        ),
        dict(name="region_id",
            property=schema.Choice(title=_(u"region"),
                source=regionSource,
                required=False
            ),
            listing_column=region_column("region_id", "region"),
            listing=True
        ),
        dict(name="party_id",
            property=schema.Choice(title=_(u"Political Party"),
                source=partySource,
                required=False),
            listing_column=party_column("party_id", "Party"),
            listing=True
        ),
        dict(name="leave_reason",
            property=schema.Text(title=_("Leave Reason"), required=False)
        ),
        dict(name="notes",
            property=schema.Text(title=_(u"Notes"), required=False),
            view_widget=HTMLDisplay,
            edit_widget=RichTextEditor,
            add_widget=RichTextEditor
        ),
    ])
    schema_invariants = [
        EndAfterStart, 
        ActiveAndSubstituted,
        SubstitudedEndDate, 
        InactiveNoEndDate, 
        MpStartBeforeElection
    ]
    custom_validators = [
        validations.validate_date_range_within_parent,
        validations.validate_group_membership_dates
    ]


class PartyMemberDescriptor(ModelDescriptor):
    """Membership of a user in a party."""
    display_name = _(u"member")
    container_name = _(u"members")
    
    fields = [
        dict(name="user_id",
            property=schema.Choice(title=_(u"Name"),
                source=vocabulary.MemberOfParliamentSource("user_id",)
            ),
            listing_column=user_name_column("user_id", _(u"Name"), "user"),
            listing=True,
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        dict(name="notes",
            property=schema.Text(title=_(u"Notes"), required=False),
            view_widget=HTMLDisplay,
            edit_widget=RichTextEditor,
            add_widget=RichTextEditor,
        ),
    ])
    custom_validators = [
        validations.validate_date_range_within_parent,
        validations.validate_party_membership
    ]


class MemberOfPartyDescriptor(ModelDescriptor):
    """Partymemberships of a member of a user."""
    
    display_name = _(u"Party membership")
    container_name = _(u"Party memberships")
    
    fields = [
        dict(name="user_id", omit=True),
        dict(name="short_name",
            property=schema.Text(title=_(u"Political Party"), required=True),
            listing=True
        ),
        dict(name="start_date",
            property=schema.Date(title=_(u"Start Date"), required=True),
            listing_column=day_column("start_date", _(u"Start Date")),
            listing=True,
            edit_widget=DateWidget,
            add_widget=DateWidget,
        ),
        dict(name="end_date",
            property=schema.Date(title=_(u"End Date"), required=False),
            listing=True,
            listing_column=day_column("end_date", _(u"End Date")),
            edit_widget=DateWidget,
            add_widget=DateWidget,
        ),
        dict(name="active_p",
            property=schema.Bool(title=_(u"Active"), 
                default=True, 
                required=True
            ),
            #label=_(u"Active"),
            #required=True,
            view=False
        ),
        LanguageField("language"),
        dict(name="notes",
           property=schema.Text(title=_(u"Notes"), required=False),
            view_widget=HTMLDisplay,
            edit_widget=RichTextEditor,
            add_widget=RichTextEditor,
        ),
        dict(name="substitution_type", omit=True),
        dict(name="replaced_id", omit=True),
        dict(name="membership_id", omit=True),
        dict(name="status", omit=True),
        dict(name="membership_type", omit=True),
    ]
    #schema_invariants = [EndAfterStart]
    #custom_validators =[validations.validate_date_range_within_parent,]


class GroupDescriptor(ModelDescriptor):
    
    fields = [
        dict(name="group_id", omit=True),
        dict(name="type", omit=True),
        dict(name="full_name",
            property=schema.TextLine(title=_(u"Name"), required=True),
            listing=True,
            listing_column=name_column("full_name", _(u"Full Name"))
        ),
        dict(name="short_name",
            property=schema.TextLine(title=_(U"Acronym"), required=True),
            listing=True,
            listing_column=name_column("short_name", _(u"Name"))
        ),
        LanguageField("language"),
        dict(name="description",
            property=schema.Text(title=_(u"Description") , required=False),
            view_widget=HTMLDisplay,
            edit_widget=RichTextEditor,
            add_widget=RichTextEditor,
        ),
        dict(name="start_date",
            property=schema.Date(title=_(u"Start Date"), required=True),
            listing=True,
            listing_column=day_column("start_date", _(u"Start Date")),
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="end_date",
            property=schema.Date(title=_(u"End Date"), required=False),
            listing=True,
            listing_column=day_column("end_date", _(u"End Date")),
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="status", omit=True),
        dict(name="status_date", omit=True),
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
        dict(name="group_id", omit=True),
        dict(name="parliament_id", omit=True),
        dict(name="full_name",
            property=schema.TextLine(title=_(u"Name"), required=True),
            description=_(u"Parliament name"),
            listing=True,
            listing_column=name_column("full_name", "Name"),
        ),
        dict(name="short_name",
            property=schema.TextLine(title=_(u"Parliament Identifier"),
                description=_("Unique identifier of each Parliament "
                    "(e.g. IX Parliament)"),
                required=True
            ),
            listing=True,
        ),
        LanguageField("language"),
        dict(name="description",
            property=schema.Text(title=_(u"Description"), required=False),
            view_widget=HTMLDisplay,
            edit_widget=RichTextEditor,
            add_widget=RichTextEditor,
        ),
        dict(name="election_date",
            property=schema.Date(title=_(u"Election Date"),
                description=_(u"Date of the election"),
                required=True
            ),
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="start_date",
            property=schema.Date(title=_(u"In power from"),
                description=_(u"Date of the swearing in"),
                required=True
            ),
            listing_column=day_column("start_date", _(u"In power from")),
            listing=True,
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="end_date",
            property=schema.Date(title=_(u"In power till"),
                description=_(u"Date of the dissolution"),
                required=False
            ),
            listing_column=day_column("end_date", _(u"In power till")),
            listing=True,
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="status", omit=True),
        dict(name="status_date", omit=True),
        dict(name="type", omit=True),
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
    
    typeSource = vocabulary.DatabaseSource(domain.CommitteeType,
        token_field="committee_type_id",
        title_field="committee_type",
        value_field="committee_type_id"
    )
    
    fields = deepcopy(GroupDescriptor.fields)
    fields.extend([
        dict(name="committee_id", omit=True),
        dict(name="committee_type_id",
            property=schema.Choice(title=_(u"Type of committee"), 
                source=typeSource
            ),
            listing_column=committee_type_column("committee_type_id", 
                _(u"Type")
            ),
            listing=True,
        ),
        dict(name="no_members",
            property=schema.Int(title=_(u"Number of members"), required=False),
        ),
        dict(name="min_no_members",
            property=schema.Int(title=_(u"Minimum Number of Members"), 
                required=False
            )
        ),
        dict(name="quorum",
            property=schema.Int(title=_(u"Quorum"), required=False)
        ),
        dict(name="no_clerks",
            property=schema.Int(title=_(u"Number of clerks"), required=False)
        ),
        dict(name="no_researchers",
            property=schema.Int(title=_(u"Number of researchers"), 
                required=False
            )
        ),
        dict(name="proportional_representation",
            property=schema.Bool(title=_(u"Proportional representation"), 
                default=True, 
                required=False
            )
        ),
        dict(name="default_chairperson", 
            label=_(u"Default chairperson"),
            omit=True
        ),
        dict(name="reinstatement_date",
            property=schema.Date(title=_(u"Reinstatement Date"), 
                required=False
            ),
            edit_widget=DateWidget,
            add_widget=DateWidget
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


class CommitteeMemberDescriptor(ModelDescriptor):
    display_name = _(u"Member")
    container_name = _(u"Membership")
    fields = [
        dict(name="user_id",
            property=schema.Choice(title=_(u"Name"),
                source=vocabulary.UserSource(
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id"
                )
            ),
            listing_column=user_name_column("user_id", _(u"Name"), "user"),
            listing=True,
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        dict(name="notes",
            property=schema.TextLine(title=_(u"Notes"), required=False),
            view_widget=HTMLDisplay,
            edit_widget=RichTextEditor,
            add_widget=RichTextEditor,
        ),
    ])
    
    custom_validators = [validations.validate_date_range_within_parent]
    schema_invariants = [
        EndAfterStart, 
        ActiveAndSubstituted,
        SubstitudedEndDate, 
        InactiveNoEndDate
    ]


class AddressTypeDescriptor(ModelDescriptor):
    display_name = _(u"Address type")
    container_name = _(u"Address types")
    
    fields = [
        dict(name="address_type_id", omit=True),
        dict(name="address_type_name",
            property=schema.TextLine(title=_(u"Address Type"))
        ),
    ]


class AddressDescriptor(ModelDescriptor):
    display_name = _(u"Address")
    container_name = _(u"Addresses")
    
    fields = [
        dict(name="address_id", omit=True),
        dict(name="role_title_id", omit=True),
        dict(name="user_id", omit=True),
        dict(name="address_type_id",
            property=schema.Choice(title=_(u"Address Type"),
                source=vocabulary.DatabaseSource(domain.AddressType,
                    title_field="address_type_name",
                    token_field="address_type_id",
                    value_field="address_type_id"
                ),
            )
        ),
        dict(name="po_box", 
            property=schema.TextLine(title=_(u"P.O. Box"), required=False)
        ),
        dict(name="address",
            property=schema.Text(title=_(u"Address"), required=False),
            edit_widget=zope.app.form.browser.TextAreaWidget,
            add_widget=zope.app.form.browser.TextAreaWidget,
        ),
        dict(name="city",
            property=schema.TextLine(title=_(u"City"), required=False)
        ),
        dict(name="zipcode", label=_(u"Zip Code")),
        dict(name="country",
            property=schema.Choice(title=_(u"Country"),
                source=vocabulary.DatabaseSource(domain.Country,
                    title_field="country_name",
                    token_field="country_id",
                    value_field="country_id"
                ),
                required=False
            ),
        ),
        dict(name="phone",
            property=schema.Text(title=_(u"Phone Number(s)"),
                description=_(u"Enter one phone number per line"),
                required=False
            ),
            edit_widget=zope.app.form.browser.TextAreaWidget,
            add_widget=zope.app.form.browser.TextAreaWidget,
            #view_widget=zope.app.form.browser.ListDisplayWidget,
        ),
        dict(name="fax",
            property=schema.Text(title=_(u"Fax Number(s)"),
                description=_(u"Enter one fax number per line"),
                required=False
            ),
            edit_widget=zope.app.form.browser.TextAreaWidget,
            add_widget=zope.app.form.browser.TextAreaWidget,
        ),
        dict(name="email",
            property=schema.TextLine(title=_(u"Email"),
                description=_(u"Email address"),
                constraint=constraints.check_email,
                required=False
            ),
            listing=True,
        ),
        dict(name="im_id",
            property=schema.TextLine(title=_(u"Instant Messenger Id"),
                description=_(u"ICQ, AOL IM, GoogleTalk..."), 
                required=False
            )
        ),
        dict(name="status", omit=True),
        dict(name="status_date", omit=True),
    ]
    schema_invariants = [POBoxOrAddress]
    public_wfstates = [address_wf_state[u"public"].id]


class MemberRoleTitleDescriptor(ModelDescriptor):
    display_name = _(u"Title")
    container_name = _(u"Titles")
    
    fields = [
        dict(name="role_title_id", omit=True),
        dict(name="membership_id", omit=True),
        dict(name="title_name_id", label=_(u"Title"),
            property=schema.Choice(title=_(u"Title"),
                source=vocabulary.MemberTitleSource("title_name_id"),
            ),
            listing_column=member_title_column("title_name_id", _(u"Title")),
            listing=True,
        ),
        dict(name="start_date",
            property=schema.Date(title=_(u"Start Date"), required=True),
            listing=True,
            listing_column=day_column("start_date", _(u"Start Date")),
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="end_date",
            property=schema.Date(title=_(u"End Date"), required=False),
            listing=True,
            listing_column=day_column("end_date", _(u"End Date")),
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        LanguageField("language"),
    ] + deepcopy(AddressDescriptor.fields)
    
    schema_invariants = [
        EndAfterStart, 
        POBoxOrAddress
    ]
    custom_validators = [
        validations.validate_date_range_within_parent,
        validations.validate_member_titles
    ]


class CommitteeStaffDescriptor(ModelDescriptor):
    display_name = _(u"Staff")
    container_name = _(u"Staff")
    fields = [
        dict(name="user_id",
            property=schema.Choice(title=_(u"Name"),
                source=vocabulary.UserNotMPSource(
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id"
                )
            ),
            listing_column=user_name_column("user_id", _(u"Name"), "user"),
            listing=True,
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        dict(name="notes",
            property=schema.Text(title=_(u"Notes"), required=False),
            view_widget=HTMLDisplay,
            edit_widget=RichTextEditor,
            add_widget=RichTextEditor,
        ),
    ])
    custom_validators = [validations.validate_date_range_within_parent]
    schema_invariants = [
        EndAfterStart, 
        ActiveAndSubstituted,
        SubstitudedEndDate, 
        InactiveNoEndDate
    ]


class PoliticalPartyDescriptor(GroupDescriptor):
    display_name = _(u"political party")
    container_name = _(u"political parties")
    custom_validators = [validations.validate_date_range_within_parent, ]
    
    fields = deepcopy(GroupDescriptor.fields)
    fields.extend([
        dict(name="logo_data",
            property=schema.Bytes(title=_(u"Logo"), required=False),
            edit=True,
            add=True,
            view=True,
            listing=False,
            view_widget=ImageDisplayWidget,
            edit_widget=ImageInputWidget
        ),
        dict(name="party_id", omit=True),
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
        dict(name="office_type", 
            property=schema.Choice(title=_(u"Type"),
                description=_(u"Type of Office"),
                source=vocabulary.OfficeType
            ),
            listing=False,
        )
    ]
    fields.extend(deepcopy(GroupDescriptor.fields))
    custom_validators = [validations.validate_date_range_within_parent]


class OfficeMemberDescriptor(ModelDescriptor):
    display_name = _(u"Office Member")
    container_name = _(u"Office Members")
    fields = [
        dict(name="user_id",
            property=schema.Choice(title=_(u"Name"),
                source=vocabulary.UserNotMPSource(
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id"
                )
            ),
            listing_column=user_name_column("user_id", _(u"Name"), "user"),
            listing=True,
        )
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        dict(name="notes",
              property=schema.Text(title=_(u"Notes"), required=False),
              view_widget=HTMLDisplay,
              edit_widget=RichTextEditor,
              add_widget=RichTextEditor,
        ),
    ])
    custom_validators = [validations.validate_date_range_within_parent]
    schema_invariants = [
        ActiveAndSubstituted, 
        SubstitudedEndDate,
        InactiveNoEndDate
    ]


class MinistryDescriptor(GroupDescriptor):
    display_name = _(u"Ministry")
    container_name = _(u"Ministries")
    
    fields = deepcopy(GroupDescriptor.fields)
    schema_invariants = [EndAfterStart]
    custom_validators = [validations.validate_date_range_within_parent]


class MinisterDescriptor(ModelDescriptor):
    display_name = _(u"Minister")
    container_name = _(u"Ministers")
    
    fields = [
        dict(name="user_id",
            property=schema.Choice(title=_(u"Name"),
                source=vocabulary.UserSource(
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id"
                )
            ),
            listing_column=user_name_column("user_id", _(u"Name"), "user"),
            listing=True,
        )
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        dict(name="notes",
            property=schema.Text(title=_(u"Notes"), required=False),
            view_widget=HTMLDisplay,
            edit_widget=RichTextEditor,
            add_widget=RichTextEditor,
        ),
    ])
    custom_validators = [validations.validate_date_range_within_parent]
    schema_invariants = [
        ActiveAndSubstituted, 
        SubstitudedEndDate,
        InactiveNoEndDate
    ]


class GovernmentDescriptor(GroupDescriptor):
    display_name = _(u"Government")
    container_name = _(u"Governments")
    
    fields = [
        dict(name="group_id", omit=True),
        dict(name="short_name",
            property=schema.TextLine(title=_(u"Name"),
                description=_(u"Name"), 
                required=False
            ),
            listing=True
        ),
        dict(name="full_name", label=_(u"Number")),
        dict(name="start_date",
            property=schema.Date(title=_(u"In power from"), required=True),
            listing=True,
            listing_column=day_column("start_date", _(u"In power from")),
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="end_date",
            property=schema.Date(title=_(u"In power till"), required=False),
            listing=True,
            listing_column=day_column("end_date", _(u"In power till")),
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        LanguageField("language"),
        dict(name="description",
            property=schema.Text(title=_(u"Notes"), required=False),
            view_widget=HTMLDisplay,
            edit_widget=RichTextEditor,
            add_widget=RichTextEditor,
        ),
        dict(name="status", omit=True),
        dict(name="status_date", omit=True),
        dict(name="type", omit=True),
    ]
    schema_invariants = [EndAfterStart]
    custom_validators = [validations.validate_government_dates]


class GroupItemAssignmentDescriptor(ModelDescriptor):
    fields = [
        dict(name="assignment_id", omit=True),
        dict(name="start_date",
            property=schema.Date(title=_(u"Start Date"),
                required=True),
            listing_column=day_column("start_date",
                _(u"Start Date")),
                listing=True,
            edit_widget=DateWidget, add_widget=DateWidget),
        dict(name="end_date",
            property=schema.Date(title=_(u"End Date"),
            required=False),
            listing_column=day_column("end_date",
                _(u"End Date")),
                listing=True,
            edit_widget=DateWidget, add_widget=DateWidget),
        dict(name="due_date",
            property=schema.Date(title=_(u"Due Date"),
            required=False),
            listing_column=day_column("due_date",
                _(u"Due Date")),
                listing=True,
            edit_widget=DateWidget, add_widget=DateWidget),
        dict(name="status", omit=True),
        dict(name="status_date", 
            add=False, 
            edit=False,
            label=_(u"Status date"),
            view=False, 
            listing=False,
            listing_column=day_column("status_date", _(u"Status date")),
        ),
        dict(name="notes",
            property=schema.Text(title=_(u"Notes") , required=False),
                view_widget=HTMLDisplay,
                edit_widget=RichTextEditor,
                add_widget=RichTextEditor,
        ),
        LanguageField("language"),
    ]


class ItemGroupItemAssignmentDescriptor(GroupItemAssignmentDescriptor):
    display_name = _(u"Assigned bill")
    container_name = _(u"Assigned bills")
    fields = [
        dict(name="item_id",
            property=schema.Choice(title=_(u"Bill"),
                source=vocabulary.BillSource(
                    title_field="short_name",
                    token_field="parliamentary_item_id",
                    value_field="parliamentary_item_id"
                ),
            ),
            listing_column=item_name_column("parliamentary_item_id", _(u"Item")),
            listing=True,
        ),
        dict(name="group_id", omit=True),
    ]
    fields.extend(deepcopy(GroupItemAssignmentDescriptor.fields))


class GroupGroupItemAssignmentDescriptor(GroupItemAssignmentDescriptor):
    display_name = _(u"Assigned group")
    container_name = _(u"Assigned groups")
    fields = [
        dict(name="item_id", omit=True),
        dict(name="group_id",
            property=schema.Choice(title=_(u"Committee"),
                source=vocabulary.CommitteeSource(
                    title_field="short_name",
                    token_field="group_id",
                    value_field="group_id"
                ),
            ),
            listing_column=group_name_column("group_id", _(u"Group")),
            listing=True,
        ),
    ]
    fields.extend(deepcopy(GroupItemAssignmentDescriptor.fields))


class AttachedFileDescriptor(ModelDescriptor):
    display_name = _(u"File")
    container_name = _(u"Files")
    fields = [
        dict(name="attached_file_id", omit=True),
        dict(name="item_id", omit=True),
        dict(name="file_version_id", omit=True),
        LanguageField("language"),
        dict(name="file_title",
            property=schema.TextLine(title=_(u"Title"), required=True),
            listing=True,
            edit_widget=widgets.LongTextWidget,
            add_widget=widgets.LongTextWidget,
            add=True,
            edit=True,
            omit=False
        ),
        dict(name="file_description",
            property=schema.Text(title=_(u"Description"), required=False),
            view_widget=HTMLDisplay,
            edit_widget=RichTextEditor,
            add_widget=RichTextEditor,
        ),
        dict(name="file_data",
            property=schema.Bytes(title=_(u"File"), required=True),
            description=_(u"Upload a file"),
            edit_widget=FileEditWidget,
            add_widget=FileAddWidget,
            view_widget=FileDisplayWidget,
            required=True,
            listing=False
        ),
        dict(name="file_name", 
            label=u"",
            edit_widget=NoInputWidget,
            add_widget=NoInputWidget,
            view=False
        ),
        dict(name="file_mimetype", 
            label=u"",
            edit_widget=NoInputWidget,
            add_widget=NoInputWidget,
            view=False
        ),
        dict(name="status",
            label=_(u"Status"),
             property=schema.Choice(title=_(u"Status"),
                 vocabulary="bungeni.vocabulary.workflow",
            ),
            listing_column=workflow_column("status", "Workflow status"),
            add=False,
            listing=True,
            omit=False
        ),
        dict(name="status_date", 
            add=False, 
            edit=False,
            view=True, 
            listing=True,
            label=_(u"Status date"),
            listing_column=day_column("status_date", _(u"Status date")),
        ),
    ]
    public_wfstates = [af_wf_state[u"public"].id]


class AttachedFileVersionDescriptor(ModelDescriptor):
    display_name = _(u"Attached file version")
    container_name = _(u"Versions")
    fields = deepcopy(AttachedFileDescriptor.fields)


class ParliamentaryItemDescriptor(ModelDescriptor):
    
    parliamentSource = vocabulary.DatabaseSource(domain.Parliament,
        token_field="parliament_id",
        title_field="short_name",
        value_field="parliament_id"
    )
    fields = [
        dict(name="parliamentary_item_id", omit=True),
        dict(name="parliament_id",
            property=schema.Choice(title=_(u"Parliament"),
                source=parliamentSource,
                required=True
            ),
            add=False,
        ),
        dict(name="short_name",
            property=schema.TextLine(title=_(u"Title"), required=True),
            listing=True,
            edit_widget=widgets.LongTextWidget,
            add_widget=widgets.LongTextWidget,
            add=True,
            edit=True,
            omit=False,
        ),
        dict(name="full_name",
            #property=schema.TextLine(title=_(u"Summary"),required=False), 
            listing=False,
            edit_widget=widgets.LongTextWidget,
            add_widget=widgets.LongTextWidget,
            add=True,
            edit=True,
            omit=True
        ),
        dict(name="registry_number",
            property=schema.Int(title=_(u"Registry number"), required=False),
            listing=False,
            add=False,
            edit=True,
        ),
        dict(name="owner_id",
            property=schema.Choice(title=_(u"Moved by"),
                description=_(u"Select the user who moved the document"),
                source=vocabulary.MemberOfParliamentDelegationSource("owner_id"),
            ),
            listing_column=user_name_column("owner_id", _(u"Name"), "owner"),
            listing=True
        ),
        #LanguageField("language"),
        dict(name="language",
            listing=False,
            add=True,
            edit=True,
            omit=False,
            property=schema.Choice(title=_(u"Language"),
                default=get_default_language(),
                vocabulary="language_vocabulary",
                required=True,
            ),
        ),
        dict(name="body_text",
            property=schema.Text(title=_(u"Text"), required=False),
            view_widget=HTMLDisplay,
            edit_widget=RichTextEditor,
            add_widget=RichTextEditor,
        ),
        dict(name="submission_date",
            property=schema.Date(title=_(u"Submission Date"), required=False),
            add=False,
            edit=True,
            view_permission="bungeni.edit.historical",
            edit_permission="bungeni.edit.historical",
            listing=True ,
            edit_widget=DateWidget,
            add_widget=DateWidget,
            omit=False
        ),
        dict(name="status",
            label=_(u"Status"),
            property=schema.Choice(title=_(u"Status"),
                vocabulary="bungeni.vocabulary.workflow",
            ),
            listing_column=workflow_column("status", "Workflow status"),
            add=False,
            listing=True,
            omit=False
        ),
        dict(name="status_date", 
            add=False, 
            edit=False,
            view=True, 
            listing=True,
            label=_(u"Status date"),
            listing_column=day_column("status_date", _(u"Status date")),
        ),
        dict(name="note",
            label=_(u"Notes"),
            description="Recommendation note",
            property=schema.Text(title=_(u"Notes"),
                description=_(u"Recommendation note"), 
                required=False
            ),
            edit=True,
            add=True,
            view=False,
            add_widget=OneTimeEditWidget,
            edit_widget=OneTimeEditWidget,
        ),
        dict(name="receive_notification",
            property=schema.Choice(title=_(u"Receive notification"),
                description=_("Select this option to receive notifications "
                    "for this item"),
                source=vocabulary.YesNoSource
            ),
            edit_widget=CustomRadioWidget,
            add_widget=CustomRadioWidget,
            listing=False,
            omit=False
        ),
        dict(name="type",
            omit=False,
            listing=False,
            edit=False,
            add=False,
            view=False,
        ),
    ]


class VersionDescriptor(ModelDescriptor):
    fields = [
        dict(name="parliamentary_item_id", omit=True),
        dict(name="parliament_id", omit=True),
        dict(name="owner_id", omit=True),
        dict(name="short_name",
            property=schema.TextLine(title=_(u"Title"), required=True),
            edit_widget=widgets.LongTextWidget,
            add_widget=widgets.LongTextWidget,
            listing=True,
            add=True,
            edit=True,
            omit=False,
        ),
        dict(name="full_name",
            property=schema.TextLine(title=_(u"Summary"), required=True),
            listing=False,
            edit_widget=widgets.LongTextWidget,
            add_widget=widgets.LongTextWidget,
            add=True,
            edit=True,
            omit=False,
        ),
        #LanguageField("language"),
        dict(name="language",
            property=schema.Choice(title=_(u"Language"),
                default=get_default_language(),
                vocabulary="language_vocabulary",
            ),
            listing=True,
            add=True,
            edit=False,
            omit=False,
            required=True,
        ),
        dict(name="body_text",
            property=schema.Text(title=_(u"Text")),
            view_widget=HTMLDisplay,
            edit_widget=RichTextEditor,
            add_widget=RichTextEditor,
        ),
        dict(name="submission_date", omit=True),
        dict(name="status", omit=True),
        dict(name="note",
            description="Recommendation note",
            property=schema.Text(title=_(u"Notes"),
                description=_(u"Recommendation note"), 
                required=False
            ),
            edit=True,
            add=True,
            view=False,
            edit_widget=OneTimeEditWidget,
        ),
        dict(name="receive_notification", omit=True),
        dict(name="type", omit=True,),
    ]
    public_wfstates = [version_wf_state[u"archived"].id]


class HeadingDescriptor(ParliamentaryItemDescriptor):
    display_name = _(u"Heading")
    container_name = _(u"Headings")
    fields = deepcopy(ParliamentaryItemDescriptor.fields)
    public_wfstates = [heading_wf_state[u"public"].id]


class AgendaItemDescriptor(ParliamentaryItemDescriptor):
    display_name = _(u"Agenda item")
    container_name = _(u"Agenda items")
    fields = deepcopy(ParliamentaryItemDescriptor.fields)
    fields.extend([
        dict(name="agenda_item_id", omit=True),
        dict(name="group_id", omit=True),
    ])
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
        dict(name="approval_date",
            property=schema.Date(title=_(u"Approval Date"), required=False),
            view_permission="bungeni.edit.historical",
            edit_permission="bungeni.edit.historical",
            add=False,
            listing=False,
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="notice_date",
            property=schema.Date(title=_(u"Notice Date"), required=False),
            add=False,
            edit=False,
            listing=False,
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="motion_number",
            property=schema.Int(title=_(u"Identifier"), required=False),
            add=False,
            edit=False,
            listing=True
        ),
        # TODO omit for now
        dict(name="entered_by", label=_(u"Entered By"), omit=True),
        dict(name="party_id",
            #property = schema.Choice(title=_(u"Political Party"), 
            #   source=vocabulary.MotionPartySource(
            #     title_field="short_name", 
            #     token_field="party_id", 
            #     value_field = "party_id"), 
            #   required=False),
            omit=True
        ),
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
    for field in fields:
        if field["name"] == "body_text":
            field["label"] = _(u"Statement of Purpose")
            field["property"] = schema.Text(title=_(u"Statement of Purpose"),
                required=False)
    
    fields.extend([
        dict(name="bill_id", omit=True),
        dict(name="bill_type_id", 
            property=schema.Choice(title=_(u"Bill Type"),
                source=vocabulary.DatabaseSource(domain.BillType,
                    title_field="bill_type_name",
                    token_field="bill_type_id",
                    value_field="bill_type_id"
                ),
            ),
        ),
        dict(name="ministry_id",
            property=schema.Choice(title=_(u"Ministry"),
                source=vocabulary.MinistrySource("ministry_id"), 
                    required=False
                ),
            listing=False
        ),
        dict(name="identifier",
            property=schema.Text(title=_(u"Identifier"), required=False),
            add=False
        ),
        dict(name="publication_date",
            property=schema.Date(title=_(u"Publication Date"), required=False),
            listing=True,
            add=True,
            edit_widget=DateWidget,
            add_widget=DateWidget ,
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
        dict(name="question_id", omit=True),
        dict(name="question_number",
            property=schema.Int(title=_(u"Question Number"), required=False),
            listing=True, 
            add=False, 
            edit=True
        ),
        dict(name="short_name", omit=True),
        dict(name="supplement_parent_id",
            label=_(u"Initial/supplementary question"),
            view_widget=SupplementaryQuestionDisplay,
            add=False,
            edit=False, 
            view=False
        ),
        dict(name="ministry_id",
            property=schema.Choice(title=_(u"Ministry"),
                source=vocabulary.MinistrySource("ministry_id"), 
                required=True
            ),
            listing_column=ministry_column("ministry_id" , _(u"Ministry")),
            listing=True
        ),
        dict(name="approval_date",
            property=schema.Date(title=_(u"Date approved"), required=False),
            edit_widget=DateWidget,
            add_widget=DateWidget,
            listing=False,
            add=False
        ),
        dict(name="ministry_submit_date",
            property=schema.Date(title=_(u"Submitted to ministry"), 
                required=False
            ),
            edit_widget=DateWidget,
            add_widget=DateWidget,
            listing=False,
            add=False
        ),
        dict(name="question_type",
            property=schema.Choice(title=_(u"Question Type"),
                description=_("Ordinary or Private Notice"),
                vocabulary=vocabulary.QuestionType
            ),
            listing=False
        ),
        dict(name="response_type",
            property=schema.Choice(title=_(u"Response Type"),
                description=_("Oral or Written"),
                vocabulary=vocabulary.ResponseType
            ),
            listing=False
        ),
        dict(name="response_text",
            property=schema.TextLine(title=_(u"Response"),
                description=_(u"Response to the Question"),
                required=False
            ),
            view_widget=HTMLDisplay,
            edit_widget=RichTextEditor,
            edit=True,
            view=True,
            add=False
        ),
        dict(name="sitting_time",
            label=_(u"Sitting Time"),
            listing=False,
            omit=True
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
    
    fields = deepcopy(ParliamentaryItemDescriptor.fields)
    fields.extend([
        dict(name="event_item_id", omit=True),
        dict(name="item_id", omit=True),
        dict(name="event_date",
            property=schema.Datetime(title=_(u"Date"), required=True),
            listing_column=day_column("event_date", _(u"Date")),
            listing=True,
            edit_widget=DateTimeWidget,
            add_widget=DateTimeWidget,
            required=True
        ),
    ])
    public_wfstates = [event_wf_state[u"public"].id]


class TabledDocumentDescriptor(ParliamentaryItemDescriptor):
    display_name = _(u"Tabled document")
    container_name = _(u"Tabled documents")
    fields = deepcopy(ParliamentaryItemDescriptor.fields)
    fields.extend([
        dict(name="tabled_document_id", omit=True),
        dict(name="group_id", omit=True),
        dict(name="tabled_document_number",
            property=schema.Int(title=_(u"Tabled document Number"), 
                required=True
            ),
            add=False,
            listing=False,
            edit=True,
            view=True,
        ),
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
        dict(name="sitting_id", omit=True),
        dict(name="group_id", omit=True),
        LanguageField("language"),
        dict(name="sitting_type_id",
            listing_column=sitting_type_column("sitting_type_id",
                _(u"Sitting Type")
            ),
            property=schema.Choice(title=_(u"Sitting Type"),
                source=vocabulary.SittingTypes(
                    title_field="sitting_type",
                    token_field="sitting_type_id",
                    value_field="sitting_type_id"
                ),
                required=True
            ),
            listing=True
        ),
        dict(name="start_date",
            property=schema.Datetime(title=_(u"Date"), required=True),
            listing_column=date_from_to_column("start_date", _(u"Start")),
            edit_widget=DateTimeWidget,
            add_widget=DateTimeWidget,
            listing=True
        ),
        dict(name="end_date",
            property=schema.Datetime(title=_(u"End"), required=True),
            listing_column=time_column("end_date", _(u"End Date")),
            edit_widget=DateTimeWidget,
            add_widget=DateTimeWidget,
            listing=False
        ),
        dict(name="venue_id",
            property=schema.Choice(title=_(u"Venue"),
                source=vocabulary.DatabaseSource(domain.Venue,
                    title_field="short_name",
                    token_field="venue_id",
                    value_field="venue_id"
                ),
                required=False
            ),
            listing=False,
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


class SittingTypeDescriptor(ModelDescriptor):
    display_name = _(u"Type")
    container_name = _(u"Types")


class SessionDescriptor(ModelDescriptor):
    display_name = _(u"Parliamentary session")
    container_name = _(u"Parliamentary sessions")
    
    fields = [
        dict(name="session_id", omit=True),
        dict(name="parliament_id", omit=True),
        dict(name="short_name",
            property=schema.TextLine(title=_(u"Short Name"), required=True),
            listing=True
        ),
        dict(name="full_name",
            property=schema.TextLine(title=_(u"Full Name"), required=True)
        ),
        dict(name="start_date",
            property=schema.Date(title=_(u"Start Date"), required=True),
            listing=True,
            listing_column=day_column("start_date", _(u"Start Date")),
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="end_date",
            property=schema.Date(title=_(u"End Date"), required=True),
            listing=True,
            listing_column=day_column("end_date", _(u"End Date")),
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        LanguageField("language"),
        dict(name="notes", label=_(u"Notes"), required=False)
    ]
    schema_invariants = [EndAfterStart]
    custom_validators = [validations.validate_date_range_within_parent]


#class DebateDescriptor (ModelDescriptor):
#    display_name = _(u"Debate")
#    container_name = _(u"Debate")

#    fields = [
#        dict(name="sitting_id", omit=True), 
#        dict(name="debate_id", omit=True),
#        dict(name="short_name", 
#                label=_(u"Short Name"), 
#                listing=True,
#                listing_column=name_column("short_name", 
#                    _(u"Name"))), 
#        dict(name="body_text", label=_(u"Transcript"),
#              property = schema.Text(title=u"Transcript"),
#              view_widget=HTMLDisplay,
#              edit_widget=RichTextEditor, 
#              add_widget=RichTextEditor,
#             ),
#        ]


class AttendanceDescriptor(ModelDescriptor):
    display_name = _(u"Sitting attendance")
    container_name = _(u"Sitting attendances")
    
    attendanceVocab = vocabulary.DatabaseSource(
        domain.AttendanceType,
        token_field="attendance_id",
        title_field="attendance_type",
        value_field="attendance_id"
    )
    fields = [
        dict(name="sitting_id", omit=True),
        dict(name="member_id", listing=True,
            property=schema.Choice(title=_(u"Attendance"),
                source=vocabulary.SittingAttendanceSource(
                    title_field="fullname",
                    token_field="user_id",
                    value_field="member_id"
                )
            ),
            listing_column=user_name_column("member_id", _(u"Name"), "user")
        ),
        dict(name="attendance_id",
            property=schema.Choice(title=_(u"Attendance"),
                source=attendanceVocab,
                required=True
            ),
            listing_column=attendance_column("attendance_id", _(u"Attendance")),
            listing=True,
        ),
    ]


class AttendanceTypeDescriptor(ModelDescriptor):
    display_name = _(u"Sitting attendance")
    container_name = _(u"Sitting attendances")
    
    fields = [
        dict(name="attendance_id", omit=True),
        dict(name="attendance_type",
            property=schema.TextLine(title=_(u"Attendance type"), 
                required=True)
            ),
        LanguageField("language"),
    ]


class ConsignatoryDescriptor(ModelDescriptor):
    display_name = _(u"Cosignatory")
    container_name = _(u"Cosignatories")
    
    fields = [
        dict(name="bill_id", omit=True),
        dict(name="user_id",
            property=schema.Choice(title=_(u"Cosignatory"),
                source=vocabulary.MemberOfParliamentDelegationSource("user_id"),
                required=True
            ),
            listing_column=user_name_column("user_id", 
                _(u"Cosignatory"),
                "owner"
            ),
            listing=True,
        ),
    ]


class ConstituencyDescriptor(ModelDescriptor):
    display_name = _(u"Constituency")
    container_name = _(u"Constituencies")
    
    fields = [
        dict(name="constituency_id", omit=True),
        LanguageField("language"),
        dict(name="name",
            property=schema.TextLine(title=_(u"Name"),
                description=_("Name of the constituency"),
                required=True
            ),
            listing=True
        ),
        dict(name="start_date",
            property=schema.Date(title=_(u"Start Date"), required=True),
            listing=True,
            listing_column=day_column("start_date", _(u"Start Date")),
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="end_date",
            property=schema.Date(title=_(u"End Date"), required=False),
            listing=True,
            listing_column=day_column("end_date", _(u"End Date")),
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
    ]
    schema_invariants = [EndAfterStart]


class ProvinceDescriptor(ModelDescriptor):
    display_name = _(u"Province")
    container_name = _(u"Provinces")
    fields = [
        LanguageField("language"),
        dict(name="province_id", omit=True),
        dict(name="province",
            property=schema.TextLine(title=_(u"Province"),
                description=_(u"Name of the Province"),
                required=True
            ),
            listing=True
        ),
    ]


class RegionDescriptor(ModelDescriptor):
    display_name = _(u"Region")
    container_name = _(u"Regions")
    fields = [
        LanguageField("language"),
        dict(name="region_id", omit=True),
        dict(name="region",
            property=schema.TextLine(title=_(u"Region"),
                description=_(u"Name of the Region"),
                required=True
            ),
            listing=True
        ),
    ]


class CountryDescriptor(ModelDescriptor):
    fields = [
        LanguageField("language"),
        dict(name="country_id",
            property=schema.TextLine(title=_(u"Country Code"),
                description=_(u"ISO Code of the  country")
            )
        ),
        dict(name="country_name",
            property=schema.TextLine(title=_(u"Country"),
                description=_(u"Name of the Country")
            ),
            listing=True
        ),
    ]


class ConstituencyDetailDescriptor(ModelDescriptor):
    display_name = _(u"Constituency details")
    container_name = _(u"Details")
    fields = [
        dict(name="constituency_detail_id", omit=True),
        dict(name="constituency_id",
            label=_(u"Name"),
            description=_("Name of the constituency"),
            listing=False,
            omit=True
        ),
        dict(name="date",
            property=schema.Date(title=_(u"Date"),
                description=_("Date the data was submitted from the "
                    "Constituency"),
                required=True
            ),
            listing=True,
            listing_column=day_column("date", "Date"),
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="population",
            property=schema.Int(title=_(u"Population"),
                description=_(u"Total Number of People living in this "
                    "Constituency"),
                required=True
            ),
            listing=True
        ),
        dict(name="voters",
            property=schema.Int(title=_(u"Voters"),
                description=_(u"Number of Voters registered in this "
                    "Constituency"),
                required=True
            ),
            listing=True
        ),
    ]


################
# Hansard
################

class RotaDescriptor(ModelDescriptor):
    fields = [
        dict(name="rota_id", omit=True),
        dict(name="reporter_id", omit=True), #XXX
        dict(name="identifier", title=_("Rota Identifier"), listing=True),
        dict(name="start_date",
            label=_(u"Start Date"),
            listing_column=day_column("start_date", _(u"Start Date")),
            listing=True,
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
        dict(name="end_date",
            label=_(u"End Date"),
            listing_column=day_column("end_date", _(u"End Date")),
            listing=True,
            edit_widget=DateWidget,
            add_widget=DateWidget
        ),
    ]
    schema_invariants = [EndAfterStart]


class DocumentSourceDescriptor(ModelDescriptor):
    display_name = _(u"Document source")
    container_name = _(u"Document sources")
    
    fields = [
        dict(name="document_source_id", omit=True),
        dict(name="document_source", label=_(u"Document Source")),
    ]


class ItemScheduleDescriptor(ModelDescriptor):
    display_name = _(u"Scheduling")
    container_name = _(u"Schedulings")
    
    fields = [
        dict(name="sitting_id", omit=True),
        dict(name="schedule_id", omit=True),
        dict(name="item_id",
            property=schema.Choice(title=_(u"Item"),
                source=vocabulary.DatabaseSource(domain.ParliamentaryItem,
                    token_field="parliamentary_item_id",
                    value_field="parliamentary_item_id",
                    title_getter=lambda obj: "%s - %s" % (
                        type(obj).__name__, obj.short_name)
                )
            ),
            listing=False,
        ),
    ]


class ScheduledItemDiscussionDescriptor(ModelDescriptor):
    display_name = _(u"Discussion")
    container_name = _(u"Discussions")
    
    fields = [
        LanguageField("language"),
        dict(name="schedule_id", omit=True),
        dict(name="body_text", 
            label=_(u"Minutes"),
            property=schema.Text(title=_(u"Minutes")),
            view_widget=HTMLDisplay,
            edit_widget=RichTextEditor,
            add_widget=RichTextEditor,
        ),
        #dict(name="sitting_time", 
        #    label=_(u"Sitting time"), 
        #    description=_(u"The time at which the discussion took place."), 
        #    listing=True
        #),
    ]


class ReportDescriptor(ModelDescriptor):
    display_name = _(u"Report")
    container_name = _(u"Reports")
    
    fields = [
        dict(name="report_id", omit=True),
        #LanguageField("language"),
        dict(name="language",
            label=_(u"Language"),
            listing=False,
            add=True,
            edit=True,
            omit=False,
            required=True,
            view=False,
            property=schema.Choice(title=_(u"Language"),
                default=get_default_language(),
                vocabulary="language_vocabulary",
            ),
        ),
        dict(name="report_type",
            label=_(u"Publications type"),
            listing=True,
            view=False
        ),
        dict(name="start_date",
            label=_(u"Report Start Date"),
            listing_column=day_column("start_date", _(u"Start Date")),
            listing=True,
            edit_widget=DateWidget,
            add_widget=DateWidget,
            view=False
        ),
        dict(name="end_date",
            label=_(u"Report End Date"),
            listing_column=day_column("end_date", _(u"End Date")),
            listing=True,
            edit_widget=DateWidget,
            add_widget=DateWidget,
            view=False
        ),
        dict(name="note",
            label=_(u"Note"),
            listing=True,
            view=False
        ),
        dict(name="body_text",
            label=_(u"Text"),
            property=schema.Text(title=_(u"Text")),
            view_widget=HTMLDisplay,
            edit_widget=RichTextEditor,
            add_widget=RichTextEditor,
        ),
    ]


class Report4SittingDescriptor(ReportDescriptor):
    fields = deepcopy(ReportDescriptor.fields)
    fields.extend([
        dict(name="sitting_report_id", omit=True),
        dict(name="report_id", omit=True),
        dict(name="sitting_id", omit=True),
    ])


