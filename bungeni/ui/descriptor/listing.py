# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Support for UI Form Fields descriptions in listing mode

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.descriptor.listing")


from sqlalchemy.sql import expression, func

from zope.i18n import translate
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.security.proxy import removeSecurityProxy
import zope.formlib
from zc.table import column

from bungeni.alchemist import Session
from bungeni.alchemist.interfaces import IAlchemistContainer
from bungeni.models import domain
from bungeni.models.utils import get_db_user
from bungeni.models.interfaces import IOwned, IScheduleText
from bungeni.ui.interfaces import IAdminSectionLayer
from bungeni.ui import vocabulary
from bungeni.ui.utils import common, date, url
from bungeni.ui.i18n import _


def _column(name, title, renderer, default=""):
    def getter(item, formatter):
        value = getattr(item, name)
        if value:
            return renderer(value)
        return default
    return column.GetterColumn(title, getter)

def _multi_attrs_column_filter(instrumented_attributes,
        query, filter_string, sort_dir_func
    ):
    """Generic column query filter logic, applied to the list of the specified 
    columns for this domain type.
    
    instrumented_attributes:[sqlalchemy.orm.attributes.InstrumentedAttribute]
    query:sqlalchemy.orm.query.Query
    filter_string:str
        space-separated value to filter the column on
    sort_dir_func:callable(sqlalchemy.orm.attributes.InstrumentedAttribute)
        the sqlalchemy sort expression desc or asc
    """
    filter_strings = filter_string.lower().split()
    for fs in filter_strings:
        query = query.filter(
            expression.or_( *[
                func.lower(attr).like("%%%s%%" % fs) 
                for attr in instrumented_attributes ]
            ))
    return query.order_by( 
        *[ sort_dir_func(attr) for attr in instrumented_attributes ])


def localized_datetime_column(name, title, default="",
        category="date",    # "date" | "time" | "dateTime"
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
    return _multi_attrs_column_filter(
        [domain.Group.full_name, domain.Group.short_name],
        query, filter_string, sort_dir_func)


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
    query = query.join(domain.User)
    return _multi_attrs_column_filter(
        [domain.User.last_name, domain.User.first_name, domain.User.middle_name],
        query, filter_string, sort_dir_func)


def user_listing_name_column_filter(query, filter_string, sort_dir_func):
    return _multi_attrs_column_filter(
        [domain.User.last_name, domain.User.first_name, domain.User.middle_name],
        query, filter_string, sort_dir_func)


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
    query = query.join(domain.User)
    return _multi_attrs_column_filter(
        [domain.User.first_name, domain.User.middle_name, domain.User.last_name],
        query, filter_string, sort_dir_func)


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
        if IOwned.providedBy(item):
            if item.owner == get_db_user():
                return owner_msg or default
        return default
    return column.GetterColumn(title, getter)


def member_title_column(name, title, default=""):
    def getter(item, formatter):
        return item.title_type.title_name
    return column.GetterColumn(title, getter)


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
        dc = IDCDescriptiveProperties(item.item)
        return dc.description if IScheduleText.providedBy(item.item) else dc.title
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

