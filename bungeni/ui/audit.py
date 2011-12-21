# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Audit UI

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.audit")

import sys

from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.security.proxy import removeSecurityProxy
from zope.security import checkPermission
from sqlalchemy import orm
from zc.table import batching, column

from bungeni.alchemist import Session
from bungeni.models import interfaces
from bungeni.models import domain
from bungeni.models.utils import is_current_or_delegated_user
from bungeni.core import audit
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
CHANGE_ACTIONS = audit.CHANGE_ACTIONS.keys()


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
        # fails. Whatever this may be due to, we assume that it is visible 
        # only to the user who affected *change*.
        # !+PERMISSION_CHANGE(mr, dec-2011) above assumption not always correct.
        return is_current_or_delegated_user(change.user)


class GetterColumn(column.GetterColumn):
    def cell_formatter(self, value, item, formatter):
        """Override super's behaviour of XML-escaping values e.g. to allow 
        returning snippets of generated HTML code as table cell content.
        """
        return unicode(value)


# !+AuditLogView(mr, nov-2011) should inherit from forms.common.BaseForm, 
# as for VersionLogView?
class AuditLogViewBase(browser.BungeniBrowserView):
    """Base view for audit change log for a context.
    """
    
    #!+TABLEFORMATTER(mr, nov-2011) seems to be the only place where a 
    # table formatter is used but is not bungeni.ui.table.TableFormatter
    formatter_factory = batching.Formatter
    batch_size = capi.default_number_of_listing_items
    
    def __init__(self, context, request):
        browser.BungeniBrowserView.__init__(self, context, request)
        # table to display the versions history
        date_formatter = date.getLocaleFormatter(self.request, "dateTime", "short")
        
        # evaluate serialization of a dict, failure returns an empty dict
        def _eval_as_dict(s):
            try:
                d = eval(s)
                assert isinstance(d, dict)
                return d
            except (SyntaxError, TypeError, AssertionError):
                debug.log_exc(sys.exc_info(), log_handler=log.info)
                return {}
        
        def _get_type_name(change):
            #return change.head.type
            cname = change.__class__.__name__
            if cname.endswith("Change"):
                return cname[:-6].lower()
            return cname.lower()
        
        def _format_description(change):
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
                    url = "files/obj-%s/versions/obj-%s" % (
                        change.content_id, version_id)
                else:
                    url = "versions/obj-%s" % (version_id)
                try:
                    return """<a href="%s">%s</a>""" % (
                        url, _(change.description))
                except (KeyError,):
                    # no recorded version_id, just localize what is supplied
                    return _(change.description)
            else:
                return _(change.description)
        
        # !+ note this breaks the previous sort-dates-as-strings-hack of 
        # formatting dates, for all locales, as date.strftime("%Y-%m-%d %H:%M")
        # that, when sorted as a string, gives correct results.
        self.columns = [
            descriptor.user_name_column("user_id", _("user"), "user"),
            column.GetterColumn(title=_("action date"),
                getter=lambda i,f: date_formatter.format(i.date_active)),
            column.GetterColumn(title=_("action"), 
                getter=lambda i,f: "%s / %s" % (_get_type_name(i), i.action)),
            GetterColumn(title=_(u"description"), 
                getter=lambda i,f: _format_description(i)),
            column.GetterColumn(title=_(u"audit date"),
                getter=lambda i,f: date_formatter.format(i.date_audit)),
        ]
    
    # !+listing bind to declarations in UI configuration (descriptor)
    visible_column_names = []
    
    # !+ParametrizedAuditLog(mr, dec-2011) bungeni_custom parameters:
    # change types X change actions
    include_change_types = []
    include_change_actions = []
    
    def listing(self):
        # Formatter.__init__(self, 
        #       context, request, items, visible_column_names=None,
        #       batch_start=None, batch_size=unspecified, prefix=None,
        #       columns=None, sort_on=None)
        formatter = self.formatter_factory(self.context, self.request,
            self.get_feed_entries(),
            visible_column_names=self.visible_column_names,
            batch_size=self.batch_size,
            prefix="results",
            columns=self.columns
        )
        formatter.cssClasses["table"] = "listing"
        formatter.updateBatching()
        return formatter()
    
    @property
    def _change_class(self):
        auditor = audit.get_auditor(self.context)
        return auditor.change_class
    
    def get_feed_entries(self):
        head = removeSecurityProxy(self.context)
        session = Session()
        mapper = orm.object_mapper(head)
        content_id = mapper.primary_key_from_instance(head)[0]
        changes = []
        
        def actions_filtered_query(query, change_class):
            if self.include_change_actions == CHANGE_ACTIONS or \
                    not self.include_change_actions:
                # no filtering on actions needed, bypass altogether
                return query
            return query.filter(
                change_class.action.in_(self.include_change_actions))
        
        # !+ANONYMOUS(mr, dec-2011) may need to take into account whether 
        # display listing is a for public (anonymous) listing or not
        
        # changes direct on head item
        if "head" in self.include_change_types:
            query = session.query(self._change_class
                ).filter_by(content_id=content_id)
            query = actions_filtered_query(query, self._change_class)
            for c in query.all():
                # !+CHANGE.__parent__(mr, dec-2011) when & where should this be
                # set? For changes direct on parent item, if __parent__ not set
                # then checkPermission("zope.View") returns False (almost always)
                c.__parent__ = c.head
                if checkPermissionChange("zope.View", c):
                    changes.append(c)
        
        # changes on item signatories
        if "signatory" in self.include_change_types:
            signatories = [ s for s in 
                session.query(domain.Signatory
                    ).filter_by(item_id=content_id).all()
                if checkPermission("zope.View", s) ]
            # !+ align checkPermission zope.View with listing of signatories
            for s in signatories:
                query = session.query(domain.SignatoryChange
                    ).filter_by(content_id=s.signatory_id)
                query = actions_filtered_query(query, domain.SignatoryChange)
                changes += [ c for c in query.all() 
                    if checkPermissionChange("zope.View", c) ]
        
        # changes on item attachments
        if "attachedfile" in self.include_change_types:
            attachments = [ f for f in 
                session.query(domain.AttachedFile
                    ).filter_by(item_id=content_id).all()
                if checkPermission("zope.View", f) ]
            # !+ align checkPermission zope.View with listing of attachments
            for f in attachments:
                query = session.query(domain.AttachedFileChange
                    ).filter_by(content_id=f.attached_file_id)
                query = actions_filtered_query(query, domain.AttachedFileChange)
                changes += [ c for c in query.all() 
                    if checkPermissionChange("zope.View", c) ]
        
        # changes on item events
        if "event" in self.include_change_types:
            events = [ e for e in 
                session.query(domain.EventItem
                    ).filter_by(item_id=content_id).all() 
                if checkPermission("zope.View", e) ]
            # !+ align checkPermission zope.View with listing of events
            if events:
                # !+AuditLogSubs(mr, dec-2011) events not currently audited, so
                # we temporarily simulate a singular "add" change action:
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
                    c = EventChange(e)
                    if c.action in self.include_change_actions and \
                            checkPermissionChange("zope.View", c):
                        changes.append(c)
        
        # sort aggregated changes by date_active
        changes = [ dc[1] for dc in 
            reversed(sorted([ (c.date_active, c) for c in changes ])) ]
        
        print "==== !+AUDITLOG add optional inclusion of auditing " \
            "of sub-objects for:", head
        # attached files:
        print "---- !+ATTACHED_FILES", head.attached_files, head.files, [
            f for f in head.files ]
        # events:
        print "---- !+EVENT", head.event_item, head.event, [ 
            e for e in head.event ]
        # !+ why the two attrributes item.event_item, item.event:
        #   event_item -> EventItem instance ?
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
        
        return changes


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
        super(AuditLogView, self).__init__(context, request)
        if hasattr(self.context, "short_name"):
            self._page_title = "%s: %s" % (
                _(self._page_title), _(self.context.short_name))
        else:
            self._page_title = _(self._page_title)


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
class TimeLineViewlet(AuditLogView, browser.BungeniItemsViewlet):
    view_title = _("Timeline")
    view_id = "timeline"
    weight = 20
    
    # !+BACTHING_VIEWLET(mr, dec-2011) paging within a viewlet does not work,
    # as this reloads the page; should have a different strategy e.g. iframe,
    # or ajax container listing, ContextDataTableFormatter.
    batch_size = capi.default_number_of_listing_items
    
    # evoque
    render = z3evoque.PageViewTemplateFile("audit.html#timeline")
    
    visible_column_names = ["action date", "description", "user"]
    include_change_types =  [ t for t in CHANGE_TYPES ]
    include_change_actions = [ a for a in CHANGE_ACTIONS if not a == "modify" ]
    
    def __init__(self,  context, request, view, manager):
        AuditLogView.__init__(self, context, request)
        browser.BungeniItemsViewlet.__init__(self, context, request, view, manager)


