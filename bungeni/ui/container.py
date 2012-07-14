log = __import__("logging").getLogger("bungeni.ui.container")

import sys
import datetime
import simplejson
import sqlalchemy.sql.expression as sql
from sqlalchemy import types, orm

from ore import yuiwidget

from zope.security import proxy
from zope.security import checkPermission
from zope.publisher.browser import BrowserPage
from zc.resourcelibrary import need
from zope.app.pagetemplate import ViewPageTemplateFile
from bungeni.alchemist import model
from bungeni.alchemist import container
from bungeni.alchemist.interfaces import IAlchemistContainer

from bungeni.models import interfaces as mfaces
from bungeni.models import domain

from bungeni.core.workflow.interfaces import IWorkflowed
from bungeni.core import translation

from bungeni.ui import interfaces as ufaces
from bungeni.ui.utils import url, date, debug
from bungeni.ui import cookies
from bungeni.ui import browser
from bungeni.utils import register
from bungeni.utils.capi import capi
from bungeni.utils.naming import polymorphic_identity


def query_iterator(query, parent, permission=None):
    """Generator of the items in a query.
    
    If a permission is specified, then checkPermission() is called.
    Note that -- in some cases -- NOT calling checkPermission() on an item
    has resulted in SQLAlchemy-related data errors downstream.
    """
    for item in query:
        item.__parent__ = parent
        if (permission is None or 
                checkPermission(permission, proxy.ProxyFactory(item))
            ):
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
        return getattr(model.queryModelDescriptor(dm), "container_name",
            dm.__name__)

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
        self.domain_interface = model.queryModelInterface(self.domain_model)
        self.domain_annotation = model.queryModelDescriptor(
            self.domain_interface)
        self.fields = tuple(container.getFields(
            self.context, self.domain_interface, self.domain_annotation))
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


@register.view(IAlchemistContainer, name="jsontableheaders")
class ContainerJSONTableHeaders(ContainerJSONBrowserView):
    def __call__(self):
        return simplejson.dumps([
            dict(name=field.__name__, title=field.title)
            for field in self.fields
        ])


