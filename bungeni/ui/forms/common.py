# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Common forms for Bungeni user interface

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.forms.common")


#import transaction
from copy import copy
from zope.publisher.interfaces import BadRequest
from zope import component
from zope import interface
from zope import formlib

from zope.security.proxy import removeSecurityProxy
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from zope.schema.interfaces import IChoice
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.location.interfaces import ILocation
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.container.contained import ObjectRemovedEvent
from zope.formlib.interfaces import IDisplayWidget
from zope.formlib.namedtemplate import NamedTemplate
from zope.securitypolicy.interfaces import IPrincipalRoleMap
from zope.securitypolicy.settings import Allow
import sqlalchemy as sa

from bungeni.alchemist import Session
from bungeni.alchemist import ui
from bungeni.alchemist.interfaces import IAlchemistContainer, IAlchemistContent
from bungeni.core.interfaces import TranslationCreatedEvent
from bungeni.core.language import get_default_language
from bungeni.core.translation import is_translation, get_field_translations
from bungeni.core.language import CurrentLanguageVocabulary, get_language_by_name
from bungeni.core.workflows.utils import set_group_local_role, unset_group_local_role
from bungeni.models.interfaces import IVersion, IAttachmentContainer #, IBungeniContent, ISittingContainer
from bungeni.models import domain
from bungeni.ui.forms.fields import filterFields
from bungeni.ui.interfaces import (
    IBungeniSkin, 
    IFormAddLayer, 
    IFormEditLayer,
    IGenenerateVocabularyDefault,
)
from bungeni.ui import browser
#from bungeni.ui import z3evoque
from bungeni.ui.utils import url
from bungeni.ui.container import invalidate_caches_for
from bungeni.utils import naming, register
from bungeni.capi import capi
from bungeni import _, translate
from bungeni.core.workflows.utils import get_group_privilege_extent_context


#!+CHANGES(mb, Mar-2013) Turned off - has a side effect (multiple serialization)
def cascade_modifications(obj):
    """Cascade modify events on an object to the direct parent.
    !+NAMING(mr, nov-2012) why cascade (implies down?!) instead of bubble (up, usually)?
    Plus, we are not cascading *modifications* anyway, we are just notifying of such... !
    !+EVENT_CONSUMER_ISSUE(mr, nov-2012) why fire new events off the ancestor if 
    the descendent has presumably already fired off its own modified event? 
    If anything it should be a new specialized type of event, with a pointer to 
    the original trigger object (descendent that was modified), so that the 
    consumer can know it is a "derived" event and maybe act accordingly... as
    it is, all modified event handlers registerd will execute, e.g. auditing of 
    the change if the ancestor is auditable, but the change had already been 
    audited on the originator modified descendent object.
    """
    if not ILocation.providedBy(obj):
        return
    if IAlchemistContainer.providedBy(obj.__parent__):
        if IAlchemistContent.providedBy(obj.__parent__.__parent__):
            notify(ObjectModifiedEvent(obj.__parent__.__parent__))
    elif IAlchemistContent.providedBy(obj.__parent__):
        notify(ObjectModifiedEvent(obj.__parent__))

class DisplayForm(browser.BungeniBrowserView):
    """Content Display
    """
    #template = z3evoque.PageViewTemplateFile("content.html#view")
    template = ViewPageTemplateFile("templates/content-view.pt")
    
    form_name = _("View")
    
    def __call__(self):
        return self.template()


# !+PageForm(mr, jul-2010) converge usage of formlib.form.PageForm to PageForm
# !+NamedTemplate(mr, jul-2010) converge all views to not use anymore
# !+alchemist.form(mr, jul-2010) converge all form views to not use anymore
class PageForm(ui.BaseForm, formlib.form.PageForm, browser.BungeniBrowserView):
    #template = z3evoque.PageViewTemplateFile("form.html#page")
    template = NamedTemplate("alchemist.form")


@register.view(IAttachmentContainer, layer=IBungeniSkin, name="add",
    protect={"bungeni.attachment.Add": register.VIEW_DEFAULT_ATTRS})
