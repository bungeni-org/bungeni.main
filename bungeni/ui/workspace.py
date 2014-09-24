# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Workspace

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.workspace")

import os
import simplejson

from sqlalchemy import distinct
from zope import component
from zope.publisher.browser import BrowserPage
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.app.component.hooks import getSite
from zope.security.proxy import removeSecurityProxy
from zc.table import column
from zc.resourcelibrary import need
from zope.dublincore.interfaces import IDCDescriptiveProperties

from bungeni.alchemist.container import contained
from bungeni.alchemist.ui import Getter
from bungeni.alchemist import utils, Session
from bungeni.core import translation
from bungeni.core.language import get_default_language
from bungeni.core.content import WorkspaceSection
from bungeni.core.interfaces import (IWorkspaceTabsUtility,
    IWorkspaceContainer,
    IWorkspaceUnderConsiderationContainer,
    IWorkspaceGroupsContainer,
)

from bungeni.models.interfaces import ITranslatable
from bungeni.models import domain
from bungeni.models import utils as model_utils

from bungeni.ui.utils import url
from bungeni.ui.utils.common import get_workspace_roles
from bungeni.ui import table
from bungeni.ui.interfaces import IWorkspaceContentAdapter
from bungeni.ui.forms import common
from bungeni.core.workspace import ROLES_DIRECTLY_DEFINED_ON_OBJECTS
#from bungeni.core.workflow.interfaces import IWorkflow
from bungeni.utils import register
from bungeni.capi import capi
from bungeni.ui.widgets import date_input_search_widget

from bungeni import _, translate

_path = os.path.split(os.path.abspath(__file__))[0]


def get_document_groups():
    """Get Document Groups
    """
    group_options = [("", "-")]
    user = model_utils.get_login_user()
    groups = [ g for g in model_utils.get_user_groups(user) ]
    group_values = [ (g.group_id, IDCDescriptiveProperties(g).short_title)
        for g in groups ]
    group_options += group_values
    return group_options

class WorkspaceField(object):

    def __init__(self, name, title):
        self.name = name
        self.title = title

    def query(item, formatter):
        return getattr(IWorkspaceContentAdapter(item), name, None)

# These are the columns to be displayed in the workspace
workspace_doc_fields = [
    WorkspaceField("title", _("workspace_column_title", default="title")),
    WorkspaceField("type", 
        _("workspace_column_type", default="item type")),
    WorkspaceField("status", 
        _("workspace_column_status", default="status")),
    WorkspaceField("status_date", 
        _("workspace_column_status_date", default="status date")),
    WorkspaceField("translation_status", 
        _("workspace_column_translation_status", default="translations")),
    WorkspaceField("group_id", 
        _("workspace_column_document_group", default="group"))
    ]


workspace_group_fields = [
    WorkspaceField("title", 
        _("workspace_column_group_title", default="title")),
    WorkspaceField("type", 
        _("workspace_column_group_type", default="group type")),
    WorkspaceField("status", 
        _("workspace_column_group_status", default="status")),
    WorkspaceField("status_date", 
        _("workspace_column_group_status_date", default="status date"))
    ]

@register.view(IWorkspaceContainer, name="jsonlisting",
    protect={"bungeni.ui.workspace.View": register.VIEW_DEFAULT_ATTRS})
class WorkspaceContainerJSONListing(BrowserPage):
    """Paging, batching, json contents of a workspace container.
    """
    workspace_fields = workspace_doc_fields

    def __init__(self, context, request):
        super(WorkspaceContainerJSONListing, self).__init__(context, request)
        self.defaults_sort_on = "status_date"
        if not self.request.get("sort"):
            self.request.form["sort"] = u"sort_%s" % (self.defaults_sort_on)
        self.sort_on = self.request.get("sort")[5:]
        # sort_dir: "desc" | "asc"
        # pick off request, or set default
        if not self.request.get("dir"):
            self.request.form["dir"] = "desc"
        self.sort_dir = self.request.get("dir")

    def get_offsets(self, default_start=0,
            default_limit=capi.default_number_of_listing_items
        ):
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
        batch = self.get_batch(start, limit, lang)
        data = dict(
            length=self.set_size,  # total result set length, set in getBatch()
            start=start,
            recordsReturned=len(batch),
            nodes=batch
            )
        return simplejson.dumps(data)

    def _json_values(self, nodes):
        values = []
        for node in nodes:
            d = {}
            for field in self.workspace_fields:
                d[field.name] = getattr(
                    IWorkspaceContentAdapter(node), field.name, None
                    )
            d["object_id"] = url.set_url_context(node.__name__)
            values.append(d)
        return values

    def translate_objects(self, nodes, lang=None):
        """ Translate container items if translatable
        """
        if lang is None:
            lang = get_default_language()
        for index, node in enumerate(nodes):
            if ITranslatable.providedBy(node):
                nodes[index] = translation.translated(node, lang)
        return nodes
    
    def get_batch(self, start=0, limit=25, lang=None):
        context = removeSecurityProxy(self.context)
        filter_title = self.request.get("filter_title", None)
        filter_type = self.request.get("filter_type", None)
        filter_status = self.request.get("filter_status", None)
        filter_status_date = self.request.get("filter_status_date", "")
        filter_group = self.request.get("filter_group", "")
        results, self.set_size = context.query(
            filter_title=filter_title,
            filter_type=filter_type,
            filter_status=filter_status,
            filter_status_date=filter_status_date,
            filter_group=filter_group,
            sort_on=self.sort_on,
            sort_dir=self.sort_dir,
            start=start,
            limit=limit,
        )
        results = [ contained(ob, self, context.string_key(ob))
            for ob in results ]
        nodes = results[start:start + limit]
        nodes = self.translate_objects(nodes, lang)
        batch = self._json_values(nodes)
        return batch

    def __call__(self):
        start, limit = self.get_offsets()  # ? start=0&limit=25
        lang = get_default_language()
        return self.json_batch(start, limit, lang)


