log = __import__("logging").getLogger("bungeni.ui.container")

import sys
import datetime
import zc.table
import simplejson
import sqlalchemy.sql.expression as sql
from sqlalchemy import types, orm

from zope import interface
from zope import component
from zope import formlib
from zope.security import proxy
from zope.security import checkPermission
from zope.publisher.browser import BrowserView
from zc.table import column, table

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
from bungeni.ui.interfaces import IBusinessSectionLayer
from bungeni.ui.interfaces import IMembersSectionLayer
from bungeni.ui.i18n import _

def stringKey(obj):
    """Replacement for ore.alchemist.container.stringKey
    
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
    """Generator of all fields that will be displayed in a containerlisting 
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


def get_query(context):
    """Get context's query.
    """
    return proxy.removeSecurityProxy(context)._query


def query_filter_date_range(context, request, query, domain_model):
    """If the model has start- and end-dates, constrain the query to
    objects appearing within those dates.
    """
    if ((IBusinessSectionLayer.providedBy(request) and
            ICommitteeContainer.providedBy(context)) or 
        (IMembersSectionLayer.providedBy(request) and
            IMemberOfParliamentContainer.providedBy(context)) or 
        (IBusinessSectionLayer.providedBy(request) and
            ICommitteeMemberContainer.providedBy(context)) or 
        (IBusinessSectionLayer.providedBy(request) and
            ICommitteeStaffContainer.providedBy(context))
    ):
        start_date, end_date = datetime.date.today(), None
    else:
        start_date, end_date = cookies.get_date_range(request)
    if not start_date and not end_date:
        return query
    else:
        if not start_date:
            start_date = datetime.date(1900, 1, 1)
        elif not end_date:
            end_date = datetime.date(2100, 1, 1)
        date_range_filter = component.getSiteManager().adapters.lookup(
            (interface.implementedBy(domain_model),), IDateRangeFilter)
        if date_range_filter is not None:
            query = query.filter(date_range_filter(domain_model)).params(
                start_date=start_date, end_date=end_date)
        return query


def dateFilter(request):
    return date.getFilter(date.getDisplayDate(request))



'''
from zope.app.pagetemplate import ViewPageTemplateFile
#from bungeni.ui import z3evoque
class ContainerListing(formlib.form.DisplayForm):
    """Formatted listing.
    """
    form_fields = formlib.form.Fields()
    mode = "listing"
    
    # evoque
    #index = z3evoque.PageViewTemplateFile("content.html#container")
    
    # zpt
    index = ViewPageTemplateFile("templates/generic-container.pt")
    
    def update(self):
        context = proxy.removeSecurityProxy(self.context)
        columns = core.setUpColumns(context.domain_model)
        columns.append(
            column.GetterColumn(title=_(u'Actions'), getter=viewEditLinks)
        )
        self.columns = columns
        super(ContainerListing, self).update()
    
    def render(self):
        return self.index()
    
    def listing(self):
        return self.formatter()
    
    @property
    def formatter(self):
        """We replace the formatter in our superclass to set up column
        sorting.
        
        Default sort order is defined in the model class
        (``sort_on``); if not set, the table is ordered by the
        ``short_name`` column (also used as secondary sort order).
        """
        context = proxy.removeSecurityProxy(self.context)
        model = context.domain_model
        query = get_query(self.context, self.request)
        table = query.table
        names = table.columns.keys()
        order_list = []
        
        order_by = self.request.get("order_by", None)
        if order_by:
            if order_by in names:
                order_list.append(order_by)
        
        default_order = getattr(model, "sort_on", None)
        if default_order:
            if default_order in names:
                order_list.append(default_order)
        
        if "short_name" in names and "short_name" not in order_list:
            order_list.append("short_name")
        
        filter_by = dateFilter(self.request)
        if filter_by:
            if "start_date" in names and "end_date" in names:
                query = query.filter(filter_by).order_by(order_list)
            else:
                query = query.order_by(order_list)
        else:
            query = query.order_by(order_list)
        
        subset_filter = getattr(context,"_subset_query", None)
        if subset_filter:
            query = query.filter(subset_filter)
        query = query_iterator(query, self.context, "zope.View")
        
        formatter = zc.table.table.AlternatingRowFormatter(
            context, self.request, query, prefix="form", columns=self.columns)
        
        formatter.cssClasses["table"] = "listing"
        formatter.table_id = "datacontents"
        return formatter
    
    @property
    def form_name(self):
        domain_model = proxy.removeSecurityProxy(self.context).domain_model
        
        descriptor = queryModelDescriptor(domain_model)
        if descriptor:
            name = getattr(descriptor, "container_name", None)
            if name is None:
                name = getattr(descriptor, "display_name", None)
        if not name:
            name = getattr(self.context, "__name__", None)
        return name
    
    @formlib.form.action(_(u"Add"))
    def handle_add(self, action, data):
        self.request.response.redirect("add")
'''

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
        self.defaults_sort_on = getattr(self.domain_model, "sort_on", None)
        self.default_sort_dir = getattr(self.domain_model, "sort_dir", "desc")
        self.sort_dir = self.request.get("dir", self.default_sort_dir)