#@register.view(ISittingContainer, layer=IBungeniSkin, name="add",
#    protect={"bungeni.sitting.Add": register.VIEW_DEFAULT_ATTRS})
class AddForm(ui.AddForm):
    """Custom add-form for Bungeni content.
    
    Additional actions are set up to allow users to continue editing
    an object, or add another of the same kind.
    """
    interface.implements(ILocation, IDCDescriptiveProperties)
    description = None
    
    def __init__(self, *args):
        super(AddForm, self).__init__(*args)
        interface.alsoProvides(self.request, IFormAddLayer)
    
    def validate(self, action, data):
        errors = super(AddForm, self).validate(action, data)
        errors += self.validate_unique(action, data)
        errors += self.validate_derived_table_schema(action, data)
        for validator in getattr(self.model_descriptor, "custom_validators", ()):
            errors += validator(action, data, None, self.context)
        return errors
    
    def filter_fields(self):
        return filterFields(self.context, self.form_fields)
    
    def update(self):
        super(AddForm, self).update()
        # set humanized default value for choice fields with no defaults
        for widget in self.widgets:
            field = widget.context
            if IChoice.providedBy(field):
                if IGenenerateVocabularyDefault.providedBy(widget):
                    field.default = widget.getDefaultVocabularyValue()
            if IChoice.providedBy(field) and field.default is None:
                    widget._messageNoValue = _("bungeni_widget_no_value", 
                            "choose ${title} ...",
                        mapping = {"title": field.title}
                    )
    
    @property
    def context_class(self):
        return self.domain_model
    
    @property
    def type_name(self):
        if self.model_descriptor:
            name = getattr(self.model_descriptor, "display_name", None)
        if not name:
            name = getattr(self.domain_model, "__name__", None)
        return name
    
    @property
    def form_name(self):
        return _(u"add_item_legend", default=u"Add $name", mapping={
            "name": translate(self.type_name, context=self.request)})
    
    @property
    def title(self):
        return _(u"add_item_title", default=u"Adding $name", mapping={
            "name": translate(self.type_name.lower(), context=self.request)})
    
    def finishConstruction(self, ob):
        """Adapt the custom fields to the object.
        """
        adapts = self.Adapts
        if adapts is None:
            adapts = self.model_interface
        self.adapters = {adapts: ob}
    
    def createAndAdd(self, data):
        ob = super(AddForm, self).createAndAdd(data)
        self.created_object = ob # !+ used by calendar/browser sitting
        # execute domain.Entity on create hook
        removeSecurityProxy(ob).on_create()
        # cascade_modifications(ob)
        return ob
    
    @formlib.form.action(_(u"Save and view"), name="save_and_view",
        condition=formlib.form.haveInputWidgets)
    def handle_add_and_view(self, action, data):
        ob = self.createAndAdd(data)
        name = self.domain_model.__name__
        if not self._next_url:
            self._next_url = "%s/?portal_status_message=%s Added" % (
                    url.absoluteURL(ob, self.request), name)
    
    @formlib.form.action(_(u"Cancel"), name="cancel",
        validator=ui.null_validator)
    def handle_cancel(self, action, data):
        """Cancelling redirects to the listing."""
        if not self._next_url:
            self._next_url = url.absoluteURL(self.__parent__, self.request)
        self.request.response.redirect(self._next_url)
    
    @formlib.form.action(_(u"Save"), name="save", 
        condition=formlib.form.haveInputWidgets)
    def handle_add(self, action, data):
        ob = self.createAndAdd(data)
        name = self.domain_model.__name__
        if not self._next_url:
            self._next_url = "%s/edit?portal_status_message=%s Added" % (
                    url.absoluteURL(ob, self.request), name)
    
    @formlib.form.action(_(u"Save and add another"),
        name="save_and_add_another",
        condition=formlib.form.haveInputWidgets)
    def handle_add_and_add_another(self, action, data):
        ob = self.createAndAdd(data)
        name = self.domain_model.__name__
        if not self._next_url:
            self._next_url = "%s/%s?portal_status_message=%s Added" % (
                    url.absoluteURL(self.context, self.request),
                    self.add_action_verb, 
                    name)
    
    @property
    def add_action_verb(self):
        return "add"



@register.view(domain.Attachment, layer=IBungeniSkin, name="edit",
    protect={"bungeni.attachment.Edit": register.VIEW_DEFAULT_ATTRS})
