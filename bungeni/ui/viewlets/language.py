# encoding: utf-8

from zope import component
from zope.app.component.hooks import getSite
from zope.location.interfaces import ILocation
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.security import proxy
from zope.viewlet import viewlet
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.app.publisher.interfaces.browser import IBrowserMenu
from zope.app.component.hooks import getSite
from zope.publisher.browser import BrowserView

from ore.alchemist.interfaces import IAlchemistContainer, IAlchemistContent
from ore.alchemist.model import queryModelDescriptor
from ore.wsgiapp.interfaces import IApplication
from alchemist.traversal.managed import ManagedContainerDescriptor

from bungeni.core.translation import get_all_languages
from bungeni.core.translation import get_available_translations
from bungeni.core.app import BungeniApp
from bungeni.core import location

import bungeni.ui.utils as ui_utils

import datetime


class LanguageViewlet(object):
    """Language selection viewlet."""
    
    render = ViewPageTemplateFile("templates/language.pt")
    showFlags = False
    available = True
    
    def update(self):
        
        def css_class(language):
            css_attr = None
            if language == selected:
                css_attr = 'selected'
            if language in translations:
                if css_attr:
                    css_attr = css_attr + ' available'
                else:
                    css_attr = 'available'
            return css_attr
        
        def language_name(language): 
            langname = language.get('native', None)
            if langname == None:
                langname = language.get('name')
            return langname
        
        translations = get_available_translations(self.context)
        if hasattr(self.context,'language'):
            translations[self.context.language] = None
        languages = get_all_languages()
        selected = self.request.locale.getLocaleID()
        url = ui_utils.url.absoluteURL(getSite(), self.request)
        
        self.languages = [{
            'code': language,
            'flag': url+languages[language].get('flag', ''),
            'name': language_name(languages[language]),
            'css_class': css_class(language),
            'url': "%s/change-language?language=%s" % (url, language),
            } for language in languages]

class ChangeLanguage(BrowserView):

    def __call__(self):
        """set the I18N_LANGUAGES cookie and redirect back to referrer"""
        response = self.request.response
        lang = self.request.get('language', None)
        if lang:
            response.setCookie('I18N_LANGUAGES', lang, path='/')
        else:
            response.expireCookie('I18N_LANGUAGES', path='/')
        url =  self.request.get('HTTP_REFERER','..')
        return response.redirect(url)

              

