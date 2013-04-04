log = __import__("logging").getLogger("bungeni.ui.container")

import datetime
import simplejson
import sqlalchemy.sql.expression as sql
from sqlalchemy import types, orm, Date, cast

from ore import yuiwidget

from zope.security import proxy, checkPermission
from zope.publisher.browser import BrowserPage
from zope.schema.interfaces import IText, IDate, IDatetime
from zc.resourcelibrary import need
from zope.app.pagetemplate import ViewPageTemplateFile
from bungeni.alchemist import utils
from bungeni.alchemist import container
from bungeni.alchemist.interfaces import IAlchemistContainer

from bungeni.models import interfaces as mfaces
from bungeni.models import domain

from bungeni.core.workflows.utils import view_permission
from bungeni.core import translation

from bungeni.ui import interfaces as ufaces
from bungeni.ui.utils import url, date
from bungeni.ui import cookies
from bungeni.ui import browser
from bungeni.utils import register
from bungeni.capi import capi


def query_iterator(query, parent):
    """Generator of the items in a query.
    
    Checks if the user has view permission on the objects """
    for item in query:
        item.__parent__ = parent
        if checkPermission(view_permission(item), item):
            yield item


def query_filter_date_range(context, request, query, domain_model):
    """Add date range filter to query:
    - if the model has start & end dates, constrain the query to objects
      appearing within those dates.
    - else (archive section) pick off start/end date from the request's cookies
    - else try getting a display date off request
    """
    if (
            (ufaces.IBusinessSectionLayer.providedBy(request) and (
                mfaces.ICommitteeContainer.providedBy(context) or
                mfaces.ICommitteeMemberContainer.providedBy(context) or
                mfaces.ICommitteeStaffContainer.providedBy(context))
            ) or
            (ufaces.IMembersSectionLayer.providedBy(request) and
                mfaces.IMemberOfParliamentContainer.providedBy(context))
        ):
        start_date, end_date = datetime.date.today(), None
    elif ufaces.IArchiveSectionLayer.providedBy(request):
        start_date, end_date = cookies.get_date_range(request)
    else:
        start_date, end_date = date.getDisplayDate(request), None

    ''' !+DATERANGEFILTER(mr, dec-2010) disabled until intention is understood
    if not start_date and not end_date:
        return query
    elif not start_date:
        start_date = datetime.date(1900, 1, 1)
    elif not end_date:
        end_date = datetime.date(2100, 1, 1)

    date_range_filter = component.getSiteManager().adapters.lookup(
        (interface.implementedBy(domain_model),), mfaces.IDateRangeFilter)
    if date_range_filter is not None:
        query = query.filter(date_range_filter(domain_model)).params(
            start_date=start_date, end_date=end_date)
    '''
    return query


def get_date_strings(date_string):
    date_str = date_string.strip()
    start_date, end_date = None, None
    dates = date_str.split("->")
    if date_str.startswith("->"):
        end_date = dates[1]
    elif date_str.endswith("->"):
        start_date = dates[0]
    elif len(date_str.split("->")) == 2:
        start_date = dates[0]
        end_date = dates[1]
    return start_date, end_date


def string_to_date(date_str):
    date = None
    if date_str:
        try:
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            log.error("The string %s does not conform to the format required" %
                      date_str)
    return date

class AjaxContainerListing(
        container.ContainerListing,
        browser.BungeniBrowserView
    ):
    """Container listing as an HTML Page.
    """
    formatter_factory = yuiwidget.ContainerDataTableFormatter

    template = ViewPageTemplateFile("templates/generic-container.pt")
    
    def __call__(self):
        need("yui-datatable")
        self.update()
        return self.template()
    
    @property
    def form_name(self):
        dm = self.context.domain_model
        try:
            return utils.get_descriptor(dm).container_name
        except KeyError:
            return dm.__name__
    
    @property
    def prefix(self):
        return "container_contents"
    
    @property
    def formatter(self):
        context = proxy.removeSecurityProxy(self.context)
        formatter = self.formatter_factory(
            context,
            self.request,
            (),
            prefix=self.prefix,
            columns=self.columns
        )
        formatter.cssClasses["table"] = "listing"
        formatter.table_id = "datacontents"
        return formatter


