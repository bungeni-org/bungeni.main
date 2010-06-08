from zope import interface
from zope.publisher.browser import BrowserView
from zope.app.pagetemplate import ViewPageTemplateFile


class ArchiveBrowseContentView(BrowserView):
    __call__ = ViewPageTemplateFile("templates/archive.pt")


# NOTE: AdminBrowseContentView is identical to ArchiveBrowseContentView
AdminBrowseContentView = ArchiveBrowseContentView
