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

from zope.security.proxy import removeSecurityProxy
from zope.security.interfaces import NoInteraction
from zope.i18n import translate

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

from bungeni.alchemist import Session
from bungeni.models.interfaces import IVersion, ITranslatable
from bungeni.models import domain
from bungeni.utils import naming
from bungeni.core.language import get_default_language


def get_field_translations(context, lang):
    """Get the FieldTranslation items for context fields in language lang
    NOTE: context may NOT be None
    """
    assert ITranslatable.providedBy(context), "%s %s" % (lang, context)
    trusted = removeSecurityProxy(context)
    type_key = naming.polymorphic_identity(trusted.__class__)
    mapper = orm.object_mapper(trusted)
    pk = getattr(trusted, mapper.primary_key[0].name)
    session = Session()
    query = session.query(domain.FieldTranslation).filter(
        sql.and_(
            domain.FieldTranslation.object_type == type_key,
            domain.FieldTranslation.object_id == pk,
            domain.FieldTranslation.lang == lang
        )
    )
    return query.all()


def translated(context, lang=None):
    """Translate an ITranslatable content object (context, that may NOT be None)
    into the specified language or that defined in the request
    -> copy of the object translated into language of the request
    """
    if lang is None:
        lang = get_default_language()
    # only translate if needed i.e. if target language is other than context's original
    if context.language == lang:
        return context
    # ok, translate...
    # !+TRANSLATED mark translated obj with the translation lang?
    # plus, is it ok to translate object then get an attr that triggers 
    # dynamic SA/db requests?
    obj = copy(removeSecurityProxy(context))
    field_translations = get_field_translations(context, lang)
    for field_translation in field_translations:
        setattr(obj, field_translation.field_name, field_translation.field_text)
    return obj


'''
def translate_attr(obj, pk, attr_name, lang=None):
    """Translate a single object attribute, an optimization on translated().
        
        !+TRANSLATE_ATTR(mr, sep-2010) as it turnes out (at least for a simple
        object e.g. ministry) this is slower than using translated(obj).
    """
    if lang is None:
        lang = get_request_language()
    session = Session()
    query = session.query(domain.FieldTranslation).filter(
        sql.and_(
            domain.FieldTranslation.object_type == obj.__class__.__name__,
            domain.FieldTranslation.object_id == pk,
            domain.FieldTranslation.field_name == attr_name,
            domain.FieldTranslation.lang == lang
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
        query = session.query(domain.FieldTranslation).filter(
                sql.and_(
                    domain.FieldTranslation.object_id == pk,
                    domain.FieldTranslation.object_type == type_key)
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
        to_language = language or get_default_language()
    except NoInteraction:
        to_language = capi.default_language
    return translate(message_id, target_language=to_language, domain=domain)