@register.view(IAlchemistContainer, name="jsonlisting")
class ContainerJSONListing(ContainerJSONBrowserView):
    """Paging, batching, sorting, json contents of a container.
    """
    permission = "zope.View"
    
    def _get_operator_field_filters(self, field_filter):
        field_filters = [ff for ff in field_filter.strip().split(" ") if ff]
        if "AND" in field_filters:
            operator = " AND "
            while "AND" in field_filters:
                field_filters.remove("AND")
        else:
            operator = " OR "
        while "OR" in field_filters:
            field_filters.remove("OR")
        return operator, field_filters

    def _get_field_filter(self, fieldname, field_filters, operator):
        """If we are filtering for replaced fields we assume
        that they are character fields.
        """
        fs = operator.join([
                "lower(%s) LIKE '%%%s%%' " % (fieldname, f.lower())
                for f in field_filters
        ])
        if fs:
            return "(%s)" % (fs)
        return ""

    def get_filter(self):
        """ () -> str
        """
        utk = self.utk
        fs = []  # filter string
        filter_queries = []
        for field in self.fields:
            fn = field.__name__  # field name
            column, kls = None, None
            if fn in utk:
                column = utk[fn]
                kls = column.type.__class__
            ff_name = "filter_%s" % (fn)  # field filter name
            ff = self.request.get(ff_name, None)  # field filter
            if ff:
                md_field = self.domain_annotation.get(fn) #model descriptor field
                if md_field:
                    lc_filter = md_field.listing_column_filter
                    if lc_filter:
                        filter_queries.append((lc_filter,ff))
                        continue
                if fs:
                    fs.append(" AND ")
                if fn in utk:
                    if kls in (types.String, types.Unicode):
                        op, ffs = self._get_operator_field_filters(ff)
                        fs = [self._get_field_filter(str(column), ffs, op)]
                    elif kls in (types.Date, types.DateTime):
                        f_name = "to_char(%s, 'YYYY-MM-DD')" % (column)
                        fs = [self._get_field_filter(f_name, [ff], "")]
                    else:
                        fs.append("%s = %s" % (column, ff))
        return ("".join(fs), filter_queries)

    def query_add_filters(self, query, *filter_strings):
        """ (filter_sytings) -> query
        """
        for fs in filter_strings:
            if fs:
                query = query.filter(fs)
        return query

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
            if md_field:
                sort_on_keys.append(sort_on)
        
        # second, process model defaults
        if self.defaults_sort_on:
            for dso in self.defaults_sort_on:
                if dso not in sort_on_keys:
                    sort_on_keys.append(dso)
        return sort_on_keys
    
    def get_offsets(self, 
            default_start=0,
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
        """ (nodes:[ITranslatable]) -> [nodes]
        """
        # !+ lang should always be valid here... make not optional, assert?
        if lang is None:
            lang = translation.get_request_language(request=self.request)
        t_nodes = []
        for node in nodes:
            try:
                t_nodes.append(translation.translate_obj(node, lang))
            except (AssertionError,):  # node is not ITranslatable
                debug.log_exc_info(sys.exc_info(), log_handler=log.warn)
                # if a node is not translatable then we assume that NONE of
                # the nodes are translatable, so we simply break out,
                # returning the untranslated nodes as is
                return nodes
        return t_nodes

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
        filter_string, lc_filter_queries = self.get_filter()
        query = self.query_add_filters(query, filter_string)
        sort_on_keys = self.get_sort_keys()
        if sort_on_keys:
            for sort_on in sort_on_keys:
                md_field = self.domain_annotation.get(sort_on)
                if md_field:
                    lc_filter = md_field.listing_column_filter
                    if not lc_filter:   
                        sort_on_expressions.append(
                            self.sort_dir_func(
                                getattr(self.domain_model, sort_on)))
        for lc_filter_query, lc_filter_string in lc_filter_queries:
            query = lc_filter_query(query, lc_filter_string, self.sort_dir_func)
        if sort_on_expressions:
            query = query.order_by(sort_on_expressions)
        # get total number of items before applying an offset and limit
        self.set_size = query.count()
        # offset and limit
        query = query.offset(start).limit(limit)
        # bungeni.alchemist.container.AlchemistContainer.batch()
        # nodes: [<bungeni.models.domain.Question]
        return [ 
            container.contained(ob, self, container.stringKey(ob))
            for ob in query_iterator(query, self.context, self.permission)
        ]
    
    def json_batch(self, start, limit, lang):
        batch = self.get_batch(start, limit) 
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

#@register.view(IAlchemistContainer, 
#    layer=ufaces.IMembersSectionLayer, name="jsonlisting") 
#@register.view(IAlchemistContainer, 
#    layer=ufaces.IArchiveSectionLayer, name="jsonlisting")
#@register.view(IAlchemistContainer, 
#    layer=ufaces.IMembersSectionLayer, name="jsonlisting") 
#@register.view(IAlchemistContainer, 
#    layer=ufaces.IArchiveSectionLayer, name="jsonlisting")
@register.view(IAlchemistContainer, 
    layer=ufaces.IBusinessSectionLayer, name="jsonlisting",
    protect=register.PROTECT_VIEW_PUBLIC)
class PublicStatesContainerJSONListing(ContainerJSONListing):
    """JSON Listing based on public workflow states.
    
    Given public states only, for viewing no permission checking is needed.
    
    Given results are the same (for a given set of input parameters) for all
    users, they are cached.
    
    Used for listings for all roles/users in the UI layers:
    IBusinessSectionLayer, IMembersSectionLayer, IArchiveSectionLayer
    """
    # !+PUBLIC_CONTAINER_VIEW(mr, may-2102) having permission=None is a
    # somewhat dangerous optimization of avoiding to call checkPermission on
    # each item (under the assumption that the state-based logic will never
    # be faulty. Should really be left as "ziope.View". 
    # In any case, this view class will go away.
    permission = None
    
    def query_add_filters(self, query, *filter_strings):
        """Add filtering on public workflow states
        """
        if IWorkflowed.implementedBy(self.context.domain_model):
            type_key = polymorphic_identity(self.context.domain_model)
            workflow = capi.get_type_info(type_key).workflow
            #!+WORKFLOWS(mb, July-2012) skip filter states if no workflow
            # type_info lookup of workflows will fail if no wf is explicitly
            # registered. DISCREPANCY
            # inheriting classes e.g. Report4Sitting implement IWorkflowed
            # but lookup here fails. TODO rework/review Report4Sitting
            # also type_info lookup should mirror zope registry lookup
            if workflow:
                public_wfstates = workflow.get_state_ids(tagged=["public"], 
                    restrict=False)
                if public_wfstates:
                    query = query.filter(
                        self.domain_model.status.in_(public_wfstates))
        else:
            log.warn("PublicStateContainerJSONListing.query_add_filters called "
                "a type [%s] that is not workflowed... cannot apply any filters "
                "on workflow states!" % (self.context.domain_model))
        return super(PublicStatesContainerJSONListing, self
            ).query_add_filters(query, *filter_strings)
    
    def get_cache_key(self, context, lang, start, limit, sort_direction):
        r = self.request
        jslc = JSLCaches[context.__name__]  # raises KeyError
        filters = tuple(r.get(name) or None for name in jslc.filter_params)
        # as sort_dir param may have a (overridable) model default, we 
        # treat it differently than other params (note that sort_on may 
        # also have a model default, but the values here accumulate, so for
        # key uniqueness it suffices to consider only any sort_on parameter 
        # value incoming in the request).
        return (lang, start, limit, sort_direction, self.sort_on, filters)
    
    def __call__(self):
        # prepare required parameters
        start, limit = self.get_offsets()
        lang = translation.get_request_language(request=self.request)
        context = proxy.removeSecurityProxy(self.context)
        # there may not be a cache defined for this context type
        try:
            cache_key = self.get_cache_key(context, lang, start, limit, 
                self.sort_dir)
            cache = JSLCaches[context.__name__].cache
        except KeyError:
            log.warn(" ********* [%s] No such JSLCache !" % (context.__name__))
            # no cache, proceed...
            return self.json_batch(start, limit, lang)
        # OK, we have a cache and a cache_key
        if not cache.has(cache_key):
            log.debug(" [%s] CACHE SETTING key: %s" % (
                context.__name__, cache_key,))
            cache.set(cache_key, self.json_batch(start, limit, lang))
        return cache.get(cache_key)


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
            self._descriptor = capi.get_type_info(self.model_interface).descriptor
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
    "bills": 
        JSLCache(99, mfaces.IBill, ["Bill"]),
     "signatories": 
        JSLCache(49, mfaces.ISignatory, 
            ["Signatory", "Bill", "Motion", "Question"]
        ),
    "questions": 
        JSLCache(199, mfaces.IQuestion, ["Question", "Ministry"]),
    "motions": 
        JSLCache(99, mfaces.IMotion, ["Motion"]),
    "tableddocuments": 
        JSLCache(99, mfaces.ITabledDocument, ["TabledDocument"]),
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

