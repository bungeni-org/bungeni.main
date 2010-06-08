import itertools

from zope.interface import implementer
from zope.interface import implements
from zope.interface import providedBy
from zope.interface import Interface
from zope.component import adapter
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from zope.traversing.interfaces import ITraversable
from zope.security.proxy import removeSecurityProxy
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces import NotFound
from zope.filerepresentation.interfaces import IReadDirectory
from zope.schema.interfaces import IField
from zope.filerepresentation.interfaces import IWriteFile
from zope.publisher.interfaces.http import IHTTPRequest

from z3c.dav.publisher import WebDAVRequestFactory
from z3c.dav.properties import DAVProperty
from z3c.dav.interfaces import IWebDAVRequest
from z3c.dav.coreproperties import IDAVCoreSchema
from z3c.dav.coreproperties import IDAVResourcetype
from z3c.dav.coreproperties import IDAVGetSchema

from ore.wsgiapp.publication import Publication

_marker = object()

class WSGIWebDAVRequestFactory(WebDAVRequestFactory):
    def __call__(self):
        request_class, publication_class = WebDAVRequestFactory.__call__(self)
        return request_class, Publication

class FieldProxy(object):
    def __init__(self, context):
        self.context = context

    def __getattr__(self, name):
        assert name.startswith('++field++')
        return getattr(self.context, name[9:])
        
class FieldView(BrowserView):
    def __call__(self):
        field = removeSecurityProxy(self.context)
        context = field.__parent__

        if field.__name__.startswith('++field++'):
            context = FieldProxy(context)
            
        value = field.get(context)
        if not isinstance(str, basestring):
            value = str(value)
            
        return value

    def LOCK(self):
        pass

    def UNLOCK(self):
        pass

class FileFieldWriter(object):
    adapts(IField)
    implements(IWriteFile)
    
    def __init__(self, field):
        self.field = removeSecurityProxy(field)

    def write(self, body):
        import logging
        logging.critical("Writing body: %s." % body)
        name = self.field.__name__
        if name.startswith('++field++'):
            name = name[9:]

        if isinstance(body, str):
            body = body.decode('utf-8')
            
        value = self.field.fromUnicode(body)
        context = self.field.__parent__
        setattr(context, name, value)

        notify(ObjectModifiedEvent(context))
        
class FieldNamespaceTraverser(object):
    """Traverses to a bound schema field."""

    implements(ITraversable)
    adapts(Interface, IHTTPRequest)
    
    def __init__(self, context, request=None):
        self.context = removeSecurityProxy(context)
        self.request = request
        
    def traverse(self, name, ignore):
        field = providedBy(self.context).get(name)
        if field is not None and IField.providedBy(field):
            value = getattr(self.context, name, _marker)
            if value is not _marker:
                bound_field = field.bind(value)
                bound_field.__parent__ = self.context
                return bound_field

        raise NotFound(self.context, name, self.request)

    def publishTraverse( self, request, name ):
        if name == '.':
            return self.context

        if name.startswith('._'):
            raise NotFound(self.context, name, request)
        
        if name.startswith('++field++'):
            return self.traverse(name[9:], None)
        
        raise NotFound(self.context, name, request)

class FieldDirectory(object):
    implements(IReadDirectory)
    adapts(Interface)
    
    def __init__(self, context):
        self.context = removeSecurityProxy(context)

    def values(self):
        results = []
        provides = providedBy(self.context)
        names = set(itertools.chain(*provides))
        for name in names:
            field = provides.get(name)
            if not IField.providedBy(field):
                continue
            
            value = getattr(self.context, name, _marker)
            if value is _marker:
                continue

            bound_field = field.bind(value)
            bound_field.__name__ = "++field++%s" % bound_field.__name__
            bound_field.__parent__ = self.context
            
            results.append(bound_field)
        return results

class IDAVSchema(IDAVCoreSchema,
                 IDAVResourcetype,
                 IDAVGetSchema):
    """Combined DAV schema."""

class FieldStorage(object):
    implements(IDAVSchema)
    adapts(IField, IWebDAVRequest)

    def __init__(self, context, request):
        self.context = removeSecurityProxy(context)
        self.request = request

        view = getMultiAdapter(
            (self.context, self.request), name="index.html")

        self.data = view()
        self.core = getMultiAdapter(
            (self.context.__parent__, request), IDAVCoreSchema)
        
    @property
    def displayname(self):
        return "%s [%s]" % (
            self.core.getlastmodified, self.context.__name__)

    @property
    def getlastmodified(self):
        return self.core.getlastmodified

    @property
    def creationdate(self):
        return self.core.creationdate

    @property
    def getcontentlength(self):
        """Return content length."""

        return len(self.data)

    resourcetype = None
    getcontentlanguage = None
    getcontenttype = None
    getetag = None