class ContainerJSONTableHeaders(ContainerBrowserView):

    def __call__(self):
        th = []
        for field in self.fields:
            th.append({"name":  field.__name__, "title": field.title})
        return simplejson.dumps(th)


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
                for f in field_filters ])
        if fs:
            return "(%s)" % (fs)
        return ""
    
    def getFilter(self):
        """ () -> str
        """
        fs = [] # filter string
        table = orm.class_mapper(self.domain_model).mapped_table
        utk = {}
        for k in table.columns.keys():
            utk[table.columns[k].key] = k
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
    
    def getSort(self):
        """ server side sort,
        @web_parameter sort - request variable for sort column
        @web_parameter dir - sort direction, only once acceptable value "desc"
        """
        columns = []
        # first process user specified values
        sort_on = self.request.get("sort", None)
        table = orm.class_mapper(self.domain_model).mapped_table
        utk = {}
        for k in table.columns.keys():
            utk[table.columns[k].key] = k
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
            if self.sort_dir == "desc":
                columns.append(sql.desc(sort_on))
            else:
                columns.append(sort_on)
        # second, process model defaults
        sd_dir = sql.asc
        if self.default_sort_dir:
            if self.default_sort_dir == "desc":
                sd_dir = sql.desc
        if self.defaults_sort_on:
            for sort_on in self.defaults_sort_on:
                if sort_on not in sort_on_keys:
                    columns.append(sd_dir(sort_on))
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
        query = get_query(context)
        
        # !+DATE_FILTERS(mr, sep-2010) why so many date filters?
        # date_range filter (cookie)
        query = query_filter_date_range(context, self.request, query, 
            self.domain_model)
        # displayDate filter (request)
        filter_by = dateFilter(self.request)
        if filter_by:
            if (("start_date" in context._class.c) and 
                ("end_date" in context._class.c)
            ):
                # apply date range resrictions
                query = query.filter(filter_by)
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
    
    def get_cache_key(self, context, start, limit, lang):
        qs_params = tuple(
            self.request.get(name, default)
            for name, default in JSLCaches[context.__name__].qs_params
        )
        # as sort_dir may have a (overridable) model default, we treat 
        # it specially (note that sort_on may also have a model default, but
        # the values here accumulate, so for key uniqueness it suffices to 
        # only consider only the sort_on parameter in the request.
        return (lang, start, limit, self.sort_dir, qs_params)
        # !+ class name and context name are actually unnecessary to guarantee 
        # uniqueness for each item within *this* cache:
        #self.__class__.__name__, context.__name__,
    
    def __call__(self):
        # prepare required parameters
        start, limit = self.getOffsets()
        lang = self.request.locale.getLocaleID() # get_request_language()
        context = proxy.removeSecurityProxy(self.context)
        cache_key = self.get_cache_key(context, start, limit, lang)
        cache = JSLCaches[context.__name__].cache
        if not cache.has(cache_key):
            log.info("SETTING CACHE for key: %s" % (cache_key,))
            cache.set(cache_key, self.json_batch(start, limit, lang))
        return cache.get(cache_key)
    
    ''' 
    !+BATCH(mr, sep-2010) what was the reason that there be a 
        different getBatch() form the superclass's
    !+LISTINGS_CLASS(mr, sep-2010) if listings_class is not used here, 
        is it then superfluous?
    
    def getBatch(self, start=0, limit=20):
        context = proxy.removeSecurityProxy(self.context)
        mapper = orm.class_mapper(self.domain_model) 
        listing_class = getattr(self.domain_model, "listings_class", None)
        context_parent = proxy.removeSecurityProxy(context.__parent__)
        try:
            p_mapper = orm.class_mapper(context_parent.__class__)
            pk = p_mapper.primary_key_from_instance(context_parent)[0]
        except orm.exc.UnmappedClassError: 
            pk = None
        l_query = None
        if listing_class:
            session = Session()
            self.domain_model = listing_class
            l_query = session.query(listing_class)
        if listing_class and pk:
            # if we substituted a foreign key in our listing class with 
            # clear text we have to adjust our modifier accordingly
            # "_fk_" + field name is the convention
            _fk_fieldname = "_fk_%s" % (context.constraints.fk)
            if hasattr(listing_class, _fk_fieldname):
                modifier = getattr(listing_class, _fk_fieldname) == pk
            else:
                modifier = getattr(listing_class, context.constraints.fk) == pk
            l_query = l_query.filter(modifier)
        query = get_query(self.context,  self.request, l_query, 
            self.domain_model)
        
        # filters
        # workflow public states
        public_wfstates = getattr(self.domain_annotation, "public_wfstates", 
                None)
        if public_wfstates:
            query = query.filter(self.domain_model.status.in_(public_wfstates))
        query = self.query_add_filters(query, self.getFilter())
        
        # order_by
        order_by = self.getSort()
        if order_by:
            query = query.order_by(order_by)
        
        #query = query.limit(limit).offset(start) 
        #nodes = query.all()
        #self.set_size = query.count()
        # nodes: [<bungeni.models.domain.ListQuestion]
        nodes = self._get_secured_batch(query, start, limit)
        #
        # !+LIST_TRANSLATIONS(mr, sep-2010) the numerous derived domain objects, 
        # conventionally named "List<ClassName>", also should be translatable ?
        # There should be a way to map the i18n attributes of the derived object 
        # to use the translations for the master object...
        nodes = self.translate_objects(nodes)
        #batch = self._jsonValues(nodes, self.fields, self.context)
        batch = self._jsonValues(nodes, self.fields, self.context,
            self._get_anno_getters_by_field_name(self.context))
        return batch
    '''

