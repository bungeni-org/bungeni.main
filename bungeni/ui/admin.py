# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni admin views

$Id$
"""

from zope import component
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.formlib import form, namedtemplate

from bungeni.alchemist import Session
from bungeni.alchemist import ui
from bungeni.models import domain, interfaces
# !+DISABLE_XAPIAN
#from bungeni.core.index import IndexReset
from bungeni.core.serialize import batch_serialize
from bungeni.ui import browser
from bungeni.ui.interfaces import IBungeniSkin, ISerializationManager
from bungeni.utils import register
from bungeni.ui.i18n import _

@register.view(interfaces.IBungeniAdmin, IBungeniSkin, name="email-settings",
    protect={"zope.ManageSite": register.VIEW_DEFAULT_ATTRS})
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
    like_class=EmailSettings)
class XapianSettings(browser.BungeniBrowserView):
    
    render = ViewPageTemplateFile("templates/xapian-settings.pt")
    
    def __init__(self, context, request):
        return super(XapianSettings, self).__init__(context, request)
    
    def __call__(self):
        if self.request.method == "POST":
            pass
            # !+DISABLE_XAPIAN
            #IndexReset().start()
        return self.render()
    

@register.view(interfaces.IBungeniAdmin, IBungeniSkin, name="registry-settings",
    like_class=EmailSettings)
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





@register.view(interfaces.IBungeniAdmin, IBungeniSkin, 
    name="serialization-manager", like_class=EmailSettings)
class SerializationManager(form.PageForm, browser.BungeniBrowserView):
    template = namedtemplate.NamedTemplate("alchemist.form")
    form_fields = form.FormFields(ISerializationManager)
    form_name = _(u"Batch Serialization")
    form_description = _(u"This will serialize all workflowable objects "
        "in Bungeni to XML. You can limit by type below or choose "
        "*All types* to serialize everything."
    )
    
    @form.action(_(u"Serialize Items"), 
        name="serialize-objects")
    def handle_serialize_objects(self, action, data):
        item_count = batch_serialize(data.get("object_type"))
        self.status = _("Sent ${item_count} items for serialization",
            mapping = { "item_count": item_count }
        )
