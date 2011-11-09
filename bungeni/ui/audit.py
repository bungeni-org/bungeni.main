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
from bungeni.core import audit
from bungeni.core.workflows import _conditions
from bungeni.ui.i18n import _
from bungeni.ui.utils import date
from bungeni.ui import browser
from bungeni.ui import z3evoque
from bungeni.utils import register


def checkVisibleChange(change):
    """Check visibility permission for a change log entry.
    """
    change.__parent__ = change.head
    if change.status:
        if checkPermission("zope.View", change):
            return True
    else:
        # no status, must be a changelog for object creation--whatever it is
        # we assume that it is visible only to the owner of *head* object
        # !+added(mr, nov-2011) for when the Clerk creates on behalf of an MP,
        # this assumption gives a somewhat strange that the MP can see the 
        # added log entry, but the Clerk can not (as he is not the owner).
        if _conditions.user_is_context_owner(change.head):
            return True
    return False


class ChangeBaseView(browser.BungeniBrowserView):
    """Base view for looking at changes to context.
    """
    
    formatter_factory = batching.Formatter
    
    def __init__(self, context, request):
        super(ChangeBaseView, self).__init__(context, request)
        # table to display the versions history
        formatter = date.getLocaleFormatter(self.request, "dateTime", "short")
        
        # !+ note this breaks the previous sort-dates-as-strings-hack of 
        # formatting dates, for all locales, as date.strftime("%Y-%m-%d %H:%M")
        # that, when sorted as a string, gives correct results.
        self.columns = [
            column.GetterColumn(title=_(u"action"), 
                    getter=lambda i,f:i.action),
            column.GetterColumn(title=_(u"date"),
                    getter=lambda i,f:formatter.format(i.date_active)),
            column.GetterColumn(title=_(u"user"), 
                    getter=lambda i,f:IDCDescriptiveProperties(i.user).title),
            column.GetterColumn(title=_(u"description"), 
                    getter=lambda i,f:i.description),
            column.GetterColumn(title=_(u"audit date"),
                    getter=lambda i,f:formatter.format(i.date_audit)),
        ]
    
    def listing(self):
        formatter = self.formatter_factory(self.context, self.request,
                        self.get_feed_entries(),
                        prefix="results",
                        visible_column_names=[ c.name for c in self.columns ],
                        columns=self.columns)
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
            if checkVisibleChange(c) ]
        return changes


@register.view(IAuditable, name="audit-log")
class ChangeLog(ChangeBaseView):
    """Change Log View for an object
    """
    
    # evoque
    __call__ = z3evoque.PageViewTemplateFile("audit.html#changes")
    
    # zpt
    #__call__ = ViewPageTemplateFile("templates/changes.pt")
    
    _page_title = "Change Log"
    
    def __init__(self, context, request):
        super(ChangeLog, self).__init__(context, request)
        if hasattr(self.context, "short_name"):
            self._page_title = "%s: %s" % (
                _(self._page_title), _(self.context.short_name))
    
