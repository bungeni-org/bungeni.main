# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

""" Parliamentary object attachment(s) views

$Id$
$URL$
"""

from bungeni.core.workflow.interfaces import IStateController
from tempfile import TemporaryFile
from zope.interface import implements
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.browser import BrowserView
from zope.security.proxy import removeSecurityProxy
from zope.security import proxy
from zc.table import column
import operator
from bungeni.models.interfaces import IAttachedFile, IAttachedFileVersion, IAttachedFileVersionContainer
from bungeni.ui.browser import BungeniBrowserView
from bungeni.ui.i18n import _
from bungeni.ui.utils import date, url
from bungeni.ui.table import TableFormatter

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
        context = proxy.removeSecurityProxy(self.context)
        #response.setHeader('Content-Type', 'application/octect-stream')
        if len(self.traverse_subpath) != 1:
            return
        fname = self.traverse_subpath[0]
        tempfile = TemporaryFile()
        data = getattr(context, fname, None)
        if type(data) == buffer:
            tempfile.write(data)
            return tempfile


class FileDownload(BrowserView):

    def __call__(self):
        context = proxy.removeSecurityProxy(self.context)
        mimetype = getattr(context, 'file_mimetype', None)
        if mimetype == None:
            mimetype = 'application/octect-stream'
        filename = getattr(context, 'file_name', None)
        if filename == None:
            filename = getattr(context, 'file_title', None)
        tempfile = TemporaryFile()
        data = getattr(context, 'file_data', None)
        if type(data) == buffer:
            tempfile.write(data)
            self.request.response.setHeader('Content-type', mimetype)
            self.request.response.setHeader('Content-disposition', 'attachment;filename="%s"' % filename)
            return tempfile


class FileDeactivate(BrowserView):
    """ Changes attached file state to 'inactive'
    """

    def __call__(self):
        trusted = removeSecurityProxy(self.context)
        wf_state_adapter = IStateController(trusted)
        wf_state_adapter.setState('inactive')
        redirect_url = self.request.getURL().replace('/deactivate', '')
        return self.request.response.redirect(redirect_url)

class FileListingView(BungeniBrowserView):

    _page_title = _(u"Attachments")

    formatter_factory = TableFormatter

    def __init__(self, context, request):
        super(FileListingView, self).__init__(context.__parent__, request)
        formatter = date.getLocaleFormatter(self.request, "dateTime", "short")
        
        self.columns = [
            column.GetterColumn(title=_(u"file"),
                    getter=lambda i,f:'<a href="%s/files/obj-%d">%s</a>' % (
                            f.url, i.attached_file_id, i.file_title)),
            column.GetterColumn(title=_(u"status"), 
                    getter=lambda i,f:i.status),
            column.GetterColumn(title=_(u"modified"), 
                    getter=lambda i,f:formatter.format(i.status_date)),
        ]

    @property
    def attachments(self):
        instance = removeSecurityProxy(self.context)
        attachments = instance.files.values()
        return list(attachments)

    def hasAttachments(self):
        return len(self.attachments) > 0

    def listing(self):
        values = self.attachments
        values.sort(key=operator.attrgetter("attached_file_id"))
        values.reverse()
        formatter = self.formatter_factory(
            self.context, self.request,
            values,
            prefix="results",
            visible_column_names = [c.name for c in self.columns],
            columns = self.columns)
        formatter.url = url.absoluteURL(self.context, self.request)
        formatter.updateBatching()
        return formatter()
