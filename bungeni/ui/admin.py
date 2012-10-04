# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni admin views

$Id$
"""

from zope import component
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.formlib import form

from bungeni.alchemist import Session
from bungeni.alchemist import ui
from bungeni.models import domain, interfaces
from bungeni.core.index import IndexReset
from bungeni.ui import browser
from bungeni.ui.interfaces import IBungeniSkin
from bungeni.utils import register
#from bungeni.ui.utils.queries import execute_sql


@register.view(interfaces.IBungeniAdmin, IBungeniSkin, name="settings",
    protect={"zope.ManageSite": register.VIEW_DEFAULT_ATTRS})
class Settings(ui.EditForm):
    
    form_fields = form.Fields(interfaces.IBungeniSettings)
    
    def update(self):
        settings = component.getUtility(interfaces.IBungeniSettings)()
        self.adapters = {interfaces.IBungeniSettings : settings}
        super(Settings, self).update()


## class FieldEditColumn(column.FieldEditColumn):
##     def renderCell(self, item, formatter):
##         id = self.makeId(item)
##         request = formatter.request
##         field = self.field
##         if self.bind:
##             field = field.bind(item)
##         widget = component.getMultiAdapter((field, request), IInputWidget)
##         widget.setPrefix(self.prefix + "." + id)
##         if self.widget_extra is not None:
##             widget.extra = self.widget_extra
##         if self.widget_class is not None:
##             widget.cssClass = self.widget_class
##         ignoreStickyValues = getattr(formatter, "ignoreStickyValues", False)
##         if ignoreStickyValues or not widget.hasInput():
##             widget.setRenderedValue(self.get(item))
##         return widget()


@register.view(interfaces.IBungeniAdmin, IBungeniSkin, name="email-settings",
    like_class=Settings)
class EmailSettings(ui.EditForm):
    
    form_fields = form.Fields(interfaces.IBungeniEmailSettings)
    
    def update(self):
        settings = \
            component.getUtility(interfaces.IBungeniEmailSettings)()
        self.adapters = {interfaces.IBungeniEmailSettings : settings}
        super(EmailSettings, self).update()



@register.view(None, IBungeniSkin, name="user-settings")
class UserSettings(ui.EditForm):

    form_fields = form.Fields(interfaces.IBungeniUserSettings, interfaces.IUser)
    form_fields = form_fields.omit("user_id", "login", "date_of_death", "status")
    
    def update(self):
        session = Session()
        query = session.query(domain.User).filter(
            domain.User.login == self.request.principal.id)
        results = query.all()
        if len(results) == 1:
            user = results[0]
        else:
            user = None
        settings = interfaces.IBungeniUserSettings(user, None)
        if settings is None:
            raise SyntaxError("User Settings Only For Database Users")
        self.adapters = {interfaces.IBungeniUserSettings : settings,
                          interfaces.IUser : user}
        super(UserSettings, self).update()

@register.view(interfaces.IBungeniAdmin, IBungeniSkin, name="xapian-settings",
    like_class=Settings)
class XapianSettings(browser.BungeniBrowserView):
    
    render = ViewPageTemplateFile("templates/xapian-settings.pt")
    
    def __init__(self, context, request):
        return super(XapianSettings, self).__init__(context, request)
    
    def __call__(self):
        if self.request.method == "POST":
            IndexReset().start()
        return self.render()
    

@register.view(interfaces.IBungeniAdmin, IBungeniSkin, name="registry-settings",
    like_class=Settings)
class RegistrySettings(ui.EditForm):
    
    form_fields = form.Fields(interfaces.IBungeniRegistrySettings)
    
    def update(self):
        '''
        # !+REGISTRY(mr, apr-2011) should store these counts (per type) in a generic table
        # !+RESETTABLE per parliamentary session
        if self.request.method == "POST":
            # !+NUMBER_GENERATION (ah, nov-2011) - Reset the number sequence here.
            # Added the 'false' parameter at the end, otherwise setval() automatically
            # increments the sequence when called.
            # NOTE: this is a direct PG call, there is no SQLAlchemy way of resetting
            # a sequence, perhaps they should be dropped and recreated in SQLALchemy
            if self.request.get("form.questions_number") == "on":
                execute_sql("SELECT setval('question_registry_sequence', 1, false);")
            if self.request.get("form.motions_number") == "on":
                execute_sql("SELECT setval('motion_registry_sequence', 1, false);")
            if self.request.get("form.agendaitems_number") == "on":
                execute_sql("SELECT setval('agendaitem_registry_sequence', 1, false);")
            if self.request.get("form.bills_number") == "on":
                execute_sql("SELECT setval('bill_registry_sequence', 1, false);")
            if self.request.get("form.reports_number") == "on":
                execute_sql("SELECT setval('report_registry_sequence', 1, false);")
            if self.request.get("form.tableddocuments_number") == "on":
                execute_sql("SELECT setval('tableddocument_registry_sequence', 1, false);")
            if self.request.get("form.global_number") == "on":
                execute_sql("SELECT setval('registry_number_sequence', 1, false);")
        '''
        settings = \
            component.getUtility(interfaces.IBungeniRegistrySettings)()
        self.adapters = {interfaces.IBungeniRegistrySettings : settings}