COLUMN_DEFS = {
    "default_first": """{label:"%(label)s", key:"sort_%(key)s",
        formatter:"%(formatter)sCustom", sortable:true, resizeable:true ,
        children: [{ key:"%(key)s", sortable:false}]}""",
    "default": """{label:"%(label)s", key:"sort_%(key)s",
        sortable:true, resizeable:true,
        children: [{key:"%(key)s", sortable:false}]}""",
    "translation_status": """{label:"%(label)s", key:"%(key)s",
        sortable:false, resizeable:false,
        children: [{key:"%(key)s", label:"&nbsp;", sortable:false}]}""",
}

class WorkspaceDataTableFormatter(table.ContextDataTableFormatter):
    data_view = "/jsonlisting"
    workspace_fields = workspace_doc_fields

    js_file = open(_path + "/templates/datatable-workspace.js")
    script = js_file.read()
    js_file.close()

    def get_search_widgets(self):
        return date_input_search_widget("table", "status_date")

    def get_item_types(self):
        workspace_config = component.getUtility(IWorkspaceTabsUtility)
        roles = get_workspace_roles() + ROLES_DIRECTLY_DEFINED_ON_OBJECTS
        domains = []
        for role in roles:
            dom = workspace_config.get_role_domains(
                role, self.context.__name__
                )
            if dom:
                for key in dom:
                    if key not in domains:
                        domains.append(key)
        result = dict([("", "-")])
        for d in domains:
            value = workspace_config.get_type(d)
            if value:
                descriptor_model = utils.get_descriptor(d)
                name = descriptor_model.display_name if descriptor_model else value
                result[value] = translate(name, context=self.request)
        return result

    def get_status(self, type_key):
        translated = dict()
        if not type_key:
            return translated
        ti = capi.get_type_info(type_key)
        workflow, domain_model = ti.workflow, ti.domain_model
        workspace_config = component.getUtility(IWorkspaceTabsUtility)
        roles = get_workspace_roles() + ROLES_DIRECTLY_DEFINED_ON_OBJECTS
        results = set()
        for role in roles:
            status = workspace_config.get_status(
                role, domain_model, self.context.__name__)
            if status:
                for s in status:
                    results.add(s)
        for result in results:
            status_title = translate(
                workflow.get_state(result).title,
                domain="bungeni",
                context=self.request)
            translated[result] = status_title
        return translated

    def getDataTableConfig(self):
        config = super(WorkspaceDataTableFormatter, self).getDataTableConfig()
        item_types = self.get_item_types()
        config["item_types"] = simplejson.dumps(item_types)
        document_groups = get_document_groups()
        config["document_groups"] = simplejson.dumps(document_groups)
        all_item_status = dict()
        status = dict([("", "-")])
        for item_type in item_types:
            for k, v in self.get_status(item_type).iteritems():
                item_status_value = "%s+%s" % (item_type, k)
                status[item_status_value] = v
                all_item_status[k] = v
        status.update(all_item_status)
        config["status"] = simplejson.dumps(status)
        return config

    def getFieldColumns(self):
        column_model = []
        field_model = []
        default_format = COLUMN_DEFS.get("default")
        default_format_first = COLUMN_DEFS.get("default_first")
        for field in self.workspace_fields:
            coldef = {
                "key": field.name,
                "label": translate(_(field.title), context=self.request),
                "formatter": self.context.__name__
                }
            coldef_format = COLUMN_DEFS.get(field.name, None)
            if column_model == []:
                if not coldef_format:
                    coldef_format = default_format_first
            else:
                if not coldef_format:
                    coldef_format = default_format
            column_model.append(coldef_format % coldef)
            field_model.append('{key:"%s"}' % (field.name))
        return ",".join(column_model), ",".join(field_model)


@register.view(IWorkspaceContainer, name="index",
    protect={"bungeni.ui.workspace.View": register.VIEW_DEFAULT_ATTRS})