class ContainerJSONBrowserView(BrowserPage):
    """Base BrowserView Container listing as a JSON AJAX callback.
    """
    permission = None

    def __init__(self, context, request):
        super(ContainerJSONBrowserView, self).__init__(context, request)
        self.domain_model = proxy.removeSecurityProxy(
            self.context).domain_model
        ti = capi.get_type_info(self.domain_model)
        derived_table_schema = ti.derived_table_schema
        self.domain_annotation = ti.descriptor_model
        self.fields = tuple(container.getFields(
            self.context, derived_table_schema, self.domain_annotation))
        # table keys
        self.table = orm.class_mapper(self.domain_model).mapped_table
        self.utk = dict(
            [ (column.key, column) for column in self.table.columns ])
        
        # sort_on defaults: [str]
        self.defaults_sort_on = getattr(self.domain_annotation, "sort_on", None)
        # sort_on parameter name: str
        # pick off request, if necessary setting it from the first name
        # defined in defaults_sort_on
        if not self.request.get("sort") and self.defaults_sort_on:
            self.request.form["sort"] = u"sort_%s" % (self.defaults_sort_on[0])
        self.sort_on = request.get("sort")
        # sort_dir: "desc" | "asc"
        # pick off request, if necessary setting it from default in
        # domain model, else "desc"
        if not self.request.get("dir"):
            self.request.form["dir"] = unicode(
                getattr(self.domain_annotation, "sort_dir", "desc"))
        self.sort_dir = self.request.get("dir")
        _sort_dir_funcs = dict(asc=sql.asc, desc=sql.desc)
        self.sort_dir_func = _sort_dir_funcs.get(self.sort_dir, sql.desc)

# !+VIEW_PERMISSION(miano, nov 2012) These two views are defined to be public
# but they only list items that the user has permission to view
# ideally the should not be registered on IAlchemistContainer but
# per container type with the appropriate permissions


@register.view(IAlchemistContainer, name="jsontableheaders",
    protect=register.PROTECT_VIEW_PUBLIC)
class ContainerJSONTableHeaders(ContainerJSONBrowserView):
    def __call__(self):
        return simplejson.dumps([
            dict(name=field.__name__, title=field.title)
            for field in self.fields
        ])


@register.view(IAlchemistContainer, name="jsonlisting",
    protect=register.PROTECT_VIEW_PUBLIC)
