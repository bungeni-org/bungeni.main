# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Audit UI

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.audit")

import sys

from zope.security.proxy import removeSecurityProxy
from zope.security import checkPermission
from zc.table import column
import zc.table

from bungeni.models import interfaces
from bungeni.models import domain
from bungeni.models.utils import is_current_or_delegated_user
from bungeni.core.workflow.interfaces import InvalidStateError
from bungeni.ui.forms.interfaces import ISubFormViewletManager
from bungeni.ui.i18n import _
from bungeni.ui.descriptor import descriptor
from bungeni.ui.utils import date, debug
from bungeni.ui import browser
from bungeni.ui import z3evoque
from bungeni.utils import register
from bungeni.utils.capi import capi


CHANGE_TYPES = ("head", "signatory", "attachedfile", "event")
CHANGE_ACTIONS = domain.CHANGE_ACTIONS


def checkPermissionChange(permission, change):
    """checkPermission for a change log entry.
    
    This is a variation of generic checkPermission that adds special handling 
    for when the RolePermissionMap lookup for a change record fails becuase
    change.status is not validly set e.g. on "add" change records.
    # !+PERMISSION_CHANGE(mr, dec-2011) should be eliminated (ensure status is 
    # always validly set) or made part of RolePermissionMap's logic.
    """
    try:
        return checkPermission(permission, change)
    except InvalidStateError:
        # No state as RPM for change.status... and as IRolePermission(change) 
        # uses workflow.state.get_head_object_state_rpm the RPM lookup call 
        # fails. Whatever this may be due to, we assume that it OK to grant it 
        # only to the user who actually *affected* the change.
        # !+PERMISSION_CHANGE(mr, dec-2011) above assumption may not 
        # necessarily always be appropriate.
        return is_current_or_delegated_user(change.user)


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
        changes = []
        def append_visible_changes_on_item(item, item_as__parent__=False):
            for c in domain.get_changes(item, *self.include_change_actions):
                # !+CHANGE.__parent__(mr, dec-2011) when & where should this be
                # set? For changes direct on parent item, if __parent__ not set
                # then checkPermission("zope.View") returns False (almost always)
                if item_as__parent__:
                    c.__parent__ = item
                if checkPermissionChange("zope.View", c):
                    changes.append(c)
        
        # !+ align checkPermission zope.View with listings of sub item types...
        
        # changes direct on head item
        if "head" in self.include_change_types:
            append_visible_changes_on_item(self.head, item_as__parent__=True)
        
        # changes on item signatories
        if "signatory" in self.include_change_types:
            signatories = [ s for s in self.head.item_signatories
                if checkPermission("zope.View", s)
            ]
            for s in signatories:
                append_visible_changes_on_item(s)
        
        # changes on item attachments
        if "attachedfile" in self.include_change_types:
            attachments = [ f for f in self.head.attached_files
                if checkPermission("zope.View", f)
            ]
            for f in attachments:
                append_visible_changes_on_item(f)
        
        # changes on item events
        if "event" in self.include_change_types:
            events = [ e for e in self.head.event_items
                if checkPermission("zope.View", e)
            ]
            if events:
                # !+AuditLogSubs(mr, dec-2011) events not currently audited, so
                # we temporarily simulate a singular "add" change action and 
                # stuff it on an event.changes attribute.
                class EventChange(domain.ItemChanges):
                    def __init__(self, event):
                        self._event = event
                        self.item_id = event.event_item_id
                        #change_id
                        #self.content
                        self.head = event.item
                        self.action = "add"
                        self.date_audit = self.date_active = event.status_date
                        self.description = event.short_name
                        self.notes = None # self.extras
                        self.user = event.owner
                        self.status = event.status
                for e in events:
                    e.changes = [EventChange(e)]
                    append_visible_changes_on_item(e)
        
        # sort aggregated changes by date_active
        changes = [ dc[1] for dc in 
            reversed(sorted([ (c.date_active, c) for c in changes ])) ]
        return changes
        '''
        print "==== !+AUDITLOG add optional inclusion of auditing " \
            "of sub-objects for:", head
        # attached files:
        print "---- !+ATTACHED_FILES", head.attached_files, head.files, [
            f for f in head.files ]
        # events:
        print "---- !+EVENT", head.event_items, head.event, [ 
            e for e in head.event ]
        # !+ why the two attributes item.event_items, item.event:
        #   event_items -> EventItem instances ?
        #   event -> Managed bungeni.models.domain.EventItemContainer
        # !+ why is event (container) singular?
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
        #   attached_files, (files->) amc_attached_files
        #   (event_items->) events, (event->) amc_events
        '''


# Display Descriptors

def _eval_as_dict(s):
    """Utility to eval serialization of a dict, failure returns an empty dict.
    """
    try:
        d = eval(s)
        assert isinstance(d, dict)
        return d
    except (SyntaxError, TypeError, AssertionError):
        debug.log_exc(sys.exc_info(), log_handler=log.info)
        return {}

def _get_type_name(change):
    """Get document type name.
    """
    #return change.head.type # !+ not all heads define such a type attr 
    cname = change.__class__.__name__
    if cname.endswith("Change"):
        return cname[:-6].lower()
    return cname.lower()

