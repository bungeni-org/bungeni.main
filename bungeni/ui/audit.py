# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Audit UI

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.audit")

from zope.security.proxy import removeSecurityProxy
from zope.security.management import getInteraction

import zc.table
from zc.table import column
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.i18n import translate
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.security import checkPermission

from bungeni.models import interfaces
from bungeni.models import domain
from bungeni.core.workflow.interfaces import IWorkflow
from bungeni.core.workflows.utils import view_permission
from bungeni.ui.forms.interfaces import ISubFormViewletManager
from bungeni.ui.i18n import _
from bungeni.ui.descriptor import listing
from bungeni.ui.utils import date
from bungeni.ui import browser
from bungeni.utils import register, naming

CHANGE_TYPES = ("head", "signatory", "attachment", "event")
CHANGE_ACTIONS = domain.CHANGE_ACTIONS
# ("add", "modify", "workflow", "remove", "version", "translate")


# Data

class ChangeDataProvider(object):
    
    def __init__(self, context,
            include_change_types=CHANGE_TYPES, 
            include_change_actions=CHANGE_ACTIONS
        ):
        self.head = removeSecurityProxy(context)
        self.include_change_types = include_change_types
        self.include_change_actions = include_change_actions
    
    def change_data_items(self):
        """Get change data items, reverse-sorted by date (most recent first).
        """
        interaction = getInteraction()
        changes = []

        def append_visible_changes_on_item(item):
            permission = view_permission(item)
            for c in domain.get_changes(item, *self.include_change_actions):
                if checkPermission(permission, c):
                    changes.append(c)
    
        # changes direct on head item
        if "head" in self.include_change_types:
            append_visible_changes_on_item(self.head)
        
        # changes on sub-items -- only Parliamentary Content may have sub-items
        if interfaces.IBungeniParliamentaryContent.providedBy(self.head):
            hwf = IWorkflow(self.head)
            
            # changes on item signatories
            if "signatory" in self.include_change_types:
                signatories = [ s for s in self.head.item_signatories
                    if interaction.checkPermission("bungeni.signatory.View", s)
                ]
                for s in signatories:
                    append_visible_changes_on_item(s)
            
            # changes on item attachments
            if ("attachment" in self.include_change_types 
                    and hwf.has_feature("attachment") #!+IFeatureAttachment?
                ):
                attachments = [ f for f in self.head.attachments
                    if interaction.checkPermission("bungeni.attachment.View", f)
                ]
                for f in attachments:
                    append_visible_changes_on_item(f)
            
            # changes on item events
            if ("event" in self.include_change_types 
                    # and workflow.has_feature("event"): #!+IEventable?
                    # at least no recursion, on events on events...
                    and not interfaces.IEvent.providedBy(self.head)
                ):
                events = [ e for e in self.head.sa_events
                    if interaction.checkPermission("bungeni.event.View", e)
                ]
                for e in events:
                    append_visible_changes_on_item(e)
        
        # sort aggregated changes by date_active
        changes = [ dc[1] for dc in 
            reversed(sorted([ (c.date_active, c) for c in changes ])) ]
        return changes
        '''
        print "==== !+AUDITLOG add optional inclusion of auditing " \
            "of sub-objects for:", head
        # attached files:
        print "---- !+ATTACHMENTS", head.attachments, head.files, [
            f for f in head.files ]
        print "---- !+ATTACHMENTS", list(head.files.values()), head.files.values()
        # events:
        print "---- !+EVENT", head.sa_events, head.events, [ 
            e for e in head.events ]
        # signatories:
        print "---- !+AUDITLOG SIGNATORIES", head.itemsignatories, \
            [ s.user_id for s in head.itemsignatories ], \
            head.signatories, \
            [ (type(s), s) for s in head.signatories ]
        # !+ why are items in head.itemsignatories User instances?
        # !+ why are items in bungeni.models.domain.SignatoryContainer strings?
        # versions:  auditing is already done in the item's changes table
        print "==== /!+AUDITLOG"
        
        # !+AlchemistManagedContainer(mr, jan-2012) adopt a simple naming 
        # convention for attributes for the real data list or for attributes 
        # to Alchemist Managed Container of string ids, e.g:
        #   signatories:[Signatory], amc_signatories:Managed(str)
        #   attachments, (files->) amc_attachments
        #   (events->) events, (event->) amc_events
        # or, adopt pattern: @xxx -> amc_xxx.values()
        '''


