# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Form Schemas for Domain Objects

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.descriptor")

from copy import deepcopy
from zope import schema, interface
from sqlalchemy.sql import expression
import zope.formlib
from zope.i18n import translate
from zc.table import column
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.security.proxy import removeSecurityProxy

from bungeni.alchemist import Session
from bungeni.alchemist.interfaces import IAlchemistContainer
from bungeni.alchemist.model import ModelDescriptor, Field, show, hide

from bungeni.models import domain
import bungeni.models.interfaces
from bungeni.models.utils import get_db_user

# We import bungeni.core.workflows.adapters to ensure that the "states"
# attribute on each "workflow" module is setup... this is to avoid an error
# when importing bungeni.ui.descriptor.descriptor from standalone scripts:
import bungeni.core.workflows.adapters # needed by standalone scripts !+review

#from bungeni.core import translation

from bungeni.ui import widgets
from bungeni.ui.fields import VocabularyTextField
from bungeni.ui import constraints
from bungeni.ui.forms import validations
from bungeni.ui.i18n import _
from bungeni.ui.utils import common, date, debug, url
from bungeni.ui import vocabulary
from bungeni.ui.interfaces import IAdminSectionLayer
from bungeni.utils import misc


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


def localized_datetime_column(name, title, default="",
        category="date", # "date" | "time" | "dateTime"
        length="medium"     # "short" | "medium" | "long" | "full" | None
    ):
    def getter(item, formatter):
        value = getattr(item, name)
        if value:
            request = common.get_request()
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
        request = common.get_request()
        start = getattr(item, "start_date")
        if start:
            start = date.getLocaleFormatter(request,
                "dateTime", format_length).format(start)
        end = getattr(item, "end_date")
        if end:
            end = date.getLocaleFormatter(request,
                "time", format_length).format(end)
        return "%s - %s" % (start, end)
    return column.GetterColumn(title, getter)


def name_column(name, title, default=""):
    def renderer(value, size=50):
        if len(value) > size:
            return "%s..." % value[:size]
        return value
    return _column(name, title, renderer, default)


def combined_name_column(name, title, default=""):
    """An extended name, combining full_name (localized)
    and short_name columns.

    For types that have both a full_name and a short_name attribute:
    Group, ParliamentarySession
    """
    def getter(item, formatter):
        return "%s [%s]" % (_(item.full_name), item.short_name)
    return column.GetterColumn(title, getter)
    
def combined_name_column_filter(query, filter_string, sort_dir_func):
    fs = filter_string.strip().split(" ")
    fc = []
    for fs_ in fs:
        fc.extend([domain.Group.full_name.like("%%%s%%" % fs_),
            domain.Group.short_name.like("%%%s%%" % fs_),]
        )
    return query.filter(expression.or_(*fc)).order_by(
        sort_dir_func(domain.Group.full_name), 
        sort_dir_func(domain.Group.short_name),)      
    

def dc_property_column(name, title, property_name="title"):
    def renderer(value):
        if value:
            return getattr(IDCDescriptiveProperties(value), property_name, "")
        return ""
    return _column(name, title, renderer)

def _get_related_user(item_user, attr):
    """Get the user instance that is related to this item via <attr>,
    or if <attr> is None, return the item_user itself.
    """
    assertion_message = "Item User [%s] may not be None" % (item_user)
    if attr:
        item_user = getattr(item_user, attr, None)
        assertion_message = "Item [%s] may not have None as [%s]" % (
            item_user, attr)
    assert item_user is not None, assertion_message
    return item_user

def user_name_column(name, title, attr):
    # !+FIELD_KEYERROR why cannot use the User.fullname property directly?
    def getter(item_user, formatter):
        item_user = _get_related_user(item_user, attr)
        return item_user.fullname # User.fullname property
    return column.GetterColumn(title, getter)

def user_name_column_filter(query, filter_string, sort_dir_func):
    fs = filter_string.strip().split(" ")
    fc = []
    for fs_ in fs:
        fc.extend([domain.User.first_name.like("%%%s%%" % fs_),
            domain.User.middle_name.like("%%%s%%" % fs_),
            domain.User.last_name.like("%%%s%%" % fs_),]
        )
    return query.join(domain.User).filter(expression.or_(*fc)).order_by(
        sort_dir_func(domain.User.last_name),
        sort_dir_func(domain.User.first_name),
        sort_dir_func(domain.User.middle_name),
    )

def linked_mp_name_column(name, title, attr):
    """This may be used to customize the default URL generated as part of the
    container listing.

    E.g. instead of the URL to the association view between a signatory (MP)
    and a bill:
        /business/bills/obj-169/signatories/obj-1/
    the direct URL for the MP's "home" view is used instead:
        /members/current/obj-55/
    """
    def get_member_of_parliament(user_id):
        """Get the MemberOfParliament instance for user_id."""
        return Session().query(domain.MemberOfParliament).filter(
            domain.MemberOfParliament.user_id == user_id).one()

    def getter(item_user, formatter):
        related_user = _get_related_user(item_user, attr)
        request = common.get_request()
        if IAdminSectionLayer.providedBy(request):
            parent = item_user
            while parent and not IAlchemistContainer.providedBy(parent):
                parent = removeSecurityProxy(parent.__parent__)
            item_user.__parent__ = parent
            href = url.absoluteURL(item_user, request)
        else:
            mp = get_member_of_parliament(related_user.user_id)
            href = "/members/current/obj-%s/" % (mp.membership_id)
        return zope.formlib.widget.renderElement("a",
            contents=related_user.fullname,  # User.fullname derived property
            href=href
        )
    return column.GetterColumn(title, getter)
    
def linked_mp_name_column_filter(query, filter_string, sort_dir_func):
    fs = filter_string.strip().split(" ")
    fc = []
    for fs_ in fs:
        fc.extend([domain.User.first_name.like("%%%s%%" % fs_),
            domain.User.middle_name.like("%%%s%%" % fs_),
            domain.User.last_name.like("%%%s%%" % fs_),]
        )
    return query.join(domain.User).filter(expression.or_(*fc)).order_by(
        sort_dir_func(domain.User.first_name),
        sort_dir_func(domain.User.middle_name),
        sort_dir_func(domain.User.last_name)
    )
    
def user_party_column(name, title, default="-"):
    def getter(item, formatter):
        session = Session()
        mp_obj = session.query(domain.MemberOfParliament).filter(
            domain.MemberOfParliament.user_id==item.user_id
        ).one()
        if mp_obj is not None:
            if mp_obj.party is not None:
                return vocabulary.party.getTerm(mp_obj.party).title
        return default
    return column.GetterColumn(title, getter)


def simple_view_column(name, title, default=_(u"view"), owner_msg=None):
    """Replace primary key with meaningful title - tests for owner.
    """
    def getter(item, formatter):
        if bungeni.models.interfaces.IOwned.providedBy(item):
            if item.owner == get_db_user():
                return owner_msg or default
        return default
    return column.GetterColumn(title, getter)


