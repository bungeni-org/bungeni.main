from zope.app.pagetemplate import ViewPageTemplateFile
from bungeni.core.interfaces import ISection
from navigation import _get_context_chain
from zope.traversing.browser import absoluteURL

class SearchViewlet(object):
    render = ViewPageTemplateFile("templates/search.pt")

    def update(self):
        chain = _get_context_chain(self.context)
        i = len(chain) - 1
        ob = chain[i]
        while not ISection.providedBy(ob):
            i -= 1
            if i < 0:
                ob = None
                break
            ob = chain[i]
        if ob:
            self.action = absoluteURL(ob, self.request) + '/search'
        else:
            self.action = None
