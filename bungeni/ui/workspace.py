import datetime
import simplejson
from zope.publisher.browser import BrowserView
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy
from zope.formlib import form
from zope.security.proxy import removeSecurityProxy
from zope.i18n import translate
from z3c.pt.texttemplate import ViewTextTemplateFile
from ore import yuiwidget
from ore.alchemist import container
from bungeni.models import workspace
from bungeni.core import translation
from bungeni.core.i18n import _
from bungeni.ui.container import query_iterator
from bungeni.ui.utils import url
from bungeni.ui.container import query_iterator
from bungeni.ui.container import ContainerJSONListing
from bungeni.ui import table
from bungeni.ui.interfaces import IWorkspaceAdapter
class WorkspaceField(object):
    def __init__(self, name, title):
        self.name = name
        self.title = title
    def query(item):
        return getattr(IWorkspaceAdapter(item), name, None)

# These are the columns to be displayed in the workspace
workspace_fields = [WorkspaceField("title", _("title")), 
                    WorkspaceField("item_type", _("item type")), 
                    WorkspaceField("status", _("status")),
                    WorkspaceField("status_date", _("status date"))]

class WorkspaceContainerJSONListing(BrowserView):
    """Paging, batching, json contents of a workspace container.
    """
    permission = "zope.View"
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
                d[field.name] = getattr(IWorkspaceAdapter(node), field.name, None)
            d["object_id"] = url.set_url_context(node.__name__)
            values.append(d)
        return values
        
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
        
    def getBatch(self, start=0, limit=20, lang=None):
        context = removeSecurityProxy(self.context)
        nodes = [container.contained(ob, self, workspace.stringKey(ob)) 
                 for ob in query_iterator(context._query, self.context, self.permission)]
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
            coldef = {"key": field.name, "label": translate(_(field.title), context=self.request), "formatter": self.context.__name__ 
            }
            if column_model == []:
                column_model.append(
                    """{key:"%(key)s", label:"%(label)s", 
                    formatter:"%(formatter)sCustom", sortable:false, minWidth:200,
                    resizeable:true}""" % coldef
                    )
            else:
                column_model.append(
                    """{key:"%(key)s", label:"%(label)s", 
                    sortable:false, resizeable:true, minWidth:150}""" % coldef
                    )
                    
            '''if column_model == []:
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
                    )'''
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
