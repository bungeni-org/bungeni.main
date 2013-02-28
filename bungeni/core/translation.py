#!/usr/bin/env python
# -*- coding: utf-8 -*-

# bungeni - http://www.bungeni.org/
# Parliamentary and Legislative Information System
# Copyright (C) 2010 UN/DESA - http://www.un.org/esa/desa/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Utilities to translate content

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.translation")

from copy import copy

from zope import component
from zope.security.proxy import removeSecurityProxy
from zope.security.interfaces import NoInteraction
from zope.app.schema.vocabulary import IVocabularyFactory
from zope.interface import implements
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary
from zope.publisher.interfaces.http import IHTTPRequest
from zope.i18n import translate
from zope.publisher.browser import BrowserLanguages
from zope.i18n.locales import locales

from sqlalchemy import orm, sql

# !+CAPI(mr, feb-2011) the python used to execute this should have previously 
# set up os.environ["zope_i18n_allowed_languages",
# the value of which is parliament-specific and set in:
#   bungeni_custom.zope_i18n_allowed_languages
# Similar for: bungeni_custom.zope_i18n_compile_mo_files
# See zope.i18n.config for how these values are consumed.
# 
#from zope.i18n.config import ALLOWED_LANGUAGES
from bungeni.capi import capi
ALLOWED_LANGUAGES = capi.zope_i18n_allowed_languages

from bungeni.alchemist import Session
from bungeni.models.interfaces import IVersion, ITranslatable
from bungeni.models import domain
from bungeni.ui.utils import common # !+CORE_UI_DEPENDENCY(mr, dec-2011)
from bungeni.utils import naming


class BrowserFormLanguages(BrowserLanguages):

    def getPreferredLanguages(self):
        langs = super(BrowserFormLanguages, self).getPreferredLanguages()
        # use same cookie as linguaplone 
        form_lang = self.request.getCookies().get("I18N_LANGUAGE")
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
            request = common.get_request()
        except NoInteraction:
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

def get_request_language(request=None, default=capi.default_language):
    """Get current request's language; if no request use specified default.
    
    If the request instance is handy, it may be passed in as a parameter thus
    avoidng the need to call for it.
    """
    if request is None:
        request = common.get_request()
    if IHTTPRequest.providedBy(request):
        return request.locale.getLocaleID()
    return default


def get_translation_for(context, lang):
    """Get the translation for context in language lang
    NOTE: context may NOT be None
    """
    assert ITranslatable.providedBy(context), "%s %s" % (lang, context)
    trusted = removeSecurityProxy(context)
    type_key = naming.polymorphic_identity(trusted.__class__)
    mapper = orm.object_mapper(trusted)
    pk = getattr(trusted, mapper.primary_key[0].name)
    session = Session()
    query = session.query(domain.ObjectTranslation).filter(
        sql.and_(
            domain.ObjectTranslation.object_type == type_key,
            domain.ObjectTranslation.object_id == pk,
            domain.ObjectTranslation.lang == lang
        )
    )
    return query.all()

def translate_obj(context, lang=None):
    """Translate an ITranslatable content object (context, that may NOT be None)
    into the specified language or that defined in the request
    -> copy of the object translated into language of the request
    """
    trusted = removeSecurityProxy(context)
    if lang is None:
        try:
            lang = get_request_language()
        except NoInteraction:
            log.warn("Returning original object %s. No request was found and"
                " no target language was provided to get translation.",
                trusted
            )
            return trusted
    translation = get_translation_for(trusted, lang)
    obj = copy(trusted)
    for field_translation in translation:
        setattr(obj, field_translation.field_name, 
            field_translation.field_text)
    return obj

'''
def translate_attr(obj, pk, attr_name, lang=None):
    """Translate a single object attribute, an optimization on translate_obj().
        
        !+TRANSLATE_ATTR(mr, sep-2010) as it turnes out (at least for a simple
        object e.g. ministry) this is slower than using translate_obj(obj).
    """
    if lang is None:
        lang = get_request_language()
    session = Session()
    query = session.query(domain.ObjectTranslation).filter(
        sql.and_(
            domain.ObjectTranslation.object_type == obj.__class__.__name__,
            domain.ObjectTranslation.object_id == pk,
            domain.ObjectTranslation.field_name == attr_name,
            domain.ObjectTranslation.lang == lang
        )
    )
    from sqlalchemy.orm.exc import NoResultFound
    try:
        return query.one().field_text
    except (NoResultFound,):
        return getattr(obj, attr_name)
'''

def get_available_translations(context):
    """ returns a dictionary of all
    available translations (key) and the object_id
    of the object (value)
    """
    trusted = removeSecurityProxy(context)
    type_key = naming.polymorphic_identity(trusted.__class__)
    try:
        mapper = orm.object_mapper(trusted)
        pk = getattr(trusted, mapper.primary_key[0].name)
        session = Session()
        query = session.query(domain.ObjectTranslation).filter(
                sql.and_(
                    domain.ObjectTranslation.object_id == pk,
                    domain.ObjectTranslation.object_type == type_key)
            ).distinct().values("lang", "object_id")
        return dict(query)
    except:
        return {}

def is_translation(context):
    return IVersion.providedBy(context) and \
           context.status in (u"draft_translation",)

def translate_i18n(message_id, language=None, domain="bungeni"):
    """Get message_id translation from catalogs.
    """
    #!+I18N(murithi, july-2011) should not be used if message ids exist in 
    # translation catalogs and a locale-aware context exists.
    try:
        to_language = language or get_request_language()
    except NoInteraction:
        to_language = capi.default_language
    return translate(message_id, target_language=to_language, domain=domain)