#@register.view(domain.Sitting, layer=IBungeniSkin, name="edit",
#    protect={"bungeni.sitting.Edit": register.VIEW_DEFAULT_ATTRS})
class EditForm(ui.EditForm):
    """Custom edit-form for Bungeni content.
    """
    def __init__(self, *args):
        # !+view/viewlet(mr, jul-2011)
        super(EditForm, self).__init__(*args)
        # !+IFormEditLayer(mr, jun-2013) why only for IBungeniContent?
        # For bungeni content, mark the request that we are in edit mode e.g. 
        # useful for when editing a question's response, but not wanting to 
        # offer option to submit the response while in response edit mode. 
        #if IBungeniContent.providedBy(self.context): # and self.mode=="edit"
        interface.alsoProvides(self.request, IFormEditLayer)
    
    # !+EDIT_FORM_TRANSLATION(mr, feb-2013) what is all this conditional 
    # translation-related logic here? It seems to be debris from some earlier 
    # refactoring... why is it not marked/commented/disabled/cleaned out?
    
    @property
    def is_translation(self):
        return is_translation(self.context)

    @property
    def side_by_side(self):
        return self.is_translation

    @property
    def form_name(self):
        if IVersion.providedBy(self.context):
            context = self.context.head
        else:
            context = self.context
        props = IDCDescriptiveProperties(context, None) or context
        
        if self.is_translation:
            language = get_language_by_name(self.context.language)["name"]
            return _(u"edit_translation_legend",
                     default=u"Editing $language translation of '$title'",
                     mapping={"title": translate(props.title, context=self.request),
                              "language": language})
        
        elif IVersion.providedBy(self.context):
            return _(u"edit_version_legend",
                     default=u'Editing "$title" (version $version)',
                     mapping={"title": translate(props.title, context=self.request),
                              "version": self.context.seq})
        return _(u"edit_item_legend", default=u'Editing "$title"',
                 mapping={"title": translate(props.title, context=self.request)})
    
    @property
    def form_description(self):
        if self.is_translation:
            # !+HEAD_DOCUMENT_ITEM(mr, sep-2011)
            language = get_language_by_name(self.context.head.language)["name"]
            return _(u"edit_translation_help",
                     default=u"The original $language version is shown on the left",
                     mapping={"language": language})

    def validate(self, action, data):
        errors = super(EditForm, self).validate(action, data)
        errors += self.validate_unique(action, data)
        errors += self.validate_derived_table_schema(action, data)
        for validator in getattr(self.model_descriptor, "custom_validators", ()):
            errors += validator(action, data, self.context, self.context.__parent__)
        return errors
    
    def filter_fields(self):
        return filterFields(self.context, self.form_fields)

    def setUpWidgets(self, ignore_request=False):
        super(EditForm, self).setUpWidgets(ignore_request=ignore_request)
        # for translations, add a ``render_original`` method to each
        # widget, which will render the display widget bound to the
        # original (HEAD) document
        if self.is_translation:
            # !+HEAD_DOCUMENT_ITEM(mr, sep-2011)
            head = self.context.head
            form_fields = ui.setUpFields(self.context.__class__, "view")
            for widget in self.widgets:
                form_field = form_fields.get(widget.context.__name__)
                if form_field is None:
                    form_field = formlib.form.Field(widget.context)

                # bind field to head document
                field = form_field.field.bind(head)

                # create custom widget or instantiate widget using
                # component lookup
                if form_field.custom_widget is not None:
                    display_widget = form_field.custom_widget(
                        field, self.request)
                else:
                    display_widget = component.getMultiAdapter(
                        (field, self.request), IDisplayWidget)

                display_widget.setRenderedValue(field.get(head))

                # attach widget as ``render_original``
                widget.render_original = display_widget
    
    def _do_save(self, data):
        formlib.form.applyChanges(self.context, self.form_fields, data)
        # !+EVENT_DRIVEN_CACHE_INVALIDATION(mr, mar-2011) no modify event
        # invalidate caches for this domain object type
        notify(ObjectModifiedEvent(self.context))
        #cascade_modifications(self.context)
        invalidate_caches_for(self.context.__class__.__name__, "edit")
        
    @formlib.form.action(_(u"Save"), name="save",
        condition=formlib.form.haveInputWidgets)
    def handle_edit_save(self, action, data):
        """Saves the document and goes back to edit page.
        """
        self._do_save(data)

    @formlib.form.action(_(u"Save and view"), name="save_and_view",
        condition=formlib.form.haveInputWidgets)
    def handle_edit_save_and_view(self, action, data):
        """Saves the  document and redirects to its view page.
        """
        self._do_save(data)
        if not self._next_url:
            self._next_url = url.absoluteURL(self.context, self.request) + \
                "?portal_status_message= Saved"
        self.request.response.redirect(self._next_url)

    @formlib.form.action(_(u"Cancel"), name="cancel",
        validator=ui.null_validator)
    def handle_edit_cancel(self, action, data):
        """Cancelling redirects to the listing.
        """
        if not self._next_url:
            self._next_url = url.absoluteURL(self.context, self.request)
        self.request.response.redirect(self._next_url)


