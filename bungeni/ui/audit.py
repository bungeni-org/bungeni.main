# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Audit UI

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.audit")

from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.security.proxy import removeSecurityProxy
from zope.security import checkPermission
from sqlalchemy import orm
from sqlalchemy import desc
from zc.table import batching, column

from bungeni.alchemist import Session
from bungeni.models.interfaces import IAuditable
from bungeni.models.utils import is_current_or_delegated_user
from bungeni.core import audit
from bungeni.ui.i18n import _
from bungeni.ui.utils import date
from bungeni.ui import browser
from bungeni.ui import z3evoque
from bungeni.utils import register


def check_visible_change(change):
    """Check visibility permission for a change log entry.
    """
    change.__parent__ = change.head
    if change.status:
        if checkPermission("zope.View", change):
            return True
    else:
        # no status, must be a change log for object creation--whatever it is
        # we assume that it is visible only to the user who affected *change*
        return is_current_or_delegated_user(change.user)
    return False

# !+AuditLogView(mr, nov-2011) should inherit from forms.common.BaseForm, 
# as for VersionLogView?
class AuditLogViewBase(browser.BungeniBrowserView):
    """Base view for audit change log for a context.
    """
    
    #!+TABLEFORMATTER(mr, nov-2011) seems to be the only palce where a 
    # table formatter is used but is not bungeni.ui.table.TableFormatter
    formatter_factory = batching.Formatter
    
    def __init__(self, context, request):
        super(AuditLogViewBase, self).__init__(context, request)
        # table to display the versions history
        formatter = date.getLocaleFormatter(self.request, "dateTime", "short")
        
        # !+ note this breaks the previous sort-dates-as-strings-hack of 
        # formatting dates, for all locales, as date.strftime("%Y-%m-%d %H:%M")
        # that, when sorted as a string, gives correct results.
        self.columns = [
            column.GetterColumn(title=_(u"action"), 
                    getter=lambda i,f: i.action),
            column.GetterColumn(title=_(u"date"),
                    getter=lambda i,f: formatter.format(i.date_active)),
            column.GetterColumn(title=_(u"user"), 
                    getter=lambda i,f: IDCDescriptiveProperties(i.user).title),
            column.GetterColumn(title=_(u"description"), 
                    getter=lambda i,f: i.description),
            column.GetterColumn(title=_(u"audit date"),
                    getter=lambda i,f: formatter.format(i.date_audit)),
        ]
    
    def listing(self):
        formatter = self.formatter_factory(self.context, self.request,
            self.get_feed_entries(),
            prefix="results",
            visible_column_names=[ c.name for c in self.columns ],
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
        instance = removeSecurityProxy(self.context)
        session = Session()
        mapper = orm.object_mapper(instance)
        content_id = mapper.primary_key_from_instance(instance)[0]
        changes = [ c for c in 
            session.query(self._change_class
                ).filter_by(content_id=content_id
                ).order_by(desc(self._change_class.change_id)
                ).all()
            if check_visible_change(c) ]
        
        # !+AuditLogSubs(mr, nov-2011) extend with options to include
        # auditing of sub-objects. In each case, would need to loop over each
        # type of sub-object, and aggregate its auditlog...
        
        print "==== !+AUDITLOG add optional inclusion of auditing " \
            "of sub-objects for:", instance
        
        # attached files:
        print "---- !+ATTACHED_FILES", instance.attached_files, instance.files, [
            f for f in instance.files ]
        
        # events:
        print "---- !+EVENT", instance.event_item, instance.event, [ 
            e for e in instance.event ]
        # !+ why the two attrributes item.event_item, item.event:
        #   event_item -> EventItem instance ?
        #   event -> Managed bungeni.models.domain.EventItemContainer
        # !+ why is event (container) singular?

        # signatories:
        print "---- !+AUDITLOG SIGNATORIES", instance.itemsignatories, \
            instance.signatories, \
            [ (type(s), s) for s in instance.signatories ]
        # !+ why are items in bungeni.models.domain.SignatoryContainer strings?
        
        # versions:  auditing is already done in the item's changes table
        
        print "==== /!+AUDITLOG"
        return changes


@register.view(IAuditable, name="audit-log")
class AuditLogView(AuditLogViewBase):
    """Change Log View for an object
    """
    
    # evoque
    __call__ = z3evoque.PageViewTemplateFile("audit.html#changes")
    
    # zpt
    #__call__ = ViewPageTemplateFile("templates/changes.pt")
    
    _page_title = "Change Log"
    
    def __init__(self, context, request):
        super(AuditLogView, self).__init__(context, request)
        if hasattr(self.context, "short_name"):
            self._page_title = "%s: %s" % (
                _(self._page_title), _(self.context.short_name))
        else:
            self._page_title = _(self._page_title)

