#!/usr/bin/env python
# encoding: utf-8


from zope.viewlet import viewlet
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy

from bungeni.ui.i18n import _
import bungeni.ui.utils as ui_utils

class LibraryViewlet (viewlet.ViewletBase):
    render = ViewPageTemplateFile ('templates/attached-files.pt')
    form_name = _(u"attached files")
    for_display = True
    def __init__( self,  context, request, view, manager ):
        trusted = removeSecurityProxy(context)
        self.context = trusted.attached_files
        self.request = request
        self.__parent__= context
        self.manager = manager
        self.query = None
        self.for_display = len(self.context) > 0

    def results(self):
        return self.context
    
class VersionLibraryViewlet(LibraryViewlet):
    render = ViewPageTemplateFile ('templates/version-attached-files.pt')
    def results(self):
        rl = []
        rd = {}
        url = ui_utils.url.absoluteURL(
                    self.__parent__.__parent__.__parent__, self.request)
        for result in self.context:
            rd["file_title"] = result.file_title
            rd["url"] =  url + "/files/obj-%i/versions/obj-%i" % (result.content_id,
                        result.version_id)
            rd["file_name"] = result.file_name
            rd["file_mimetype"] = result.file_mimetype
            rl.append(rd)
            rd= {}
        return rl