# caches for json container listings

from evoque.collection import Cache

class JSLCache(object):
    """JSON Listing Cache"""
    def __init__(self, max_size, class_names, qs_params):
        """ max_size:int - max number of items to cache, 0 implies unlimited,
                oldest in excess of max are discarded
            class_names:[str] - name of target domain class
            qs_params:[(param_name:str, default:str)] - query string params
        """
        self.cache = Cache(max_size)
        self.class_names = class_names
        self.qs_params = qs_params

JSLCaches = {
    # /business/...
    "committees": JSLCache(99, ["Committee"], [
        ("sort", u""),
        ("filter_full_name", u""),
        ("filter_short_name", u""),
        ('filter_start_date', u""),
        ('filter_end_date', u""),
        ('filter_committee_type_id', u""),
    ]),
    "bills": JSLCache(99, ["Bill"], [
        ("sort", u""),
        ("filter_short_name", u""),
        ("filter_owner_id", u""),
        ("filter_submission_date", u""),
        ("filter_status", u""),
        ("filter_status_date", u""),
        ("filter_publication_date", u""),
    ]),
    "questions": JSLCache(199, ["Question", "Ministry"], [
        ("sort", u""),
        ("filter_short_name", u""),
        ("filter_owner_id", u""),
        ("filter_submission_date", u""),
        ("filter_status", u""),
        ("filter_status_date", u""),
        ("filter_question_number", u""),
        ("filter_ministry_id", u""),
    ]),
    "motions": JSLCache(99, ["Motion"], [
        ("sort", u""),
        ("filter_short_name", u""),
        ("filter_owner_id", u""),
        ("filter_submission_date", u""),
        ("filter_status", u""),
        ("filter_status_date", u""),
        ("filter_motion_number", u""),
    ]),
    "tableddocuments": JSLCache(99, ["TabledDocument"], [
        ("sort", u""),
        ("filter_short_name", u""),
        ("filter_owner_id", u""),
        ("filter_submission_date", u""),
        ("filter_status", u""),
        ("filter_status_date", u""),
    ]),
    "agendaitems": JSLCache(99, ["AgendaItem"], [
        ("sort", u""),
        ("filter_short_name", u""),
        ("filter_owner_id", u""),
        ("filter_submission_date", u""),
        ("filter_status", u""),
        ("filter_status_date", u""),
    ]),
    # sittings
    "preports": JSLCache(99, ["Report"], [
        ("sort", u""),
        ("filter_short_name", u""),
        ("filter_owner_id", u""),
        ("filter_submission_date", u""),
        ("filter_status", u""),
        ("filter_status_date", u""),
        ("filter_publication_date", u""),
        ("filter_note", u""),
    ]),
    "attendance": JSLCache(99, ["GroupSittingAttendance"], [
        ("sort", u""),
        ("filter_member_id", u""),
        ("filter_sitting_id", u""),
        ("filter_attendance_id", u""),
    ]),    
    # /members/...
    "current": JSLCache(99, 
        ["MemberOfParliament", "Constituency", "Province", "Region",
         "PoliticalParty"], [
        ("sort", u""),
        ("filter_user_id", u""),
        ("filter_elected_nominated", u""),
        ("filter_start_date", u""),
        ("filter_constituency_id", u""),
        ("filter_province_id", u""),
        ("filter_region_id", u""),
        ("filter_party_id", u""),
    ]),
    "political-groups": JSLCache(99, ["PoliticalGroup"], [
        ("sort", u""),
        ("filter_full_name", u""),
        ("filter_short_name", u""),
        ("filter_start_date", u""),
        ("filter_end_date", u""),
    ]),
    # /archive/browse/...
    "parliaments": JSLCache(99, ["Parliament"], [
        ("sort", u""),
        ("filter_full_name", u""),
        ("filter_short_name", u""),
        ("filter_start_date", u""),
        ("filter_end_date", u""),
    ]),
    "governments": JSLCache(99, ["Government"], [
        ("sort", u""),
        ("filter_short_name", u""),
        ("filter_start_date", u""),
        ("filter_end_date", u""),
    ]),
    "sessions": JSLCache(99, ["ParliamentSession"], [
        ("sort", u""),
        ("filter_short_name", u""),
        ("filter_start_date", u""),
        ("filter_end_date", u""),
    ]),
    "sittings": JSLCache(99, ["GroupSitting"], [
        ("sort", u""),
        ("filter_sitting_type_id", u""),
        ("filter_start_date", u""),
    ]),
    "committeestaff": JSLCache(99, ["CommitteeStaff"], [
        ("sort", u""),
        ("filter_user_id", u""),
        ("filter_short_name", u""),
    ]),
    "committeemembers": JSLCache(99, ["CommitteeMember"], [
        ("sort", u""),
        ("filter_user_id", u""),
        ("filter_short_name", u""),
    ]),
    "ministries": JSLCache(99, ["Ministry"], [
        ("sort", u""),
        ("filter_short_name", u""),
        ("filter_full_name", u""),
        ("filter_start_date", u""),
        ("filter_end_date", u""),
    ]),
    # politicalgroups -- same as for /members/political-groups
    # committees -- same as under /business/
    "constituencies": JSLCache(99, ["Parliament"], [
        ("sort", u""),
        ("filter_name", u""),
        ("filter_start_date", u""),
        ("filter_end_date", u""),
    ]),
}
# aliases for same JSLCache instances
# /browse/politicalgroups
JSLCaches["politicalgroups"] = JSLCaches["political-groups"] 
# /browse/constituencies/
JSLCaches["parliamentmembers"] = JSLCaches["current"] 
# /business/sittings/...
JSLCaches["sreports"] = JSLCaches["preports"]


def get_CacheByClassName():
    """ build mapping of class_name to caches to invalidate."""
    CacheByClassName = {} # {class_name: set(JSCache.cache)}
    for jslc in JSLCaches.values():
        for class_name in jslc.class_names:
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


