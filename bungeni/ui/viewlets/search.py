from zope.app.pagetemplate import ViewPageTemplateFile
from bungeni.core.interfaces import ISection
from navigation import _get_context_chain
from zope.traversing.browser import absoluteURL
from bungeni.ui.utils.url import get_section_name, absoluteURL as abs_url
from zope.app.component.hooks import getSite
from urlparse import urljoin

class SearchViewlet(object):
    render = ViewPageTemplateFile("templates/search.pt")

    def update(self):
        base_url = abs_url(getSite(), self.request)
        self.action = urljoin(base_url, get_section_name()) + '/search'