''' !+UNUSED
def _eval_as_dict(s):
    """Utility to eval serialization of a dict, failure returns an empty dict.
    """
    try:
        d = eval(s)
        assert isinstance(d, dict)
        return d
    except (SyntaxError, TypeError, AssertionError):
        import sys
        from bungeni.ui.utils import debug
        debug.log_exc(sys.exc_info(), log_handler=log.info)
        return {}
'''


# Audit description formatting

def get_auditable_type_key(change):
    """Get the type_key of the auditable type that this change audits.
    """
    #return change.head.type # !+ not all heads define such a type attr
    name = type(change.audit).__name__
    if name.endswith("Audit"):
        name = name[:-5]
    return naming.un_camel(name)

def get_changed_attribute_names(change):
    """Get the names of attributes (including extended attributes) that have
    been changed since last change. Return empty list if no previous change.
    """
    prev = change.previous
    if prev:
        prau, chau = prev.audit, change.audit
        names = [
            name for name in 
                prau.__dict__.keys() + [ 
                vp_name for (vp_name, vp_type) in prau.extended_properties ]
            if name not in get_changed_attribute_names.IGNORE ]
        return sorted([ name for name in names
            if getattr(prau, name) != getattr(chau, name) ])
    return []
get_changed_attribute_names.IGNORE = (
    "_sa_instance_state", "audit_id", "timestamp")

def _label(change):
    """Get a displayable translated label for this change.
    """
    return translate(change.audit.label)

def _link_event(change):
    return"""<a href="events/obj-%s">%s</a>""" % (
        change.audit.audit_head_id, _label(change))

# Audit description format handlers !+bungeni_custom
#
# action: "add", "modify", "workflow", "remove", "version"
# change_type: "head", "signatory", "attachment", "event"
# 
# api: formatter(change) -> localized string
# formatter naming convention: _df_{action}[_{change_type}]

_df_add = _label
def _df_add(change):
    return "%s: [%s]" % (translate(change.action), _label(change))
def _df_add_event(change):
    # !+LINKED_SUB_ITEMS_IN_AUDIT_DESCRIPTION
    return """%s: [<a href="events/obj-%s">%s</a>]""" % (
        translate(change.action), change.audit.audit_head_id, _label(change))

def _df_modify(change):
    # !+ rss -> get_changed_attribute_names(change) always returns empty list!
    changed = ", ".join(get_changed_attribute_names(change))
    if changed:
        return "%s: %s on [%s]" % (
            translate(change.action), changed, _label(change))
    else:
        # !+ should never occur?
        return "%s: [%s]" % (translate(change.action), _label(change))
def _df_modify_head(change):
    changed = ", ".join(get_changed_attribute_names(change))
    #return '<span class="workflow_info">%s</span>' % (", ".join(changed))
    return "%s: %s" % (translate(change.action), changed)
def _df_modify_event(change):
    changed = ", ".join(get_changed_attribute_names(change))
    if changed:
        return """%s: %s on [%s]""" % (
            translate(change.action), changed, _link_event(change))
    else:
        # !+ should never occur?
        return "%s: [%s]" % (translate(change.action), _link_event(change))

def _df_workflow(change):
    return "%s [%s]" % (_df_workflow_head(change), _label(change))
def _df_workflow_head(change):
    # !+change.audit.status(mr, apr-2012) use the workflow state's title instead? 
    wf_prev, wf_prev_status = change.seq_previous, None
    if wf_prev:
        wf_prev_status = wf_prev.audit.status
    return (
        '%s: '
        '%s <span class="workflow_info">%s</span> '
        '%s <span class="workflow_info">%s</span>' % (
            translate(change.action),
            translate("from"),
            translate(wf_prev_status),
            translate("to"),
            translate(change.audit.status)))
def _df_workflow_event(change):
    return "%s [%s]" % (_df_workflow_head(change), _link_event(change))

_df_remove = _label
_df_remove_event = _df_add_event

def _df_version(change):
    return "%s: %d [%s]" % (
        translate(change.action), change.seq, _label(change))