class ContainerJSONListing(ContainerJSONBrowserView):
    """Paging, batching, sorting, json contents of a container.
    """

    filter_property_fields = []

    def string_listing_filter(self, 
            query, filter_string, sort_dir_func, column
        ):
        filter_strings = filter_string.lower().split()
        attr = getattr(self.domain_model, column)
        for fs in filter_strings:
            query = query.filter(
                sql.or_(sql.func.lower(attr).like("%%%s%%" % fs)))
        return query.order_by(sort_dir_func(attr))

    def exact_string_listing_filter(self, 
            query, filter_string, sort_dir_func, column
        ):
        attr = getattr(self.domain_model, column)
        query = query.filter(attr == filter_string)
        return query.order_by(sort_dir_func(attr))

    def date_listing_filter(self, query, filter_string, sort_dir_func, column):
        """
        query: sqlalchemy query
        filter_str: string with dates to filter on
        sort_dir_func: desc or asc
        column: date column to filter on.
        """
        attr = getattr(self.domain_model, column)
        start_date_str, end_date_str = get_date_strings(filter_string)
        start_date = string_to_date(start_date_str)
        end_date = string_to_date(end_date_str)
        if start_date:
            query = query.filter(cast(attr, Date) >= start_date)
        if end_date:
            query = query.filter(cast(attr, Date) <= end_date)
        return query.order_by(sort_dir_func(attr))

    def get_filter(self):
        """ () -> str
        """
        utk = self.utk
        filter_queries = []
        for field in self.fields:
            fn = field.__name__  # field name
            column, kls = None, None
            if fn in utk:
                column = utk[fn]
                kls = column.type.__class__
            ff_name = "filter_%s" % (fn)  # field filter name
            ff = self.request.get(ff_name, "").strip()  # field filter
            if not ff:
                # no filtering on this field
                continue
            # OK, add filter for this column...
            md_field = self.domain_annotation.get(fn)  # model descriptor field
            if md_field and md_field.listing_column_filter:
                filter_queries.append((md_field.listing_column_filter,
                                       [ff, None]))
            else:
                # no md_field.listing_column_filter (or md_field)
                if fn in utk:
                    # !+sqlalchemy.types.Unicode inherits from types.String
                    if kls in (types.String, types.Unicode):
                        filter_queries.append(
                            (self.string_listing_filter, [ff, fn]))
                    elif kls in (types.Date, types.DateTime):
                        filter_queries.append(
                            (self.date_listing_filter, [ff, fn]))
                    else:
                        filter_queries.append(
                            (self.exact_string_listing_filter, [ff, fn]))
                else:
                    self.filter_property_fields.append(fn)
        return filter_queries

    def get_sort_keys(self):
        """ server side sort,
        @web_parameter sort - request variable for sort column
        @web_parameter dir - sort direction, only once acceptable value "desc"
        """
        sort_on_keys = []
        # first process user specified values
        sort_on = self.sort_on
        if sort_on:
            sort_on = sort_on[5:]
            md_field = self.domain_annotation.get(sort_on) #model descriptor field
            if md_field and sort_on in self.utk:
                sort_on_keys.append(sort_on)

        # second, process model defaults
        if self.defaults_sort_on:
            for dso in self.defaults_sort_on:
                if dso not in sort_on_keys:
                    sort_on_keys.append(dso)
        return sort_on_keys
    
    #!+SQLAlchemy(miano, Aug 2012) This should be removed once we upgrade to
    # sqlalchemy 0.7 and take advantage of Hybrid Properties
    def filter_batch_on_properties(self, batch):
        reverse = True if (self.sort_dir == "desc") else False
        if self.sort_on in self.filter_property_fields:
            sort_on = self.sort_on[5:]
            if sort_on not in self.utk:
                batch.sort(key=lambda x: getattr(x, sort_on),
                           reverse=reverse)
        for field_name in self.filter_property_fields:
            md_field = self.domain_annotation.get(field_name)
            ff_name = "filter_%s" % (field_name)
            ff = self.request.get(ff_name, None)
            if ff and md_field:
                if (IDate.providedBy(md_field.property) or
                    IDatetime.providedBy(md_field.property)):
                    start_date_str, end_date_str = get_date_strings(ff)
                    start_date = string_to_date(start_date_str)
                    end_date = string_to_date(end_date_str)
                    if start_date:
                        batch = [x for x in batch if (
                                getattr(x, field_name) and
                                getattr(x, field_name).date() >= start_date)
                                 ]
                    if end_date:
                        batch = [x for x in batch if (
                                getattr(x, field_name) and
                                getattr(x, field_name).date() <= end_date)
                                 ]
                elif IText.providedBy(md_field.property):
                    batch = [x for x in batch
                             if ff in getattr(x, field_name)]
        return batch

    def get_offsets(self, default_start=0,
            default_limit=capi.default_number_of_listing_items
        ):
        start = self.request.get("start", default_start)
        limit = self.request.get("limit", default_limit)
        try:
            start, limit = int(start), int(limit)
            if start < 0:
                start = default_start
            if limit <= 0:
                limit = default_limit
        except ValueError:
            start, limit = default_start, default_limit
        return start, limit
    
    def translate_objects(self, nodes, lang=None):
        """Translate container items if context domain is translatable
        """
        if not mfaces.ITranslatable.implementedBy(self.domain_model):
            return nodes
        # !+ lang should always be valid here... make not optional, assert?
        if lang is None:
            lang = translation.get_request_language(request=self.request)
        return [ translation.translate_obj(node, lang) for node in nodes ]

    def _json_values(self, nodes):
        """
        filter values from the nodes to respresent in json, currently
        that means some footwork around, probably better as another
        set of adapters.
        """
        def get_listing_column_getters():
            # dict of (descriptor) field getters by name, for fast lookup
            getters = dict([
                (f.name, getattr(f.listing_column, "getter",
                    lambda n, field: field.query(n)))
                for f in self.domain_annotation.fields
            ])
            return getters
        listing_column_getters = get_listing_column_getters()
        values = []
        for node in nodes:
            d = {}
            for field in self.fields:
                fn = field.__name__
                d[fn] = listing_column_getters[fn](node, field)
                # !+i18n_DATE(mr, sep-2010) two problems with the isinstance
                # tests below:
                # a) they seem to always fail (no field values of this type?)
                # b) this is incorrect way to localize dates
                v = d[fn]
                if isinstance(v, datetime.datetime):
                    d[fn] = v.strftime("%F %I:%M %p")
                elif isinstance(v, datetime.date):
                    d[fn] = v.strftime("%F")
            
            d["object_id"] = url.set_url_context(container.stringKey(node))
            values.append(d)
        return values

    def query_add_filters(self, query):
        """Sub classes can add filters to the query by overriding this method
        """
        return query

    # !+BATCH(mr, sep-2010) this method (plus other support methods here)
    # replaces the combined logic in:
    #   - alchemist.ui.container.ContainerJSONListing.getBatch()
    #   - bungeni.alchemist.container.AlchemistContainer.batch()
    def get_batch(self, start, limit):
        """Get the data instances for this batch.
        """
        context = proxy.removeSecurityProxy(self.context)
        query = context._query
        # date_range filter (try from: model, then cookie, then request)
        query = query_filter_date_range(context, self.request, query,
            self.domain_model)
        sort_on_expressions = []
        # other filters
        lc_filter_queries = self.get_filter()
        sort_on_keys = self.get_sort_keys()
        if sort_on_keys:
            for sort_on in sort_on_keys:
                md_field = self.domain_annotation.get(sort_on)
                if md_field:
                    if not md_field.listing_column_filter:
                        pass
                        #continue
                        #!+SORTING(mb, Mar-2013) why does sorting need a filter?
                else:
                    # check domain model if this if field is not in descriptor
                    if not hasattr(self.domain_model, sort_on):
                        continue
                sort_on_expressions.append(
                    self.sort_dir_func(
                        getattr(self.domain_model, sort_on)))
        for lc_filter_query, params in lc_filter_queries:
            filter_string = params[0]
            column_name = params[1]
            query = lc_filter_query(query, filter_string, self.sort_dir_func, column_name)
        if sort_on_expressions:
            query = query.order_by(*sort_on_expressions)
        #add optional filters, used by sub classes
        query = self.query_add_filters(query)
        # get total number of items before applying an offset and limit
        self.set_size = query.count()
        # offset and limit
        query = query.offset(start).limit(limit)
        # bungeni.alchemist.container.AlchemistContainer.batch()
        # nodes: [<bungeni.models.domain.Question]
        # !+STRING_KEY_FILE_VERSION + no permission "bungeni.attachment_version.View"!
        return [
            container.contained(ob, self, container.stringKey(ob))
            for ob in query_iterator(query, self.context)
        ]


    def json_batch(self, start, limit, lang):
        batch = self.get_batch(start, limit)
        batch = self.filter_batch_on_properties(batch)
        batch = self.translate_objects(batch, lang) # translate
        batch = self._json_values(batch) # serialize to json
        data = dict(
            length=self.set_size, # total result set length, set in get_batch()
            start=start,
            recordsReturned=len(batch), # batch length
            sort=self.sort_on,
            dir=self.sort_dir,
            nodes=batch
        )
        return simplejson.dumps(data)

    def __call__(self):
        # prepare required parameters
        start, limit = self.get_offsets()  # ? start=0&limit=25
        lang = translation.get_request_language(request=self.request)
        return self.json_batch(start, limit, lang)


