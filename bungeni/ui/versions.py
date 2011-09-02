log = __import__("logging").getLogger("bungeni.ui.versions")

import operator

from zope import interface
from zope import schema
from zope import formlib

from zope.app.pagetemplate import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy
from zope.security import checkPermission, canWrite
from zope.security.interfaces import ForbiddenAttribute

from sqlalchemy import orm

from bungeni.alchemist.interfaces import IIModelInterface
from bungeni.alchemist.ui import getSelected

from bungeni.ui.i18n import MessageFactory as _
from bungeni.ui.table import TableFormatter
from bungeni.ui.utils import date, url
from bungeni.ui.diff import textDiff
from bungeni.ui import browser
from bungeni.ui import z3evoque
from bungeni.ui import forms

from bungeni.core.interfaces import IVersioned

from zc.table import column
from zope.dublincore.interfaces import IDCDescriptiveProperties
'''
from zope.publisher.browser import BrowserView
class VersionsView(BrowserView):
    """To-Do: Find out why this class isn't hooked up."""
    
    def __call__(self):
        context = self.context.__parent__.__parent__
        ifaces = filter(IIModelInterface.providedBy, interface.providedBy(context))
        
        class Form(formlib.form.DisplayForm):
            
            template = ViewPageTemplateFile("templates/form.pt")
            form_fields = formlib.form.FormFields(*ifaces)
            form_name = _(u"View")
            
            @property
            def description(self):
                return _(u"Currently displaying version ${version}",
                         mapping={"version": self.context.version_id})
            
            def setUpWidgets(self, ignore_request=False):
                self.adapters = dict(
                    [(iface, self.context) for iface in ifaces])

                self.widgets = formlib.form.setUpEditWidgets(
                    self.form_fields, self.prefix, self.context, self.request,
                    adapters=self.adapters, for_display=True,
                    ignore_request=ignore_request
                    )
        
        view = Form(self.context, self.request)
        
        return view()
'''

class VersionLogView(browser.BungeniBrowserView, forms.common.BaseForm):
    class IVersionEntry(interface.Interface):
        commit_message = schema.Text(title=_(u"Change Message"))
    
    form_fields = formlib.form.Fields(IVersionEntry)
    formatter_factory = TableFormatter
    
    # evoque
    render = z3evoque.PageViewTemplateFile("version.html")
    # zpt
    #render = ViewPageTemplateFile("templates/version.pt")
    
    diff_view = None
    
    def __init__(self, context, request):
        super(VersionLogView, self).__init__(context.__parent__, request)
        # table to display the versions history
        formatter = date.getLocaleFormatter(self.request, "dateTime", "short")
        # !+ note this breaks the previous sort-dates-as-strings-hack of 
        # formatting dates, for all locales, as date.strftime("%Y-%m-%d %H:%M")
        # that, when sorted as a string, gives correct results.
        self.columns = [
            column.SelectionColumn(
                    lambda item:str(item.version_id), name="selection"),
            column.GetterColumn(title=_(u"version"),
                    getter=lambda i,f:'<a href="%s">%d</a>' % (
                            "%s/versions/obj-%d" % (f.url, i.version_id), 
                            i.version_id)),
            column.GetterColumn(title=_(u"manual"), 
                    getter=lambda i,f:i.manual),
            column.GetterColumn(title=_(u"modified"), 
                    getter=lambda i,f:formatter.format(i.change.date_active)),
            column.GetterColumn(title=_(u"by"), 
                    getter=lambda i,f:IDCDescriptiveProperties(i.change.user).title),
            column.GetterColumn(title=_(u"message"), 
                    getter=lambda i,f:i.change.description),
        ]
        self.selection_column = self.columns[0]
    
    def listing(self):
        # set up table
        values = [ value for value in self._versions.values()
            if checkPermission("zope.View", value) ]
        values.sort(key=operator.attrgetter("version_id"))
        values.reverse()
        formatter = self.formatter_factory(
            self.context, self.request,
            values,
            prefix="results",
            visible_column_names = [c.name for c in self.columns],
            columns = self.columns)

        # the column getter methods expect an ``url`` attribute
        formatter.url = url.absoluteURL(self.context, self.request)

        # update and render
        formatter.updateBatching()
        return formatter()

    def has_write_permission(self, context):
        """check that  the user has the rights to edit 
             the object, if not we assume he has no rights 
             to make a version
             assumption is here that if he has the rights on any of the fields
             he may create a version."""
        trusted = removeSecurityProxy(self.context)
        table = orm.class_mapper(trusted.__class__).mapped_table
        for column in table.columns:
            try:
                if canWrite(self.context, column.name):
                    return True
                else:
                    return False
            except ForbiddenAttribute:
                pass
        else:
            return False
    
    # !+action_url(mr, jul-2010) - throughout bungeni UI, defined only here
    @property
    def action_url(self):
        # this avoids that "POST"ed forms get a "@@index" appended to action URL
        return ""
    # !+action_method(mr, jul-2010) - throughout bungeni UI, defined only here
    @property
    def action_method(self):
        # XXX - for forms that only View information, this should return "get"
        # e.g. business / questions / <q> / versions / Show Differences
        return "post"
    
    @formlib.form.action(label=_("New Version"), condition=has_write_permission)
    def handle_new_version(self, action, data):
        self._versions.create(message = data["commit_message"], manual=True)
        self.status = _(u"New Version Created")

    @formlib.form.action(label=_("Revert To"), condition=has_write_permission)
    def handle_revert_version(self, action, data):
        selected = getSelected(self.selection_column, self.request)
        if len(selected) != 1:
            self.status = _("Select one item to revert to")
            return
        version = self._versions.get(selected[0])
        message = data["commit_message"]
        self._versions.revert(version, message)
        self.status = (_(u"Reverted to Previous Version %s") %(version.version_id))

    @formlib.form.action(
        label=_("Show Differences"), name="diff",
        validator=lambda form, action, data: ())
    def handle_diff_version(self, action, data):
        self.status = _("Displaying differences")

        selected = getSelected(self.selection_column, self.request)
        
        if len(selected) not in (1, 2):
            self.status = _("Select one or two items to show differences")
            return

        context = removeSecurityProxy(self.context)
        source = self._versions.get(selected[0])
                
        try:
            target = self._versions.get(selected[1])
            if source.version_id > target.version_id:
                t = source
                source = target
                target = t
        except IndexError:
            target = context
        diff_view = DiffView(source, target, self.request)
        
        self.diff_view = diff_view(
            *filter(IIModelInterface.providedBy, interface.providedBy(context)))
        
        log.debug("handle_diff_version: source=%s target=%s \n%s" % (
                        source, target, self.diff_view))


    def setUpWidgets(self, ignore_request=False):
        # setup widgets in data entry mode not bound to context
        actions = self.actions
        self.actions = []
        for action in actions:
            if getattr(action, "condition", None):
                if action.condition(self, self.context):
                    self.actions.append(action) 
            else:
                self.actions.append(action)
        if not self.has_write_permission(self.context):
            self.form_fields = self.form_fields.omit("commit_message")
        super(VersionLogView, self).setUpWidgets(self)
        
    @property
    def _versions(self):
        instance = removeSecurityProxy(self.context)
        versions = IVersioned(instance)
        return versions
        
    def __call__(self):
        self.update()
        return self.render()

