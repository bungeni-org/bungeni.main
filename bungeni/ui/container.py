log = __import__("logging").getLogger("bungeni.ui.container")

import sys
import datetime
import simplejson
import sqlalchemy.sql.expression as sql
from sqlalchemy import types, orm

from zope import interface
from zope import component
from zope.security import proxy
from zope.security import checkPermission
from zope.publisher.browser import BrowserView

from ore.alchemist.model import queryModelDescriptor
from ore.alchemist.model import queryModelInterface
from ore.alchemist.container import contained

from bungeni.models.interfaces import IDateRangeFilter
from bungeni.models.interfaces import ICommitteeContainer
from bungeni.models.interfaces import IMemberOfParliamentContainer
from bungeni.models.interfaces import ICommitteeMemberContainer
from bungeni.models.interfaces import ICommitteeStaffContainer

from bungeni.core import translation

from bungeni.ui.utils import url, date, debug
from bungeni.ui import cookies
from bungeni.ui.interfaces import IBusinessSectionLayer, \
    IMembersSectionLayer, IArchiveSectionLayer

def stringKey(obj):
    """Replacement of ore.alchemist.container.stringKey
    
    The difference is that here the primary_key is not determined by 
    sqlalchemy.orm.mapper.primary_key_from_instance(obj) but by doing the 
    logically equivalent (but a little more laborious) 
    [ getattr(instance, c.name) for c in mapper.primary_key ].
    
    This is because, in some hard-to-debug cases, the previous was returning 
    None to all pk values e.g. for objects on which checkPermission() has not
    been called. Using this version, the primary_key is correctly determined
    irrespective of whether checkPermission() had previously been called on
    the object.
    """
    unproxied = proxy.removeSecurityProxy(obj)
    mapper = orm.object_mapper(unproxied)
    #primary_key = mapper.primary_key_from_instance(unproxied)
    identity_values = [ getattr(unproxied, c.name) for c in mapper.primary_key ]
    identity_key = '-'.join(map(str, identity_values))
    return "obj-%s" % (identity_key)


def getFields(context, interface=None, annotation=None):
    """Generator of all fields that will be displayed in a containerlisting .
    
    Replacement of alchemist.ui.container.getFields
    """
    if interface is None: 
        model = proxy.removeSecurityProxy(context.domain_model)
        interface = queryModelInterface(model)
    if annotation is None:
        annotation = queryModelDescriptor(interface)
    for column in annotation.listing_columns:
        yield interface[column]


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
    if ((IBusinessSectionLayer.providedBy(request) and (
            ICommitteeContainer.providedBy(context) or 
            ICommitteeMemberContainer.providedBy(context) or
            ICommitteeStaffContainer.providedBy(context))
        ) or
        (IMembersSectionLayer.providedBy(request) and
            IMemberOfParliamentContainer.providedBy(context))
    ):
        start_date, end_date = datetime.date.today(), None
    elif IArchiveSectionLayer.providedBy(request):
        start_date, end_date = cookies.get_date_range(request)
    else:
        start_date, end_date = date.getDisplayDate(request), None
    
    if not start_date and not end_date:
        return query
    elif not start_date:
        start_date = datetime.date(1900, 1, 1)
    elif not end_date:
        end_date = datetime.date(2100, 1, 1)
    
    date_range_filter = component.getSiteManager().adapters.lookup(
        (interface.implementedBy(domain_model),), IDateRangeFilter)
    if date_range_filter is not None:
        query = query.filter(date_range_filter(domain_model)).params(
            start_date=start_date, end_date=end_date)
    return query


class ContainerBrowserView(BrowserView):
    """Base BrowserView Container listing.
    """
    permission = None
    
    def __init__(self, context, request):
        super(ContainerBrowserView, self).__init__(context, request)
        self.domain_model = proxy.removeSecurityProxy(self.context).domain_model
        self.domain_interface = queryModelInterface(self.domain_model)
        self.domain_annotation = queryModelDescriptor(self.domain_interface)
        self.fields = tuple(getFields(
            self.context, self.domain_interface, self.domain_annotation))
        # table keys
        self.table = orm.class_mapper(self.domain_model).mapped_table
        self.utk = dict([ (self.table.columns[k].key, k) 
                          for k in self.table.columns.keys() ])
        # sort defaults
        self.defaults_sort_on = getattr(self.domain_model, "sort_on", None)
        self.sort_dir = self.request.get("dir", 
            # if defined, use model's sort_dir as default, otherwise "desc"
            getattr(self.domain_model, "sort_dir", "desc")
        )

class ContainerJSONTableHeaders(ContainerBrowserView):
    def __call__(self):
        return simplejson.dumps([ 
            dict(name=field.__name__, title=field.title)
            for field in self.fields 
        ])

