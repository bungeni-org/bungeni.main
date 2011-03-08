log = __import__("logging").getLogger("bungeni.ui.container")

import sys
import datetime
import simplejson
import sqlalchemy.sql.expression as sql
from sqlalchemy import types, orm

from ore import yuiwidget

from zope import interface
from zope import component
from zope.security import proxy
from zope.security import checkPermission
from zope.publisher.browser import BrowserView

from bungeni.alchemist import model
from bungeni.alchemist import container

from bungeni.models import interfaces as mfaces
from bungeni.models import domain

from bungeni.core import translation

from bungeni.ui import interfaces as ufaces
from bungeni.ui.utils import url, date, debug
from bungeni.ui import cookies
from bungeni.ui import browser
from bungeni.ui import z3evoque


def query_iterator(query, parent, permission=None):
    """Generator of the items in a query. 
    
    If a permission is specified, then checkPermission() is called.
    Note that -- in some cases -- NOT calling checkPermission() on an item 
    has resulted in SQLAlchemy-related data errors downstream.
    """
    for item in query:
        item.__parent__ = parent
        if permission is None:
            yield item
        else:
            if checkPermission(permission, proxy.ProxyFactory(item)):
                yield item


def query_filter_date_range(context, request, query, domain_model):
    """Add date range filter to query:
    - if the model has start & end dates, constrain the query to objects 
      appearing within those dates.
    - else (archive section) pick off start/end date from the request's cookies
    - else try getting a display date off request
    """
    if ((ufaces.IBusinessSectionLayer.providedBy(request) and (
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
    
    # evoque
    template = z3evoque.PageViewTemplateFile("container.html#generic")
    
    def __call__(self):
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


class ContainerJSONBrowserView(BrowserView):
    """Base BrowserView Container listing as a JSON AJAX callback.
    """
    permission = None
    
    def __init__(self, context, request):
        super(ContainerJSONBrowserView, self).__init__(context, request)
        self.domain_model = proxy.removeSecurityProxy(self.context).domain_model
        self.domain_interface = model.queryModelInterface(self.domain_model)
        self.domain_annotation = model.queryModelDescriptor(
            self.domain_interface)
        self.fields = tuple(container.getFields(
            self.context, self.domain_interface, self.domain_annotation))
        # table keys
        self.table = orm.class_mapper(self.domain_model).mapped_table
        self.utk = dict([ (self.table.columns[k].key, k) 
                          for k in self.table.columns.keys() ])
        # sort_on defaults: [str] 
        self.defaults_sort_on = getattr(self.domain_model, "sort_on", None)
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
                getattr(self.domain_model, "sort_dir", "desc"))
        self.sort_dir = self.request.get("dir")

class ContainerJSONTableHeaders(ContainerJSONBrowserView):
    def __call__(self):
        return simplejson.dumps([ 
            dict(name=field.__name__, title=field.title)
            for field in self.fields 
        ])

class ContainerJSONListing(ContainerJSONBrowserView):
    """Paging, batching, sorting, json contents of a container.
    """
    permission = "zope.View"
    
    def _get_operator_field_filters(self, field_filter):
        field_filters = [ ff for ff in field_filter.strip().split(" ") if ff ]
        if "AND" in field_filters:
            operator = " AND "
            while "AND" in field_filters:
                field_filters.remove("AND")
        else:
            operator = " OR " 
        while "OR" in field_filters:
            field_filters.remove("OR")
        return operator, field_filters
    
    def _getFieldFilter(self, fieldname, field_filters, operator):
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
    
    def getFilter(self):
        """ () -> str
        """
        table, utk = self.table, self.utk
        fs = [] # filter string
        for field in self.fields:
            fn = field.__name__ # field name
            column, kls = None, None
            if fn in utk:
                column = table.columns[utk[fn]]
                kls = column.type.__class__
            ff_name = "filter_%s" % (fn) # field filter name
            ff = self.request.get(ff_name, None) # field filter
            if ff:
                if fs:
                    fs.append(" AND ")
                if getattr(self.domain_model, "sort_replace", None):
                    if fn in self.domain_model.sort_replace.keys():
                        op, ffs = self._get_operator_field_filters(ff)
                        rfs = op.join([ 
                                self._getFieldFilter(srfn, ffs, " OR ")
                                for srfn in ( # srfn: sort_replace field_name
                                    self.domain_model.sort_replace[fn]) ])
                        if rfs:
                            fs.extend(" (%s) " % (rfs))
                        continue
                if fn in utk:
                    if kls in (types.String, types.Unicode):
                        op, ffs = self._get_operator_field_filters(ff)
                        fs = [self._getFieldFilter(str(column), ffs, op)]
                    elif kls in (types.Date, types.DateTime):
                        f_name = "to_char(%s, 'YYYY-MM-DD')" % (column)
                        fs = [self._getFieldFilter(f_name, [ff], "")]
                    else:
                        fs.append("%s = %s" % (column, ff))
        return "".join(fs)
    
    def query_add_filters(self, query, *filter_strings):
        """ (filter_sytings) -> query
        """
        for fs in filter_strings:
            if fs:
                query = query.filter(fs)
        return query
    
    _sort_dir_funcs = dict(asc=sql.asc, desc=sql.desc)
    def getSort(self):
        """ server side sort,
        @web_parameter sort - request variable for sort column
        @web_parameter dir - sort direction, only once acceptable value "desc"
        """
        table, utk = self.table, self.utk
        sort_dir_func = self._sort_dir_funcs.get(self.sort_dir, sql.desc)
        sort_on_expressions = []
        sort_on_keys = []
        # first process user specified values
        sort_on = self.sort_on
        if sort_on:
            sort_on = sort_on[5:]
            # in the domain model you may replace the sort with another column
            sort_replace = getattr(self.domain_model, "sort_replace", None) # dict
            if sort_replace and (sort_on in sort_replace):
                sort_on_keys.extend(sort_replace[sort_on])
            elif sort_on in utk:
                sort_on_keys.append(str(table.columns[utk[sort_on]]))
            if sort_on_keys:
                for sort_on in sort_on_keys:
                    sort_on_expressions.append(sort_dir_func(sort_on))
        # second, process model defaults
        if self.defaults_sort_on:
            for dso in self.defaults_sort_on:
                if dso not in sort_on_keys:
                    sort_on_expressions.append(sort_dir_func(dso))
        return sort_on_expressions
    
    def getOffsets(self, default_start=0, default_limit=25):
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
        if lang is None:
            lang = translation.get_request_language()
        t_nodes = []
        for node in nodes:
            try:
                t_nodes.append(translation.translate_obj(node, lang))
            except (AssertionError,): # node is not ITranslatable
                debug.log_exc_info(sys.exc_info(), log_handler=log.warn)
                # if a node is not translatable then we assume that NONE of 
                # the nodes are translatable, so we simply break out, 
                # returning the untranslated nodes as is
                return nodes
        return t_nodes
    
    def _jsonValues(self, nodes, fields):
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
            for field in fields:
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
    #   - ore.alchemist.container.AlchemistContainer.batch()
    def getBatch(self, start=0, limit=20, lang=None):
        context = proxy.removeSecurityProxy(self.context)
        query = context._query
        
        # date_range filter (try from: model, then cookie, then request)
        query = query_filter_date_range(context, self.request, query, 
            self.domain_model)
        
        # other filters 
        query = self.query_add_filters(query, self.getFilter())
        
        # order_by
        order_by = self.getSort() # [sort_on_expressions]
        if order_by:
            query = query.order_by(order_by)
        # ore.alchemist.container.AlchemistContainer.batch()
        # nodes: [<bungeni.models.domain.Question]
        nodes = [ container.contained(ob, self, container.stringKey(ob)) 
                  for ob in 
                  query_iterator(query, self.context, self.permission) ]
        self.set_size = len(nodes)
        nodes[:] = nodes[start : start + limit]
        nodes = self.translate_objects(nodes, lang)
        batch = self._jsonValues(nodes, self.fields)
        return batch
    
    def json_batch(self, start, limit, lang):
        batch = self.getBatch(start, limit, lang)
        data = dict(
            length=self.set_size, # total result set length, set in getBatch()
            start=start,
            recordsReturned=len(batch), # batch length
            sort=self.sort_on,
            dir=self.sort_dir,
            nodes=batch
        )
        return simplejson.dumps(data)
    
    def __call__(self):
        # prepare required parameters
        start, limit = self.getOffsets() # ? start=0&limit=25
        lang = self.request.locale.getLocaleID() # get_request_language()
        return self.json_batch(start, limit, lang)


class PublicStatesContainerJSONListing(ContainerJSONListing):
    """JSON Listing based on public workflow states.
    
    Given public states only, for viewing no permission checking is needed.
    Given results are the same (for a given set of input parameters) for all 
    users, they are cached.
    
    Used for listings for all roles/users in the UI layers: 
    IBusinessSectionLayer, IMembersSectionLayer, IArchiveSectionLayer
    """
    permission = None
    
    def query_add_filters(self, query, *filter_strings):
        """Add filtering on public_wfstates
        """
        public_wfstates = getattr(self.domain_annotation, "public_wfstates", 
            None)
        if public_wfstates:
            query = query.filter(self.domain_model.status.in_(public_wfstates))
        return super(PublicStatesContainerJSONListing, self
            ).query_add_filters(query, *filter_strings)
    
    def get_cache_key(self, context, lang, start, limit, sort_direction):
        r = self.request
        jslc = JSLCaches[context.__name__] # raises KeyError
        filters = tuple(r.get(name) or None for name in jslc.filter_params)
        # as sort_dir param may have a (overridable) model default, we 
        # treat it differently than other params (note that sort_on may 
        # also have a model default, but the values here accumulate, so for
        # key uniqueness it suffices to consider only any sort_on parameter 
        # value incoming in the request).
        return (lang, start, limit, sort_direction, self.sort_on, filters)
    
    def __call__(self):
        # prepare required parameters
        start, limit = self.getOffsets()
        lang = self.request.locale.getLocaleID() # get_request_language()
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
        print "JSLCache queryModelDescriptor(%s) -> %s" % (
            model_interface.__name__,
            model.queryModelDescriptor(model_interface))
        '''
        !+queryModelDescriptor(mr, mar-2011) because of the discrepancy between 
        test and application ZCML code, when running bungeni.ui unittests 
        the call to queryModelDescriptor here (i.e. when importing this module) 
        returns None. To reduce this timing issue, the setting up of the 
        JSLCache attributes descriptor and filter_params is being postponed 
        to when it is needed i.e. when they are actually being called
        and used--which is why they are implemented as properties. They are 
        themselves cached to minimize the overhead of repeated lookups at 
        runtime.
        
        !+queryModelDescriptor(mr, mar-2011) should be renamed, and behaviour 
        changed accordingly (raise an error when None) to getModelDescriptor().
        '''
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
            self._descriptor = model.queryModelDescriptor(self.model_interface)
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
    "assigneditems": 
        JSLCache(49, mfaces.IItemGroupItemAssignment, 
            ["ItemGroupItemAssignment"], 
        ),
    "assignedgroups": 
        JSLCache(49, mfaces.IGroupGroupItemAssignment,
            ["GroupGroupItemAssignment"], 
        ),
    "cosignatory": 
        JSLCache(49, mfaces.ICosignatory, ["Cosignatory"]),
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
        # !+NAMING(mr, sep-2010) descriptor name: AttendanceDescriptor
        JSLCache(99, mfaces.IGroupSittingAttendance, ["GroupSittingAttendance"]),
    "parliamentmembers": # alias: "current"
        # !+NAMING(mr, sep-2010) descriptor name: MpDescriptor
        JSLCache(99, mfaces.IMemberOfParliament, 
            ["MemberOfParliament", "Constituency", "Province", "Region",
                "PoliticalParty"]
        ),
    "political-groups": # alias: "politicalgroups"
        JSLCache(49, mfaces.IPoliticalGroup, ["PoliticalGroup"]),
    "partymembers":
        JSLCache(49, mfaces.IPartyMember, ["PartyMember"]),        
    "parliaments": 
        JSLCache(49, mfaces.IParliament, ["Parliament"]),
    "governments": 
        JSLCache(49, mfaces.IGovernment, ["Government"]),
    "sessions": 
        # !+NAMING(mr, sep-2010) descriptor name: SessionDescriptor
        JSLCache(49, mfaces.IParliamentSession, ["ParliamentSession"]),
    "sittings": 
        # !+NAMING(mr) descriptor name: SittingDescriptor
        JSLCache(49, mfaces.IGroupSitting, ["GroupSitting"]),
    "committeestaff": 
        JSLCache(49, mfaces.ICommitteeStaff, ["CommitteeStaff"]),
    "committeemembers": 
        JSLCache(49, mfaces.ICommitteeMember, ["CommitteeMember"]),
    "ministries": 
        JSLCache(49, mfaces.IMinistry, ["Ministry"]),
    "constituencies": 
        JSLCache(49, mfaces.IConstituency, ["Constituency"]),
}
# aliases for same JSLCache instances
JSLCaches["politicalgroups"] = JSLCaches["political-groups"] # !+ same?
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
def on_invalidate_cache_event(instance, event):
    """Invalidate caches affected by creation of this instance.
    See similar handler: core.workflows.initializeWorkflow
    """
    log.warn("[invalidate_cache_event] %s / %s" % (instance, event))
    class_name = event.object.__class__.__name__
    event_name = event.__class__.__name__ # !+DRAFT_CACHE_INVALIDATION
    try:
        invalidate_caches_for(class_name, EVENT_TYPE_TO_ACTION_MAP[event_name])
    except KeyError:
        log.error("[invalidate_cache_event] No action declared for [%s]" % (
            event_name))

# !+DRAFT_CACHE_INVALIDATION(mr, mar-2010) only JSON Listings that are 
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

