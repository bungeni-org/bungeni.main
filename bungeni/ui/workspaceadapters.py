
from zope import interface
from zope.security.proxy import removeSecurityProxy
from zope.i18n.locales import locales
from zope.dublincore.interfaces import IDCDescriptiveProperties

from bungeni.ui.interfaces import IWorkspaceContentAdapter
from bungeni.ui.utils import date
from bungeni.utils.common import get_request

from bungeni.core.workflow.states import get_object_state
from bungeni.core import translation
from bungeni.core.language import get_default_language

from bungeni.alchemist import utils
from bungeni.models.interfaces import ITranslatable

from bungeni.capi import capi
from bungeni import _, translate


class WorkspaceContentAdapter(object):
    interface.implements(IWorkspaceContentAdapter)

    def __init__(self, context):
        self.context = removeSecurityProxy(context)

    @property
    def title(self):
        return IDCDescriptiveProperties(self.context).title

    @property
    def type(self):
        descriptor = utils.get_descriptor(self.context.__class__)
        item_type = descriptor.display_name if descriptor \
            else self.context.type
        request = get_request()
        return translate(item_type, context=request)

    @property
    def status(self):
        status_title = get_object_state(self.context).title
        request = get_request()
        return translate(_(status_title), context=request)

    @property
    def status_date(self):
        value = self.context.status_date
        request = get_request()
        date_formatter = date.getLocaleFormatter(request, "dateTime", "medium")
        return date_formatter.format(value)

    @property
    def document_group(self):
        if hasattr(self.context, 'group_id') and self.context.group is not None:
            return IDCDescriptiveProperties(self.context.group).short_title
        elif hasattr(self.context, 'chamber_id'):
            return IDCDescriptiveProperties(self.context.chamber).short_tile

    @property
    def translation_status(self):
        if ITranslatable.providedBy(self.context) and len(capi.pivot_languages):
            untranslated = list(capi.pivot_languages)
            if self.context.language in untranslated:
                untranslated.remove(self.context.language)
            for pivot_lang in untranslated:
                if translation.get_field_translations(self.context, pivot_lang):
                    untranslated.remove(pivot_lang)
            if len(untranslated):
                i18n_langs = []
                locale = locales.getLocale(get_default_language().split("-")[0], None)
                for lang in untranslated:
                    if (locale and locale.displayNames and 
                        locale.displayNames.languages):
                        i18n_langs.append(
                            locale.displayNames.languages.get(lang, lang))
                        continue
                    i18n_langs.append(lang)
                return ", ".join(i18n_langs)
            return translate(_("translated"), context=get_request())
        return translate("n/a", context=get_request())
