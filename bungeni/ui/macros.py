from zope.publisher.browser import BrowserView
from zope.app.basicskin.standardmacros import StandardMacros as BaseMacros
from zope.app.pagetemplate import ViewPageTemplateFile

class BungeniCalendarMacros( BrowserView ):

    template = ViewPageTemplateFile('calendar/templates/macros.pt')

    def __getitem__(self, key):
        return self.template.macros[key]

