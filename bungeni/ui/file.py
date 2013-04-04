# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

""" Parliamentary object attachment(s) views

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.file")

from tempfile import TemporaryFile
from zope.interface import implements
from zope.publisher.interfaces import IPublishTraverse, NotFound
from zope.publisher.browser import BrowserView
from zope.security.proxy import removeSecurityProxy
from zope.security.management import getInteraction
from zope.app.pagetemplate import ViewPageTemplateFile
from zc.table import column

from bungeni.core.workflow.interfaces import IStateController
from bungeni.models.interfaces import IFeatureAttachment, \
    IVersion, IAttachedFileVersion
from bungeni.models.interfaces import IAttachmentContainer
from bungeni.ui.forms.interfaces import ISubFormViewletManager
from bungeni.ui import browser
from bungeni.ui.i18n import _
from bungeni.ui.utils import date, url
from bungeni.utils import register

class RawView(BrowserView):
    implements(IPublishTraverse)
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.traverse_subpath = []

    def publishTraverse(self, request, name):
        self.traverse_subpath.append(name)
        return self

    def __call__(self):
        """Return File/Image Raw Data"""
        context = removeSecurityProxy(self.context)
        #response.setHeader("Content-Type", "application/octect-stream")
        if len(self.traverse_subpath) != 1:
            return
        fname = self.traverse_subpath[0]
        tempfile = TemporaryFile()
        data = getattr(context, fname, None)
        if data is not None:
            tempfile.write(data)
            tempfile.flush()
            return tempfile
        else:
            raise NotFound(self.context, fname, self.request)


class FileDownload(BrowserView):

    def __call__(self):
        context = removeSecurityProxy(self.context)
        mimetype = getattr(context, "mimetype", None)
        if mimetype == None:
            mimetype = "application/octect-stream"
        filename = getattr(context, "name", None)
        if filename == None:
            filename = getattr(context, "title", None)
        tempfile = TemporaryFile()
        data = getattr(context, "data", None)
        if data is not None:
            tempfile.write(data)
            tempfile.flush()
            self.request.response.setHeader("Content-type", mimetype)
            self.request.response.setHeader("Content-disposition", 
                'attachment;filename="%s"' % filename)
            return tempfile
        else:
            raise NotFound(context, "", self.request)


# listing view, viewlet

from bungeni.ui.audit import TableFormatter

class FileListingMixin(object):
    
    formatter_factory = TableFormatter
    prefix = "attachments"
    
    @property
    def columns(self):
        return [
            column.GetterColumn(
                title=_("file_column_file_link", default="file"),
                getter=lambda i,f: "%s" % (i.title),
                cell_formatter=lambda g,i,f: '<a href="%s/files/obj-%d">%s</a>' 
                    % (f.url, i.attachment_id, g)),
            column.GetterColumn(
                title=_("file_column_status", default="status"), 
                getter=lambda i,f: i.status),
            column.GetterColumn(
                title=_("file_column_last_modified", default="modified"), 
                getter=lambda i,f: self.date_formatter.format(i.status_date)),
        ]
    
    def __init__(self):
        self.date_formatter = date.getLocaleFormatter(self.request, 
            "dateTime", "short")
        self._data_items = None # cache
    
    _message_no_data = "No Attachments Found"
    @property
    def message_no_data(self):
        return _(self.__class__._message_no_data)
    
    @property
    def has_data(self):
        return bool(self.file_data_items)
    
    @property
    def file_data_items(self):
        if self._data_items is None:
            interaction = getInteraction() # slight performance optimization
            self._data_items = [ f
                for f in removeSecurityProxy(self.context).attachments
                if interaction.checkPermission("bungeni.attachment.View", f) 
            ]
        return self._data_items
    
    def listing(self):
        formatter = self.formatter_factory(self.context, self.request,
            self.file_data_items,
            prefix=self.prefix,
            visible_column_names=[ c.name for c in self.columns ],
            columns=self.columns
        )
        # !+LET_BROWSER_RELATIVE_URLS(mr. feb, 2012) ?
        formatter.url = url.absoluteURL(self.context, self.request)
        formatter.cssClasses["table"] = "listing grid"
        return formatter()


@register.view(IAttachmentContainer, name="index",
    protect=register.PROTECT_VIEW_PUBLIC)
class FileListingView(FileListingMixin, browser.BungeniBrowserView):

    __call__ = ViewPageTemplateFile("templates/listing-view.pt")
    _page_title = "Attachments"

    def __init__(self, context, request):
        browser.BungeniBrowserView.__init__(self, context.__parent__, request)
        FileListingMixin.__init__(self)
        self._page_title = _(self.__class__._page_title)


# for_, layer, view, manager
@register.viewlet(IFeatureAttachment, manager=ISubFormViewletManager, 
    name="keep-zca-happy-attachments",
    protect=register.PROTECT_VIEWLET_PUBLIC)
class FileListingViewlet(FileListingMixin, browser.BungeniItemsViewlet):
    """Viewlet to list attachments of a given document (head).
    """
    # An Attachment is a record in the attachment table.
    
    render = ViewPageTemplateFile("templates/listing-viewlet.pt")
    view_title = "Attachments"
    view_id = "attachments"
    weight = 50
    
    def __init__(self, context, request, view, manager):
        browser.BungeniItemsViewlet.__init__(self, context, request, view, manager)
        FileListingMixin.__init__(self)
        self.view_title = _(self.__class__.view_title)
        self.for_display = True # bool(self.file_data_items)


@register.viewlet(IVersion, manager=ISubFormViewletManager, 
    name="keep-zca-happy-attachments",
    protect=register.PROTECT_VIEWLET_PUBLIC)
class VersionFileListingViewlet(FileListingViewlet):
    """Viewlet to list **attachment versions** of a given **doc version**.
    """
    # Version attachments are records in the change + attachment_audit tables
    
    def __init__(self, context, request, view, manager):
        super(VersionFileListingViewlet, self).__init__(context, request, view, manager)
        # !+AttachmentableVersion viewlet should not trigger for versions
        # whose head item is not Attachmentable! We only want to display the
        # list attachments on versions whose head item is Attachmentable...
        self.for_display = IFeatureAttachment.providedBy(
            removeSecurityProxy(self.context).head)
    
    @property
    def columns(self):
        from bungeni.models import domain
        def attachment_version_uri(i):
            # !+ bungeni.models.domain.Version
            print "VersionFileListingViewlet", i
            assert isinstance(i, domain.AttachmentVersion), \
                "Not a domain.AttachmentVersion: %s"  % (i)
            # !+STRING_KEY_FILE_VERSION the "obj-%d" context below is an 
            # AttachmentVersion and does NOT have a "version-log" view!
            return "obj-%d/version-log/%s" % (i.attachment_id, i.__name__)            
        return [
            column.GetterColumn(
                title=_("file_version_filename", default="file"),
                getter=lambda i,f:"%s" % (i.title),
                cell_formatter=lambda g,i,f:'<a href="%s/files/%s">%s</a>' 
                    % (f.url, attachment_version_uri(i), g)),
            column.GetterColumn(
                title=_("file_version_status", default="status"),
                getter=lambda i,f:i.status),
            column.GetterColumn(
                title=_("file_version_last_modified", default="modified"),
                getter=lambda i,f:self.date_formatter.format(i.status_date)),
        ]


# !+IAttachedFileVersion(mr, feb-2012) for some reason AttachedFileVersions 
# insist on providing also IVersion even after making IAttachedFileVersion 
# NOT inherit from IVersion.
# AttachedFileVersions do NOT have attachments, so we do NOT want the
# VersionFileListingViewlet to trigger for IAttachedFileVersion... but it 
# would due to implementing also IVersion. So, we "hide" that with the 
# following dummy/NULL viewlet, that does not display...
@register.viewlet(IAttachedFileVersion, manager=ISubFormViewletManager, 
    name="keep-zca-happy-attachments")
class VersionFile_HACK_NonListingViewlet(FileListingViewlet):
    def __init__(self, context, request, view, manager):
        self.for_display = False # bool(self.file_data_items)        
        log.warn("!+IAttachedFileVersion should NOT be trying to list attachments !!!")
        from bungeni.ui.utils import debug
        print self.__class__.__name__, debug.interfaces(context)

