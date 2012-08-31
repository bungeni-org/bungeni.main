# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Support for UI Form Fields descriptions in listing mode

The API of the utilities:

    column listing formatter factory
        naming convention: name ends with "_column"
        params: name, title, vocabulary=None

    column listing filter:
        naming convention: name ends with "_column_filter"
        params: query, filter_string, sort_dir_func, column=None
    !+ make filter functions here also factories, to close in field names, etc.


$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.descriptor.listing")


from sqlalchemy.sql import expression, func
from sqlalchemy.exc import ArgumentError

from zope.i18n import translate
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.security.proxy import removeSecurityProxy
import zope.formlib
from zc.table import column

from bungeni.alchemist import Session
from bungeni.alchemist.interfaces import IAlchemistContainer
from bungeni.models import domain
from bungeni.models.utils import get_db_user, get_member_of_parliament
from bungeni.models.interfaces import IOwned, IScheduleText
from bungeni.ui.interfaces import IWorkspaceSectionLayer, IAdminSectionLayer
from bungeni.ui import vocabulary
from bungeni.ui.utils import common, date, url
from bungeni.ui.i18n import _


# support utils 

def _column(name, title, renderer):
    def getter(item, formatter):
        value = getattr(item, name)
        if value:
            return renderer(value)
        return ""
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

def _localized_datetime_column(name, title,
        category="date",    # "date" | "time" | "dateTime"
        length="medium"     # "short" | "medium" | "long" | "full" | None
    ):
    def getter(item, formatter):
        value = getattr(item, name)
        if value:
            request = common.get_request()
            date_formatter = date.getLocaleFormatter(request, category, length)
            return date_formatter.format(value)
        return ""
    return column.GetterColumn(title, getter)

def _get_related_user(item_user, attr):
    """Get the user instance that is related to this item via <attr>,
    or if <attr> is None, return the item_user itself.
    """
    assert item_user is not None, \
        "Item [%s] may not be None" % (item_user)
    related_user = getattr(item_user, attr, None)
    assert related_user is not None, \
        "Item [%s] may not have None as [%s]" % (item_user, attr)
    return related_user

def get_mapper_property_name_for_fk(name_id):
    # mapper property naming convention -- the mapper property on a type for 
    # the instance that is related to the type via the underlying fk column 
    # must be same as the fk column name but without the final "_id".
    assert name_id.endswith("_id"), \
        "related_user_name_column name=%r does not end with %r" % (name_id, "_id")
    return name_id[:-len("_id")]

# column listings & filters

def date_column(name, title, vocabulary=None):
    return _localized_datetime_column(name, title, "date", "medium")

def datetime_column(name, title, vocabulary=None):
    return _localized_datetime_column(name, title, "dateTime", "medium")
#def time_column(name, title, default=""):
#    return localized_datetime_column(name, title, default, "time", "long")


def date_from_to_column(name, title, vocabulary=None):
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


# !+bungeni_custom a long_text_in_listings_truncate_at parameter?
def truncatable_name_column(name, title, vocabulary=None, truncate_at=50):
    def renderer(value):
        if len(value) > truncate_at:
            return "%s..." % value[:truncate_at]
        return value
    return _column(name, title, renderer)


# !+ rename User.fullname to "combined_name"
# !+ mv combined_name_column to a property Group.combined_name, merge...
def user_name_column(name, title, vocabulary=None):
    def getter(user, formatter):
        return user.fullname # User.fullname property
    return column.GetterColumn(title, getter)

def combined_name_column(name, title, vocabulary=None):
    """An extended name, combining full_name (localized)
    and short_name columns.
    
    For types that have both a full_name and a short_name attribute:
    Group, ParliamentarySession
    """
    def getter(item, formatter):
        return "%s [%s]" % (_(item.full_name), item.short_name)
    return column.GetterColumn(title, getter)

def combined_name_column_filter(query, filter_string, sort_dir_func, column=None):
    return _multi_attrs_column_filter(
        [domain.Group.full_name, domain.Group.short_name],
        query, filter_string, sort_dir_func)


def dc_property_column(name, title, vocabulary=None, property_name="title"):
    def renderer(value):
        if value:
            return getattr(IDCDescriptiveProperties(value), property_name, "")
        return ""
    return _column(name, title, renderer)


# !+related_user_name_column - should also link to mp/user? Merge with linked_mp_name_column?
def related_user_name_column(name, title, vocabulary=None):
    related_user_attribute_name = get_mapper_property_name_for_fk(name)
    # !+FIELD_KEYERROR why cannot use the User.fullname property directly?
    def getter(item_user, formatter):
        item_user = _get_related_user(item_user, related_user_attribute_name)
        return item_user.fullname # User.fullname property
    return column.GetterColumn(title, getter)

