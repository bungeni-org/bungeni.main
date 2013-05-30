# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni search implementation
- Searches eXist database via eXist rest service
See: https://code.google.com/p/bungeni-exist/wiki/BungeniRESTXQSearchService
"""
log = __import__("logging").getLogger("bungeni.ui.search")

import re
import json
import urllib2
import urllib
import dateutil.parser
import zope.interface
import zope.component
from zope.formlib import form, namedtemplate, widget
from zope.app.pagetemplate import ViewPageTemplateFile
from zc.resourcelibrary import need
from ploned.ui.interfaces import IBelowContentManager

from sqlalchemy.util import OrderedDict
from bungeni.alchemist.utils import get_managed_containers
from bungeni.core.interfaces import IWorkspaceTabsUtility, ISearchableSection

from bungeni.ui import interfaces as ui_ifaces, browser
from bungeni.ui.widgets import MultiCheckBoxWidget, TextWidget
from bungeni.ui.utils import common, date
from bungeni.ui.utils.url import absoluteURL
from bungeni.ui.i18n import _

import interfaces

from bungeni.models import interfaces as model_ifaces
from bungeni.models.settings import SearchSettings
from bungeni.feature.interfaces import IFeatureWorkspace

from bungeni.utils import register
from bungeni.utils.common import getattr_ancestry
from bungeni.capi import capi

class SearchTextWidget(TextWidget):
    def __call__(self):
        displayWidth = 90
        button_el = widget.renderElement("span", contents="&nbsp;", 
            id="advanced_options_button")
        advanced_input = widget.renderElement("input", name="advanced",
            value="true", contents="&nbsp;", hidden="true")
        return "%s<br/>%s" %(super(SearchTextWidget, self).__call__(),
            widget.renderElement("a", contents="%s%s%s" %(button_el, 
                advanced_input, _("advanced options")),
                id="show_advanced_options", href="javascript:;")
        )

def container_obj_key(key):
    return "obj-%s" % key

def make_workspace_url(obj_id, type_name, status, context, chamber_id):
    if obj_id and type_name and status:
        domain_class = capi.get_type_info(type_name).domain_model
        if IFeatureWorkspace.implementedBy(domain_class):
            ws_roles = common.get_workspace_roles()
            tabs_config = zope.component.getUtility(IWorkspaceTabsUtility)
            ti = capi.get_type_info(domain_class)
            tab = tabs_config.get_tab(ws_roles[0], domain_class, status)
            if tab:
                return "./my-documents/%s/%s-%s" %(
                    tab, ti.workflow_key, obj_id
                )

@common.request_cached
def get_parl_container(context, chamber_id):
    parl = None
    chamber_key = container_obj_key(chamber_id)
    container = getattr_ancestry(context, None, 
        acceptable=model_ifaces.IChamberContainer.providedBy)
    if not container:
        #check locally for container
        containers = get_managed_containers(context) or context.items()
        for key, local_container in containers:
            if model_ifaces.IChamberContainer.providedBy(local_container):
                container = local_container
                break
    try:
        parl = container[chamber_key]
    except KeyError:
        log.error("No such chamber was found with key %s", chamber_key)
    return parl

@common.request_cached
def get_chamber_containers(chamber):
    return get_managed_containers(chamber)

@common.request_cached
def get_type_container(chamber, type_name):
    info = capi.get_type_info(type_name)
    containers = get_chamber_containers(chamber)
    for key, container in containers:
        if isinstance(container, info.domain_model):
            return container

def make_admin_url(obj_id, type_name, status, context, chamber_id):
    """Use traversal to find parent parliament
    """
    url = None
    chamber = get_parl_container(context, chamber_id)
    if chamber:
        items_container = get_type_container(chamber, type_name)
        if items_container:
            url = "/".join([ 
                absoluteURL(items_container, common.get_request()),
                container_obj_key(obj_id)
            ])
    return url

SEARCH_WORKSPACE = "ws"
SEARCH_ADMIN = "ad"
URL_MAKERS = {
    SEARCH_WORKSPACE : make_workspace_url,
    SEARCH_ADMIN : make_admin_url
}
DEFAULT_URL_MAKER = make_workspace_url

SEARCH_URL = "http://localhost:8088/exist/restxq/ontology_bungeni"

BASE_MAPPING = {
    "status": "status",
    "type": "docType"
}
MAPPING = {
    "document": {
        "title": "title",
        "author": ["owner", "person", "showAs"],
        "status_date": "statusDate",
    },
    "group": {
        "title": "fullName"
    }
}

@common.request_cached
def get_formatter():
    return date.getLocaleFormatter(common.get_request(), "date")

def format_date(val):
    _date = dateutil.parser.parse(val)
    return get_formatter().format(_date)

CUSTOM_FORMATTERS = {
    "statusDate": format_date
}

def get_node_value(root, key):
    if isinstance(key, list):
        val = None
        ctx = root
        for k in key:
            val = ctx.get(k)
            ctx = val
        return val
    node = root.get(key, None)
    val = None
    if node:
        if node.has_key("#text"):
            val = node.get("#text")
        elif node.has_key("showAs"):
            val = node.get("showAs")
        elif node.has_key("value"):
            val = node.get("value").get("#text")
    if val:
        formatter = CUSTOM_FORMATTERS.get(key, None)
        if formatter:
            val = formatter(val)
    return val

def get_results_meta(items_list, context, search_context=SEARCH_WORKSPACE):
    """return a dict of fields for display
    """
    items = []
    url_maker = URL_MAKERS.get(search_context, DEFAULT_URL_MAKER)
    for result in items_list:
        ontology = result.get("ontology")
        result_type = ontology.get("for")
        record = ontology.get(result_type)
        chamber_id = ontology.get("chamber").get("parliamentId").get("select")
        item = {}
        #unique ids take this form Legislature.9-Chamber.2-AgendaItem.54
        unique_id = record.get("unique-id")
        type_name, obj_key = unique_id.split("-")[-1].split(".")
        status_key = record.get("status").get("value").get("#text")
        item["type"] = type_name
        type_key = ontology.get("document").get("type").get("value").get("#text")
        item["url"] = url_maker(obj_key, type_key, status_key, context, chamber_id)
        MAP = BASE_MAPPING.items() + MAPPING.get(result_type, []).items()
        for (key, node_key) in MAP:
            item[key] = get_node_value(record, node_key)
            
        items.append(item) 
    return items

def make_pages(item_count, offset, next_offset, limit):
    num_pages = item_count/limit + int(bool(item_count%limit))
    return list(xrange(1, num_pages+1))

def get_search_url():
    return SearchSettings(common.get_application()).search_uri

def execute_search(data, prefix, request, context):
    data = dict([(key, 
        (",".join(value) if isinstance(value, list) else value))
        for key,value in data.iteritems() if value])
    #set default search types (context-aware) if none is set in form
    if data.get("type") is None:
        data["type"] = [tp for tp in 
            interfaces.search_document_types(context)][0].value
    if data.get("page"):
        limit = data.get("limit", interfaces.DEFAULT_LIMIT)
        data["offset"] = (int(data["page"])-1)*int(limit)+1
        del data["page"]
    # we are only interested in documents
    data["group"]  = "document"
    search_request = urllib2.Request(SEARCH_URL, urllib.urlencode(data))
    exist_results = json.loads(urllib2.urlopen(search_request).read())
    item_count = int(exist_results.get("total"))
    page_query_string = request.get("QUERY_STRING")
    page_query_string = re.sub("&page=\d+", "", page_query_string)
    results = {
        "total": item_count,
        "items": [],
        "current_page": int(exist_results.get("offset")),
        "pages": make_pages(item_count, int(exist_results.get("offset")),
            int(exist_results.get("next-offset")),
            int(exist_results.get("limit"))),
        "page_query_string": page_query_string
    }
    if item_count:
        _results = exist_results.get("doc")
        if item_count == 1:
            _results = [_results]
        if ui_ifaces.IAdminSectionLayer.providedBy(request):
            results["items"] = get_results_meta(_results, 
                context, SEARCH_ADMIN)
        else:
            results["items"] = get_results_meta(_results, context)
    return results

str_all_types = _("all types")
def get_search_types(types):
    """string of all searched types (for display)"""
    _types = str_all_types
    if types and not ("," in types[0]):
        type_names = []
        for typ in types:
            info = capi.get_type_info(typ)
            type_names.append(info.descriptor_model.container_name)
        _types = ", ".join(type_names)
    return _types


SEARCH_VIEW = "search"
@register.view(ISearchableSection, ui_ifaces.IBungeniSkin, 
    name=SEARCH_VIEW, protect={ "zope.Public": register.VIEW_DEFAULT_ATTRS })
class Search(form.PageForm, browser.BungeniBrowserView):
    action_method="get"
    template = namedtemplate.NamedTemplate("alchemist.form")
    form_fields = form.FormFields(interfaces.ISearchRequest)
    form_fields["search"].custom_widget = SearchTextWidget
    form_fields["type"].custom_widget = MultiCheckBoxWidget
    #form_fields["group"].custom_widget = MultiCheckBoxWidget
    form_name = _(u"Bungeni Search")
    form_description = _(u"Search Documents in Bungeni")
    show_results = False

    def __init__(self, context, request):
        super(Search, self).__init__(context, request)

    def setUpWidgets(self, ignore_request=False):
        self.widgets = form.setUpInputWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            ignore_request=ignore_request,
            )

    def widget_groups(self):
        wdgt_groups = OrderedDict()
        wdgt_groups["search_text"] = [ self.widgets.get("search") ]
        wdgt_groups["advanced_opts"] = [ widget for widget in self.widgets if
            widget.context.getName() != "search" ]
        return wdgt_groups

    def legends(self):
        return { "advanced_opts": _("advanced options") }

    @form.action(_(u"Search"), name="execute-search")
    def handle_search(self, action, data):
        self.show_results = True
        #data["role"] = \
        #    common.get_context_roles(self.context, self.request.principal) + \
        #    common.get_workspace_roles() + ["bungeni.Anonymous"]
        data["page"] = self.request.form.get("page", 1)
        self.search_results = execute_search(data, self.prefix, 
            self.request, self.context)
        self.status = _("Searched for '${search_string}' and found ${count} "
            "items. Searched in ${search_types}.", 
            mapping={ 
                "search_string": data.get("search") or _("everything"), 
                "count": self.search_results.get("total"),
                "search_types": get_search_types(data.get("type")),
            }
        )

    def validate(self, action, data):
        return form.getWidgetsData(self.widgets, self.prefix, data)
    
    def __call__(self):
        need("search-js")
        need("search-css")
        return super(Search, self).__call__()

@register.viewlet(ISearchableSection, layer=ui_ifaces.IBungeniSkin,
    manager=IBelowContentManager, name="bungeni.exist-search",
    protect=register.PROTECT_VIEWLET_PUBLIC)
class SearchResults(browser.BungeniViewlet):
    """Report preview."""
    
    render = ViewPageTemplateFile("results.pt")
    
    def update(self):
        if self.available:
            self.search_results = self._parent.search_results

    @property
    def available(self):
        return (isinstance(self._parent, Search) and 
            self._parent.show_results)

class SearchBox(browser.BungeniViewlet):
    """Search box Viewlet"""

    render = ViewPageTemplateFile("search-box.pt")


    @property
    def search_section(self):
        return getattr_ancestry(self.context, None,
            acceptable=ISearchableSection.providedBy)

    @property
    def available(self):
        return self.search_section is not None

    def update(self):
        self.action_url =  "/".join([
            absoluteURL(self.search_section, self.request), SEARCH_VIEW])
        self.show_advanced_link = (self.action_url != self.request.getURL())