class ContainerJSONListing(ContainerBrowserView):
    """Paging, batching, sorting, json contents of a container.
    """
    permission = "zope.View"
    
    def _get_operator_field_filters(self, field_filter):
        field_filters = field_filter.strip().split(" ")
        if "AND" in field_filters:
            operator = " AND "
            while "AND" in field_filters:
                field_filters.remove("AND")
        else:
            operator = " OR " 
        while "OR" in field_filters:
            field_filters.remove("OR")
        while "" in field_filters:
            field_filters.remove("")
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
        columns = []
        # first process user specified values
        sort_on = self.request.get("sort", None)
        if sort_on:
            sort_on = sort_on[5:]
        sort_on_keys = []
        # in the domain model you may replace the sort with another column
        sort_replace = getattr(self.domain_model, "sort_replace", None) # dict
        if sort_replace and (sort_on in sort_replace):
            sort_on_keys = sort_replace[sort_on]
        elif sort_on and (sort_on in utk):
            sort_on_keys = [str(table.columns[utk[sort_on]])]
        for sort_on in sort_on_keys:
                columns.append(sort_dir_func(sort_on))
        # second, process model defaults
        if self.defaults_sort_on:
            for sort_on in self.defaults_sort_on:
                if sort_on not in sort_on_keys:
                    columns.append(sort_dir_func(sort_on))
        return columns
    
    def getOffsets(self, default_start=0, default_limit=25):
        start = self.request.get("start", default_start)
        limit = self.request.get("limit", default_limit)
        try:
            start, limit = int(start), int(limit)
            if not limit:
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
                t_nodes.append(node)
        return t_nodes
    
    def _jsonValues(self, nodes, fields):
        """
        filter values from the nodes to respresent in json, currently
        that means some footwork around, probably better as another
        set of adapters.
        """
        def get_anno_getters_by_field_name():
            # dict of domain_annotation field getters by name, for fast lookup
            da_getters = dict([ 
                (da_field.name, getattr(da_field.listing_column, "getter", None)) 
                for da_field in self.domain_annotation.fields
            ])
            return da_getters
        getters_by_field_name = get_anno_getters_by_field_name()
        values = []
        for n in nodes:
            d = {}
            for field in fields:
                f = field.__name__
                getter = getters_by_field_name.get(f, None)
                if getter is not None:
                    d[f] = v = getter(n, field)
                else:
                    d[f] = v = field.query(n)
                # !+i18n_DATE(mr, sep-2010) two problems with the isinstance 
                # tests below: 
                # a) they seem to always fail (no field values of this type?)
                # b) this is incorrect way to localize dates
                if isinstance(v, datetime.datetime):
                    d[f] = v.strftime("%F %I:%M %p")
                elif isinstance(v, datetime.date):
                    d[f] = v.strftime("%F")
            d["object_id"] = url.set_url_context(stringKey(n))
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
        order_by = self.getSort() # [columns]
        if order_by:
            query = query.order_by(order_by)
        # ore.alchemist.container.AlchemistContainer.batch()
        # nodes: [<bungeni.models.domain.Question]
        nodes = [ contained(ob, self, stringKey(ob)) for ob in 
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
            sort=self.request.get("sort"),
            dir=self.sort_dir,
            nodes=batch
        )
        return simplejson.dumps(data)
    
    def __call__(self):
        # prepare required parameters
        start, limit = self.getOffsets() # ? start=0&limit=25
        lang = self.request.locale.getLocaleID() # get_request_language()
        return self.json_batch(start, limit, lang)


