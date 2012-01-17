# encoding: utf-8
from zope.i18n import translate
from zope.security import proxy
from zc.resourcelibrary import need
from zc.table import batching
from zope.app.pagetemplate import ViewPageTemplateFile
from ore import yuiwidget
from bungeni import alchemist
from bungeni.ui import container
from bungeni.ui.i18n import _
from bungeni.ui.utils import url
from bungeni.utils.capi import capi


'''!+UNUSED(mr, jan-2012)
import zope.formlib
from zc.table import column
from bungeni.ui.utils import common
class LinkColumn(column.GetterColumn):
    def renderCell(self, item, formatter):
        abs_url = url.absoluteURL(item, common.get_request())
        title = super(LinkColumn, self).renderCell(item, formatter)
        if abs_url:
            link_html = zope.formlib.widget.renderElement("a",
                contents=title, href=abs_url
            )
            return zope.formlib.widget.renderElement("p",
                contents=link_html
            )
        return title
'''


class TableFormatter(batching.Formatter):
    """View-level (reloads page) batching.
    
    The out-of-box table formatter does not let us specify a custom
    table css class.
    
    
    !+ Currently being used by the Actions workflow, versions, attendace ui.
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
    script = ViewPageTemplateFile("templates/datatable.pt")

    data_view = "/jsonlisting"
    prefix = "listing"

    def getFields(self):
        return alchemist.container.getFields(self.context)

    def getFieldColumns(self):
        # get config for data table
        column_model = []
        field_model = []
        for field in self.getFields():
            key = field.__name__
            title = translate(_(field.title), context=self.request)
            coldef = {"key": key, "label": title,
                      "formatter": self.context.__name__}
            if column_model == []:
                column_model.append(
                    """{label:"%(label)s", key:"sort_%(key)s",
                    formatter:"%(formatter)sCustom", sortable:true,
                    resizeable:true ,
                    children: [{ key:"%(key)s", sortable:false}]}""" % coldef
                    )
            else:
                column_model.append(
                    """{label:"%(label)s", key:"sort_%(key)s",
                    sortable:true, resizeable:true,
                    children: [{key:"%(key)s", sortable:false}]}""" % coldef
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
        config["rows_per_page"] = capi.default_number_of_listing_items
        return config

    def __call__(self):
        need("yui-paginator")
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


''' !+UNUSED(mr, nov-2011)
class SimpleContainerListing(table.Formatter):
    """Renders a simple listing of container elements using DC properties
    """
    def __call__(self, listing_title):
        return '\n<h1>%s</h1><table%s>\n%s</table>\n%s' % (
                listing_title, self._getCSSClass('table'), self.renderRows(),
                self.renderExtra())
'''

