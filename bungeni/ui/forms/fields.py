# encoding: utf-8

from zope.app.pagetemplate import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy, ProxyFactory
from zope import security
from zope.formlib import form
from zope.i18n import translate

from ore.workflow import interfaces
from bungeni.alchemist.ui import DynamicFields
from bungeni.alchemist.ui import DisplayFormViewlet

from bungeni.alchemist.model import queryModelDescriptor
from bungeni.alchemist.interfaces import IAlchemistContainer
from bungeni.alchemist.interfaces import IAlchemistContent
from bungeni.ui.forms.workflow import bindTransitions
from bungeni.ui.i18n import _
from bungeni.core.translation import get_translation_for, get_all_languages
from copy import copy

def filterFields(context, form_fields):
    omit_names = []
    if IAlchemistContent.providedBy(context):
        md = queryModelDescriptor(context.__class__)
        for field in form_fields:
            try:
                can_write = security.canWrite( context, field.__name__)
                can_read = security.canAccess( context, field.__name__)
            except AttributeError:
                can_write = can_read = False
            if can_write:
                continue
            if can_read:
                field.for_display = True
                field.custom_widget = md.get(field.__name__).view_widget
            else:
                omit_names.append(field.__name__)
    elif not IAlchemistContainer.providedBy(context):
        ctx=getattr(context, 'context', None)
        if ctx:
            filterFields(ctx, form_fields)
        else:
            raise NotImplementedError
    return form_fields.omit(*omit_names)

class BungeniAttributeDisplay(DynamicFields, DisplayFormViewlet):
    mode = "view"
    template = ViewPageTemplateFile('templates/display_form.pt')
    form_name = _(u"General")
    has_data = True
    adapters = None

    
    def get_note(self):
        """ return Notes if supplied by context"""
        if getattr(self.context, 'note', False):
            return self.context.note

    def setupActions(self):
        return
        wf = self.wf = interfaces.IWorkflowInfo(self.context, None)
        if wf is not None:
            transitions = self.wf.getManualTransitionIds()
            self.actions = tuple(bindTransitions(
                self, transitions, None, interfaces.IWorkflow( self.context)))

    def setUpWidgets(self, ignore_request=False):
        languages = get_all_languages()
        self.form_fields = filterFields(self.context, self.form_fields)
        
        #do not display empty form fields
        omit_names = []
        for f in self.form_fields:
            val = getattr(self.context, f.__name__)
            if val is None:
                omit_names.append(f.__name__)
        self.form_fields = self.form_fields.omit(*omit_names)
        
        lang = self.request.locale.getLocaleID()
        try:
            translation = get_translation_for(self.context, lang)
        except:
            translation = []
        if (not translation) and (getattr(self.context, 'language', None) and
                (getattr(self.context, 'language', None) != lang)):
            supported_lang = languages.get(lang)
            if supported_lang:
                langname = supported_lang.get('native',None)
                if langname == None:
                    langname = supported_lang.get('name')
                self.status = translate(
                    _(u'This content is not yet translated into $language', 
                        mapping={'language': langname}),
                    domain="bungeni.ui",
                    context=self.request)
        context = copy(removeSecurityProxy(self.context))
        for field_translation in translation:
            setattr(context, field_translation.field_name, 
                    field_translation.field_text)
        self.widgets = form.setUpEditWidgets(
            self.form_fields, self.prefix, context, self.request,
            adapters=self.adapters, for_display=True, ignore_request=ignore_request)
     

    def update( self ):
        self.setupActions()
        super(BungeniAttributeDisplay, self).update() 
        self.setupActions()  # after we transition we have different actions
        try:
            wf_state =interfaces.IWorkflowState(
                removeSecurityProxy(self.context)).getState()
            self.wf_status = wf_state
        except:
            pass

    @property
    def form_name( self ):
        parent = self.context.__parent__
        if IAlchemistContainer.providedBy(parent):
            descriptor = queryModelDescriptor(parent.domain_model)
        elif IAlchemistContent.providedBy(self.context):
            descriptor = queryModelDescriptor(self.context.__class__)
        else:
            raise RuntimeError("Unsupported object: %s." % repr(self.context))
        
        if descriptor:
            name = getattr(descriptor, 'display_name', None)

        if name is None:
            name = self.context.__class__.__name__

        return name

    def getObjectClass(self):
        return self.context.__class__.__name__