class WorkspaceContainerListing(BrowserPage):
    render = ViewPageTemplateFile("templates/workspace-listing.pt")
    formatter_factory = WorkspaceDataTableFormatter
    columns = []
    prefix = "workspace"
    workspace_fields = workspace_doc_fields

    def __call__(self):
        need("yui-datatable")
        self.context = removeSecurityProxy(self.context)
        return self.render()
    
    def update(self):
        for field in self.workspace_fields:
            self.columns.append(
                column.GetterColumn(title=field.name,
                                 getter=Getter(field.query)))

    def listing(self):
        return self.formatter()

    @property
    def formatter(self):
        formatter = self.formatter_factory(
            self.context,
            self.request,
            (),
            prefix=self.prefix,
            columns=self.columns,
        )
        formatter.cssClasses["table"] = "listing"
        formatter.table_id = "datacontents"
        return formatter


class WorkspaceUnderConsiderationFormatter(WorkspaceDataTableFormatter):

    def get_item_types(self):
        result = dict([("", "-")])
        for type_key, ti in capi.iter_type_info():
            workflow = ti.workflow
            if workflow and workflow.has_feature("workspace"):
                name = ti.descriptor_model.display_name if \
                    ti.descriptor_model else ti.workflow_key
                result[ti.workflow_key] = translate(name, context=self.request)
        return result

    def get_status(self, item_type):
        result = {}
        for type_key, ti in capi.iter_type_info():
            # !+ why compare workflow_key to item_type ?!
            if (ti.workflow_key == item_type):
                states = ti.workflow.get_state_ids(
                    tagged=["public"], not_tagged=["terminal"],
                    conjunction="AND")
                for state in states:
                    state_title = translate(
                        ti.workflow.get_state(state).title,
                        domain="bungeni",
                        context=self.request
                    )
                    result[state] = state_title
                break
        return result

    def getDataTableConfig(self):
        config = table.ContextDataTableFormatter.getDataTableConfig(self)
        item_types = self.get_item_types()
        config["item_types"] = simplejson.dumps(item_types)
        document_groups = get_document_groups()
        config["document_groups"] = simplejson.dumps(document_groups)
        all_item_status = dict()
        status = dict([("", "-")])
        for item_type in item_types:
            x = self.get_status(item_type)
            for k, v in x.iteritems():
                item_status_value = "%s+%s" % (item_type, k)
                status[item_status_value] = v
                all_item_status[k] = v
        status.update(all_item_status)
        config["status"] = simplejson.dumps(status)
        return config


@register.view(IWorkspaceUnderConsiderationContainer, name="index",
    protect={"bungeni.ui.workspace.View": register.VIEW_DEFAULT_ATTRS})
class WorkspaceUnderConsiderationListing(WorkspaceContainerListing):
    formatter_factory = WorkspaceUnderConsiderationFormatter
    prefix = "workspace_under_consideration"


class WorkspaceGroupsFormatter(WorkspaceDataTableFormatter):

    workspace_fields = workspace_group_fields

    def get_item_types(self):
        result = dict([("", "-")])
        session = Session()
        group_types = session.query(distinct(domain.Group.type)).all()
        for group_type in group_types:
            result[group_type[0]] = translate(
                group_type[0], context=self.request)
        return result

    def get_status(self, item_type):
        return {}

    def getDataTableConfig(self):
        config = table.ContextDataTableFormatter.getDataTableConfig(self)
        item_types = self.get_item_types()
        config["item_types"] = simplejson.dumps(item_types)
        config["status"] = simplejson.dumps(dict([("", "-")]))
        config["document_groups"] = "[]"
        return config


@register.view(IWorkspaceGroupsContainer, name="index",
    protect={"bungeni.ui.workspace.View": register.VIEW_DEFAULT_ATTRS})
class WorkspaceGroupsListing(WorkspaceContainerListing):
    formatter_factory = WorkspaceGroupsFormatter
    prefix = "workspace_groups"
    workspace_fields = workspace_group_fields


@register.view(WorkspaceSection, name="tabcount",
    protect={"bungeni.ui.workspace.View": register.VIEW_DEFAULT_ATTRS})
@register.view(IWorkspaceContainer, name="tabcount",
    protect={"bungeni.ui.workspace.View": register.VIEW_DEFAULT_ATTRS})
class WorkspaceTabCount(BrowserPage):

    def __call__(self):
        data = {}
        app = getSite()
        filters = {}
        keys = app["workspace"]["my-documents"].keys()
        read_from_cache = True
        if self.request.get("cache") == "false":
            read_from_cache = False
        for key in keys:
            data[key] = app["workspace"]["my-documents"][key].count(
                read_from_cache, **filters)
        return simplejson.dumps(data)


class WorkspaceAddForm(common.AddForm):
    
    def get_oid(self, ob):
        return self.context.string_key(ob)
    
    @property
    def add_action_verb(self):
        return self.__name__ # "add_%s" % (self.__name__[len("add_"):])
    
    @property
    def domain_model(self):
        item_type_key = self.__name__[len("add_"):]
        # !+ domain_model = capi.get_type_info(item_type_key).domain_model
        workspace_config = component.getUtility(IWorkspaceTabsUtility)
        return workspace_config.get_domain(item_type_key)
    
    # !+ why is this variation of domain_model needed?
    def getDomainModel(self):
        return getattr(self, "domain_model", self.context.__class__)