class GroupEditForm(EditForm):
    def _do_save(self, data):
        group_role_changed = False
        prm = IPrincipalRoleMap(get_group_privilege_extent_context(self.context))
        if (data["group_role"] != self.context.group_role):
            if prm.getSetting(self.context.group_role, self.context.principal_name) == Allow:
                group_role_changed = True
                unset_group_local_role(self.context)
        formlib.form.applyChanges(self.context, self.form_fields, data)
        if group_role_changed:
            set_group_local_role(self.context)
        notify(ObjectModifiedEvent(self.context))


class TranslateForm(AddForm):
    """Custom translate-form for Bungeni content.
    """
    is_translation = False
    
    @property
    def side_by_side(self):
        return True

    def __init__(self, *args):
        # !+view/viewlet(mr, jul-2011)
        super(TranslateForm, self).__init__(*args)
        self.language = self.request.get("language", get_default_language())

    def translatable_field_names(self):
        names = ["language"]
        for field in self.model_descriptor.edit_columns:
            if field.property and (field.property._type == unicode):
                names.append(field.name)
        return names

    def set_untranslatable_fields_for_display(self):
        translatable_field_names = self.translatable_field_names()
        for field in self.form_fields:
            if field.__name__ not in translatable_field_names:
                field.for_display = True
                field.custom_widget = self.model_descriptor.get(
                    field.__name__).view_widget

    def validate(self, action, data):
        return formlib.form.getWidgetsData(self.widgets, self.prefix, data)

    @property
    def form_name(self):
        language = get_language_by_name(self.language)["name"]
        return _(u"translate_item_legend",
            default=u"Add $language translation",
            mapping={"language": language}
        )

    @property
    def form_description(self):
        language = get_language_by_name(self.language)["name"]
        props = (
            (IDCDescriptiveProperties.providedBy(self.context) and
                self.context) or
            IDCDescriptiveProperties(self.context)
        )
        if self.is_translation:
            return _(u"edit_translation_legend",
                default=u'Editing $language translation of "$title"',
                mapping={
                    "title": translate(props.title, context=self.request),
                    "language": language
                }
            )
        else:
            return _(u"translate_item_help",
                default=u'The document "$title" has not yet been translated ' \
                    u"into $language. Use this form to add the translation",
                mapping={
                    "title": translate(props.title, context=self.request),
                    "language": language
                }
            )

    @property
    def title(self):
        language = get_language_by_name(self.language)["name"]
        return _(u"translate_item_title",
            default=u"Adding $language translation",
            mapping={"language": language}
        )

    @property
    def domain_model(self):
        return type(removeSecurityProxy(self.context))

    def setUpWidgets(self, ignore_request=False):
        self.set_untranslatable_fields_for_display()

        #get the translation if available
        language = self.request.get("language")

        translation = get_field_translations(self.context, language)
        if translation:
            self.is_translation = True
        else:
            self.is_translation = False
        context = copy(removeSecurityProxy(self.context))
        for field_translation in translation:
            setattr(context, field_translation.field_name,
                    field_translation.field_text)
        self.widgets = formlib.form.setUpEditWidgets(
            self.form_fields, self.prefix, context, self.request,
            adapters=self.adapters, ignore_request=ignore_request)

        if language is not None:
            widget = self.widgets["language"]
            try:
                self.language = language
                widget.vocabulary = CurrentLanguageVocabulary().__call__(self)
                widget.vocabulary.getTermByToken(language)
            except LookupError:
                raise BadRequest("No such language token: '%s'" % language)

            # if the term exists in the vocabulary, set the value on
            # the widget
            widget.setRenderedValue(language)
        # for translations, add a ``render_original`` method to each
        # widget, which will render the display widget bound to the
        # original (HEAD) document
        # render pivot language as source if there is a translation
        head = self.context
        if capi.pivot_languages:
            for plang in capi.pivot_languages:
                trans = get_field_translations(head, plang)
                if trans:
                    head = copy(removeSecurityProxy(head))
                    for field_translation in trans:
                        setattr(head, field_translation.field_name,
                                field_translation.field_text)
                    break
        form_fields = ui.setUpFields(self.context.__class__, "view")
        for widget in self.widgets:
            form_field = form_fields.get(widget.context.__name__)
            if form_field is None:
                form_field = formlib.form.Field(widget.context)

            # bind field to head document
            field = form_field.field.bind(head)

            # create custom widget or instantiate widget using
            # component lookup
            if form_field.custom_widget is not None:
                display_widget = form_field.custom_widget(
                    field, self.request)
            else:
                display_widget = component.getMultiAdapter(
                    (field, self.request), IDisplayWidget)

            display_widget.setRenderedValue(field.get(head))

            # attach widget as ``render_original``
            widget.render_original = display_widget

    @formlib.form.action(_(u"Save translation"), name="save_translation",
        condition=formlib.form.haveInputWidgets)
    def handle_add_save(self, action, data):
        """After succesful creation of translation, redirect to the view.
        """
        #url = url.absoluteURL(self.context, self.request)
        #language = get_language_by_name(data["language"])["name"]
        session = Session()
        trusted = removeSecurityProxy(self.context)
        mapper = sa.orm.object_mapper(trusted)
        pk = getattr(trusted, mapper.primary_key[0].name)
        
        curr_trans_by_name = dict( (ct.field_name, ct) 
            for ct in get_field_translations(self.context, data["language"]) )
        
        def is_changed(context, field_name, new_field_text):
            if field_name in curr_trans_by_name:
                old_field_text = curr_trans_by_name[field_name].field_text
            else:
                old_field_text = getattr(context, field_name)
            return not old_field_text == new_field_text
        
        translated_attribute_names = []
        for field_name in data.keys():
            if field_name == "language":
                continue
            if is_changed(self.context, field_name, data[field_name]):
                translated_attribute_names.append(field_name)
                if field_name in curr_trans_by_name:
                    translation = curr_trans_by_name[field_name]
                else:
                    translation = domain.FieldTranslation()
                    translation.object_id = pk
                    translation.object_type = naming.polymorphic_identity(trusted.__class__)
                    translation.field_name = field_name
                    translation.lang = data["language"]
                    session.add(translation)
                translation.field_text = data[field_name]
        
        if translated_attribute_names:
            session.flush()
            notify(TranslationCreatedEvent(self.context, 
                    data["language"], sorted(translated_attribute_names)))
        
        # !+EVENT_DRIVEN_CACHE_INVALIDATION(mr, mar-2011) no translate event
        # invalidate caches for this domain object type
        #invalidate_caches_for(trusted.__class__.__name__, "translate")
        
        #if not self._next_url:
        #    self._next_url = ( \
        #        "%s/versions/%s" % (url, stringKey(version)) + \
        #        "?portal_status_message=Translation added")
        
        self._finished_add = True


