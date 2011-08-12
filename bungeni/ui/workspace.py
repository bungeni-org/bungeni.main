import time
import simplejson
from sqlalchemy import types
from zope import component
from zope.publisher.browser import BrowserView
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy
from zope.formlib import form
from zope.i18n import translate
from zope.event import notify
from zope.lifecycleevent import ObjectCreatedEvent
from z3c.pt.texttemplate import ViewTextTemplateFile
from ore.alchemist import container
from alchemist.ui import generic
from bungeni.models import workspace
from bungeni.core import translation
from bungeni.core.i18n import _
from bungeni.core.interfaces import IWorkspaceTabsUtility
from bungeni.ui.container import query_iterator
from bungeni.ui.utils import url
from bungeni.ui import table
from bungeni.ui.interfaces import IWorkspaceContentAdapter
from bungeni.ui.forms.common import AddForm
from bungeni.ui.container import ContainerJSONListing

class WorkspaceField(object):
    def __init__(self, name, title):
        self.name = name
        self.title = title
    def query(item):
        return getattr(IWorkspaceContentAdapter(item), name, None)

# These are the columns to be displayed in the workspace
workspace_fields = [WorkspaceField("title", _("title")), 
                    WorkspaceField("item_type", _("item type")), 
                    WorkspaceField("status", _("status")),
                    WorkspaceField("status_date", _("status date"))]

class WorkspaceContainerJSONListing(BrowserView):
    """Paging, batching, json contents of a workspace container.
    """
    #results.sort(key = lambda x: x.status_date, reverse=True)
    permission = "zope.View"
    def __init__(self, context, request):
        super(WorkspaceContainerJSONListing, self).__init__(context, request)
        self.defaults_sort_on = "status_date"
        if not self.request.get("sort"):
            self.request.form["sort"] = u"sort_%s" % (self.defaults_sort_on)
        self.sort_on = self.request.get("sort")
        # sort_dir: "desc" | "asc"
        # pick off request, if necessary setting it from default in 
        if not self.request.get("dir"):
            self.request.form["dir"] = "desc"
        self.sort_dir = self.request.get("dir")         
    
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
        
    def json_batch(self, start, limit, lang):
        batch = self.getBatch(start, limit, lang)
        data = dict(
            length=self.set_size, # total result set length, set in getBatch()
            start=start,
            recordsReturned=len(batch),
            nodes=batch
        )
        return simplejson.dumps(data)
        
    def _jsonValues(self, nodes):
        values = []
        for node in nodes:
            d = {}
            for field in workspace_fields:
                d[field.name] = getattr(IWorkspaceContentAdapter(node),
                                                            field.name, None)
            d["object_id"] = url.set_url_context(node.__name__)
            values.append(d)
        return values

    def get_status_date_filters(self):
        if self.request.get("filter_status_date"):
            dates = self.request.get("filter_status_date").split(" ")
        if dates and len(dates) == 2:
            try:
                date_from = time.strptime(dates[0], "%Y/%m/%d")
                date_to = time.strptime(dates[1], "%Y/%m/%d")
            except:
                return None
            return date_from, date_to
        else:
            return None

    def filter_title(self):
        
        if title_filter:
            return title_filter
        else:
            return None
    
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

    def getBatch(self, start=0, limit=25, lang=None):
        context = removeSecurityProxy(self.context)
        filter_title = self.request.get("filter_title") if \
            self.request.get("filter_title") else None
        filter_item_type = self.request.get("filter_item_type") if \
            self.request.get("filter_item_type") else None
        filter_status = self.request.get("filter_status") if \
            self.request.get("filter_status") else None
        query = context._query(title_filter = filter_title,
                              item_type_filter = filter_item_type,
                              status_filter = filter_status)
        #import pdb; pdb.set_trace()
        nodes = [container.contained(ob, self, workspace.stringKey(ob)) 
                 for ob in query]
        self.set_size = len(nodes)
        nodes[:] = nodes[start : start + limit]
        nodes = self.translate_objects(nodes, lang)
        batch = self._jsonValues(nodes)
        return batch
    
    def __call__(self):
        # prepare required parameters
        start, limit = self.getOffsets() # ? start=0&limit=25
        lang = self.request.locale.getLocaleID() # get_request_language()
        return self.json_batch(start, limit, lang)
        
class WorkspaceDataTableFormatter(table.ContextDataTableFormatter):
    data_view = "/jsonlisting"
    script = ViewTextTemplateFile("templates/datatable-workspace.pt")
    def getFieldColumns(self):
        column_model = []
        field_model  = []
        
        for field in workspace_fields:
            coldef = {"key": field.name,
                      "label": translate(_(field.title), context=self.request), 
                      "formatter": self.context.__name__ 
            }
            '''if column_model == []:
                column_model.append(
                    """{key:"%(key)s", label:"%(label)s", 
                    formatter:"%(formatter)sCustom", sortable:false, 
                    minWidth:200, resizeable:true}""" % coldef
                    )
            else:
                column_model.append(
                    """{key:"%(key)s", label:"%(label)s", 
                    sortable:false, resizeable:true, minWidth:150}""" % coldef
                    )'''
                    
            if column_model == []:
                column_model.append(
                    """{label:"%(label)s", key:"sort_%(key)s", 
                    formatter:"%(formatter)sCustom", sortable:true, 
                    resizeable:true ,
                    children: [ 
	                { key:"%(key)s", sortable:false}]}""" % coldef
                    )
            else:
                column_model.append(
                    """{label:"%(label)s", key:"sort_%(key)s", 
                    sortable:true, resizeable:true,
                    children: [ 
	                {key:"%(key)s", sortable:false}]
                    }""" % coldef
                    )
            field_model.append('{key:"%s"}' % (field.name))
        return ",".join(column_model), ",".join(field_model)


        

class WorkspaceContainerListing(BrowserView):
    template = ViewPageTemplateFile("templates/workspace-listing.pt")
    formatter_factory = WorkspaceDataTableFormatter
    
    columns = []      
    
    def __call__( self ):
        self.context = removeSecurityProxy(self.context)
        return self.template()
    
    def update(self):
        for field in workspace_fields:
            self.columns.append(
                column.GetterColumn( title=field.name,
                                 getter = Getter( field.query ) ) )
    
    def listing( self ):
        return self.formatter()
    
    @property
    def formatter(self):
        context = removeSecurityProxy(self.context)
        formatter = self.formatter_factory(
            context,
            self.request,
            (),
            prefix="workspace",
            columns=self.columns,
        )
        formatter.cssClasses["table"] = "listing"
        formatter.table_id = "datacontents"
        return formatter
        
class WorkspaceAddForm(AddForm):

    #from alchemist.ui.content
    def createAndAdd( self, data ):
        domain_model = removeSecurityProxy( self.domain_model )
        # create the object, inspect data for constructor args      
        try:  
            ob = generic.createInstance( domain_model, data )
        except TypeError:
            ob = domain_model()
        # apply any context values
        self.finishConstruction( ob )
        # apply extra form values
        form.applyChanges( ob, self.form_fields, data, self.adapters )
        # add ob to container
        self.context[""] = ob
        # fire an object created event
        notify(ObjectCreatedEvent(ob))
        # signal to add form machinery to go to next url
        self._finished_add = True
        name = workspace.stringKey(ob)
        return self.context.get(name)
        
    @property
    def domain_model(self):
        item_type = self.__name__.split("_")[1]
        workspace_config = component.getUtility(IWorkspaceTabsUtility)
        domain = workspace_config.getDomain(item_type)
        return domain
        
    def getDomainModel(self):
        return getattr(self, "domain_model", self.context.__class__)        
    