def member_title_column(name, title, default=""):
    def getter(item, formatter):
        return item.title_type.title_name
    return column.GetterColumn(title, getter)

''' !+UNUSED
def current_titles_in_group_column(name, title, default=""):
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

def inActiveDead_Column(name, title, default):
    aid = { "A": _("active"),
        "I": _("inactive"),
        "D": _("deceased")}
    renderer = lambda x: aid[x]
    return _column(name, title, renderer, default)
'''



def workflow_column(name, title, default=""):
    from bungeni.ui.utils.misc import get_wf_state
    def getter(item, formatter):
        state_title = get_wf_state(item)
        request = common.get_request()
        return translate(
            state_title,
            domain="bungeni",
            context=request)
    return column.GetterColumn(title, getter)


def ministry_column(name, title, default=""):
    def getter(item, formatter):
        # !+TRANSLATE_ATTR(mr, sep-2010)
        #m = item.ministry
        #return translation.translate_attr(m, m.group_id, "short_name")
        return vocabulary.get_translated_group_label(item.ministry)
    return column.GetterColumn(title, getter)

def scheduled_item_title_column(name, title):
    def getter(item, formatter):
        return IDCDescriptiveProperties(item.item).title
    return column.GetterColumn(title, getter)

def scheduled_item_mover_column(name, title):
    def getter(item, formatter):
        if hasattr(item.item, "owner"):
            return IDCDescriptiveProperties(item.item.owner).title
        return ""
    return column.GetterColumn(title, getter)

def scheduled_item_uri_column(name, title):
    def getter(item, formatter):
        return IDCDescriptiveProperties(item.item).uri
    return column.GetterColumn(title, getter)


''' !+TYPES_CUSTOM
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
'''

def vocabulary_column(name, title, vocabulary):
    def getter(context, formatter):
        try:
            return _(vocabulary.getTerm(getattr(context, name)).title)
        except LookupError:
            # !+NONE_LOOKUPERROR(mr, jul-2012) probably a vdex, 
            # and getattr(context, name)...
            value = getattr(context, name)
            m = "LookpError: vocabulary [%s] term value [%s] " \
                "for context [%s.%s]" % (
                    vocabulary, value, context, name)
            # we should only have a LookupError on a None value (and it is not 
            # defined in the vocabulary)
            assert value is None, m
            log.warn(m)
            return None
    return column.GetterColumn(title, getter)
''' !+TYPES_CUSTOM_TRANSLATION(mr, nov-2011) issues with how translation for 
the titles of such enum values should be handled:

- such enum string values probably be considered part of UI (po) as opposed 
to part of the data (translatable object records in the db)?

- there is some "overlap" in, as in some cases, parent object is translatable 
while in others it is not. Probably should auto-detect such enum columns, and 
have them **always & only** auto-translated via UI.
[Possible implementation may make use of view_widget/edit_widget on Field to
autohandle how the str-values of these columns will be translated.]

- small issue with pre-existing msgid's e.g. "Office", translations for which 
are not picked up with _("Office") or equivalent... why?
'''

''' !+TYPES_CUSTOM
from zope.dublincore.interfaces import IDCDescriptiveProperties
def dc_getter(name, title, item_attribute, default=_(u"None")):
    def getter(item, formatter):
        obj = getattr(item, item_attribute)
        return IDCDescriptiveProperties(obj).title
    return column.GetterColumn(title, getter)
'''

def get_field(fields, name):
    return misc.get_keyed_item(fields, name, key="name")
    

####
#  Constraints / Invariants
#

def ElectionAfterStart(obj):
    """Start Date must be after Election Date."""
    if obj.election_date >= obj.start_date:
        raise interface.Invalid(
            _("The life of a parliament must start after its election"),
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
        raise interface.Invalid(_("Check dates: death must follow birth"),
            "date_of_death",
            "date_of_birth"
        )

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
# modes:
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


def LanguageField(name="language", modes="view edit add listing", 
        localizable=[ 
            show("view edit"), 
            hide("listing"), 
        ]
    ):
    # if a different modes param is specified, the localizable param should 
    # also be specified accordingly
    return Field(name=name,
        label=_("Language"),
        modes=modes,
        localizable=localizable,
        property=schema.Choice(title=_("Language"),
            vocabulary="language_vocabulary"
        ),
        add_widget=widgets.LanguageLookupWidget,
    )


def AdmissibleDateField(name="admissible_date"):
    # [sys]
    return Field(name=name,
        modes="view listing",
        localizable=[ show("view listing"), ],
        property=schema.Date(title=_("Admissible Date"), required=False),
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
        Field(name="user_id", # [sys] for linking item in listing
            label="Name",
            modes="view listing",
            localizable=[
                hide("view"),
                show("listing"),
            ],
            listing_column=user_name_column("user_id", _("Name"), None),
        ),
        Field(name="salutation", # [user-req]
            modes="view edit add listing",
            localizable=[ 
                show("view edit add"), 
                show("listing"), 
            ],
            property=schema.TextLine(title=_("Salutation"),
                description=_("e.g. Mr. Mrs, Prof. etc."),
                required=False,
            ),
        ),
        Field(name="title", # [user-req]
            modes="view edit add listing",
            localizable=[ 
                show("view edit add"),
                show("listing"), 
            ],
            property=schema.TextLine(title=_("Title"),
                description=_("e.g. Chief Advisor, etc."),
                required=False,
            ),
        ),
        Field(name="first_name", # [user-req]
            modes="view edit add listing",
            localizable=[ 
                show("view edit"), 
                hide("listing"),
            ],
            property=schema.TextLine(title=_("First Name"))
        ),
        Field(name="middle_name", # [user]
            modes="view edit add listing",
            localizable=[
                show("view edit add"), 
                hide("listing"),
            ],
            property=schema.TextLine(title=_("Middle Name"), required=False)
        ),
        Field(name="last_name", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit"), 
                hide("listing"),
            ],
            property=schema.TextLine(title=_("Last Name"))
        ),
        Field(name="email", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit"), 
                show("listing"),
            ],
            property=schema.TextLine(title=_("Email"),
                description=_("Email address"),
                constraint=constraints.check_email,
            ),
        ),
        Field(name="login", # [user-req]
            modes="view add listing",
            localizable=[
                show("view"),
                hide("listing"),
            ],
            property=schema.TextLine(title=_("Login"),
                description=_("Must contain only letters, numbers, a "
                    "period(.) and underscore (_). Should start with a letter "
                    "and be between 3 and 20 characters long"),
                min_length=3,
                max_length=20,
                constraint=constraints.check_login,
            ),
        ),
        Field(name="_password", # [user-req]
            modes="add",
            property=schema.TextLine(title=_("Initial password")),
        ),
        Field(name="national_id", # [user]
            modes="view edit add listing",
            localizable=[
                show("view edit add"), 
                hide("listing"),
            ],
            property=schema.TextLine(title=_("National Id"), required=False)
        ),
        Field(name="gender", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit"), 
                show("listing"),
            ],
            property=schema.Choice(title=_("Gender"),
                source=vocabulary.gender
            ),
            edit_widget=widgets.CustomRadioWidget,
            add_widget=widgets.CustomRadioWidget
        ),
        Field(name="date_of_birth", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit"), 
                show("listing"),
            ],
            property=schema.Date(title=_("Date of Birth")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="birth_country", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit"), 
                hide("listing"),
            ],
            property=schema.Choice(title=_("Country of Birth"),
                source=vocabulary.country_factory,
            )
        ),
        Field(name="birth_nationality", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit"), 
                hide("listing"),
            ],
            property=schema.Choice(title=_("Nationality at Birth"),
                source=vocabulary.country_factory,
            ),
        ),
        Field(name="current_nationality", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit"), 
                hide("listing"),
            ],
            property=schema.Choice(title=_("Current Nationality"),
                source=vocabulary.country_factory,
            ),
        ),
        Field(name="marital_status", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit add listing"),
            ],
            property=schema.Choice(title=_("Marital Status"),
                source=vocabulary.marital_status,
            ),
            listing_column=vocabulary_column("marital_status",
                "Marital Status",
                vocabulary.marital_status
            ),
        ),
        Field(name="date_of_death", # [user]
            modes="view edit add listing",
            localizable=[
                show("view"),
                hide("add listing"),
            ],
            property=schema.Date(title=_("Date of Death"), required=False),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="image", # [img]
            # !+LISTING_IMG(mr, apr-2011) TypeError, not JSON serializable
            modes="view edit add",
            localizable=[
                show("view edit add"),
            ],
            property=schema.Bytes(title=_("Image"),
                description=_("Picture of the person"),
                required=False
            ),
            view_widget=widgets.ImageDisplayWidget,
            edit_widget=widgets.ImageInputWidget,
        ),
        LanguageField("language"), # [user-req]
        Field(name="description", # [rtf]
            modes="view edit add",
            localizable=[
                show("view edit add"),
            ],
            property=schema.Text(title=_("Biographical notes"),
                required=False
            ),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor
        ),
    ]
    schema_invariants = [DeathBeforeLife]
    custom_validators = [validations.email_validator]


