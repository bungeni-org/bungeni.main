# encoding: utf-8

from ore import yuiwidget

from bungeni import alchemist
from bungeni.ui import container
from bungeni.ui.i18n import _
from zope.i18n import translate
from zope.security import proxy
from zc.resourcelibrary import need
from zc.table import batching

from z3c.pt.texttemplate import ViewTextTemplateFile
#from bungeni.ui import z3evoque
from bungeni.ui.utils import url


class TableFormatter(batching.Formatter):
    """The out-of-box table formatter does not let us specify a custom
    table css class.
    
    !+ This is currently being used by the Actions workflow and versions views:
    bungeni/ui/versions.py
    bungeni/ui/workflow.py
    """
    
    table_css_class = "listing grid"
    
    def __call__(self):
        return ("""
            <div>
                <table class="%s" name="%s">
                 %s
                </table>
                %s
            </div>""" % (self.table_css_class, self.prefix, 
                self.renderContents(), self.renderExtra()))


class ContextDataTableFormatter(yuiwidget.table.BaseDataTableFormatter):
    
    # evoque
    #script = z3evoque.PageViewTemplateFile("container.html#datatable")
    # !+NEED_ZC_RESOURCE_LIBRARIES(mr, sep-2010)
    # Evoque rendering needs to take into account any zc.resourcelibrary 
    # declared additional libs, declared with need() below, see:
    # zc.resourcelibrary.publication.Response._addDependencies
    
    # zpt
    script = ViewTextTemplateFile("templates/datatable.pt")
    
    data_view ="/jsonlisting"
    prefix = "listing"
    
    def getFields(self):
        return alchemist.container.getFields(self.context)

    def getFieldColumns(self):
        # get config for data table
        column_model = []
        field_model  = []
        
        for field in self.getFields():
            key = field.__name__
            title =translate(_(field.title), context=self.request)
            coldef = {"key": key, "label": title, "formatter": self.context.__name__ 
            }
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
            field_model.append('{key:"%s"}' % (key))
        return ",".join(column_model), ",".join(field_model)
    
    def getDataTableConfig(self):
        config = {}
        config["columns"], config["fields"] = self.getFieldColumns()
        config["data_url"] = self.getDataSourceURL()
        config["table_id"] = self.prefix
        config["link_url"] = url.absoluteURL(self.context, self.request)
        config["context_name"] = self.context.__name__
        return config
    
    def __call__(self):
        need("yui-paginator")
        need("yui-dragdrop")
        return '<div id="%s">\n<table %s>\n%s</table>\n%s</div>' % (
            self.prefix,
            self._getCSSClass("table"),
            self.renderContents(),
            self.script(**self.getDataTableConfig()))


class AjaxContainerListing(container.AjaxContainerListing):
    formatter_factory = ContextDataTableFormatter
    
    @property
    def prefix(self):
        context = proxy.removeSecurityProxy(self.context)
        return "container_contents_%s" % (context.__name__)

