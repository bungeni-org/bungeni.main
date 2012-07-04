# encoding: utf-8


from zope.app.pagetemplate import ViewPageTemplateFile
from zope.publisher.browser import BrowserView

from bungeni.ui.utils import queries, statements, url

class BungeniRSSEventView(BrowserView):
    __call__ = ViewPageTemplateFile('templates/rss-event-view.pt')
    form_name = None

    # Required channel elements:

    def rssTitle(self):
        """title	The name of the channel. 
        It's how people refer to your service. 
        If you have an HTML website that contains the same information as your RSS file, 
        the title of your channel should be the same as the title of your website.
        """
        return self.context.title

    def rssDescription (self):
        """description
        Phrase or sentence describing the channel.
        """
        return self.context.summary

    def rssLink(self):
        """link	
        The URL to the HTML website corresponding to the channel.
        """
        return url.absoluteURL(self.context, self.request)

    # items of a channel:

    def rssItems(self):
        """Elements of <item> 
        A channel may contain any number of <item>s. 
        An item may represent a "story" -- much like a story in a newspaper or magazine; 
        if so its description is a synopsis of the story, and the link points to the full story. 
        An item may also be complete in itself, if so, the description contains the text (entity-encoded HTML is allowed; 
        see examples), and the link and title may be omitted. 
        All elements of an item are optional, 
        however at least one of title or description must be present. 
        
        title	The title of the item.
        link	The URL of the item.
        description     	The item synopsis.
        pubDate	Indicates when the item was published. 
        """

        bill_id = self.context.bill_id

        results = queries.execute_sql(
                            statements.sql_bill_timeline, item_id=bill_id)
        path = url.absoluteURL(self.context, self.request)
        rlist = []
        for result in results:
            rlist.append({
                    'title': result.atype,
                    'description': result.title,
                    'date': result.adate.isoformat()
                })
        return rlist

