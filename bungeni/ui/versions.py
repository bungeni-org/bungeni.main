# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Versioning of Domain Objects

$Id$

"""
log = __import__("logging").getLogger("bungeni.ui.versions")

from zope import interface
from zope import schema
from zope import formlib

from zope.security.proxy import removeSecurityProxy
from zope.security import canWrite, checkPermission
from zope.security.interfaces import ForbiddenAttribute
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.i18n import translate
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.annotation.interfaces import IAnnotations
from zope.publisher.interfaces.browser import IBrowserPublisher

from sqlalchemy import orm

from bungeni.alchemist.interfaces import IIModelInterface
from bungeni.alchemist.ui import getSelected

from bungeni.core import version
from bungeni.core.workflows.utils import view_permission
from bungeni.models.interfaces import IFeatureVersion
from bungeni.ui.interfaces import IWorkspaceOrAdminSectionLayer
from bungeni.ui.i18n import _
from bungeni.ui.utils import url
from bungeni.ui import browser
from bungeni.ui import forms
from bungeni.utils import register
from bungeni.ui.htmldiff import htmldiff
from bungeni.ui import audit
from zc.table import column


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
#!+zc.table the selection column below overrides the base class
# that generates id's using base64 resulting in invalid HTML ids
# eg. they contain = sign.
class CustomSelectionColumn(column.SelectionColumn):
    def makeId(self, item):
        return ''.join(self.idgetter(item).split())


# versions are a special "audit" case


class VersionDataDescriptor(audit.ChangeDataDescriptor):
    
    # !+bungeni_custom
    def columns(self):
        return [
            CustomSelectionColumn(
                    lambda item:str(item.audit_id), name="selection"),
            column.GetterColumn(title=_("version"),
                    getter=lambda i,f:"%s" % (i.audit_id),
                    cell_formatter=lambda g,i,f:'<a href="%s/version-log/%s">%s</a>'
                        % (f.url, i.__name__, i.seq)),
            column.GetterColumn(title=_("procedure"), 
                    getter=lambda i,f:i.procedure),
            column.GetterColumn(title=_("modified"), 
                    getter=lambda i,f:self.date_formatter.format(i.date_active)),
            column.GetterColumn(title=_("by"), 
                    getter=lambda i,f:IDCDescriptiveProperties(i.user).title),
            column.GetterColumn(title=_("message"),
                    getter=lambda i,f:i.note),
        ]

class VersionLogMixin(object):
    """Base handling of version log listing for a context.
    """
    formatter_factory = audit.TableFormatter
    prefix = "container_contents_versions"
    
    _message_no_data = _("No Version Data")
    @property
    def message_no_data(self):
        return translate(self.__class__._message_no_data)
    
    _columns = None
    def columns(self):
        if self._columns is None:
            self._columns = VersionDataDescriptor(self.context, self.request
                ).columns()
        return self._columns
    
    @property
    def selection_column(self): 
        return self.columns()[0]
    
    _data_items = None
    def version_data_items(self):
        # version log is only concerned with own versions (not of any child 
        # objects) i.e. only own "version changes"; as "data_provider" we 
        # simply use the versions attribute on context:
        if self._data_items is None:
            self._data_items = []
            # sorted desc by sqlalchemy, so following sorting not necessary:
            permission = view_permission(self.context)
            for v in removeSecurityProxy(self.context).versions:
                if checkPermission(permission, v):
                    self._data_items.append(v)
        return self._data_items
    
    @property
    def has_data(self):
        return bool(self.version_data_items)
    
    def listing(self):
        formatter = self.formatter_factory(self.context, self.request,
            self.version_data_items(), # formatter.items
            visible_column_names=[ c.name for c in self.columns() ], #!+self.visible_column_names, 
            prefix=self.prefix,
            columns=self.columns()
        )
        # visible_column_names & columns -> formatter.visible_columns
        formatter.url = url.absoluteURL(self.context, self.request)
        formatter.cssClasses["table"] = "listing grid"
        return formatter()

@register.view(IFeatureVersion, layer=IWorkspaceOrAdminSectionLayer, 
    name="version-log", 
    protect={"bungeni.ui.version.View": 
        dict(attributes=["publishTraverse", "browserDefault", "__call__"])})
class VersionLogView(VersionLogMixin, 
        browser.BungeniBrowserView, 
        forms.common.BaseForm,
    ):
    """Version Log View for an object
    """
    interface.implements(IBrowserPublisher)
    
    class IVersionEntry(interface.Interface):
        commit_message = schema.Text(title=_("Change Message"))
    form_fields = formlib.form.Fields(IVersionEntry)
    
    render = ViewPageTemplateFile("templates/version.pt")
    
    __name__ = "version-log"
    _page_title = _("Version Log")
    
    diff_view = None
    
    def __init__(self, context, request):
        #!+context = removeSecurityProxy(context)
        browser.BungeniBrowserView.__init__(self, context, request)
        VersionLogMixin.__init__(self)
        self._page_title = translate(self.__class__._page_title)
        if hasattr(self.context, "title"):
            self._page_title = "%s: %s" % (
                self._page_title, translate(self.context.title))
    
    def publishTraverse(self, request, ver_seq):
        seq = int(ver_seq[len("ver-"):])
        for ver in removeSecurityProxy(self.context).versions:
            if ver.seq == seq:
                removeSecurityProxy(ver).__parent__ = self
                return ver
    
    def has_write_permission(self, context):
        """Check that  the user has the rights to edit the object, if not we 
        assume he has no rights to make a version assumption is here that if 
        he has the rights on any of the fields he may create a version.
        """
        trusted = removeSecurityProxy(self.context)
        # !+extended attributes? get complete list of attribuites off kls, as 
        # in core.audit...get_field_names_to_audit(kls)
        # !+ replace with a more explict permission check?
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
    
    @formlib.form.action(label=_("New Version"), name="new_version",
        condition=has_write_permission)
    def handle_new_version(self, action, data):
        # !+ change_data not yet initialized for version requests
        change_data = IAnnotations(self.request)["change_data"] = {}
        change_data["note"] = data["commit_message"]
        change_data["procedure"] = "m"
        version.create_version(self.context)
        self.status = _("New Version Created")
    
    @formlib.form.action(label=_("Revert To"), name="revert_to",
        condition=has_write_permission)
    def handle_revert_version(self, action, data):
        # !+REVERSION must be reviewed, probably obsoleted
        selected_audit_ids = getSelected(self.selection_column, self.request)
        if len(selected_audit_ids) != 1:
            self.status = _("Select one item to revert to")
            return
        selected_audit = self.get_version_change(selected_audit_ids[0])
        # !+ change_data not yet initialized for version requests
        change_data = IAnnotations(self.request)["change_data"] = {}
        # !+polymorphic_identity_multi adding action "qualifier" to note...
        # there could be a case for an additional column on change table.
        change_data["note"] = "%s [reversion %s]" % (
            data["commit_message"], selected_audit_ids[0])
        change_data["procedure"] = "m"
        version.create_reversion(selected_audit)
        self.status = _(u"Reverted to Previous Version %s") % (
            removeSecurityProxy(selected_audit).audit_id)
    
    @formlib.form.action(label=_("Show Differences"), name="diff",
        validator=lambda form, action, data: ())
    def handle_diff_version(self, action, data):
        self.status = _("Displaying differences")
        selected_audit_ids = sorted(getSelected(self.selection_column, self.request))
        if len(selected_audit_ids) not in (1, 2):
            self.status = _("Select one or two items to show differences")
            return
        source = self.get_version_change(selected_audit_ids[0])
        try:
            target = self.get_version_change(selected_audit_ids[1])
        except IndexError:
            target = removeSecurityProxy(self.context)
        diff_view = DiffView(source, target, self.request)
        self.diff_view = diff_view(
            *filter(IIModelInterface.providedBy, interface.providedBy(self.context)))
        log.debug("handle_diff_version: source=%s target=%s \n%s" % (
                        source, target, self.diff_view))
    
    def get_version_change(self, audit_id):
        for c in removeSecurityProxy(self.context).versions:
            c = removeSecurityProxy(c)
            if c.audit_id == audit_id:
                return c
    
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
# - the result of a diff is now always being obtained via from
# htmldiff.htmldiff(),so it is all much simpler
# note that z3c.schemadiff.schema.diff() was
# anyway shortcutting any and all adapter genericity (for IFieldDiff) by
# hard-wiring explicit checks on whether not to call IFieldDiff.html_diff()!
# 
# This implementation also removes all dependencies on the z3c.schemadiff
# package, that may therefore be removed.
# 
class DiffView(object):

    template = ViewPageTemplateFile("templates/diff.pt")
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
    seen_field_names = []
    for iface in interfaces:
        # the order is locked on the order returned by of interface.names()
        for name in iface.names():
            #!+VERSIONS(miano, nov 2012) documents now implement two 
            # table schema interfaces with identical fields
            # eg. bungeni.models.interfaces.IDocTableSchema and
            # bungeni.models.interfaces.IQuestionTableSchema. 
            if name in seen_field_names:
                continue
            seen_field_names.append(name)
            #!+VERSIONS(miano, 2 may 2012) something changed in the last couple
            # of weeks that makes removeSecurityPolicy below required yet
            # it wasn't before.
            field = removeSecurityProxy(iface[name])
            # only consider for diffing fields of this type
            #!+VERSIONS(miano, 2 May 2012) This was an isinstance check before.
            # switched it to check on interfaces.
            if set((schema.interfaces.IText, schema.interfaces.ITextLine,
                schema.interfaces.ISet)).isdisjoint(
                    set(interface.providedBy(field))):
                continue
            bound = field.bind(source)
            source_value = bound.query(source, field.default)
            target_value = bound.query(target, field.default)
            if source_value is None or target_value is None:
                continue
            hresult = htmldiff(source_value, target_value)
            results.append((field, bool(hresult!=source_value), hresult))
    return results

