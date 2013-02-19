# encoding: utf-8

from zope.app.component.hooks import getSite
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.publisher.browser import BrowserView
from zope.i18n.negotiator import normalize_lang

from bungeni.core.translation import get_all_languages
from bungeni.core.translation import get_available_translations
import bungeni.ui.utils as ui_utils

class LanguageViewlet(object):
    """Language selection viewlet."""
    
    render = ViewPageTemplateFile("templates/language.pt")
    showFlags = False
    available = True
    
    def update(self):
        
        def css_class(language):
            css_attr = None
            if language == selected:
                css_attr = "selected"
            if language in translations:
                if css_attr:
                    css_attr = css_attr + " available"
                else:
                    css_attr = "available"
            return css_attr
        
        def language_name(language): 
            return language.get("native", language.get("name"))

        translations = get_available_translations(self.context)
        if hasattr(self.context, "language"):
            translations[self.context.language] = None
        languages = get_all_languages()
        selected = normalize_lang(self.request.locale.getLocaleID())
        url = ui_utils.url.absoluteURL(getSite(), self.request)
        
        self.languages = sorted([
                {
                    "code": language,
                    "flag": url+languages[language].get('flag', ''),
                    "name": language_name(languages[language]),
                    "css_class": css_class(language),
                    "url": "%s/change-language?language=%s" % (
                        url, language
                    ),
                } 
                for language in languages
            ], 
            key=lambda l:l.get("code")
        )

class ChangeLanguage(BrowserView):

    def __call__(self):
        """set the I18N_LANGUAGE cookie and redirect back to referrer"""
        response = self.request.response
        lang = self.request.get("language", None)
        if lang:
            response.setCookie("I18N_LANGUAGE", lang, path="/")
        else:
            response.expireCookie("I18N_LANGUAGE", path="/")
        url =  self.request.get("HTTP_REFERER", "..")
        # 19-02-2013 - added trusted=True parameter, since the redirect back to the source page
        # after changing language fails when hosting behind deliverance, since bungeni is on localhost
        # and is redirecting to the main webhosted url x.bungeni.org, and fails since by default 
        # trusted = False which prevents redirects to non local domains. Setting trusted=True allows
        # the redirect to work correctly
        return response.redirect(url, trusted=True)