class ContainerWFStatesJSONListing(ContainerJSONListing):
    """JSON Listing based on public workflow states.
    
    Given public states only, for viewing no permission checking is needed.
    Given results are the same (for a given set of input parameters) for all 
    users, they are cached.
    
    Used for listings for all roles/users in the layers: 
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
        return super(ContainerWFStatesJSONListing, self
            ).query_add_filters(query, *filter_strings)
    
    def get_cache_key(self, context, lang, start, limit, sort_direction):
        r, jslc = self.request, JSLCaches[context.__name__]
        filters = tuple(r.get(name) or None for name in jslc.filter_params)
        # as sort_dir qs_param may have a (overridable) model default, we 
        # treat it differently than other qs_params (note that sort_on may 
        # also have a model default, but the values here accumulate, so for
        # key uniqueness it suffices to consider only any sort_on parameter 
        # value incoming in the request.
        return (lang, start, limit, sort_direction, r.get("sort"), filters)
    
    def __call__(self):
        # prepare required parameters
        start, limit = self.getOffsets()
        lang = self.request.locale.getLocaleID() # get_request_language()
        context = proxy.removeSecurityProxy(self.context)
        cache_key = self.get_cache_key(context, 
            lang, start, limit, self.sort_dir)
        cache = JSLCaches[context.__name__].cache
        if not cache.has(cache_key):
            log.debug(" [%s] CACHE SETTING key: %s" % (
                context.__name__, cache_key,))
            cache.set(cache_key, self.json_batch(start, limit, lang))
        return cache.get(cache_key)


# caches for json container listings

import evoque.collection
import bungeni.ui.descriptor as bud

class JSLCache(object):
    """JSON Listing Cache"""
    def __init__(self, max_size, descriptor, invalidating_class_names):
        """ max_size:int - max number of items to cache, 0 implies unlimited,
                oldest in excess of max are discarded
            descriptor: domain.descriptor class for this listing
            invalidating_class_names:[str] - names of domain classes that 
                when modified will invalidate this cache
            
            filter_params: [name:str] - query string filter parameter names
        """
        self.cache = evoque.collection.Cache(max_size)
        self.descriptor = descriptor
        self.invalidating_class_names = invalidating_class_names
        # dynamically build the incoming (request querystring) filter 
        # parameter names lists from the domain class descriptor
        self.filter_params = [
            "filter_%s" % (field["name"])
            for field in self.descriptor.fields
            if field.get("listing")
        ]

JSLCaches = {
    "committees": 
        JSLCache(49, bud.CommitteeDescriptor, ["Committee"]),
    "bills": 
        JSLCache(99, bud.BillDescriptor, ["Bill"]),
    "assigneditems": 
        JSLCache(49, bud.ItemGroupItemAssignmentDescriptor, 
            ["ItemGroupItemAssignment"], 
        ),
    "assignedgroups": 
        JSLCache(49, bud.GroupGroupItemAssignmentDescriptor,
            ["GroupGroupItemAssignment"], 
        ),
    "consignatory": 
        JSLCache(49, bud.ConsignatoryDescriptor, ["Consignatory"]),
    "questions": 
        JSLCache(199, bud.QuestionDescriptor, ["Question", "Ministry"]),
    "motions": 
        JSLCache(99, bud.MotionDescriptor, ["Motion"]),
    "tableddocuments": 
        JSLCache(99, bud.TabledDocumentDescriptor, ["TabledDocument"]),
    "agendaitems": 
        JSLCache(99, bud.AgendaItemDescriptor, ["AgendaItem"]),
    "preports": 
        JSLCache(49, bud.ReportDescriptor, ["Report"]),
    "sreports": 
        JSLCache(49, bud.Report4SittingDescriptor, ["SittingReport"]),
    "attendance": 
        JSLCache(99, bud.AttendanceDescriptor, ["GroupSittingAttendance"]),
    "parliamentmembers": # alias: "current"
        JSLCache(99, bud.MpDescriptor, 
            ["MemberOfParliament", "Constituency", "Province", "Region",
                "PoliticalParty"]
        ),
    "political-groups": # alias: "politicalgroups"
        JSLCache(49, bud.PoliticalGroupDescriptor, ["PoliticalGroup"]),
    "parliaments": 
        JSLCache(49, bud.ParliamentDescriptor, ["Parliament"]),
    "governments": 
        JSLCache(49, bud.GovernmentDescriptor, ["Government"]),
    "sessions": 
        JSLCache(49, bud.SessionDescriptor, ["ParliamentSession"]),
    "sittings": 
        JSLCache(49, bud.SittingDescriptor, ["GroupSitting"]),
    "committeestaff": 
        JSLCache(49, bud.CommitteeStaffDescriptor, ["CommitteeStaff"]),
    "committeemembers": 
        JSLCache(49, bud.CommitteeMemberDescriptor, ["CommitteeMember"]),
    "ministries": 
        JSLCache(49, bud.MinistryDescriptor, ["Ministry"]),
    "constituencies": 
        JSLCache(49, bud.ConstituencyDescriptor, ["Constituency"]),
}
# aliases for same JSLCache instances
JSLCaches["politicalgroups"] = JSLCaches["political-groups"] 
JSLCaches["current"] = JSLCaches["parliamentmembers"]


def get_CacheByClassName():
    """ build mapping of class_name to caches to invalidate."""
    CacheByClassName = {} # {class_name: set(JSCache.cache)}
    for jslc in JSLCaches.values():
        for class_name in jslc.invalidating_class_names:
            CacheByClassName.setdefault(class_name, set()).add(jslc.cache)
    return CacheByClassName
CacheByClassName = get_CacheByClassName()


def invalidate_caches_for(class_name, action):
    """Invalidate caches items in which may be made stale by modificatoin 
    of an instance of the specified domain class_name.
    
    class_name: domain class name for the modified instance 
    action: edit | add | delete
    """
    assert action in ("add", "edit", "delete"), \
        "Unknown cache invalidation action: %s" % action
    # !+ is action needed?
    if class_name in CacheByClassName:
        for cache in CacheByClassName[class_name]:
            log.warn("Invalidating cache [num items: %i] on [%s] of an "
                "instance of [%s]" % (len(cache.order), action, class_name))
            # !+ encapsulate as a clear() method on evoque.collection.Cache
            cache.cache.clear()
            cache.order[:] = []
    else:
        log.warn("No cache for class_name [%s] / action [%s] " % (
            class_name, action))