@register.view(domain.Attachment, layer=IBungeniSkin, name="delete",
    protect={"bungeni.attachment.Delete": register.VIEW_DEFAULT_ATTRS})
#@register.view(domain.Sitting, layer=IBungeniSkin, name="delete",
#    protect={"bungeni.sitting.Delete": register.VIEW_DEFAULT_ATTRS})
class DeleteForm(PageForm):
    """Delete-form for Bungeni content.

    Confirmation

        The user is presented with a confirmation form which details
        the items that are going to be deleted.

    Subobjects

        Recursively, a permission check is carried out for each item
        that is going to be deleted. If a permission check fails, an
        error message is displayed to the user.

    Will redirect back to the container on success.
    """
    form_template = NamedTemplate("alchemist.form")
    template = ViewPageTemplateFile("templates/delete.pt")
    #template = z3evoque.PageViewTemplateFile("delete.html")
    
    _next_url = None
    form_fields = formlib.form.Fields()

    def _can_delete_item(self, action):
        return True

    def nextURL(self):
        return self._next_url

    def update(self):
        self.subobjects = self.get_subobjects()
        super(DeleteForm, self).update()

    def get_subobjects(self):
        return ()

    def delete_subobjects(self):
        return 0

    @formlib.form.action(_(u"Delete"),
                         name="delete",
                         condition=_can_delete_item)
    def handle_delete(self, action, data):
        count = self.delete_subobjects()
        container = self.context.__parent__
        ob = removeSecurityProxy(self.context)
        session = Session()
        session.delete(ob)
        # execute domain.Entity on delete hook
        ob.on_delete()
        count += 1
        try:
            session.flush()
        except sa.exc.IntegrityError, e:
            # this should not happen in production; it's a critical
            # error, because the transaction might have failed in the
            # second phase of the commit
            session.rollback()
            log.critical(e)
            self.status = _(
                "Could not delete item due to database integrity error. "
                "You may wish to try deleting any related sub-records first?")
            return self.render()
        
        #TODO: check that it is removed from the index!
        notify(ObjectRemovedEvent(
            self.context, oldParent=container, oldName=self.context.__name__))
        # we have to switch our context here otherwise the deleted object will
        # be merged into the session again and reappear magically
        self.context = container
        #cascade_modifications(container)
        next_url = self.nextURL()

        if next_url is None:
            next_url = url.absoluteURL(container, self.request) + \
                       "/?portal_status_message=%d items deleted" % count
        if self.is_headless:
            log.info("Deleting in headless mode - No redirection")
        else:
            self.request.response.redirect(next_url)
        
    @formlib.form.action(_(u"Cancel"), name="cancel",
                         validator=ui.null_validator)
    def delete_cancel(self, action, data):
        """Cancelling redirects to the listing."""
        if not self._next_url:
            self._next_url = url.absoluteURL(self.context, self.request)
        self.request.response.redirect(self._next_url)


