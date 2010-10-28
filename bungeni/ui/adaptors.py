from bungeni.alchemist import model
from zope.component import getMultiAdapter
from zope.security.proxy import removeSecurityProxy

class BillAnnotationAdaptor(object):
    """Annotation Adaptor for Bills."""

    def __init__(self, context):
        self.context = context

    def getBodyText(self):
        """Returns the annotable text"""
        return self.context.body_text

    def getTitle(self):
        """Returns the annotable text"""
        return self.context.short_name

    def isAnnotatable(self):
        """Returns a boolean True"""
        return True

    def getAnnotatedUrl(self, request=None):
        """Returns the annotated url """
        view = getMultiAdapter((self.context, request), name=u'absolute_url')
        return view()


class RSSValues(object):
    """ Adapter for getting
        values to form rss feed
    """

    def __init__(self, context):
        self.context = context
        self.domain_model = removeSecurityProxy(self.context).domain_model
        self.domain_interface = model.queryModelInterface(self.domain_model)
        self.domain_annotation = model.queryModelDescriptor(
            self.domain_interface)


    @property
    def values(self):
        public_wfstates = getattr(self.domain_annotation,
                                  "public_wfstates",
                                  None)
        trusted = removeSecurityProxy(self.context)
        if public_wfstates:
            return filter(lambda x: x.status in public_wfstates, trusted.values())
        return trusted.values()


class TimelineRSSValues(RSSValues):
    """ Adapter for getting values
        to form rss feed out of object's
        changes
    """

    @property
    def values(self):
        return self.context.changes
