from zope.app.pagetemplate import ViewPageTemplateFile
from bungeni.ui.utils.url import get_section_name, absoluteURL as abs_url,\
                                 get_subsection_name
from zope.app.component.hooks import getSite
from urlparse import urljoin

#!+FORMS(mb, dec-2011). Search form should be based off formlib

ALLOWED_SEARCH_SUBSECTIONS = ("committees","bills","questions", "motions",
                              "tableddocuments","agendaitems")
    
class SearchViewlet(object):
    render = ViewPageTemplateFile("templates/search.pt")
        
    def update(self):
        section = get_section_name()
        base_url = abs_url(getSite(), self.request)
        subsection = ""
        if not section:
            section = "business"
        if section == "business":
            subsection = get_subsection_name(self.request)
            
            if subsection in ALLOWED_SEARCH_SUBSECTIONS:
                subsection = "/" + subsection
            else:
                subsection = ""
        
        self.action = urljoin(base_url, section) + subsection + "/search"
            