@register.view(IAlchemistContainer, name="jsonlisting-raw",
    protect=register.PROTECT_VIEW_PUBLIC)
class ContainerJSONListingRaw(ContainerJSONListing):
    """JSON listing for a container with no formatting.
    Skip passing through descriptor listing column renderers.
    """
    def _json_values(self, nodes):
        """Return nodes as JSON"""
        values = []
        for node in nodes:
            d = {}
            for field in self.fields:
                fn = field.__name__
                d[fn] = getattr(node, fn, None)
                v = d[fn]
                if isinstance(v, datetime.datetime):
                    d[fn] = v.strftime("%F %I:%M %p")
                elif isinstance(v, datetime.date):
                    d[fn] = v.strftime("%F")

            d["object_id"] = url.set_url_context(container.stringKey(node))
            values.append(d)
        return values



# caches for json container listings

import evoque.collection

class JSLCache(object):
    """JSON Listing Cache"""
    def __init__(self, max_size, model_interface, invalidating_class_names):
        """ max_size:int - max number of items to cache, 0 implies unlimited,
                oldest in excess of max are discarded
            model_interface: interface domain model for this listing
            invalidating_class_names:[str] - names of domain classes that 
                when modified will invalidate this cache
            
            @descriptor: descriptor instance for domain model for this listing
            @filter_params: [name:str] - query string filter parameter names
        """
        self.cache = evoque.collection.Cache(max_size)
        self.model_interface = model_interface
        self._descriptor = None
        self._filter_params = None
        # !+CACHE_INVALIDATION(mr, sep-2010) this should be left open-ended?
        # sanity check -- ensure every specified (domain) class_name exists
        for icn in invalidating_class_names:
            assert getattr(domain, icn), "No such domain class: %s" % (icn)
        self.invalidating_class_names = invalidating_class_names
        # dynamically build the incoming (request querystring) filter 
        # parameter names lists from the domain class descriptor
    
    @property
    def descriptor(self):
        """Get (cached) descriptor instance for self.model_interface.
        """
        if self._descriptor is None:
            self._descriptor = utils.get_descriptor(self.model_interface)
        return self._descriptor
    
    @property
    def filter_params(self):
        """Get (cached) list of filter params for this model's listing columns.
        """
        if self._filter_params is None:
            self._filter_params = [ "filter_%s" % (field_name)
                for field_name in self.descriptor.listing_columns ]
        return self._filter_params
    
    def clear(self):
        # !+ self.cache.clear()
        self.cache.cache.clear()
        self.cache.order[:] = []


