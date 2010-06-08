import copy
import zipfile

from z3c.pt.pagetemplate import ViewPageTemplate

namespaces = {'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}

class OpenDocument(object):
    
    
    def __init__(self, filename):
        self.filename = filename
        self.zipfile = zipfile.ZipFile(filename)
        self.contents = dict(
            (info, None) for info in self.zipfile.filelist)
        
    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.filename)

    def get(self, info):
        bytes = self.contents.get(info)
        if bytes is None:
            bytes = self.zipfile.read(info.filename)
            self.contents[info] = bytes
        return bytes

    def read(self, filename):
        info = self.zipfile.getinfo("content.xml")
        return self.get(info)

    def process(self, filename, view, **kwargs):
        info = self.zipfile.getinfo(filename)
        bytes = self.get(info)
        template = ViewPageTemplate(
            bytes, encoding='utf-8', omit_default_prefix=False)
        bound_template = template.bind(view)
        result = bound_template(**kwargs)
        self.contents[info] = result.encode('utf-8')

    def save(self, filename):
        outfile = zipfile.ZipFile(filename, 'w')
        try:
            for info in self.contents:
                bytes = self.get(info)
                outfile.writestr(info, bytes)
        finally:
            outfile.close()
