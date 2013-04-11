import os
import simplejson
from sqlalchemy import distinct
from zope import component
from zope.publisher.browser import BrowserPage
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.app.component.hooks import getSite
from zope.security.proxy import removeSecurityProxy
from zope.formlib import form
from zope.i18n import translate
from zope.event import notify
from zope.lifecycleevent import ObjectCreatedEvent
from zc.resourcelibrary import need
from bungeni.alchemist.container import contained
from bungeni.alchemist.ui import createInstance
from bungeni.alchemist import utils, Session
from bungeni.core import translation
from bungeni.core.content import WorkspaceSection
from bungeni.core.i18n import _
from bungeni.core.interfaces import (IWorkspaceTabsUtility,
    IWorkspaceContainer,
    IWorkspaceUnderConsiderationContainer,
    IWorkspaceGroupsContainer)
from bungeni.models.interfaces import ITranslatable
from bungeni.ui.utils import url
from bungeni.ui.utils.common import get_workspace_roles
from bungeni.ui import table
from bungeni.ui.interfaces import IWorkspaceContentAdapter
from bungeni.ui.forms.common import AddForm
from bungeni.core.workspace import ROLES_DIRECTLY_DEFINED_ON_OBJECTS
#from bungeni.core.workflow.interfaces import IWorkflow
from bungeni.utils import register
from bungeni.capi import capi
from bungeni.ui.widgets import date_input_search_widget
from bungeni.models import domain

_path = os.path.split(os.path.abspath(__file__))[0]


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
        _("workspace_column_status_date", default="status date"))
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
        default_limit=capi.default_number_of_listing_items):
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
            lang = translation.get_request_language(request=self.request)
        for index, node in enumerate(nodes):
            if ITranslatable.providedBy(node):
                nodes[index] = translation.translate_obj(node, lang)
        return nodes
    
    def get_batch(self, start=0, limit=25, lang=None):
        context = removeSecurityProxy(self.context)
        filter_title = self.request.get("filter_title", None)
        filter_type = self.request.get("filter_type", None)
        filter_status = self.request.get("filter_status", None)
        filter_status_date = self.request.get("filter_status_date", "")
        results, self.set_size = context.query(
            filter_title=filter_title,
            filter_type=filter_type,
            filter_status=filter_status,
            filter_status_date=filter_status_date,
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
        lang = self.request.locale.getLocaleID()
        return self.json_batch(start, limit, lang)


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
        for field in self.workspace_fields:
            coldef = {
                "key": field.name,
                "label": translate(_(field.title), context=self.request),
                "formatter": self.context.__name__
                }
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
        keys = app["workspace"]["my-documents"].keys()
        read_from_cache = True
        if self.request.get("cache") == "false":
            read_from_cache = False
        for key in keys:
            data[key] = app["workspace"]["my-documents"][key].count(
                read_from_cache)
        return simplejson.dumps(data)

class WorkspaceAddForm(AddForm):
    
    # from alchemist.ui.content (assumes all responsibility, does NOT call super)
    def createAndAdd(self, data):
        domain_model = removeSecurityProxy(self.domain_model)
        # create the object, inspect data for constructor args
        try:
            ob = createInstance(domain_model, data)
        except TypeError:
            ob = domain_model()
        # apply any context values
        self.finishConstruction(ob)
        # apply extra form values
        form.applyChanges(ob, self.form_fields, data, self.adapters)
        # add ob to container
        self.context[""] = ob
        # fire an object created event
        notify(ObjectCreatedEvent(ob))
        # signal to add form machinery to go to next url
        self._finished_add = True
        name = self.context.string_key(ob)
        # execute domain.Entity on create hook -- doc_id must have been set
        ob.on_create()
        return self.context.get(name)
    
    @property
    def domain_model(self):
        item_type = self.__name__.split("_", 1)[1]
        workspace_config = component.getUtility(IWorkspaceTabsUtility)
        domain = workspace_config.get_domain(item_type)
        return domain
    
    def getDomainModel(self):
        return getattr(self, "domain_model", self.context.__class__)

