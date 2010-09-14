import logging
#import transaction
from copy import copy
from zope.publisher.interfaces import BadRequest
from zope import component
from zope import interface
from zope import schema
from zope import formlib

from zope.i18n import translate
from zope.security.proxy import removeSecurityProxy
from zope.event import notify
from zope.schema.interfaces import IChoice

from zope.location.interfaces import ILocation
from zope.dublincore.interfaces import IDCDescriptiveProperties
#from zope.formlib.namedtemplate import NamedTemplate
from zope.container.contained import ObjectRemovedEvent
#from zope.app.pagetemplate import ViewPageTemplateFile
import sqlalchemy as rdb
from ore.alchemist import Session
from alchemist.catalyst import ui
from alchemist.ui.core import null_validator
from ore.alchemist.model import queryModelDescriptor
#from bungeni.ui.container import stringKey
#from ore.workflow.interfaces import IWorkflowInfo
#from alchemist.ui.core import handle_edit_action
from alchemist.ui.core import setUpFields
from alchemist.ui.core import unique_columns
from zope.app.form.interfaces import IDisplayWidget

# !+sqlalchemy.exc(mr, jul-2010) why this try/except ?
try:
    from sqlalchemy.exceptions import IntegrityError
except ImportError:
    from sqlalchemy.exc import IntegrityError

from bungeni.core.translation import get_language_by_name
from bungeni.core.translation import get_default_language
from bungeni.core.translation import is_translation
from bungeni.core.translation import get_translation_for
from bungeni.core.translation import CurrentLanguageVocabulary
#from bungeni.core.interfaces import IVersioned
from bungeni.models.interfaces import IVersion, IBungeniContent
from bungeni.models import domain
from bungeni.ui.forms.fields import filterFields
from bungeni.ui.interfaces import IFormEditLayer
from bungeni.ui.i18n import _
from bungeni.ui import browser
from bungeni.ui import z3evoque
from bungeni.ui.utils import url, debug
from bungeni.ui.container import invalidate_caches_for

import re
import htmlentitydefs
TRUE_VALS = "true", "1"


def set_widget_errors(widgets, errors):
    for widget in widgets:
        name = widget.context.getName()
        for error in errors:
            if isinstance(error, interface.Invalid) and name in error.args[1:]:
                if widget._error is None:
                    widget._error = error


def unescape(text):
    """Removes HTML or XML character references 
        entities from a text string.
        keep &amp;, &gt;, &lt; in the source code.
        from Fredrik Lundh
        http://effbot.org/zone/re-sub.htm#unescape-html"""
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)


class NoPrefix(unicode):
    """The ``formlib`` library insists on concatenating the form
    prefix with field names; we override the ``__add__`` method to
    prevent this.
    """
    
    def __add__(self, name):
        return name

NO_PREFIX = NoPrefix()


class DefaultAction(formlib.form.Action):
    def __init__(self, action):
        self.__dict__.update(action.__dict__)
    
    def submitted(self):
        return True


