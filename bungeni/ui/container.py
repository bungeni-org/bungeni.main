log = __import__("logging").getLogger("bungeni.ui.container")

import datetime
import zc.table
import simplejson
import sqlalchemy.sql.expression as sql
from sqlalchemy import types, orm

from zope import interface
from zope import component
from zope.security import proxy
from zope.security import checkPermission
from zope.security.proxy import ProxyFactory
from zope.publisher.browser import BrowserView
from zope.annotation.interfaces import IAnnotations

from ore.alchemist import Session
from ore.alchemist.model import queryModelDescriptor
from ore.alchemist.model import queryModelInterface
from ore.alchemist.container import contained
from ore.alchemist.container import stringKey

from alchemist.ui import container
from bungeni.models.interfaces import IDateRangeFilter
from bungeni.models.interfaces import ICommitteeContainer
from bungeni.models.interfaces import IMemberOfParliamentContainer
from bungeni.models.interfaces import ICommitteeMemberContainer
from bungeni.models.interfaces import ICommitteeStaffContainer

from bungeni.core.translation import translate_obj

from bungeni.ui.utils import url, date, debug
from bungeni.ui.cookies import get_date_range
from bungeni.ui.interfaces import IBusinessSectionLayer, IMembersSectionLayer


def dateFilter(request):
    filter_by = ""
    displayDate = date.getDisplayDate(request)
    if displayDate:
        filter_by = date.getFilter(displayDate)
    else:
        filter_by = ""
    return filter_by


def getFields(context):
    """ get all fields that will be displayed 
    in a containerlisting 
    """
    domain_model = proxy.removeSecurityProxy(context.domain_model)
    domain_interface = queryModelInterface(domain_model)
    domain_annotation = queryModelDescriptor(domain_interface)
    for column in  domain_annotation.listing_columns:
        field = domain_interface[column]
        yield field


def secured_iterator(permission, query, parent):
    for item in query:
        item.__parent__ = parent
        proxied = ProxyFactory(item)
        if checkPermission(u"zope.View", proxied):
            yield item


def get_query(context, request, query=None, domain_model=None):
    """Prepare query.

    If the model has start- and end-dates, constrain the query to
    objects appearing within those dates.
    """
    unproxied = proxy.removeSecurityProxy(context)
    model = unproxied.domain_model
    session = Session()
    if not query:
        query = unproxied._query
    if (
        (IBusinessSectionLayer.providedBy(request) and
            ICommitteeContainer.providedBy(context)) or 
        (IMembersSectionLayer.providedBy(request) and
            IMemberOfParliamentContainer.providedBy(context)) or 
        (IBusinessSectionLayer.providedBy(request) and
            ICommitteeMemberContainer.providedBy(context)) or 
        (IBusinessSectionLayer.providedBy(request) and
            ICommitteeStaffContainer.providedBy(context))
    ):
        start_date = datetime.date.today()
        end_date = None
    else:
        start_date, end_date = get_date_range(request)
    if start_date or end_date:
        date_range_filter = component.getSiteManager().adapters.lookup(
            (interface.implementedBy(model),), IDateRangeFilter)
        if start_date is None:
            start_date = datetime.date(1900, 1, 1)
        if end_date is None:
            end_date = datetime.date(2100, 1, 1)
        if domain_model:
            model=domain_model
        if date_range_filter is not None:
            query = query.filter(date_range_filter(model)).params(
                start_date=start_date, end_date=end_date)
    return query


class ContainerListing(container.ContainerListing):
    
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
        query = secured_iterator("zope.View", query, self.context)
        
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


class WorkspaceRootRedirect(BrowserView):
    """Redirect to the the "pi" view of the user's *first* workspace OR for the 
    case on no workspaces, to "/workspace".
    """
    def __call__(self):
        request = self.request
        try: 
            first_workspace = IAnnotations(request)["layer_data"].workspaces[0]
            to_url = "/workspace/obj-%s/pi" % first_workspace.group_id
        except:
            to_url = "/workspace"
        # !+TRAILING_SLASH(mr, sep-2010) this is still needed?
        to_url = url.set_url_context(to_url)
        if url.get_destination_url_path(request) != to_url:
            # never redirect to same destination!
            log.warn("WorkspaceRootRedirect %s -> %s" % (request.getURL(), to_url))
            request.response.redirect(to_url)
        else:
            # !+
            # user has no workspaces and is requesting /workspace view
            # return the "no workspace" *rendered* view for /workspace
            return component.getMultiAdapter(
                        (self.context, request), name="no-workspace-index")()