class UserDelegationDescriptor(ModelDescriptor):
    """Delegate rights to act on behalf of that user."""
    order = 3 # top
    localizable = True
    display_name = _("Delegate to user")
    container_name = _("Delegations")
    
    fields = [
        Field(name="delegation_id", # [user-req]
            modes="view edit add listing",
            property=schema.Choice(title=_("User"),
                # !+vocabulary.UserSource ?
                source=vocabulary.DatabaseSource(domain.User,
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id"
                )
            ),
            listing_column=user_name_column("delegation_id", _("User"),
                "delegation"),
            listing_column_filter=user_name_column_filter,
        ),
    ]


class GroupMembershipDescriptor(ModelDescriptor):
    localizable = False
    sort_on = ["user_id"]
    sort_dir = "asc"
    SubstitutionSource = vocabulary.SubstitutionSource(
        token_field="user_id",
        title_field="fullname",
        value_field="user_id"
    )

    fields = [
        Field(name="start_date", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.Date(title=_("Start Date")),
            listing_column=day_column("start_date", _("Start Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="end_date", # [user]
            modes="view edit add listing",
            localizable=[
                show("view add edit listing"),
            ],
            property=schema.Date(title=_("End Date"), required=False),
            listing_column=day_column("end_date", _("End Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="active_p", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("edit"),
                hide("view listing"),
            ],
            property=schema.Bool(title=_("Active"), default=True),
        ),
        LanguageField("language"), # [user-req]
        Field(name="substitution_type", # [user]
            modes="view edit listing",
            localizable=[
                hide("view edit listing"),
            ],
            property=schema.TextLine(
                title=_("Type of Substitution"),
                required=False
            ),
        ),
        Field(name="replaced_id", # [user]
            modes="view edit listing",
            localizable=[
                hide("view edit listing"),
            ],
            property=schema.Choice(
                title=_("Substituted by"),
                source=SubstitutionSource,
                required=False
            ),
        ),
        Field(name="status", label=_("Status"), # [sys]
            modes="view listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Choice(title=_("Status"),
                vocabulary=vocabulary.workflow_vocabulary_factory,
            ),
            listing_column=workflow_column("status", "Workflow status"),
        ),
        Field(name="status_date", label=_("Status date"), # [sys]
            modes="view listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Date(title=_("Status Date"), required=True),
            listing_column=day_column("status_date", _("Status date")),
        ),
        #Field(name="membership_id",
        #    label=_("Roles/Titles"),
        #    modes="",
        #    listing_column=current_titles_in_group_column("membership_id",
        #        _("Roles/Titles")
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


''' !+TYPES_CUSTOM
class MemberElectionTypeDescriptor(ModelDescriptor):
    localizable = False
    display_name = _("Member election type")
    container_name = _("Member election types")

    fields = [
        Field(name="member_election_type_name",
            modes="view edit add listing",
            property=schema.TextLine(title=_("Election Type"))
        ),
        LanguageField("language"), # [user-req]
    ]
'''

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
        Field(name="user_id", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view listing"),
                hide("edit"),
            ],
            property=schema.Choice(title=_("Name"),
                source=vocabulary.MembershipUserSource(
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id"
                )
            ),
            listing_column=user_name_column("user_id", _("Name"), "user"),
            listing_column_filter=user_name_column_filter,
            edit_widget=widgets.AutoCompleteWidget(remote_data=True,
                yui_maxResultsDisplayed=5),
            add_widget=widgets.AutoCompleteWidget(remote_data=True)
        ),
        Field(name="member_election_type", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.Choice(title=_("Election Type"),
                source=vocabulary.member_election_type
            ),
            listing_column=vocabulary_column("member_election_type",
                "Election Type",
                vocabulary.member_election_type
            ),
        ),
        Field(name="election_nomination_date", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit"),
                hide("listing")
            ],
            property=schema.Date(title=_("Election/Nomination Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        Field(name="representation", # [user]
            modes="view edit add listing",
            localizable=[ 
                show("view edit add"),
                hide("listing"),
            ],
            property=VocabularyTextField(title=_("Representation"),
                description=_("Select Representation"),
                vocabulary=vocabulary.representation,
                required=False,
            ),
            edit_widget=widgets.TreeVocabularyWidget,
            add_widget=widgets.TreeVocabularyWidget,
            view_widget=widgets.TermsDisplayWidget,
        ),
        Field(name="party", # [user-req]
            modes="view edit add listing",
            localizable=[ 
                show("view edit listing"), 
            ],
            property=schema.Choice(title=_("Political Party"),
                source=vocabulary.party,
            ),
            listing_column=vocabulary_column("party",
                "Political Party",
                vocabulary.party
            ),
        ),
        Field(name="leave_reason", # [user]
            modes="view edit add listing",
            localizable=[
                show("view edit add"),
                hide("listing")
            ],
            property=schema.Text(title=_("Leave Reason"), required=False)
        ),
        Field(name="notes", # [rtf]
            modes="view edit add",
            localizable=[
                show("view edit add"),
            ],
            property=schema.Text(title=_("Notes"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor
        ),
    ])

    schema_invariants = GroupMembershipDescriptor.schema_invariants + [
       MpStartBeforeElection]


class PoliticalGroupMemberDescriptor(GroupMembershipDescriptor):
    """Membership of a user in a political group."""
    localizable = True
    display_name = _("member")
    container_name = _("members")

    fields = [
        Field(name="user_id", # [user-req]
            modes="view add listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Choice(title=_("Name"),
                source=vocabulary.MemberOfParliamentSource("user_id",)
            ),
            listing_column=linked_mp_name_column("user_id", _("Name"), "user"),
            listing_column_filter=linked_mp_name_column_filter,
            view_widget=widgets.MemberURLDisplayWidget,
            add_widget=widgets.AutoCompleteWidget(remote_data=True),
            edit_widget=widgets.AutoCompleteWidget(remote_data=True)
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        Field(name="notes", # [rtf]
            modes="view edit add",
            localizable=[
                show("view edit add"),
            ],
            property=schema.Text(title=_("Notes"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
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
        Field(name="full_name", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit"),
                hide("listing"),
            ],
            property=schema.TextLine(title=_("Full Name")),
            #listing_column=name_column("full_name", _("Full Name"))
        ),
        Field(name="short_name", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit"),
                hide("listing"),
            ],
            property=schema.TextLine(title=_("Short Name")),
            #listing_column=name_column("short_name", _("Name"))
        ),
        Field(name="acronym", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit"),
                hide("listing"),
            ],
            property=schema.TextLine(title=_("Acronym"), required=False),
            #listing_column=name_column("short_name", _("Name"))
        ),
        Field(name="combined_name", # [derived]
            modes="listing",
            localizable=[
                show("listing"),
            ],
            property=schema.TextLine(title=_combined_name_title),
            listing_column=combined_name_column("full_name",
                _combined_name_title),
            listing_column_filter=combined_name_column_filter,
        ),
        LanguageField("language"), # [user-req]
        Field(name="description", # [rtf]
            modes="view edit add",
            localizable=[
                show("view edit add"),
            ],
            property=schema.Text(title=_("Description") , required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
        Field(name="start_date", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.Date(title=_("Start Date")),
            listing_column=day_column("start_date", _("Start Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="end_date",
            modes="view edit add listing", # [user]
            localizable=[
                show("view edit add listing"),
            ],
            property=schema.Date(title=_("End Date"), required=False),
            listing_column=day_column("end_date", _("End Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="status", label=_("Status"), # [sys]
            modes="view listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Choice(title=_("Status"),
                vocabulary=vocabulary.workflow_vocabulary_factory,
            ),
            listing_column=workflow_column("status", "Workflow status"),
        ),
    ]
    schema_invariants = [EndAfterStart]
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
        Field(name="full_name", # [user-req]
            description=_("Parliament name"),
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.TextLine(title=_("Name")),
            listing_column=name_column("full_name", "Name"),
        ),
        Field(name="short_name", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.TextLine(title=_("Short Name"),
                description=_("Shorter name for the parliament"),
            ),
        ),
        Field(name="identifier", # [user-req]
            modes="view edit add",
            localizable=[
                show("view edit"),
            ],
            property=schema.TextLine(title=_("Parliament Identifier"),
                description=_("Unique identifier or number for this Parliament"),
                required=False
            ),
        ),
        LanguageField("language"), # [user-req]
        Field(name="description", # [rtf]
            modes="view edit add",
            localizable=[
                show("view edit add"),
            ],
            property=schema.Text(title=_("Description"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
        Field(name="election_date",
            property=schema.Date(title=_("Election Date"),
                description=_("Date of the election"),
            ),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="start_date", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.Date(title=_("In power from"),
                description=_("Date of the swearing in"),
            ),
            listing_column=day_column("start_date", _("In power from")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="end_date", # [user]
            modes="view edit add listing",
            localizable=[
                show("view edit add listing"),
            ],
            property=schema.Date(title=_("In power till"),
                description=_("Date of the dissolution"),
                required=False
            ),
            listing_column=day_column("end_date", _("In power till")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
    ]
    schema_invariants = [
        EndAfterStart,
        ElectionAfterStart
    ]
    custom_validators = [validations.validate_parliament_dates]


''' !+TYPES_CUSTOM
class CommitteeTypeStatusDescriptor(ModelDescriptor):
    localizable = False
    display_name = _("Committee type status")
    container_name = _("Committee type statuses")

    fields = [
        Field(name="committee_type_status_name",
            modes="view edit add listing",
            property=schema.TextLine(title=_("Committee type status"))
        ),
        LanguageField("language"), # [user-req]
    ]

class CommitteeTypeDescriptor(ModelDescriptor):
    localizable = False
    display_name = _("Committee type")
    container_name = _("Committee types")
    
    fields = [
        Field(name="committee_type", # [user-req]
            modes="view edit add listing",
            property=schema.TextLine(title=_("Committee Type"))
        ),
        Field(name="description", # [user-req]
            modes="view edit add listing",
            property=schema.Text(title=_("description"))
        ),
        Field(name="life_span", # [user-req]
            modes="view edit add listing",
            property = schema.TextLine(title=_("life span"))
        ),
        Field(name="committee_type_status_id", # [user-req]
            modes="view edit add listing",
            property=schema.Choice(title=_("Status"),
                source=vocabulary.CommitteeTypeStatus
            ),
            listing_column = dc_getter("committee_type_status_id",
                _("Status"), "committee_type_status"
            )
        ),
        LanguageField("language"), # [user-req]
    ]
'''

class CommitteeDescriptor(GroupDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("committees")
    localizable = True
    display_name = _("Profile")
    container_name = _("Committees")
    
    fields = deepcopy(GroupDescriptor.fields)
    get_field(fields, "start_date").localizable = [
        show("view edit"),
        hide("listing")
    ]
    get_field(fields, "end_date").localizable = [
        show("view edit add"),
        hide("listing")
    ]
    
    fields.extend([
        Field(name="identifier", # [user-req]
            modes="view edit add",
            localizable=[
                show("view edit"),
            ],
            property=schema.TextLine(title=_("Committee Identifier"),
                description=_("Unique identifier or number for this Committee"),
                required=False
            ),
        ),
        Field(name="sub_type", # [user-req]
            modes="view edit add listing",
            localizable=[ 
                show("view edit listing"), 
            ],
            property=schema.Choice(title=_("Committee Type"),
                source=vocabulary.committee_type,
            ),
            listing_column=vocabulary_column("sub_type",
                "Committee Type",
                vocabulary.committee_type
            ),
        ),
        Field(name="group_continuity", # [user-req]
            modes="view edit add listing",
            localizable=[ 
                show("view edit listing"), 
            ],
            property=schema.Choice(title=_("Committee Status Type"),
                source=vocabulary.committee_continuity,
            ),
            listing_column=vocabulary_column("group_continuity",
                "Committee Status Type",
                vocabulary.committee_continuity
            ),
        ),
        Field(name="num_members", # [user]
            modes="view edit add listing",
            localizable=[
                show("view edit add"),
                hide("listing")
            ],
            property=schema.Int(title=_("Number of members"), required=False),
        ),
        Field(name="min_num_members", # [user]
            modes="view edit add listing",
            localizable=[
                show("view edit add"),
                hide("listing")
            ],
            property=schema.Int(title=_("Minimum Number of Members"),
                required=False
            )
        ),
        Field(name="quorum", # [user]
            modes="view edit add listing",
            localizable=[
                show("view edit add"),
                hide("listing")
            ],
            property=schema.Int(title=_("Quorum"), required=False)
        ),
        Field(name="num_clerks", # [user]
            modes="view edit add listing",
            localizable=[
                show("view edit add"),
                hide("listing")
            ],
            property=schema.Int(title=_("Number of clerks"), required=False)
        ),
        Field(name="num_researchers", # [user]
            modes="view edit add listing",
            localizable=[
                show("view edit add"),
                hide("listing")
            ],
            property=schema.Int(title=_("Number of researchers"),
                required=False
            )
        ),
        Field(name="proportional_representation", # [user]
            modes="view edit add listing",
            localizable=[
                show("view edit add"),
                hide("listing")
            ],
            property=schema.Bool(title=_("Proportional representation"),
                default=True,
                required=False
            )
        ),
        Field(name="reinstatement_date", # [user]
            modes="view edit add listing",
            localizable=[
                show("view edit add"),
                hide("listing")
            ],
            property=schema.Date(title=_("Reinstatement Date"),
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
    custom_validators = [validations.validate_date_range_within_parent]


class CommitteeMemberDescriptor(GroupMembershipDescriptor):
    localizable = True
    display_name = _("Member")
    container_name = _("Members")

    fields = [
        Field(name="user_id", # [user-req]
            modes="view add listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Choice(title=_("Name"),
                source=vocabulary.MemberOfParliamentSource("user_id")
            ),
            listing_column=user_name_column("user_id", _("Name"), "user"),
            listing_column_filter=user_name_column_filter,
            add_widget = widgets.AutoCompleteWidget(remote_data=True),
            edit_widget = widgets.AutoCompleteWidget(remote_data=True)
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        Field(name="notes", # [rtf]
            modes="view edit add",
            localizable=[
                show("view edit add"),
            ],
            property=schema.TextLine(title=_("Notes"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
    ])

''' !+TYPES_CUSTOM
class AddressTypeDescriptor(ModelDescriptor):
    localizable = False
    display_name = _("Address type")
    container_name = _("Address types")

    fields = [
        Field(name="address_type_name", # [user-req]
            modes="view edit add listing",
            property=schema.TextLine(title=_("Address Type"))
        ),
        LanguageField("language"), # [user-req]
    ]

class PostalAddressTypeDescriptor(ModelDescriptor):
    localizable = False
    display_name = _("Postal address type")
    container_name = _("Postal address types")

    fields = [
        Field(name="postal_address_type_name",
            modes="view edit add listing",
            property=schema.TextLine(title=_("Postal address type name"))
        ),
        LanguageField("language"), # [user-req]
    ]
'''

class AddressDescriptor(ModelDescriptor):
    localizable = False
    display_name = _("Address")
    container_name = _("Addresses")

    fields = [
        Field(name="logical_address_type", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"), 
            ],
            # !+i18n(mr, nov-2011) shouldn't title be translated later?
            property=schema.Choice(title=_("Address Type"),
                source=vocabulary.logical_address_type,
            ),
            listing_column=vocabulary_column("logical_address_type", 
                "Address Type",
                vocabulary.logical_address_type
            ),
        ),
        Field(name="postal_address_type", # [user-req]
            modes="view edit add listing",
            localizable=[ 
                show("view edit listing"), 
            ],
            property=schema.Choice(title=_("Postal Address Type"),
                source=vocabulary.postal_address_type,
            ),
        ),
        Field(name="street", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit"),
                hide("listing"),
            ],
            property=schema.Text(title=_("Street"), required=True),
            edit_widget=zope.formlib.widgets.TextAreaWidget,
            add_widget=zope.formlib.widgets.TextAreaWidget,
        ),
        Field(name="city", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.TextLine(title=_("City"), required=True)
        ),
        Field(name="zipcode", # [user-req]
            label=_("Zip Code"),
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
        ),
        Field(name="country_id", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.Choice(title=_("Country"),
                source=vocabulary.country_factory,
                required=True
            ),
        ),
        Field(name="phone", # [user]
            modes="view edit add listing",
            localizable=[
                show("view edit add listing"),
            ],
            property=schema.Text(title=_("Phone Number(s)"),
                description=_("Enter one phone number per line"),
                required=False
            ),
            edit_widget=zope.formlib.widgets.TextAreaWidget,
            add_widget=zope.formlib.widgets.TextAreaWidget,
            #view_widget=zope.formlib.widgets.ListDisplayWidget,
        ),
        Field(name="fax", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit add listing"),
            ],
            property=schema.Text(title=_("Fax Number(s)"),
                description=_("Enter one fax number per line"),
                required=False
            ),
            edit_widget=zope.formlib.widgets.TextAreaWidget,
            add_widget=zope.formlib.widgets.TextAreaWidget,
        ),
        Field(name="email", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit add listing"),
            ],
            property=schema.TextLine(title=_("Email"),
                description=_("Email address"),
                constraint=constraints.check_email,
                required=False
            ),
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
        Field(name="title_name",
            modes="view edit add listing",
            property=schema.TextLine(title=_("Name"),
                description=_("Name"),
                required=True,
            ),
        ),
        Field(name="role_id", label=_("Role associated with title"),
            modes="view edit add listing",
            property=schema.Choice(title=_("Role"),
                description=_("Role associated with this title"),
                vocabulary=vocabulary.group_sub_role_factory,
                required=False,
            ),
        ),
        Field(name="user_unique",
            modes="view edit add listing",
            property=schema.Choice(title=_("Only one user may have this title"), 
                description=_("Limits persons with this title to one"),
                default=False,
                source=vocabulary.bool_yes_no
            ),
        ),
        Field(name="sort_order",
            modes="view edit add listing",
            property=schema.Int(title=_("Sort Order"), 
                description=_("The order in which members with this title "
                    "will appear relative to other members"),
                required=True
            ),
        ),
        LanguageField("language"), # [user-req]
    ]
    #custom_validators = [ validations.validate_sub_role_unique ]
class MemberTitleDescriptor(ModelDescriptor):
    localizable = True
    display_name = _("Title")
    container_name = _("Titles")

    fields = [
        Field(name="title_type_id", label=_("Title"),
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.Choice(title=_("Title"),
                source=vocabulary.TitleTypes(),
                ),
            listing_column=member_title_column("title_name", _("Title")),
        ),
        Field(name="start_date", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.Date(title=_("Start Date"), required=True),
            listing_column=day_column("start_date", _("Start Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="end_date", # [user]
            modes="view edit add listing",
            localizable=[
                show("view edit add listing"),
            ],
            property=schema.Date(title=_("End Date"), required=False),
            listing_column=day_column("end_date", _("End Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        LanguageField("language"), # [user-req]
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
    localizable = True
    display_name = _("Staff")
    container_name = _("Staff")

    fields = [
        Field(name="user_id", # [user-req]
            modes="view add listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Choice(title=_("Name"),
                source=vocabulary.UserNotMPSource(
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id"
                )
            ),
            listing_column=user_name_column("user_id", _("Name"), "user"),
            listing_column_filter=user_name_column_filter,
            add_widget=widgets.AutoCompleteWidget(remote_data=True),
            edit_widget=widgets.AutoCompleteWidget(remote_data=True)
        ),
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        Field(name="notes", # [rtf]
            modes="view edit add",
            localizable=[
                show("view edit add"),
            ],
            property=schema.Text(title=_("Notes"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
    ])


class PoliticalGroupDescriptor(GroupDescriptor):
    order = _ORDER_BY_CONTAINER_NAMES.index("politicalgroups")
    localizable = True
    display_name = _("political group")
    container_name = _("political groups")
    
    fields = deepcopy(GroupDescriptor.fields)
    fields.extend([
        Field(
            name="identifier", # [user-req]
            modes="view edit add",
            localizable=[
                show("view edit"),
            ],
            property=schema.TextLine(title=_("Identifier"),
                description=_("Unique identifier or number for this political group"),
                required=False
            )
        ),
        Field(name="logo_data", # [img]
            modes="view edit add",
            localizable=[
                show("view edit add"),
            ],
            property=schema.Bytes(title=_("Logo"), required=False),
            view_widget=widgets.ImageDisplayWidget,
            edit_widget=widgets.ImageInputWidget
        ),
    ])
    schema_invariants = [EndAfterStart]
    custom_validators = [validations.validate_date_range_within_parent]


class OfficeDescriptor(GroupDescriptor):
    order = 2 # top
    localizable = True
    display_name = _("Office")
    container_name = _("Offices")
    
    fields = [
        Field(name="identifier", # [user-req]
            modes="view edit add",
            localizable=[
                show("view edit"),
            ],
            property=schema.TextLine(title=_("Office Identifier"),
                description=_("Unique identifier or number for this Office"),
                required=False
            ),
        ),
        Field(name="office_role", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.Choice(title=_("Role"),
                description=_("Role given to members of this office"),
                vocabulary=vocabulary.office_role_factory
            ),
        )
    ]
    fields.extend(deepcopy(GroupDescriptor.fields))
    custom_validators = [validations.validate_date_range_within_parent]


class OfficeMemberDescriptor(GroupMembershipDescriptor):
    localizable = True
    display_name = _("Office Member")
    container_name = _("Office Members")
    
    fields = [
        Field(name="user_id", # [user-req]
            modes="view add listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Choice(title=_("Name"),
                source=vocabulary.UserNotMPSource(
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id"
                )
            ),
            listing_column=user_name_column("user_id", _("Name"), "user"),
            listing_column_filter=user_name_column_filter,
            add_widget=widgets.AutoCompleteWidget(remote_data=True),
            edit_widget=widgets.AutoCompleteWidget(remote_data=True)
        )
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        Field(name="notes", # [user]
            modes="view edit add listing",
            localizable=[
                show("view edit add listing"),
            ],
            property=schema.Text(title=_("Notes"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
    ])


class MinistryDescriptor(GroupDescriptor):
    localizable = True
    display_name = _("Ministry")
    container_name = _("Ministries")

    fields = deepcopy(GroupDescriptor.fields)
    fields.extend([
        Field(name="identifier", # [user-req]
            modes="view edit add",
            localizable=[
                show("view edit"),
            ],
            property=schema.TextLine(title=_("Ministry Identifier"),
                description=_("Unique identifier or number for this Ministry")
            ),
        ),
    ])
    schema_invariants = [EndAfterStart]
    custom_validators = [validations.validate_date_range_within_parent]


class MinisterDescriptor(GroupMembershipDescriptor):
    localizable = True
    display_name = _("Minister")
    container_name = _("Ministers")

    fields = [
        Field(name="user_id", # [user-req]
            modes="view add listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Choice(title=_("Name"),
                source=vocabulary.UserSource(
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id"
                )
            ),
            listing_column=user_name_column("user_id", _("Name"), "user"),
            listing_column_filter=user_name_column_filter,
            add_widget = widgets.AutoCompleteWidget(remote_data=True),
            edit_widget = widgets.AutoCompleteWidget(remote_data=True)
        )
    ]
    fields.extend(deepcopy(GroupMembershipDescriptor.fields))
    fields.extend([
        Field(name="notes", # [img]
            modes="view edit add",
            localizable=[
                show("view edit add"),
            ],
            property=schema.Text(title=_("Notes"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
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
        Field(name="identifier", # [user-req]
            modes="view edit add",
            localizable=[
                show("view edit"),
            ],
            property=schema.TextLine(title=_("Government Identifier"),
                description=_("Unique identifier or number for this Government"),
                required=False
            ),
        ),
    ])
    schema_invariants = [EndAfterStart]
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
        Field(name="type", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.Choice(title=_("Attachment Type"),
                source=vocabulary.attachment_type,
            ),
            listing_column=vocabulary_column("type", 
                "File Type",
                vocabulary.attachment_type,
            ),
        ),
        Field(name="title", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.TextLine(title=_("Title")),
            edit_widget=widgets.TextWidget,
            add_widget=widgets.TextWidget,
        ),
        Field(name="description", # [rtf]
            modes="view edit add",
            localizable=[
                show("view edit add"),
            ],
            property=schema.Text(title=_("Description"), required=False),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
        Field(name="data", # [file]
            modes="view edit add",
            localizable=[
                show("view edit"),
            ],
            property=schema.Bytes(title=_("File")),
            description=_("Upload a file"),
            edit_widget=widgets.FileEditWidget,
            add_widget=widgets.FileAddWidget,
            view_widget=widgets.FileDisplayWidget,
        ),
        Field(name="name", label="", # [user-req]
            modes="edit add",
            edit_widget=widgets.NoInputWidget,
            add_widget=widgets.NoInputWidget,
        ),
        Field(name="mimetype", label="", # [user-req]
            modes="edit add",
            edit_widget=widgets.NoInputWidget,
            add_widget=widgets.NoInputWidget,
        ),
        Field(name="status", label=_("Status"), # [user-req]
            modes="view listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Choice(title=_("Status"),
                vocabulary=vocabulary.workflow_vocabulary_factory,
            ),
            listing_column=workflow_column("status", "Workflow status"),
        ),
        Field(name="status_date", label=_("Status date"), # [sys]
            modes="view listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Date(title=_("Status date"), required=False),
            listing_column=day_column("status_date", _("Status date")),
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
        Field(name="submission_date", # [derived]
            modes="view listing",
            localizable=[ 
                show("view"),
                hide("listing")
            ],
            property=schema.Date(title=_("Submission Date"), required=False),
            listing_column=day_column("submission_date", _("Submission Date")),
        ),
        #   admissible_date
        # owner
        # signatories
        # attachments
        # events
        # doc_id
        Field(name="parliament_id", # [sys]
            modes="view listing",
            localizable=[ hide("view listing"), ],
            property=schema.Choice(title=_("Parliament"),
                source=vocabulary.DatabaseSource(domain.Parliament,
                    token_field="parliament_id",
                    title_field="short_name", # !+ GROUP_DOC
                    value_field="parliament_id"
                ),
            ),
        ),
        Field(name="owner_id", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("edit"),
                hide("view listing", "bungeni.Anonymous"),
            ],
            property=schema.Choice(title=_("Moved by"),
                description=_("Select the user who moved the document"),
                # "legal" parliamentary documents may only be moved by an MP
                source=vocabulary.MemberOfParliamentDelegationSource("owner_id"),
            ),
            listing_column=linked_mp_name_column("owner_id", _("Name"), "owner"),
            listing_column_filter=linked_mp_name_column_filter,
            add_widget=widgets.MemberDropDownWidget,
            view_widget=widgets.MemberURLDisplayWidget,
        ),
        # type
        Field(name="doc_type", # [user-req]
            modes="view edit add listing",
            localizable=[ 
                show("view edit listing"), 
            ],
            property=schema.Choice(title=_("Document Type"),
                source=vocabulary.doc_type,
            ),
            listing_column=vocabulary_column("doc_type",
                "Document Type",
                vocabulary.doc_type
            ),
        ),
        # doc_procedure
        Field(name="type_number", # [sys]
            modes="view listing",
            localizable=[ 
                show("view listing"),
            ],
            property=schema.Int(title=_("Number"), required=False),
        ),
        Field(name="registry_number", # [user]
            modes="view edit listing",
            localizable=[
                show("view"),
                hide("edit listing"),
            ],
            property=schema.Int(title=_("Registry number"), required=False),
        ),
        Field(name="uri", # [user]
            modes="view edit listing",
            localizable=[ 
                show("view edit"), 
                hide("listing"), 
            ],
            property=schema.Text(title=_("URI"), required=False),
        ),
        Field(name="acronym",
            modes="view edit add listing",
            localizable=[
                show("view edit add"),
                hide("listing"),
            ],
        ),
        Field(name="title", # [user]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.TextLine(title=_("Title"), required=True),
            edit_widget=widgets.LongTextWidget,
            add_widget=widgets.LongTextWidget,
        ),
        Field(name="description",
            modes="view edit add listing",
            localizable=[
                show("view edit add"),
                hide("listing"),
            ],
        ),
        LanguageField("language"), # [user-req]
        Field(name="body", # [rtf]
            modes="view edit add",
            localizable=[ show("view"), ],
            property=schema.Text(title=_("Text")),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
        Field(name="status", label=_("Status"), # [sys]
            modes="view listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Choice(title=_("Status"),
                vocabulary=vocabulary.workflow_vocabulary_factory,
            ),
            listing_column=workflow_column("status", "Workflow status"),
        ),
        Field(name="status_date", label=_("Status date"), # [sys]
            modes="view listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Date(title=_("Status Date"), required=False),
            listing_column=day_column("status_date", _("Status date")),
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
        Field(name="timestamp", # [sys]
            modes="edit",
            localizable=[ show("edit"), ],
            property=schema.Datetime(title=_(""), required=False),
            edit_widget=widgets.HiddenTimestampWidget,
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
                value_field="user_id")
        )
        # !+f.localizable changing localizable modes AFTER Field is initialized
        # gives mismatch error when descriptors are (re-)loaded, e.g. 
        #f.localizable = [ hide("view edit add listing"), ]
        f.listing_column = user_name_column("owner_id", _("Name"), "owner")
        f.listing_column_filter = listing_column_filter=user_name_column_filter
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
        listing_column=vocabulary_column("event_type",
            "Event Type",
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
            property=schema.Choice(title=_("User"), 
                source=vocabulary.UserSource(
                    token_field="user_id",
                    title_field="fullname",
                    value_field="user_id")),
            view_widget=None,
            listing_column=user_name_column("user_id", _("Name"), "user"),
            listing_column_filter=user_name_column_filter,
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
            listing_column=datetime_column("date_audit", "Date Audit"),
        ),
        Field(name="date_active", # [user]
            modes="view listing",
            localizable=[ show("view listing"), ],
            property=schema.Date(title=u"Active Date", required=True),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget,
            listing_column=datetime_column("date_active", "Date Active"),
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

''' !+TYPES_CUSTOM
class BillTypeDescriptor(ModelDescriptor):
    localizable = False
    display_name = _("Bill Type")
    container_name = _("Bill types")

    fields = [
        Field(name="bill_type_name", # [user-req]
            modes="view edit add listing",
            localizable=[ 
                show("view edit listing"), 
            ],
            property=schema.TextLine(title=_("Bill Type"))
        ),
        LanguageField(name="language"),
    ]
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
            listing_column=vocabulary_column("doc_type",
                "Bill Type",
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
        ),
        Field(name="publication_date", # [user]
            modes="view listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Date(title=_("Publication Date"), required=False),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget ,
            listing_column=day_column("publication_date", "Publication Date"),
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

''' !+TYPES_CUSTOM
class QuestionTypeDescriptor(ModelDescriptor):
    localizable = False
    display_name = _("Question type")
    container_name = _("Question types")

    fields = [
        Field(name="question_type_name",
            modes="view edit add listing",
            property=schema.TextLine(title=_("Question Type"))
        ),
        LanguageField("language"),
    ]

class ResponseTypeDescriptor(ModelDescriptor):
    localizable = False
    display_name = _("Response type")
    container_name = _("Response types")

    fields = [
        Field(name="response_type_name",
            modes="view edit add listing",
            property=schema.TextLine(title=_("Response Type"))
        ),
        LanguageField("language"),
    ]
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
            listing_column=ministry_column("ministry_id" , _("Ministry")),
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
            listing_column=vocabulary_column("doc_type",
                "Question Type",
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
            listing_column=vocabulary_column("response_type",
                "Response Type",
                vocabulary.response_type
            ),
        ),
        Field(name="response_text", # [user-req]
            modes="edit",
            property=schema.Text(title=_("Response"),
                description=_("Response to the Question"),
                required=False
            ),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
        ),
        Field(name="subject", # [user]
            modes="view edit add listing",
            localizable=[ 
                show("view edit add"),
                hide("listing"),
            ],
            property=VocabularyTextField(title=_("Subject Terms"),
                description=_("Select Subjects"),
                vocabulary=vocabulary.subject_terms,
                required = False,
            ),
            edit_widget=widgets.TreeVocabularyWidget,
            add_widget=widgets.TreeVocabularyWidget,
            view_widget=widgets.TermsDisplayWidget,
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
            listing_column=date_from_to_column("start_date", _("Start")),
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
            listing_column=dc_property_column("venue", _(u"Venue")),
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
    schema_invariants = [EndAfterStart]
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
        Field(name="start_date", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.Date(title=_("Start Date")),
            listing_column=day_column("start_date", _("Start Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="end_date", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.Date(title=_("End Date")),
            listing_column=day_column("end_date", _("End Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        LanguageField("language"),
        Field(name="notes", label=_("Notes"), # [rtf]
            modes="view edit add",
            localizable=[
                show("view edit add"),
            ],
        )
    ]
    schema_invariants = [EndAfterStart]
    custom_validators = [validations.validate_date_range_within_parent]


#class DebateDescriptor (ModelDescriptor):
#    display_name = _("Debate")
#    container_name = _("Debate")

#    fields = [
#        Field(name="sitting_id", modes=""),
#        Field(name="debate_id", modes=""),
#        Field(name="short_name",
#                label=_("Short Name"),
#                modes="view edit add listing",
#                listing_column=name_column("short_name",
#                    _("Name"))),
#        Field(name="body_text", label=_("Transcript"),
#              property = schema.Text(title="Transcript"),
#              view_widget=widgets.HTMLDisplay,
#              edit_widget=widgets.RichTextEditor,
#              add_widget=widgets.RichTextEditor,
#             ),
#        ]


class SittingAttendanceDescriptor(ModelDescriptor):
    localizable = True
    display_name = _("Sitting attendance")
    container_name = _("Sitting attendances")
    sort_on = ["member_id"]
    fields = [
        Field(name="member_id", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.Choice(title=_("Member of Parliament"),
                source=vocabulary.SittingAttendanceSource(
                    token_field="user_id",
                    title_field="fullname",
                    value_field="member_id"
                )
            ),
            listing_column=user_name_column("member_id", _("Name"), "user"),
            listing_column_filter=user_name_column_filter,
        ),
        Field(name="attendance_type", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.Choice(title=_("Attendance"),
                source=vocabulary.attendance_type,
            ),
            listing_column=vocabulary_column("attendance_type",
                "Attendance",
                vocabulary.attendance_type
            ),
        ),
    ]


''' !+TYPES_CUSTOM
class AttendanceTypeDescriptor(ModelDescriptor):
    localizable = False
    display_name = _("Attendance types")
    container_name = _("Attendance types")
    fields = [
        Field(name="attendance_type", # [user-req]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.TextLine(title=_("Attendance type"))
        ),
       LanguageField("language"),
    ]
'''

class SignatoryDescriptor(ModelDescriptor):
    localizable = True
    display_name = _("Signatory")
    container_name = _("Signatories")
    fields = [
        Field(name="signatory_id",
            modes="listing",
            localizable = [show("listing", "bungeni.Signatory bungeni.Owner")],
            property = schema.TextLine(title=_("View")),
            listing_column = simple_view_column("signatory_id", 
                _(u"review"), _(u"view"), _(u"review")
            ),
        ),
        Field(name="user_id", # [user-req]
            modes="view add listing",
            localizable=[
                show("view listing"),
            ],
            property=schema.Choice(title=_("Signatory"),
                source=vocabulary.MemberOfParliamentSignatorySource(
                    "user_id"
                ),
            ),
            listing_column=linked_mp_name_column("user_id",
                _("Signatory"),
                "user"
            ),
            listing_column_filter=linked_mp_name_column_filter,
            view_widget=widgets.MemberURLDisplayWidget,
            add_widget=widgets.AutoCompleteWidget(remote_data=True),
            edit_widget=widgets.AutoCompleteWidget(remote_data=True)
        ),
        Field(name="political_party",
            modes="listing",
            property=schema.TextLine(title=_(u"political party")),
            listing_column=user_party_column("political_party",
                _(u"political party"), _(u"no party")
            )
        ),
        Field(name="status",
            modes="view listing",
            localizable = [
                show("view listing", 
                    "bungeni.Signatory bungeni.Owner bungeni.Clerk")
            ],
            property=schema.Choice(title=_("Signature status"), 
                vocabulary=vocabulary.workflow_vocabulary_factory,
                required=True
            ),
            listing_column = workflow_column("status", "Signature Status"),
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


################
# Hansard
################

''' !+UNUSED_Rota(mr, feb-2011)
class RotaDescriptor(ModelDescriptor):
    fields = [
        # !+ Field(name="reporter_id") ??
        Field(name="identifier",
            modes="view edit add listing",
        ), # !+ title=_("Rota Identifier"),
        Field(name="start_date",
            modes="view edit add listing",
            label=_("Start Date"),
            listing_column=day_column("start_date", _("Start Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
        Field(name="end_date",
            modes="view edit add listing",
            label=_("End Date"),
            listing_column=day_column("end_date", _("End Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget
        ),
    ]
    schema_invariants = [EndAfterStart]
'''

''' !+UNUSED_DocumentSource(mr, feb-2011)
class DocumentSourceDescriptor(ModelDescriptor):
    display_name = _("Document source")
    container_name = _("Document sources")

    fields = [
        Field(name="document_source", label=_("Document Source")),
    ]
'''

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
            listing_column = scheduled_item_title_column("title", _(u"Title"))
        ),
        Field(name="item_mover", # [derived]
            modes="view listing",
            localizable=[
                show("view listing")
            ],
            property=schema.TextLine(title=_("Mover"), required=False),
            listing_column = scheduled_item_mover_column("mover", _(u"Mover"))
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
            listing_column=scheduled_item_uri_column("uri", _(u"Item URI"))
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
        Field(name="text", 
            modes="view edit add listing",
            localizable=[
                show("view edit add listing")
            ],
            property=schema.Text(title=_(u"Text")),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
        LanguageField("language")
    ]

class ItemScheduleDiscussionDescriptor(ModelDescriptor):
    localizable = True
    display_name = _("Discussion")
    container_name = _("Discussions")
    
    fields = [
        LanguageField("language"),
        Field(name="body", label=_("Minutes"), # [rtf]
            modes="view edit add listing",
            localizable=[
                show("view edit listing"),
            ],
            property=schema.Text(title=_("Minutes")),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
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
            listing_column=datetime_column("status_date", _("Published Date")),
            edit_widget=widgets.DateWidget,
            add_widget=widgets.DateWidget,
        ),
        Field(name="body", label=_("Text"), # [rtf]
            modes="view edit add",
            localizable=[
                show("view edit"),
            ],
            property=schema.Text(title=_("Text")),
            view_widget=widgets.HTMLDisplay,
            edit_widget=widgets.RichTextEditor,
            add_widget=widgets.RichTextEditor,
        ),
    ]
    default_field_order = [ f.name for f in fields ]


class Report4SittingDescriptor(ReportDescriptor):
    localizable = True
    fields = deepcopy(ReportDescriptor.fields)