def _df_version_head(change):
    return "%s: %d" % (translate(change.action), change.seq)
def _df_version_event(change):
    return "%s: %d [%s]" % (
        translate(change.action), change.seq, _link_event(change))

def _df_translate(change):
    return "%s: %s" % (translate(change.action), translate(change.audit.language))



# !+LINKED_SUB_ITEMS_IN_AUDIT_DESCRIPTION(mr, may-2012) should the change 
# instance for the type know how to generate the URL for the action/type?
# And, do we need to support both linked and unlinked descriptions 
# e.g. for audit log (linked) and for rss (unlinked) ?
# version/*: see "version" column cell_formatter in versions.VersionDataDescriptor

# !+RSS(mr, may-2012) should descriptions for RSS only be CDATA (no markup)?
# !+AUDIT-TIMELINE-RSS need different change description formatters for each?

def get_description_formatter(action, change_type):
    # assert change_type in CHANGE_TYPES
    # assert action in CHANGE_ACTIONS
    return globals().get("_df_%s_%s" % (action, change_type), 
        # failing that, use the generic formatter for action
        globals().get("_df_%s" % (action)))

def format_description(change, head):
    """Build the (localized) description for display, for each change, per 
    change type and action.
    """
    change_type = "head" if head is change.head else get_auditable_type_key(change)
    return get_description_formatter(change.action, change_type)(change)


# Display descriptors

class GetterColumn(column.GetterColumn):
    def cell_formatter(self, value, item, formatter):
        """Override super's behaviour of XML-escaping values e.g. to allow 
        returning snippets of generated HTML code as table cell content.
        """
        return unicode(value)

class ChangeDataDescriptor(object):
    
    def __init__(self, context, request):
        self.head = removeSecurityProxy(context)
        self.request = request
        self.date_formatter = date.getLocaleFormatter(self.request, 
            "dateTime", "short")
    
    # !+bungeni_custom
    def columns(self):
        return [
            listing.related_user_name_column("user_id", _("user")),
            column.GetterColumn(name="date_active",
                title=_("audit_column_date_active", "date active"),
                getter=lambda i,f: self.date_formatter.format(i.date_active)),
            column.GetterColumn(name="object",
                title=_("audit_column_object", "object"), 
                getter=lambda i,f: get_auditable_type_key(i)),
            GetterColumn(name="description",
                title=_("audit_column_description", "description"), 
                getter=lambda i,f: format_description(i, self.head)),
            column.GetterColumn(name="note",
                title=_("audit_column_note", "note"),
                getter=lambda i,f: i.note and translate(i.note) or ""),
            column.GetterColumn(name="date_audit",
                title=_("audit_column_date_audit", "date audit"),
                getter=lambda i,f: self.date_formatter.format(i.date_audit)),
        ]


# Views

class TableFormatter(
        zc.table.table.AlternatingRowFormatterMixin, 
        zc.table.Formatter
    ):
    """Simple non-batching table formatter, with alternating rows.
    """