#### 
# Handling of version diffs (implementation of Issue 588)
# 
# The DiffView class is adapted from: z3c.schemadiff.browser.py
# The diff() utility is adapted from: z3c.schemadiff.schema.py
# 
# The DiffView here is different than the one in schemadiff.browser, as:
# - the result of a diff is now always being obtained via .diff.textDiff(), so
#   it is all much simpler -- note that z3c.schemadiff.schema.diff() was 
#   anayway shortcutting any and all adapter genericity (for IFieldDiff) by 
#   hard-wiring explicit checks on whether not to call IFieldDiff.html_diff()!
# - the template is an evoque template in the default "bungeni.ui" collection.
# 
# This implementation also removes all dependencies on the z3c.schemadiff
# package, that may therefore be removed.
# 
class DiffView(object):

    # evoque
    template = z3evoque.ViewTemplateFile("diff.html")
    context = None
    
    def __init__(self, source, target, request):
        self.source = source
        self.target = target
        self.request = request
    
    def __call__(self, *interfaces):
        results = diff(self.source, self.target, *interfaces)
        tables = []
        content_changed = False
        for (field, changed, hresult) in results:
            tables.append({
                "name": field.__name__,
                "title": field.title,
                "changed": changed,
                "html": hresult})
            if changed:
                content_changed = True
        return self.template(tables=tables, content_changed=content_changed)

def diff(source, target, *interfaces):
    """Get a list of (field, changed, result) 3-tuples, for "diff-able" fields.
    """
    if not len(interfaces):
        interfaces = interface.providedBy(source)
    results = []
    for iface in interfaces:
        # the order is locked on the order returned by of interface.names()
        for name in iface.names():
            field = iface[name]
            # only consider for diffing fields of this type
            if not isinstance(field, (schema.Text, schema.TextLine, schema.Set)):
                continue
            bound = field.bind(source)
            source_value = bound.query(source, field.default)
            target_value = bound.query(target, field.default)
            if source_value is None or target_value is None:
                continue
            hresult = textDiff(source_value, target_value)
            results.append((field, bool(hresult!=source_value), hresult))
    return results