class _IndexRedirect(BrowserView):
    """Redirect to the named "index" view."""
    index_name = "index"
    def __call__(self):
        request = self.request
        log.warn("%s: %s -> %s" % (
            self.__class__.__name__, request.getURL(), self.index_name))
        request.response.redirect(self.index_name)
class WorkspaceContainerIndexRedirect(_IndexRedirect):
    # !+TRAILING_SLASH(mr, sep-2010) this is still needed?
    index_name = url.set_url_context("pi")
class BusinessIndexRedirect(_IndexRedirect):
    index_name = "whats-on"
class MembersIndexRedirect(_IndexRedirect):
    index_name = "current"
class ArchiveIndexRedirect(_IndexRedirect):
    index_name = "browse"
class AdminIndexRedirect(_IndexRedirect):
    index_name = "content"


class ContainerJSONTableHeaders(BrowserView):

    def __call__(self):
        fields = getFields(self.context)
        th = []
        for field in fields:
            th.append({"name":  field.__name__, "title": field.title})
        return simplejson.dumps(th)


class ContainerJSONListing(BrowserView):
    """Paging, batching, sorting, json contents of a container.
    """
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
    
    def _getFilterStr(self, fieldname, field_filters, operator):
        """If we are filtering for replaced fields we assume 
        that they are character fields.
        """
        fs = "" # filter string
        for f in field_filters:
            if len(fs) > 0:
                fs += operator
            else:
                fs = "("
            fs += "lower(%s) LIKE '%%%s%%' " % (fieldname, f.lower())
        if len(fs) > 0:
            fs += ")"
        return fs
    
    def getFilter(self):
        """ () -> str
        """
        fs = [] # filter string
        domain_model = proxy.removeSecurityProxy(self.context.domain_model)
        table = orm.class_mapper(self.domain_model).mapped_table
        utk = {}
        for k in table.columns.keys():
            utk[table.columns[k].key] = k
        for field in getFields(self.context):
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
                if getattr(domain_model, "sort_replace", None):
                    if fn in domain_model.sort_replace.keys():
                        rfs = [] # replace filter string
                        op, ffs = self._get_operator_field_filters(ff)
                        # sort_replace field_names
                        for srfn in (domain_model.sort_replace[fn]):
                            if rfs:
                                rfs.append(op)
                            else:
                                rfs.append(" (")
                            rfs.append(self._getFilterStr(srfn, ffs, " OR "))
                        if rfs:
                             rfs.append(") ")
                        fs.extend(rfs)
                        continue
                if fn in utk:
                    if kls in (types.String, types.Unicode):
                        op, ffs = self._get_operator_field_filters(ff)
                        fs = [self._getFilterStr(str(column), ffs, op)]
                    elif kls in (types.Date, types.DateTime):
                        f_name = "to_char(%s, 'YYYY-MM-DD')" % (column)
                        fs = [self._getFilterStr(f_name, [ff], "")]
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
        default_sort = None
        sort_key = self.request.get("sort")
        sort_dir = self.request.get("dir")
        domain_model = proxy.removeSecurityProxy(self.context.domain_model)
        table = orm.class_mapper(self.domain_model).mapped_table
        utk = {}
        for k in table.columns.keys():
            utk[table.columns[k].key] = k
        if sort_key:
            sort_key = sort_key[5:]
        sort_keys = []
        # in the domain model you may replace the sort with another column
        sort_replace = getattr(domain_model, "sort_replace", None) # dict
        if sort_replace and (sort_key in sort_replace):
            sort_keys = sort_replace[sort_key]
        elif sort_key and (sort_key in utk):
            sort_keys = [str(table.columns[utk[sort_key]])]
        
        for sort_key in sort_keys:
            if sort_dir == "desc":
                columns.append(sql.desc(sort_key))
            else:
                columns.append(sort_key)
        
        sort_defaults = getattr(domain_model, "sort_on", None)
        sort_default_dir = getattr(domain_model, "sort_dir", None)
        sd_dir = sql.asc
        if sort_default_dir:
            if sort_default_dir == "desc":
                sd_dir = sql.desc
        if sort_defaults:
            for sort_key in sort_defaults:
                if sort_key not in sort_keys:
                    columns.append(sd_dir(sort_key))
        return columns
    
    def getOffsets(self):
        nodes = []
        start, limit = self.request.get("start",0), self.request.get("limit", 25)
        try:
            start, limit = int(start), int(limit)
            if not limit:
                limit = 100
        except ValueError:
            start, limit = 0, 100
        return start, limit 

    def _get_secured_batch(self, query, start, limit):
        secured_query = secured_iterator("zope.View", query, self.context)
        nodes = []
        for ob in secured_query:
            ob = contained(ob, self, stringKey(ob))
            nodes.append(ob)
        self.set_size = len(nodes)
        return nodes[start : start + limit]
    
    def _get_anno_getters_by_field_name(self, context):
        domain_model = proxy.removeSecurityProxy(context.domain_model)
        domain_interface = queryModelInterface(domain_model)
        domain_annotation = queryModelDescriptor(domain_interface)
        # dict of domain_annotation field getters by name, for fast lookup
        return dict([ 
            (da_field.name, getattr(da_field.listing_column, "getter", None)) 
            for da_field in domain_annotation.fields
        ])
    
    def _jsonValues(self, nodes, fields, context, getters_by_field_name={}):
        """
        filter values from the nodes to respresent in json, currently
        that means some footwork around, probably better as another
        set of adapters.
        """
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
    # replaces the logic in:
    #   - alchemist.ui.container.ContainerJSONListing.getBatch()
    #   - ore.alchemist.container.AlchemistContainer.batch()
    def getBatch(self, start=0, limit=20):
        context = proxy.removeSecurityProxy(self.context)
        query = get_query(self.context, self.request)
        # filters
        filter_by = dateFilter(self.request)
        if filter_by:
            if (("start_date" in context._class.c) and 
                ("end_date" in context._class.c)
            ):
                # apply date range resrictions
                query = query.filter(filter_by)
        query = self.query_add_filters(query, self.getFilter())
        # order_by
        order_by = self.getSort()
        if order_by:
            query = query.order_by(order_by)
        
        # ore.alchemist.container.AlchemistContainer.batch()
        # nodes: [<bungeni.models.domain.Question]
        nodes = self._get_secured_batch(query, start, limit)
        nodes = self.translate_objects(nodes)
        batch = self._jsonValues(nodes, self.fields, self.context,
            self._get_anno_getters_by_field_name(self.context))
        return batch
    
    def translate_objects(self, nodes):
        """ (nodes:[ITranslatable]) -> [nodes]
        """
        import sys
        t_nodes = []
        for node in nodes:
            try:
                t_nodes.append(translate_obj(node))
            except (AssertionError,): # node is not ITranslatable
                debug.log_exc_info(sys.exc_info(), log_handler=log.warn)
                t_nodes.append(node)
        return t_nodes
    
    def __call__(self):
        context = proxy.removeSecurityProxy(self.context)
        self.domain_model = context.domain_model
        self.domain_interface = queryModelInterface(self.domain_model)
        self.domain_annotation = queryModelDescriptor(self.domain_interface)
        session = Session()
        self.set_size = 0
        self.fields = list(getFields(self.context))
        start, limit = self.getOffsets()
        batch = self.getBatch(start, limit)
        data = dict(
            length=self.set_size,
            start=start,
            recordsReturned=len(batch),
            sort=self.request.get("sort"),
            dir=self.request.get("dir", "asc"),
            nodes=batch
        )
        session.close()
        return simplejson.dumps(data)


class ContainerWFStatesJSONListing(ContainerJSONListing):
    
    def query_add_filters(self, query, *filter_strings):
        """Add filtering on public_wfstates
        """
        public_wfstates = getattr(self.domain_annotation, "public_wfstates", 
            None)
        if public_wfstates:
            query = query.filter(self.domain_model.status.in_(public_wfstates))
        return super(ContainerWFStatesJSONListing, self
            ).query_add_filters(query, *filter_strings)
    
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