class BaseForm(formlib.form.FormBase):
    """Base form class for Bungeni content.

    Headless submission

        Adds support for "headless" submission, relying only on the
        schema field ids. The headless mode is enabled by giving a
        true value for the request parameter ``headless``.  In this
        mode, no form prefix is applied and the default action is
        always executed.

    Custom validation

        The ``CustomValidation`` attribute is queried for extra validation
        steps to be performed.

    Redirection

        If ``next_url`` is provided, a redirect is issued upon
        successful form submission.
    """

    Adapts = None
    CustomValidation = None
    
    legends = {} # { iface:_(str) } i.e. 
    # keys are of type Interface, values are localized strings
    
    status = None
    
    def __init__(self, *args):
        super(BaseForm, self).__init__(*args)

        if str(self.request.get("headless", "")).lower() in TRUE_VALS:
            self.setPrefix(NO_PREFIX)

            # in headless mode, the first action defined is submitted
            # by default
            for action in self.actions:
                default = DefaultAction(action)
                self.actions = formlib.form.Actions(default)
                break

        # the ``_next_url`` attribute is used internally by our
        # superclass to implement formlib's ``nextURL`` method
        next_url = self._next_url = self.request.get("next_url", None)
        if next_url == "...":
            self._next_url = self.request.get("HTTP_REFERER", "")
    
    def __call__(self):
        #session = Session()
        # XXX control the display order of the submit buttons 
        # the order seems to be determined by the self.actions.actions 
        # tuple of zope.formlib.form.Action instances
        print "XXX Order of Form Submit Buttons:", [ (a.name, a.label)
                                                for a in self.actions.actions ]
        call = super(BaseForm, self).__call__()
        #session.close()
        return call
    
    @property
    def widget_groups(self):
        groups = {}
        for widget in self.widgets:
            iface = widget.context.interface
            legend = self.legends.get(iface)
            if legend is None:
                iface = interface.Interface
            group = groups.setdefault(iface, [])
            group.append(widget)
        return groups
    
    def update(self):
        self.status = self.request.get("portal_status_message", self.status)
        self.form_fields = self.filter_fields()
        super(BaseForm, self).update()
        set_widget_errors(self.widgets, self.errors)
    
    def filter_fields(self):
        return self.form_fields
    
    def validate(self, action, data):
        """Validation that require context must be called here,
        invariants may be defined in the descriptor."""
        errors = (
            formlib.form.getWidgetsData(self.widgets, self.prefix, data) +
            formlib.form.checkInvariants(self.form_fields, data))
        if not errors and self.CustomValidation is not None:
            return list(self.CustomValidation(self.context, data))
        return errors
    
    @property
    def next_url(self):
        return self._next_url
    
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
        Called from the form template.
        """
        return filter(None,
                [ error.message for error in self.invariantErrors ])


# !+PageForm(mr, jul-2010) converge usage of formlib.form.PageForm to PageForm
# !+NamedTemplate(mr, jul-2010) converge all views to not use anymore
# !+alchemist.form(mr, jul-2010) converge all form views to not use anymore
class PageForm(BaseForm, formlib.form.PageForm, browser.BungeniBrowserView):
    #template = NamedTemplate("alchemist.form")
    template = z3evoque.PageViewTemplateFile("form.html#page")


class DisplayForm(ui.DisplayForm, browser.BungeniBrowserView):
    
    # evoque
    template = z3evoque.PageViewTemplateFile("content.html#view")
    
    # zpt
    #template = ViewPageTemplateFile("templates/content-view.pt")
    
    form_name = _("View")
    
    def __call__(self):
        return self.template()


class AddForm(BaseForm, ui.AddForm):
    """Custom add-form for Bungeni content.

    Additional actions are set up to allow users to continue editing
    an object, or add another of the same kind.
    """

    interface.implements(ILocation, IDCDescriptiveProperties)
    description = None
    
    def getDomainModel(self):
        return getattr(self.context, "domain_model", self.context.__class__)
    
    def validate(self, action, data):
        errors = super(AddForm, self).validate(action, data)
        errors += self.validateUnique(action, data)
        descriptor = queryModelDescriptor(self.domain_model)
        for validator in getattr(descriptor, "custom_validators", ()):
            errors += validator(action, data, None, self.context)
        return errors
    
    def validateUnique(self, action, data):
        """Validate unique.
        
        Since this class always adds a single object, we can safely
        return an empty list of errors.
        
        """
        errors = []
        domain_model = removeSecurityProxy(self.getDomainModel())
        
        # find unique columns in data model.. TODO do this statically
        mapper = rdb.orm.class_mapper(domain_model)
        ucols = list(unique_columns(mapper))

        # query out any existing values with the same unique values,
        session = Session()
        # find data matching unique columns
        for key, col in ucols:
            if key in data:
                # on edit ignore new value if its the same as the previous value
                if isinstance(self.context, domain_model) \
                   and data[key] == getattr(self.context, key, None):
                   continue
                value = session.query(domain_model
                    ).filter(col == data[key]).count()
                if not value:
                    continue
                widget = self.widgets[ key ]
                error = formlib.form.WidgetInputError(
                    widget.name, widget.label, 
                    _(u"Duplicate Value for Unique Field"))
                widget._error = error
                errors.append(error)
        return errors
    
    def filter_fields(self):
        return filterFields(self.context, self.form_fields)

    def update(self):
        super(AddForm, self).update()
        # set default values for required choice fields
        for widget in self.widgets:
            field = widget.context
            if (IChoice.providedBy(field) and field.required and
                field.default is None
                ):
                for term in field.vocabulary:
                    field.default = term.value

    @property
    def domain_model(self):
        return removeSecurityProxy(self.context).domain_model

    @property
    def context_class(self):
        return self.domain_model
    
    @property
    def type_name(self):
        descriptor = queryModelDescriptor(self.domain_model)
        if descriptor:
            name = getattr(descriptor, "display_name", None)
        if not name:
            name = getattr(self.domain_model, "__name__", None)
        return name
    
    @property
    def form_name(self):
        return _(u"add_item_legend", default=u"Add $name", mapping={
            "name": translate(self.type_name.lower(), context=self.request)})
    
    @property
    def title(self):
        return _(u"add_item_title", default=u"Adding $name", mapping={
            "name": translate(self.type_name.lower(), context=self.request)})

    def finishConstruction(self, ob):
        """Adapt the custom fields to the object."""
        adapts = self.Adapts
        if adapts is None:
            adapts = self.model_schema
        self.adapters = {
            adapts : ob
        }
    
    def createAndAdd(self, data):
        added_obj = super(AddForm, self).createAndAdd(data)
        # invalidate caches for this domain object type
        invalidate_caches_for(added_obj.__class__.__name__, "add")
        # !+ADD_invalidate_CACHE(mr, sep-2010) should not be necessary as 
        # all domain items are created into a "draft" workflow state that 
        # is NOT public, so in theory any existing cache of listings of public 
        # items are NOT affected. Plus, the required subsequent modification 
        # of the item (to transit the item into a public state) will anyway
        # invalidate the cache.
        return added_obj
    
    @formlib.form.action(
        _(u"Save and view"), 
        condition=formlib.form.haveInputWidgets)
    def handle_add_save(self, action, data):
        for key in data.keys():
            print "[handle_add_save] KEY:%s VALUE:%s" % (key, data[key])
            if isinstance(data[key], str): 
                data[key] = unescape(data[key])
        ob = self.createAndAdd(data)
        name = self.context.domain_model.__name__
        if not self._next_url:
            self._next_url = url.absoluteURL(ob, self.request) + \
                "?portal_status_message=%s added" % name
        
    @formlib.form.action(_(u"Cancel"), validator=null_validator)
    def handle_cancel(self, action, data):
        """Cancelling redirects to the listing."""
        session = Session()
        if not self._next_url:
            self._next_url = url.absoluteURL(self.__parent__, self.request)
        self.request.response.redirect(self._next_url)
        session.close()
        
    @formlib.form.action(_(u"Save"), condition=formlib.form.haveInputWidgets)
    def handle_add_edit(self, action, data):
        for key in data.keys():
            if isinstance(data[key], str): 
                data[key] = unescape(data[key])
        ob = self.createAndAdd(data)
        name = self.context.domain_model.__name__
        if not self._next_url:
            self._next_url = url.absoluteURL(ob, self.request) + \
                             "/edit?portal_status_message=%s Added" % name

    @formlib.form.action(
        _(u"Save and add another"), condition=formlib.form.haveInputWidgets)
    def handle_add_and_another(self, action, data):
        for key in data.keys():
            if isinstance(data[key], str): 
                data[key] = unescape(data[key])
        self.createAndAdd(data)
        name = self.context.domain_model.__name__

        if not self._next_url:
            self._next_url = url.absoluteURL(self.context, self.request) + \
                             "/add?portal_status_message=%s Added" % name
                              

class EditForm(BaseForm, ui.EditForm):
    """Custom edit-form for Bungeni content.
    """
    
    def __init__(self, *args):
        super(EditForm, self).__init__(*args)
        # For bungeni content, mark the request that we are in edit mode e.g. 
        # useful for when editing a question's response, but not wanting to 
        # offer option to submit the response while in response edit mode. 
        if IBungeniContent.providedBy(self.context): # and self.mode=="edit"
            interface.alsoProvides(self.request, IFormEditLayer)
    
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

        props = IDCDescriptiveProperties.providedBy(context) \
                and context or IDCDescriptiveProperties(context)

        if self.is_translation:
            language = get_language_by_name(self.context.language)["name"]
            return _(u"edit_translation_legend",
                     default=u'Editing $language translation of "$title"',
                     mapping={"title": translate(props.title, context=self.request),
                              "language": language})
        
        elif IVersion.providedBy(self.context):
            return _(u"edit_version_legend",
                     default=u'Editing "$title" (version $version)',
                     mapping={"title": translate(props.title, context=self.request),
                              "version": self.context.version_id})

        return _(u"edit_item_legend", default=u'Editing "$title"',
                 mapping={"title": translate(props.title, context=self.request)})

    @property
    def form_description(self):
        if self.is_translation:
            language = get_language_by_name(self.context.head.language)["name"]
            return _(u"edit_translation_help",
                     default=u"The original $language version is shown on the left",
                     mapping={"language": language})
            
    def validate(self, action, data):
        errors = super(EditForm, self).validate(action, data)

        descriptor = queryModelDescriptor(self.context.__class__)
        for validator in getattr(descriptor, "custom_validators", ()):
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
            head = self.context.head
            form_fields = setUpFields(self.context.__class__, "view")
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
        for key in data.keys():
            if isinstance(data[key], str):
                data[key] = unescape(data[key])
        formlib.form.applyChanges(self.context, self.form_fields, data)
        # invalidate caches for this domain object type
        invalidate_caches_for(self.context.__class__.__name__, "edit")
    
    @formlib.form.action(_(u"Save"), condition=formlib.form.haveInputWidgets)
    def handle_edit_save(self, action, data):
        """Saves the document and goes back to edit page"""
        self._do_save(data)
    
    @formlib.form.action(
        _(u"Save and view"), condition=formlib.form.haveInputWidgets)
    def handle_edit_save_and_view(self, action, data):
        """Saves the  document and redirects to its view page"""
        self._do_save(data)
        if not self._next_url:
            self._next_url = url.absoluteURL(self.context, self.request) + \
                "?portal_status_message= Saved"
        self.request.response.redirect(self._next_url)
    
    @formlib.form.action(_(u"Cancel"), validator=null_validator)
    def handle_edit_cancel(self, action, data):
        """Cancelling redirects to the listing."""
        for key in data.keys():
            if isinstance(data[key], str): 
                data[key] = unescape(data[key])
        session = Session()
        if not self._next_url:
            self._next_url = url.absoluteURL(self.context, self.request) 
        self.request.response.redirect(self._next_url)
        session.close()


class TranslateForm(AddForm):
    """Custom translate-form for Bungeni content.
    """
    is_translation = False

    @property
    def side_by_side(self):
        return True
    
    def __init__(self, *args):
        super(TranslateForm, self).__init__(*args)
        self.language = self.request.get("language", get_default_language())
        
    def translatable_field_names(self):
        trusted = removeSecurityProxy(self.context)
        table = rdb.orm.object_mapper(trusted).mapped_table
        names = ["language",]
        for column in table.columns:
            if type(column.type) in [rdb.Unicode, rdb.UnicodeText]:
                names.append(column.name)
        return names

    def set_untranslatable_fields_for_display(self):
        md = queryModelDescriptor(self.context.__class__)
        for field in self.form_fields:
            if field.__name__ not in self.translatable_field_names():
                field.for_display = True
                field.custom_widget = md.get(field.__name__).view_widget
                
    def validate(self, action, data):
        return (
            formlib.form.getWidgetsData(self.widgets, self.prefix, data) 
            )
        
    @property
    def form_name(self):
        language = get_language_by_name(self.language)["name"]
        return _(u"translate_item_legend",
                 default=u"Add $language translation",
                 mapping={"language": language})

    @property
    def form_description(self):
        language = get_language_by_name(self.language)["name"]
        props = IDCDescriptiveProperties.providedBy(self.context) \
                and self.context or IDCDescriptiveProperties(self.context)
        if self.is_translation:
            return _(u"edit_translation_legend",
             default=u'Editing $language translation of "$title"',
             mapping={"title": translate(props.title, context=self.request),
                      "language": language}) 
        else:
            return _(u"translate_item_help",
                default=u'The document "$title" has not yet been translated ' \
                    u'into $language. Use this form to add the translation',
                mapping={
                    "title": translate(props.title, context=self.request),
                    "language": language
                }
            )
    
    @property
    def title(self):
        language = get_language_by_name(self.language)["name"]
        return _(u"translate_item_title", default=u"Adding $language translation",
                 mapping={"language": language})
    
    @property
    def domain_model(self):
        return type(removeSecurityProxy(self.context))
    
    def setUpWidgets(self, ignore_request=False):
        self.set_untranslatable_fields_for_display()
        
        #get the translation if available
        language = self.request.get("language")
        
        translation = get_translation_for(self.context, language)
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
        head = self.context
        form_fields = setUpFields(self.context.__class__, "view")
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
    
    @formlib.form.action(
        _(u"Save translation"), condition=formlib.form.haveInputWidgets)
    def handle_add_save(self, action, data):
        """After succesful creation of translation, redirect to the
        view."""
        for key in data.keys():
            if isinstance(data[key], str): 
                data[key] = unescape(data[key])
            
        #url = url.absoluteURL(self.context, self.request)
        
        #language = get_language_by_name(data["language"])["name"]

        
        session = Session()
        trusted = removeSecurityProxy(self.context)
        mapper = rdb.orm.object_mapper(trusted)
        pk = getattr(trusted, mapper.primary_key[0].name) 
        
        current_translation = get_translation_for(self.context, data["language"])
        if current_translation:
            for translation in current_translation:
                session.delete(translation)
                
        
        for form_field in data.keys():
            if form_field == "language":
                continue
            translation = domain.ObjectTranslation()
            translation.object_id = pk
            translation.object_type = trusted.__class__.__name__
            translation.field_name = form_field
            translation.lang = data["language"]
            translation.field_text = data[form_field]
            session.add(translation)
        session.flush()
        session.commit()
        session.close()
        
        #versions = IVersioned(self.context)
        #version = versions.create("'%s' translation added" % language)

        # reset workflow state
        #version.status = None
        #IWorkflowInfo(version).fireTransition("create-translation")
        # redefine form context and proceed with edit action
        #self.setUpAdapters(version)
        #handle_edit_action(self, action, data)

        # commit version such that it gets a version id
        #transaction.commit()
        
        #if not self._next_url:
        #    self._next_url = ( \
        #        '%s/versions/%s' % (url, stringKey(version)) + \
        #        '?portal_status_message=Translation added')

        self._finished_add = True
        
class ReorderForm(PageForm):
    """Item reordering form.

    We use an intermediate list of ids to represent the item order.

    Note that this form must be subclassed with the ``save_ordering``
    method overriden.
    """

    class IReorderForm(interface.Interface):
        ordering = schema.List(
            title=u"Ordering",
            value_type=schema.TextLine())

    # evoque
    template = z3evoque.PageViewTemplateFile("form.html#page")
    # zpt
    #template = NamedTemplate("alchemist.form")
    form_name = _(u"Item reordering")
    form_fields = formlib.form.Fields(IReorderForm, render_context=True)

    def setUpWidgets(self, ignore_request=False):
        class context:
            ordering = list(self.context)

        self.adapters = {
            self.IReorderForm: context,
            }

        self.widgets = formlib.form.setUpWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            form=self, adapters=self.adapters, ignore_request=ignore_request)
    
    def save_ordering(self, ordering):
        raise NotImplementedError("Must be defined by subclass")
    
    @formlib.form.action(_(u"Save"))
    def handle_save(self, action, data):
        self.save_ordering(data["ordering"])

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
    # evoque
    template = z3evoque.PageViewTemplateFile("delete.html")
    
    # zpt
    # !+form_template(mr, jul-2010) this is unused here, but needed by
    # some adapter of this "object delete" view
    #form_template = NamedTemplate("alchemist.form")
    #template = ViewPageTemplateFile("templates/delete.pt")
    
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
    
    @formlib.form.action(_(u"Delete"), condition=_can_delete_item)
    def handle_delete(self, action, data):
        count = self.delete_subobjects()
        container = self.context.__parent__
        trusted = removeSecurityProxy(self.context)
        session = Session()
        session.delete(trusted)
        count += 1

        try:
            session.commit()
        except IntegrityError, e:
            # this should not happen in production; it's a critical
            # error, because the transaction might have failed in the
            # second phase of the commit
            session.rollback()
            logging.critical(e)

            self.status = _(u"Could not delete item due to "
                            "database integrity error")

            return self.render()
        session.close()
        # invalidate caches for this domain object type
        invalidate_caches_for(self.context.__class__.__name__, "delete")
        
        #TODO: check that it is removed from the index!
        notify(ObjectRemovedEvent(
            self.context, oldParent=container, oldName=self.context.__name__))
        # we have to switch our context here otherwise the deleted object will
        # be merged into the session again and reappear magically
        self.context = container
        next_url = self.nextURL()
        
        if next_url is None:
            next_url = url.absoluteURL(container, self.request) + \
                       "/?portal_status_message=%d items deleted" % count

        self.request.response.redirect(next_url)