JSLCaches = {
    #"addresses": +! needs invalidation testing
    #    JSLCache(49, mfaces.IGroupAddress, ["GroupAddress"]),
    "committees": 
        JSLCache(49, mfaces.ICommittee, ["Committee"]),
    #"bills": 
    #    JSLCache(99, mfaces.IBill, ["Bill"]),
    #"signatories": 
    #    JSLCache(49, mfaces.ISignatory, 
    #        ["Signatory", "Bill", "Motion", "Question"]
    #    ),
    #"questions": 
    #    JSLCache(199, mfaces.IQuestion, ["Question", "Ministry"]),
    #"motions": 
    #    JSLCache(99, mfaces.IMotion, ["Motion"]),
    #"tableddocuments": 
    #    JSLCache(99, mfaces.ITabledDocument, ["TabledDocument"]),
    "agendaitems": 
        JSLCache(99, mfaces.IAgendaItem, ["AgendaItem"]),
    "preports": 
        JSLCache(49, mfaces.IReport, ["Report"]),
    "attendance": 
        JSLCache(99, mfaces.ISittingAttendance, ["SittingAttendance"]),
    "parliamentmembers": # alias: "current"
        JSLCache(99, mfaces.IMemberOfParliament, ["MemberOfParliament"]),
    "political-groups": # alias: "politicalgroups"
        JSLCache(49, mfaces.IPoliticalGroup, ["PoliticalGroup"]),
    "parliaments": 
        JSLCache(49, mfaces.IParliament, ["Parliament"]),
    "governments": 
        JSLCache(49, mfaces.IGovernment, ["Government"]),
    "sessions": 
        JSLCache(49, mfaces.ISession, ["Session"]),
    "sittings": 
        JSLCache(49, mfaces.ISitting, ["Sitting"]),
    "committeestaff": 
        JSLCache(49, mfaces.ICommitteeStaff, ["CommitteeStaff"]),
    "committeemembers": 
        JSLCache(49, mfaces.ICommitteeMember, ["CommitteeMember"]),
    "ministries": 
        JSLCache(49, mfaces.IMinistry, ["Ministry"]),
}
# aliases for same JSLCache instances
JSLCaches["current"] = JSLCaches["parliamentmembers"]