def related_user_name_column_filter(query, filter_string, sort_dir_func, column=None):
    try: 
        query = query.join(domain.User)
    except ArgumentError, e:
        # !+domain.UserDelegation fails on join, cause of 2 fk rels to User.
        # But, it does not *need* the join... or else it needs to be more 
        # specific, something like (for which we would need to close field 
        # name and maybe other info into this filter function):
        #   query.join( 
        #       (domain.User, domain.UserDelegation.delegation_id == domain.User.user_id) 
        #   )
        # We log, and ignore...
        log.warn("related_user_name_column_filter: %s -- QUERY:\n%s", e, query)
    return _multi_attrs_column_filter(
        [domain.User.last_name, domain.User.first_name, domain.User.middle_name],
        query, filter_string, sort_dir_func)


def user_listing_name_column_filter(query, filter_string, sort_dir_func,
        column=None):
    return _multi_attrs_column_filter(
        [domain.User.last_name, domain.User.first_name, domain.User.middle_name],
        query, filter_string, sort_dir_func)

def linked_mp_name_column(name, title, vocabulary=None):
    """This may be used to customize the default URL generated as part of the
    container listing.

    E.g. instead of the URL to the association view between a signatory (MP)
    and a bill:
        /business/bills/obj-169/signatories/obj-1/
    the direct URL for the MP's "home" view is used instead:
        /members/current/obj-55/
    """
    related_user_attribute_name = get_mapper_property_name_for_fk(name)
    def getter(item_user, formatter):
        related_user = _get_related_user(item_user, related_user_attribute_name)
        request = common.get_request()
        # !+ replace with: bungeni.ui.widgets._render_link_to_mp_or_user ?
        if IAdminSectionLayer.providedBy(request):
            # under admin, we link to the natural "view" of the schema relation
            parent = item_user
            while parent and not IAlchemistContainer.providedBy(parent):
                parent = removeSecurityProxy(parent.__parent__)
            item_user.__parent__ = parent
            href = url.absoluteURL(item_user, request)
        else:
            # else we link direct to the MP's "public" view
            mp = get_member_of_parliament(related_user.user_id)
            href = "/members/current/obj-%s/" % (mp.membership_id)
        return zope.formlib.widget.renderElement("a",
            contents=related_user.fullname,  # User.fullname derived property
            href=href
        )
    return column.GetterColumn(title, getter)


def workflow_column(name, title, vocabulary=None):
    from bungeni.ui.utils.misc import get_wf_state
    def getter(item, formatter):
        state_title = get_wf_state(item)
        request = common.get_request()
        state_title = translate(state_title, domain="bungeni", context=request)
        # !+MY_LISTING_ROWS(mr, aug-2012) the following is a (exploratory) 
        # mechanism to add a distinction between what rows are owned by the 
        # current user and others. Here it is added only to "status" columns
        # here, but a generic "row-level" means to mark such rows as different 
        # from the others may be a useful feature.
        if IWorkspaceSectionLayer.providedBy(request) and IOwned.providedBy(item):
            # !+delegation?
            if item.owner == get_db_user():
                state_title = "<b>%s</b> *" % (state_title)
        return state_title
    return column.GetterColumn(title, getter)


def ministry_column(name, title, default=""):
    def getter(item, formatter):
        # !+TRANSLATE_ATTR(mr, sep-2010)
        #m = item.ministry
        #return translation.translate_attr(m, m.group_id, "short_name")
        return vocabulary.get_translated_group_label(item.ministry)
    return column.GetterColumn(title, getter)

def ministry_column_filter(query, filter_string, sort_dir_func,
                                 column=None):
    query = query.join(domain.Ministry)
    return _multi_attrs_column_filter(
        [domain.Ministry.full_name, domain.Ministry.short_name],
        query, filter_string, sort_dir_func)

def scheduled_item_title_column(name, title):
    def getter(item, formatter):
        dc = IDCDescriptiveProperties(item.item)
        return (dc.description if (IScheduleText.providedBy(item.item) and
            dc.description) else dc.title
        )
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


def vocabulary_column(name, title, vocabulary=None):
    if isinstance(vocabulary, basestring): # !+tmp
        from zope.component import getUtility
        from zope.schema.interfaces import IVocabularyFactory
        vocabulary = getUtility(IVocabularyFactory, vocabulary)
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
        except AttributeError:
            # !+bungeni.ui.vocabulary.SpecializedSource -> GroupTitleTypesFactory
            from bungeni.ui.vocabulary import GroupTitleTypesFactory
            assert isinstance(vocabulary, GroupTitleTypesFactory)
            return context.title_type.title_name
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


