from zope.viewlet.viewlet import ResourceViewletBase, ViewletBase
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

class FeedViewlet(ResourceViewletBase, ViewletBase):
    """Base class for feed links eg. RSS, Atom"""
    _feed_type = None
    _href = None
    index = ViewPageTemplateFile("templates/feed-resource.pt")
    
    def getURL(self):
        return self._href
    
    def getType(self):
        return self._feed_type

class RSSFeedViewlet(FeedViewlet):
    """Create a viewlet that inserts an RSS feed link"""
    _feed_type = "application/rss+xml"
    _href = "feed.rss"
