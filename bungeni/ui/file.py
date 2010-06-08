# encoding: utf-8
# download view to download a file or image
from zope.interface import implements
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.browser import BrowserView
from zope.security import proxy
from tempfile import TemporaryFile


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
        context = proxy.removeSecurityProxy( self.context )
        response = self.request.response
        #response.setHeader('Content-Type', 'application/octect-stream')
        if len(self.traverse_subpath) != 1:
            return
        fname = self.traverse_subpath[0]
        tempfile = TemporaryFile()
        data =  getattr(context,fname,None)
        if type(data) == buffer:
            tempfile.write(data)
            return tempfile
 
class FileDownload(BrowserView):
    def __call__(self):
        context = proxy.removeSecurityProxy( self.context )
        response = self.request.response
        mimetype = getattr(context,'file_mimetype',None)
        if mimetype == None:
            mimetype='application/octect-stream'
        filename=getattr(context,'file_name',None)
        if filename == None:
            filename=getattr(context,'file_title',None) 
        tempfile = TemporaryFile()
        data =  getattr(context,'file_data',None)
        if type(data) == buffer:
            tempfile.write(data)
            self.request.response.setHeader('Content-type', mimetype)
            self.request.response.setHeader('Content-disposition', 'attachment;filename="%s"' % filename)
            return tempfile
            