# !+AuditLogView(mr, nov-2011) should inherit from forms.common.BaseForm, 
# as for VersionLogView?
class AuditLogMixin(object):
    """Base handling of audit change log listing for a context.
    """
    formatter_factory = TableFormatter
    prefix = "container_contents_changes"
    
    # !+bungeni_custom listing bind to UI configuration (descriptor)
    visible_column_names = []
    # !+ParametrizedAuditLog(mr, dec-2011) bungeni_custom parameters:
    # change types X change actions
    include_change_types = []
    include_change_actions = []
    
    def columns(self):
        return ChangeDataDescriptor(self.context, self.request).columns()
    
    _message_no_data = _("No Change Data")
    @property
    def message_no_data(self):
        return translate(self.__class__._message_no_data)
    
    _data_items = None
    def change_data_items(self):
        if self._data_items is None:
            self._data_items = ChangeDataProvider(self.context, 
                    self.include_change_types, 
                    self.include_change_actions
                ).change_data_items()
        return self._data_items
    
    @property
    def has_data(self):
        return bool(self.change_data_items)
    
    def listing(self):
        # !+FormatterFactoryAPI(mr, jan-2012) the various formatter factories 
        # used in bungeni have different API's! Undermines any advantages of 
        # "abstracting as a factory" as may not easily switch from one
        # factory to another (e.g. think via configuration).
        #
        # zc.table.table.Formatter.__init__(self, 
        #       context, request, items, visible_column_names=None,
        #       batch_start=None, batch_size=None, prefix=None, columns=None):
        # zc.table.batching.Formatter.__init__(self, 
        #       context, request, items, visible_column_names=None,
        #       batch_start=None, batch_size=unspecified, prefix=None,
        #       columns=None, sort_on=None)
        # ore.yuiwidget.table.ContextDataTableFormatter.__init__(self, 
        #       context, request, items, paginator=None, data_view=None, 
        #       *args, **kw)
        #
        formatter = self.formatter_factory(self.context, self.request,
            self.change_data_items(), # formatter.items
            visible_column_names=self.visible_column_names, 
            prefix=self.prefix,
            columns=self.columns()
        )
        # visible_column_names & columns -> formatter.visible_columns
        formatter.cssClasses["table"] = "listing grid"
        return formatter()
    
    #@property
    #def _audit_class(self):
    #    auditor = audit.get_auditor(self.context)
    #    return auditor.audit_class


@register.view(interfaces.IFeatureAudit, name="audit-log",
    protect={"bungeni.ui.audit.View": register.VIEW_DEFAULT_ATTRS})
class AuditLogView(AuditLogMixin, browser.BungeniBrowserView):
    """Change Log View for an object
    """
    
    __call__ = ViewPageTemplateFile("templates/listing-view.pt")
    
    _page_title = _("Change Log")
    visible_column_names = [
        "user", "date_active", "object", "description", "note", "date_audit"]
    include_change_types = [ t for t in CHANGE_TYPES ]
    include_change_actions = [ a for a in CHANGE_ACTIONS ]
    
    def __init__(self, context, request):
        browser.BungeniBrowserView.__init__(self, context, request)
        AuditLogMixin.__init__(self)
        if hasattr(self.context, "title"):
            dc = IDCDescriptiveProperties(self.context, None)
            self._page_title = "%s: %s" % (
                translate(self._page_title), 
                dc and dc.title or self.context.title
            )

@register.viewlet(interfaces.IFeatureAudit, manager=ISubFormViewletManager, 
    name="keep-zca-happy-timeline", protect=register.PROTECT_VIEWLET_PUBLIC)
class TimeLineViewlet(AuditLogMixin, browser.BungeniItemsViewlet):
    view_title = "Timeline"
    view_id = "timeline"
    weight = 20
    
    render = ViewPageTemplateFile("templates/listing-viewlet.pt")
    
    visible_column_names = ["object", "description", "user", "date_active"]
    include_change_types =  [ t for t in CHANGE_TYPES ]
    include_change_actions = [ a for a in CHANGE_ACTIONS ] #if not a == "modify" ]
    
    def __init__(self,  context, request, view, manager):
        browser.BungeniItemsViewlet.__init__(self, context, request, view, manager)
        AuditLogMixin.__init__(self)
        self.view_title = _(self.__class__.view_title)