def get_CacheByClassName():
    """Build mapping of class_name to JSLCaches to invalidate.
    """
    CacheByClassName = {} # {class_name: set(JSCache.cache)}
    for jslc in JSLCaches.values():
        for class_name in jslc.invalidating_class_names:
            CacheByClassName.setdefault(class_name, set()).add(jslc)
    return CacheByClassName
CacheByClassName = get_CacheByClassName()

# keys should be names of event classes, such as those defined in 
# zope.lifecycleevent or subclasses thereof. 
EVENT_TYPE_TO_ACTION_MAP = {
    "ObjectCreatedEvent": "add",
    "ObjectAddedEvent": "add",
    "ObjectRemovedEvent": "delete",
    "ObjectModifiedEvent": "edit",
    "WorkflowTransitionEvent": "transition",
}

from bungeni.alchemist.interfaces import IAlchemistContent
from zope.component.interfaces import IObjectEvent
@register.handler((IAlchemistContent, IObjectEvent))
def on_invalidate_cache_event(instance, event):
    """Invalidate caches affected by creation of this instance.
    See similar handler: core.workflows.initializeWorkflow
    """
    log.debug("[invalidate_cache_event] %s / %s" % (instance, event))
    class_name = event.object.__class__.__name__
    event_name = event.__class__.__name__ # !+DRAFT_CACHE_INVALIDATION
    try:
        invalidate_caches_for(class_name, EVENT_TYPE_TO_ACTION_MAP[event_name])
    except KeyError:
        log.debug("[invalidate_cache_event] No action declared for [%s]" % (
            event_name))

# !+DRAFT_CACHE_INVALIDATION(mr, mar-2011) only JSON Listings that are 
# publically viewable are cached. Most bungeni domain types are created into 
# a "draft" workflow state that is NOT public, so in theory any existing cache 
# of listings of public items is NOT affected. Plus, the required subsequent 
# modification of the item (to transit the item into a public state) will 
# anyway invalidate the cache. Should refine the cache invalidation logic 
# to also consider (type, status, action).

# !+EVENT_DRIVEN_CACHE_INVALIDATION(mr, mar-2011) invalidation of JSON Listing 
# caches should be event driven--all actions which should result in the 
# invalidation of one or more caches should fire an appropriate, and the 
# on_invalidate_cache_event() handler adjusted to take it into account.
# 
# There should be no direct calls to invalidate_caches_for() anywhere 
# throughout bungeni code.

def invalidate_caches_for(class_name, action):
    """Invalidate caches items in which may be made stale by modificatoin 
    of an instance of the specified domain class_name.
    
    class_name: domain class name for the modified instance 
    action: originating action (see code for allowed values)
    """
    assert action in ("add", "edit", "delete", "transition", "translate"), \
        "Unknown cache invalidation action: %s" % action
    # !+ is action needed?
    if class_name in CacheByClassName:
        for jslc in CacheByClassName[class_name]:
            log.debug("Invalidating [descriptor: %s] cache [num items: %i] "
                "on [%s] of an instance of [%s]" % (
                    jslc.descriptor.__class__.__name__,
                    len(jslc.cache.order),
                    action, 
                    class_name))
            jslc.clear()
    else:
        log.warn("No cache for class_name [%s] / action [%s] " % (
            class_name, action))

