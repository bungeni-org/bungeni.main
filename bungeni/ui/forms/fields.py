# encoding: utf-8

#from zope.app.pagetemplate import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy
from zope import security
from zope import interface
from zope.formlib import form
from zope.i18n import translate

from bungeni.core.workflow import interfaces
from bungeni.alchemist.ui import DynamicFields

from bungeni.alchemist.model import queryModelDescriptor
from bungeni.alchemist.interfaces import IAlchemistContainer
from bungeni.alchemist.interfaces import IAlchemistContent
from bungeni.ui.forms.workflow import bindTransitions
from bungeni.ui.i18n import _
from bungeni.ui import browser
from bungeni.ui import z3evoque
from bungeni.models.interfaces import ITranslatable
from bungeni.core.translation import get_translation_for, get_all_languages
from copy import copy

def filterFields(context, form_fields):
    omit_names = []
    if IAlchemistContent.providedBy(context):
        md = queryModelDescriptor(context.__class__)
        for field in form_fields:
            try:
                can_write = security.canWrite(context, field.__name__)
                can_read = security.canAccess(context, field.__name__)
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
        ctx = getattr(context, "context", None)
        if ctx:
            filterFields(ctx, form_fields)
        else:
            raise NotImplementedError
    return form_fields.omit(*omit_names)


class BungeniAttributeDisplay(DynamicFields, form.SubPageDisplayForm,
    browser.BungeniViewlet):
    """
    bungeni.subform.manager
    """

    # evoque
    render = z3evoque.ViewTemplateFile("form.html#display")
    # zpt
    #render = ViewPageTemplateFile("templates/display_form.pt")

    # the instance of the ViewProvideViewletManager
    provide = z3evoque.ViewProvideViewletManager(
        default_provider_name="bungeni.subform.manager")

    mode = "view"
    form_name = _(u"General")
    view_id = "display-item"
    has_data = True
    adapters = None

    def get_note(self):
        """Return Notes if supplied by context.
        """
        context = removeSecurityProxy(self.context)
        if getattr(context, "note", False):
            return context.note
    
    def setupActions(self):
        return # !+ ??
        wfc = interfaces.IWorkflowController(self.context, None)
        if wfc is not None:
            transitions = wfc.getManualTransitionIds()
            self.actions = tuple(
                bindTransitions(self, transitions, wfc.workflow))
    
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
        context = self.context
        if ITranslatable.providedBy(self.context):
            lang = self.request.locale.getLocaleID()
            try:
                translation = get_translation_for(self.context, lang)
            except:
                translation = []
            if (not translation and
                getattr(self.context, "language", None) and
                getattr(self.context, "language", None) != lang
            ):
                supported_lang = languages.get(lang)
                if supported_lang:
                    langname = supported_lang.get("native", None)
                    if langname == None:
                        langname = supported_lang.get("name")
                    self.status = translate(
                        _(u"This content is not yet translated into" +\
                            " $language",
                            mapping={"language": langname}),
                        domain="bungeni",
                        context=self.request
                    )
            context = copy(removeSecurityProxy(self.context))
            for field_translation in translation:
                setattr(context, field_translation.field_name,
                        field_translation.field_text)
        self.widgets = form.setUpEditWidgets(
            self.form_fields, self.prefix, context, self.request,
            adapters=self.adapters,
            for_display=True,
            ignore_request=ignore_request
        )

    def update(self):
        self.setupActions()
        #super(BungeniAttributeDisplay, self).update()
        DynamicFields.update(self)
        self.setupActions()  # after we transition we have different actions
        try:
            self.wf_status = interfaces.IStateController(
                removeSecurityProxy(self.context)).get_status()
        except:
            pass

    @property
    def form_name(self):
        parent = self.context.__parent__
        #DESCRIPTOR(miano, June 2011) This originally first checked the parent's 
        #descriptor then the item's descriptor. Why???
        #This was causing an error in the display pages of items in the 
        #workspace since the workspace containers have no descriptor
        #defined for them.
        if IAlchemistContent.providedBy(self.context):
            descriptor = queryModelDescriptor(self.context.__class__)
        elif IAlchemistContainer.providedBy(parent):
            descriptor = queryModelDescriptor(parent.domain_model)
        else:
            raise RuntimeError("Unsupported object: %s." % repr(self.context))

        if descriptor:
            name = getattr(descriptor, "display_name", None)

        if name is None:
            name = self.context.__class__.__name__

        return name

    def getObjectClass(self):
        return self.context.__class__.__name__

    # !+ from ui.forms.common.BaseForm -- merge these 2 base classes? 
    @property
    def invariantErrors(self):
        """ () -> [error:zope.interface.Invalid]
        """
        errors = []
        for error in self.errors:
            if isinstance(error, interface.Invalid):
                errors.append(error)
        return errors

    @property
    def invariantMessages(self):
        """ () -> [message:str]
        Called from the form.html#display template.
        """
        return filter(None,
                [ error.message for error in self.invariantErrors ])

