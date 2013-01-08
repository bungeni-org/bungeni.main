# encoding: utf-8
import os
from zope.i18n import translate
from zope.security import proxy
from zc.resourcelibrary import need
from zc.table import batching
from zope.app.pagetemplate import ViewPageTemplateFile
from ore import yuiwidget
from bungeni.ui import container
from bungeni.ui.i18n import _
from bungeni.ui.utils import url
from bungeni.ui.widgets import text_input_search_widget
from bungeni.capi import capi
import bungeni.alchemist
from bungeni.alchemist import utils
from bungeni.utils import naming

_path = os.path.split(os.path.abspath(__file__))[0]

class TableFormatter(batching.Formatter):
    """View-level (reloads page) batching.
    
    The out-of-box table formatter does not let us specify a custom
    table css class.
    
    
    !+ Currently being used by the Actions workflow, versions, attendace ui.
    """
    table_css_class = "listing grid"
    #!+zc.table(miano, March 2012) This template overrides the base
    # zc.table batching template to remove an invalid lang attibute from script
    # tag in batching.pt. This workaround should be removed once this bug 
    # is fixed in zc.table
    batching_template = ViewPageTemplateFile("templates/batching.pt")

    def __call__(self):
        return ("""
            <div>
                <table class="%s">
                 %s
                </table>
                %s
            </div>""" % (self.table_css_class,
                self.renderContents(), self.renderExtra()))


class ContextDataTableFormatter(yuiwidget.table.BaseDataTableFormatter):
    
    script = open("%s/templates/datatable.js" % (_path)).read()
    
    data_view = "/jsonlisting"
    prefix = "listing"
    _fields = None
    
    def getFields(self):
        if not self._fields:
            self._fields = bungeni.alchemist.container.getFields(self.context)
        return self._fields
    
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

    def get_search_widgets(self):
        script_html = ""
        script_js = ""
        domain_model = proxy.removeSecurityProxy(self.context).domain_model
        descriptor = utils.get_descriptor(domain_model)
        for field in descriptor.listing_columns:
            search_widget = descriptor.get(field).search_widget
            if search_widget:
                s_html, s_js = search_widget(self.prefix, field)
            else:
                s_html, s_js = text_input_search_widget(self.prefix, field)
            script_html += s_html
            script_js += s_js
        return script_html, script_js

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
        script_html, script_js = self.get_search_widgets()
        return '%s<div id="%s">\n%s%s</div>' % (script_html,
            self.prefix,
            self.script % self.getDataTableConfig(),
            script_js)


class AjaxContainerListing(container.AjaxContainerListing):
    formatter_factory = ContextDataTableFormatter

    @property
    def prefix(self):
        context = proxy.removeSecurityProxy(self.context)
        return "container_contents_%s" % (naming.as_identifier(context.__name__))


''' !+UNUSED(mr, nov-2011)
class SimpleContainerListing(table.Formatter):
    """Renders a simple listing of container elements using DC properties
    """
    def __call__(self, listing_title):
        return '\n<h1>%s</h1><table%s>\n%s</table>\n%s' % (
                listing_title, self._getCSSClass('table'), self.renderRows(),
                self.renderExtra())
'''

