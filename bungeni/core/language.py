# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Language Negotiation Utilities

$Id$
$URL$
"""
log = __import__("logging").getLogger("bungeni.core.language")

from zope import interface
from zope import component
from zope.interface import implements
from zope.app.schema.vocabulary import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary
from zope.publisher.interfaces.http import IHTTPRequest
import zope.security
from zope.app.zapi import getUtilitiesFor
from zope.publisher.browser import BrowserLanguages
from zope.annotation.interfaces import IAnnotations
from zope.i18n.negotiator import Negotiator, normalize_lang
from zope.i18n.locales import locales

from locale import getdefaultlocale

from bungeni.core.interfaces import ILanguageProvider
from bungeni.capi import capi
from bungeni.utils import register
from bungeni.utils.common import get_request
from ploned.ui.interfaces import ITextDirection

ALLOWED_LANGUAGES = capi.zope_i18n_allowed_languages
I18N_COOKIE_NAME = 'I18N_LANGUAGE'


def get_request_language(request=None, default=capi.default_language):
    """Get current request's language; if no request use specified default.
    
    If the request instance is handy, it may be passed in as a parameter thus
    avoidng the need to call for it.
    """
    if request is None:
        request = get_request()
    if IHTTPRequest.providedBy(request):
        return request.locale.getLocaleID()
    return default


class BrowserFormLanguages(BrowserLanguages):
    '''See interface zope.i18n.interfaces.IUserPreferredLanguages'''

    def getPreferredLanguages(self):
        '''get preferred user language - inject cookie language if any'''
        langs = super(BrowserFormLanguages, self).getPreferredLanguages()
        # use same cookie as linguaplone 
        form_lang = self.request.getCookies().get(I18N_COOKIE_NAME)
        if form_lang is not None:
            langs.insert(0, form_lang)
        return langs

class LanguageVocabulary(object):
    """This is a simple vocabulary of available languages.
    The generated terms are composed of the language code and the localized
    name for that language if there is a a request object.
    """
    implements(IVocabularyFactory)

    def __call__(self, context):
        try:
            request = get_request()
        except zope.security.interfaces.NoInteraction:
            request = None
        def get_locale_lang(code):
            if request and hasattr(request, "locale"):
                return request.locale.displayNames.languages.get(code)
            return None
        languages = get_all_languages()
        items = [ 
            (
                lang, 
                (request and get_locale_lang(lang) or languages[lang]["name"])
            )
            for lang in languages.keys()
        ]
        items.sort(key=lambda language: language[1])
        items = [ SimpleTerm(i[0], i[0], i[1]) for i in items ]
        return SimpleVocabulary(items)

language_vocabulary_factory = LanguageVocabulary()
component.provideUtility(language_vocabulary_factory, IVocabularyFactory, "language")

class CurrentLanguageVocabulary(LanguageVocabulary):
    def __call__(self, context):
        language = get_language(context)
        languages = get_all_languages([language])
        items = [ (l, languages[l].get("name", l)) for l in languages ]
        items = [ SimpleTerm(i[0], i[0], i[1]) for i in items ]
        return SimpleVocabulary(items)


def get_language_by_name(name):
    return dict(get_all_languages())[name]

def get_language(translatable):
    return translatable.language

def get_all_languages(language_filter=None):
    """Build a list of all languages.

    To-do: the result of this method should be cached indefinitely.
    """
    #availability = component.getUtility(ILanguageAvailability)
    if language_filter is None:
        language_filter = ALLOWED_LANGUAGES
    # TypeError if filter is not iterable
    def get_lang_data(code):
        lang_data = {}
            #try to extract native name from zope
        lang_parts = code.split("-")
        lang_code = lang_parts[0]
        territory = None
        if len(lang_parts) == 2:
            territory = lang_parts[1].upper()
        lang_locale = locales.getLocale(lang_code, territory)
        if not lang_locale.id.language:
            return
        lang_name = lang_locale.id.language
        if lang_locale.displayNames and lang_locale.displayNames.languages:
            lang_name = lang_locale.displayNames.languages.get(lang_code, 
                "").capitalize()
        lang_data["name"] = lang_name
        locale_territory = lang_locale.displayNames.territories.get(
            territory, ""
        )
        if locale_territory:
            lang_data["native"] = u"%s (%s)" %(lang_name, locale_territory)
        else:
            lang_data["native"] = lang_name
        return lang_data
    return dict([ (name, get_lang_data(name)) for name in language_filter ])


class BaseLanguageProvider(object):
    interface.implements(ILanguageProvider)
    # precedence order (first sorting values first) - subclasses must specify
    PRECEDENCE = None
    
    def __call__(self):
        language = self.getLanguage()
        return normalize_lang(language) if language else None
    
    def getLanguage(self):
        raise NotImplementedError("Inheriting class must implement this")

@register.utility(provides=ILanguageProvider, name="System Language")
class SystemLanguage(BaseLanguageProvider):
    PRECEDENCE = 10
    def getLanguage(self):
        locale = getdefaultlocale()
        try:
            return locale[0]
        except IndexError:
            return None

@register.utility(provides=ILanguageProvider, name="Application Language")
class ApplicationLanguage(BaseLanguageProvider):
    PRECEDENCE = 9
    def getLanguage(self):
        return capi.default_language

@register.utility(provides=ILanguageProvider, name="Browser Language")
class BrowserLanguage(BaseLanguageProvider):
    PRECEDENCE = 8
    def getLanguage(self):
        try:
            request = get_request()
        except zope.security.interfaces.NoInteraction:
            request=None
        if request is not None:
            browser_langs = BrowserLanguages(request)
            langs = browser_langs.getPreferredLanguages()
            try:
                return langs[0]
            except IndexError:
                return None
        else:
            return None

@register.utility(provides=ILanguageProvider, name="UI Language")
class UILanguage(BaseLanguageProvider):
    PRECEDENCE = 7
    def getLanguage(self):
        try:
            request = get_request()
            return get_request_language()
        except zope.security.interfaces.NoInteraction:
            return None

@register.utility(provides=ILanguageProvider, name="User Preferred Language")
class UserLanguage(BaseLanguageProvider):
    PRECEDENCE = 6
    def getLanguage(self):
        try:
            request = get_request()
            if request:
                identity = request.environment.get('repoze.who.identity')
                if identity:
                    return identity.get("home_language")
        except (zope.security.interfaces.NoInteraction, AttributeError):
            return None

@register.utility(provides=ILanguageProvider, name="Cookie Language")
class SelectedLanguage(BaseLanguageProvider):
    PRECEDENCE = 5
    def getLanguage(self):
        try:
            request = get_request()
            if request and IHTTPRequest.providedBy(request):
                return request.getCookies().get(I18N_COOKIE_NAME)
        except zope.security.interfaces.NoInteraction:
            return None

def get_default_language():
    default_language = None
    language_providers = getUtilitiesFor(ILanguageProvider)
    provider_list = [(p[0], p[1]) for p in language_providers]
    sorted_providers = sorted(provider_list, key=lambda p: p[1].PRECEDENCE)
    for name, provider in sorted_providers:
        _language = provider()
        log.debug("Looking for language in %s found %s", name, _language)
        if _language and (_language in capi.zope_i18n_allowed_languages):
            default_language = _language
            log.debug(
                "Got default language as %s from provider %s", _language, name)
            break
    return default_language

DEFAULT_LANGUAGE_KEY = "bungeni.ui.default_language"
class Negotiator(Negotiator):
    def getLanguage(self, langs, env):
        annotations = IAnnotations(env, None)
        if annotations:
            lang = annotations.get(DEFAULT_LANGUAGE_KEY)
            if lang is None:
                annotations[DEFAULT_LANGUAGE_KEY] = get_default_language()
            lang = annotations.get(DEFAULT_LANGUAGE_KEY)
        else:
            lang = get_default_language()
        return lang

i18n_negotiator = Negotiator()

def get_base_direction():
    ui_lang = get_default_language()
    if ui_lang in capi.right_to_left_languages:
        return "rtl"
    else:
        return "ltr"

def is_rtl():
    if get_base_direction() == "rtl":
        return True
    else:
        return False
        
             
@register.utility(provides=ITextDirection)
class TextDirection(object):
    def get_text_direction(self):
        return get_base_direction()