def _format_description(change):
    """
    """
    change_type_name = _get_type_name(change)
    # event
    if change_type_name == "event":
        return """<a href="event/obj-%s">%s</a>""" % (
                change.item_id, _(change.description))
    # workflow
    elif change.action == "workflow":
        # description
        # the workflow transition change log stores the (unlocalized) 
        # human title for the transition's destination workflow state 
        # -- here we just localize what is supplied:
        return _(change.description)
        # NOTE: we could elaborate an entirely custom description 
        # e.g. using source/destination and other extras infromation
    # version
    elif change.action == "version":
        extras = _eval_as_dict(change.notes)
        version_id = extras["version_id"]
        # description
        if change_type_name == "attachedfile":
            _url = "files/obj-%s/versions/obj-%s" % (
                change.content_id, version_id)
        else:
            _url = "versions/obj-%s" % (version_id)
        try:
            return """<a href="%s">%s</a>""" % (
                _url, _(change.description))
        except (KeyError,):
            # no recorded version_id, just localize what is supplied
            return _(change.description)
    else:
        return _(change.description)


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
    
    def columns(self):
        return [
            descriptor.user_name_column("user_id", _("user"), "user"),
            column.GetterColumn(title="action date",
                getter=lambda i,f: self.date_formatter.format(i.date_active)),
            column.GetterColumn(title="action", 
                getter=lambda i,f: "%s / %s" % (_get_type_name(i), i.action)),
            GetterColumn(title="description", 
                getter=lambda i,f: _format_description(i)),
            column.GetterColumn(title="audit date",
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
class AuditLogViewBase(browser.BungeniBrowserView):
    """Base view for audit change log for a context.
    """
    formatter_factory = TableFormatter
    prefix = "container_contents_changes"
    
    # !+listing bind to declarations in UI configuration (descriptor)
    visible_column_names = []
    # !+ParametrizedAuditLog(mr, dec-2011) bungeni_custom parameters:
    # change types X change actions
    include_change_types = []
    include_change_actions = []
    
    def __init__(self, context, request):
        browser.BungeniBrowserView.__init__(self, context, request)
    
    def columns(self):
        return ChangeDataDescriptor(self.context, self.request).columns()
    
    def change_data_items(self):
        return ChangeDataProvider(self.context, 
                self.include_change_types, 
                self.include_change_actions).change_data_items()
    
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
        formatter.cssClasses["table"] = "listingdescription"
        return formatter()
    
    #@property
    #def _change_class(self):
    #    auditor = audit.get_auditor(self.context)
    #    return auditor.change_class


@register.view(interfaces.IAuditable, name="audit-log")
class AuditLogView(AuditLogViewBase):
    """Change Log View for an object
    """
    
    # evoque
    __call__ = z3evoque.PageViewTemplateFile("audit.html#changes")
    
    # zpt
    #__call__ = ViewPageTemplateFile("templates/changes.pt")
    
    _page_title = "Change Log"
    
    visible_column_names = ["user", "action date", "action", "description", "audit date"]
    include_change_types =  [ t for t in CHANGE_TYPES ]
    include_change_actions = [ a for a in CHANGE_ACTIONS ]
    
    def __init__(self, context, request):
        AuditLogViewBase.__init__(self, context, request)
        if hasattr(self.context, "short_name"):
            self._page_title = "%s: %s" % (
                _(self._page_title), _(self.context.short_name))
        else:
            self._page_title = _(self._page_title)


# !+ @register.view(interfaces.IAuditable, name="bungeni.viewlet.timeline")
@register.viewlet(interfaces.IQuestion, manager=ISubFormViewletManager, 
    name="bungeni.viewlet.question-timeline")
@register.viewlet(interfaces.ITabledDocument, manager=ISubFormViewletManager, 
    name="bungeni.viewlet.tableddocument-timeline")
@register.viewlet(interfaces.IBill, manager=ISubFormViewletManager, 
    name="bungeni.viewlet.bill-timeline")
@register.viewlet(interfaces.IAgendaItem, manager=ISubFormViewletManager, 
    name="bungeni.viewlet.agendaitem-timeline")
@register.viewlet(interfaces.IMotion, manager=ISubFormViewletManager, 
    name="bungeni.viewlet.motion-timeline")
class TimeLineViewlet(AuditLogViewBase, browser.BungeniItemsViewlet):
    view_title = _("Timeline")
    view_id = "timeline"
    weight = 20
    
    # evoque
    render = z3evoque.PageViewTemplateFile("audit.html#timeline")
    
    visible_column_names = ["action date", "description", "user"]
    include_change_types =  [ t for t in CHANGE_TYPES ]
    include_change_actions = [ a for a in CHANGE_ACTIONS if not a == "modify" ]
    
    def __init__(self,  context, request, view, manager):
        AuditLogViewBase.__init__(self, context, request)
        browser.BungeniItemsViewlet.__init__(self, context, request, view, manager)



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
    permission = "zope.View"
    
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


@register.view(interfaces.IAuditable, name="jsonlisting_view")
class ChangeDataTableJSONListingView(ChangeDataTableJSONListingBase, AuditLogView):
    """Json Listing callback for View.
    """

@register.view(interfaces.IAuditable, name="jsonlisting_viewlet")
class ChangeDataTableJSONListingViewlet(ChangeDataTableJSONListingBase, TimeLineViewlet):
    """Json Listing callback for Viewlet.
    """


    <class class=".audit.ChangeDataTableJSONListingView">
        <require permission="zope.View" attributes="browserDefault __call__" />
    </class>
    <class class=".audit.ChangeDataTableJSONListingViewlet">
        <require permission="zope.View" attributes="browserDefault __call__" />
    </class>
'''