''' !+JSON_BATCHED_FORMATTER(mr, jan-2012) incomplete code to switch from a 
non-batching table formatter to a json-callback-batched alchemist-container 
formatter for use at BOTH page view level or embedded within a view e.g.
for a viewlet. Several tricky issues remain (e.g. tweaking of alchemist 
container's default linking of first column, add (limited) support for 
filtering and sorting), other than using alchemist container for this case
is probably not appropriate anyway.


from zope.i18n import translate
from bungeni.alchemist.container import stringKey
from bungeni.core import translation
from bungeni.ui import container, table
from bungeni.ui.utils import url

# Batched table base Formatter, with JSON callbacks
    
    # for AuditLogView
    class formatter_factory(ChangeDataTableFormatter):
        data_view = "/jsonlisting_view"
    # for TimelineViewlet
    class formatter_factory(ChangeDataTableFormatter):
        data_view = "/jsonlisting_viewlet"

class ChangeDataTableFormatter(table.ContextDataTableFormatter):
    data_view = None
    prefix = "listing"
    
    def __init__(self, *args, **kw):
        super(ChangeDataTableFormatter, self).__init__(*args, **kw)
    
    def getFields(self):
        """Generate all [zope.schema] fields to be displayed.
        """
        # !+ a cheap duck typing of columns into zope.schema fields could be:
        #c.__name__ = c.name
        for vc in self.visible_columns:
            yield vc
    
    def getFieldColumns(self):
        """ () -> (str, str)
        Get str reprs for: columns, fields
        """
        column_model, field_model = [], []
        for field in self.getFields():
            key = field.name # __name__
            col_info = {
                "key": key, 
                "label": translate(_(field.title), context=self.request),
                "formatter": self.context.__name__
            }
            # special handling of model for first visible column
            if column_model == []:
                column_model.append(
                    '{'
                    'label:"%(label)s", key:"sort_%(key)s", '
                    'formatter:"%(formatter)sCustom", sortable:true, '
                    'resizeable:true, '
                    'children:[{key:"%(key)s", sortable:false}]'
                    '}' % col_info
                )
            else:
                column_model.append(
                    '{'
                    'label:"%(label)s", key:"sort_%(key)s", '
                    'sortable:true, resizeable:true, '
                    'children:[{key:"%(key)s", sortable:false}]'
                    '}' % col_info
                )
            field_model.append('{key:"%s"}' % (key))
        
        print "GFC columns", column_model
        print "GFC fields", field_model
        return ", ".join(column_model), ", ".join(field_model)
    
    def getDataTableConfig(self):
        dtc = super(ChangeDataTableFormatter, self).getDataTableConfig()
        print "DTC", self, dtc
        return dtc

    def __call__(self):
        return super(ChangeDataTableFormatter, self).__call__()

# JSON Listing callbacks

class ChangeDataTableJSONListingBase(container.ContainerJSONListing):
    """JSON data callback for batching/paging.
    """
    permission = "!+VIEW_PERMISSION"
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
        
        # sort params
        # sort_on defaults: [str]
        self.defaults_sort_on = None # getattr(self.domain_model, "sort_on", None)
        # sort_on parameter name: str
        # pick off request, if necessary setting it from the first name
        # defined in defaults_sort_on
        if not self.request.get("sort") and self.defaults_sort_on:
            self.request.form["sort"] = "sort_%s" % (self.defaults_sort_on[0])
        self.sort_on = request.get("sort")
        # sort_dir: "desc" | "asc"
        # pick off request, else "asc"
        self.sort_dir = self.request.get("dir") or "asc"
        # !+ filtering
        
        log.info("Callback URL to ChangeDataTableJSONListing: %s ? %s" % (
            request.URL, request.get("QUERY_STRING")))
    
    def _json_values(self, nodes):
        """Filter values from the nodes to respresent in json.
        """
        values = []
        for node in nodes:
            d = {}
            for column in self.columns():
                name = column.name
                d[name] = column.getter(node, column)
            d["object_id"] = url.set_url_context(stringKey(node))
            values.append(d)
        return values

    def get_batch(self, start, limit):
        # !+ very crude slicing of entire data set
        batch = self.change_data_items()[start:start+limit]
        # !+ add handling of sort, filtering
        self.set_size = len(batch)
        return batch
    
    def __call__(self):
        # prepare required parameters
        start, limit = self.get_offsets()  # ? start=0&limit=25
        lang = translation.get_request_language(request=self.request)
        return self.json_batch(start, limit, lang)


@register.view(interfaces.IFeatureAudit, name="jsonlisting_view")
class ChangeDataTableJSONListingView(ChangeDataTableJSONListingBase, AuditLogView):
    """Json Listing callback for View.
    """

@register.view(interfaces.IFeatureAudit, name="jsonlisting_viewlet")
class ChangeDataTableJSONListingViewlet(ChangeDataTableJSONListingBase, TimeLineViewlet):
    """Json Listing callback for Viewlet.
    """


    <class class=".audit.ChangeDataTableJSONListingView">
        <require permission="!+VIEW_PERMISSION" attributes="browserDefault __call__" />
    </class>
    <class class=".audit.ChangeDataTableJSONListingViewlet">
        <require permission="!+VIEW_PERMISSION" attributes="browserDefault __call__" />
    </class>
'''