class SignOpenDocumentForm(PageForm):
    """Provides a form to allow signing of a document open for signatures
    """
    form_template = NamedTemplate("alchemist.form")
    template = ViewPageTemplateFile("templates/sign-open-document.pt")
    form_fields = formlib.form.Fields()

    @property
    def unproxied(self):
        return removeSecurityProxy(self.context)

    @property
    def action_message(self):
        if self._can_sign_document(None):
            return _("Please confirm that you wish to sign"
                " this document")
        elif self._can_review_signature(None):
            return _(u"You have already signed this document")
        else:
            return _(u"You may not sign this document")
    
    def _can_sign_document(self, action):
        return self.unproxied.signatory_feature.can_sign(self.context)
    
    def _can_review_signature(self, action):
        return self.unproxied.signatory_feature.is_signatory(self.context)
    
    def redirect_to_review(self):
        self.request.response.redirect("./signatory-review")

    def nextURL(self):
        return url.absoluteURL(self.context, self.request)
  
    @formlib.form.action(_(u"Sign Document"), name="sign_document", 
        condition=_can_sign_document)
    def handle_sign_document(self, action, data):
        self.unproxied.signatory_feature.sign_document(self.context)
        self.request.response.redirect(self.nextURL())

    @formlib.form.action(_(u"Review Signature"), name="review_signature", 
        condition=_can_review_signature)
    def handle_review_signature(self, action, data):    
        self.redirect_to_review()
        
    @formlib.form.action(_(u"Cancel"), name="cancel", 
        validator=ui.null_validator)    
    def handle_cancel(self, action, data):
        self.request.response.redirect(self.nextURL())
    
    def __call__(self):
        if self._can_review_signature(None):
            self.redirect_to_review()
        return super(SignOpenDocumentForm, self).__call__()
            
