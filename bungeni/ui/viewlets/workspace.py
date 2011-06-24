from zope.app.component.hooks import getSite
from ploned.ui.viewlet import StructureAwareViewlet
from zope.app.pagetemplate import ViewPageTemplateFile
from bungeni.ui.utils import url

class WorkspaceContextNavigation(StructureAwareViewlet):

    render = ViewPageTemplateFile("templates/workspace.pt")
    
    def update(self):
        self.tabs = []
        app = getSite()
        keys = app["workspace"]["documents"].keys()
        for key in keys:
            tab = {}
            tab["title"] = key
            tab["url"] = url.absoluteURL(app["workspace"]["documents"][key], self.request)
            self.tabs.append(tab)
