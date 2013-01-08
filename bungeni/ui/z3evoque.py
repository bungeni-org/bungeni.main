# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Zope3 + Evoque Templating: http://evoque.gizmojo.org/

Evoque advantages (over Chameleon/ZPT):
- No server restart needed each time a file-based template is modified (well, I
  am told this should also be the case with ZPT, but in this setup it is not).
- A template may invoke other templates (that may be within same collection or 
  within any other collection in the domain), where selection of which template
  to invoke may also be dynamic (data-driven).
- Template inheritance, offering options to easily:
  - move page presentational composition logic out of core application.
  - define skins, that may be dynamically switched at runtime as per 
    user-preference.
- May be used to generate output in any format, not only X/HTML e.g. JSON, CSS,
  JavaScript, INI, SQL, Python Scripts, etc. 
- No "XML Situps".
- Multiple templates may be defined in a single file, if so wished.
- A direct and immediately obvious, and memorable, syntax.
- Super fast, simple, extremely flexible, small.
- Lightweight:
  - to use Evoque with Zope all you basically need is this module + evoque 
    itself (a 1000 SLOC package); 
  - to use ZPT with Zope it seems that you'd need: zope.tal, zope.tales, 
    zope.pagetemplate, zope.app.pagetemplate, z3c.pt, z3c.template, 
    z3c.ptcompat, chameleon.core, chameleon.zpt, chameleon.html, ... ?!?
- Evoque runs also on Python 3 (as well as on 2.4 and up).

Other Evoque features (also supported by ZPT):
- May be run in restricted mode (to allow untrusted authors to edit templates).
- Automatic XML/HTML escaping of all data values, guaranteeing XSS protection. 
  Evoque goes further (than ZPT) on this feature, as it even guarantees that
  data is escaped once-and-only-once. The ability is less relevant for ZPT 
  however, as ZPT does not support loading and invoking other templates from 
  within a template.
- Evoque, like ZPT, does not allow embedding *python statements* -- meaning 
  there can be no data manipulation except through exposed python code. 
  On the other hand, unlike ZPT, Evoque supports arbitrary *python expressions*, 
  giving plenty of flexibility for stating presentation logic while still 
  retaining good control over the code i.e. is still able to run it within 
  a restricted sandbox.

ZPT non-features:
- CLAIM: "ZPT produces only well-formed XML documents."
  REALITY-CHECK: Chameleon/ZPT may produce well-formed XML snippets, but not 
necessarily valid XML documents e.g. in our case, the DOCTYPE declaration 
specified in the main template is being stripped out from the output somewhere 
in the Chameleon/ZPT stack, thus the document is already invalid as it has no 
DOCTYPE. And, as far as HTML documents are concerned, there is NO help from ZPT 
to help the developer produce valid HTML documents (all sorts of incorrectnesses 
e.g. form elements without action attributes, div elements in the head, etc).
- CLAIM: "A Page Template is like a model of the pages that it will generate. 
In particular, it is a valid HTML page."
  REALITY-CHECK: here's a citation from Paul Everitt (co-founder of Zope 
Corporation) in an article on developing skins for Zope 3: 
    "Unfortunately, the original idea of page templates -- that they would be 
    valid HTML that could be directly edited in an HTML layout tool -- is no 
    longer true. The <metal:block> element that encloses the template breaks 
    this feature."
Well, maybe if you used ZPT without METAL, this claim might still be true. But,
who uses ZPT without METAL?

Current limitations:
A "template" attribute may currently not be specified in a ZCML declaration -- 
for now, the template for a ZCML-declared view should be specified in the class.
But, I actually see this as a *positive*, a best practice... given that the 
class's main purpose is to prepare the data for *this* specific template.

Status:
Exploratory, to first verify that Evoque templates may be used everywhere 
that ZPT templates are used.

Using Evoque templates with a main "site" main page template, BrowserViews, 
Viewlets and ViewletManagers is confirmed to work, as proven by sample 
implementations of each of these using evoque templates. 

The following still need to be 100% verified with real working examples:
- Using evoque templates with: 
  - Forms/Widgets (formlib, do these use ZPT templates?)
  - any other Zope construct that uses a "template".
- i18n catalog extraction: this may simply mean adopting a supported alias for 
  the gettext() function -- the implementation below uses "i18n" as alias, 
  i.e. i18n(messageid) to get the translation for messageid, however the most 
  common is to use an "_" i.e. _(messageid).

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.z3evoque")

import sys
import os
import zope
from evoque.domain import Domain

#
# Configuration
#

# this is the core "high-level config" for evoque
# !+ should be externalized to the application's config.ini file
evoque_ini = {
    "evoque.default_dir": "templates",
    "evoque.default_template": None,
    "evoque.restricted": False,
    "evoque.errors": 3,
    "evoque.cache_size": 0,
    "evoque.auto_reload": 2,
    "evoque.slurpy_directives": True,
    "evoque.quoting": "xml",
    "evoque.input_encoding": "utf-8",
    # i18n defaults
    "evoque.i18n_domain": "bungeni",
    "evoque.i18n_lang": "en",
}

def abs_norm_path(path):
    """Utility to ensure that a path is a normalized absolute path with respect 
    to the ABS_PATH as specified by the application. 
    
    Note: setup_evoque() must have been already called.
    """
    if os.path.isabs(os.path.normpath(path)):
        return os.path.normpath(path)
    else:
        return os.path.normpath(os.path.join(ABS_BASE, path))

'''
def set_additional_collections():
    """Define and set additional collections (other than default collection) 
    onto the evoque domain. 
    
    Convention for collection names: dotted parent package name.
    All other non-specified container parameters (i.e. cache_size, auto_reload, 
    slurpy_directives, quoting, input_encoding, filters) are defaulted to 
    what is set on the domain.
    
    The collection's path must be specified relative to ABS_BASE
    """
    #domain.set_collection("bungeni.ui", abs_norm_path("")) # default collection
    domain.set_collection("bungeni.ui.viewlets", 
            abs_norm_path("viewlets/templates"))
    #"bungeni.ui.forms":"forms/templates",
    #"ploned.ui":"../../../ploned.ui/ploned/ui/templates",
    #"alchemist.ui":"../../../alchemist.ui/alchemist/ui/templates"
'''

# i18n domains

# global get_gettext callable
get_gettext = None

def set_get_gettext():
    """Set this callable as the z3evoque.get_gettext global function to return 
    a gettext bound onto an i18n domain and a language. 
    
    This function is to be defined and called by the application - 
    get_gettext itself should have the parameters (i18n_domain, language).
    """
    from bungeni.capi import capi
    _i18n_domain_localedirs = {
        "bungeni": capi.get_path_for("translations", "bungeni"),
    }
    _untranslated = []
    def _get_gettext(i18n_domain, language):
        """Get a _() i18n gettext function bound to domain and language.
        !+ There is probably a better way to do this; the following "obvious"
           way does not work:
                zope.i18nmessageid.MessageFactory(i18n_domain)
        """
        import gettext
        try:
            t = gettext.translation(i18n_domain,
                    localedir=_i18n_domain_localedirs[i18n_domain],
                    languages=[language])
        except (IOError,):
            cls, exc, tb = sys.exc_info()
            if language != "en":
                log.error(""" [%s] %s [lang=%s] -> trying with [lang=%s]""" % (
                    cls.__name__, exc, language, "en"))
                return _get_gettext(i18n_domain, "en")
            else:
                log.error(""" [%s] %s [lang=%s]""" % (
                    cls.__name__, exc, language))
                raise exc
        # wrap t.gettext to intercept and log possibly untranslated msgids
        def _gt(msgid):
            try: 
                msgstr = t.gettext(msgid)
                return msgstr
            finally:
                if msgid == msgstr and msgid not in _untranslated:
                    _untranslated.append(msgid)
                    log.warn('i18n NOT LOCALIZED [%s, %s] "%s"' % (
                        i18n_domain, language, msgid))
        return _gt
    global get_gettext
    get_gettext = _get_gettext


#
# Setup of the Evoque Domain
#
# !+ z3evoque.setup_evoque

# Global evoque domain singleton utility
# Summary of usage:
#   from bungeni.ui.z3evoque import domain
#   print domain.get_template( ... ).evoque( ... )
# See: http://evoque.gizmojo.org/usage/api/
#
domain = None

def zca_register_domain(evoque_domain):
    """ZCA register the domain as a utility (not really necessary).
    """
    # tag with IEvoqueDomain
    zope.interface.alsoProvides(evoque_domain, IEvoqueDomain)
    # register as utility
    zope.component.getGlobalSiteManager(
            ).registerUtility(evoque_domain, IEvoqueDomain)
    # retrieve the utility set on IEvoqueDomain
    return zope.component.getUtility(IEvoqueDomain)

class IEvoqueDomain(zope.interface.Interface):
    """Marker for an Evoque Domain instance."""

# The ABSOLUTE path as reference base location against which to resolve all 
# RELATIVE collection paths. Initialized in setup_evoque().
ABS_BASE = None

def setup_evoque(abs_base=None):
    if abs_base is None:
        # then we just use the grand-parent folder for this package
        abs_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert os.path.isabs(abs_base) # ensure that base path is absolute
    global ABS_BASE
    ABS_BASE = abs_base
    
    import logging
    evoque_domain = Domain(
        # root folder for the default template collection, must be abspath;
        abs_norm_path(evoque_ini.get("evoque.default_dir", "")),
        
        # whether evaluation namespace is restricted or not 
        restricted = evoque_ini.get("evoque.restricted", False),
        
        # how should any evaluation errors be rendered
        # int 0 to 4, for: [silent, zero, name, render, raise]
        errors = int(evoque_ini.get("evoque.errors", 3)),
        
        # evoque logger; additional settings should be specified via the app's 
        # config ini file, just as for any other logger in the application e.g:
        # [logger_evoque]
        # level = DEBUG
        # handlers =
        # qualname = evoque
        log = logging.getLogger("evoque"),
        
        # [collections] int, max loaded templates in a collection
        cache_size = int(evoque_ini.get("evoque.cache_size", 0)), 
        
        # [collections] int, min seconds to wait between checks for
        # whether a template needs reloading
        auto_reload = int(evoque_ini.get("evoque.auto_reload", 60)), 
        
        # [collections] bool, consume all whitespace trailing a directive
        slurpy_directives = evoque_ini.get("evoque.slurpy_directives", True),
        
        # [collections/templates] str or class, to specify the *escaped* 
        # string class that should be used i.e. if any str input is not of 
        # this type, then cast it to this type). 
        # Builtin str key values are: "xml" -> qpy.xml, "str" -> unicode
        quoting = evoque_ini.get("evoque.quoting", "xml"),
        
        # [collections/templates] str, preferred encoding to be tried 
        # first when decoding template source. Evoque decodes template
        # strings heuristically, i.e. guesses the input encoding.
        input_encoding = evoque_ini.get("evoque.input_encoding", "utf-8"),
        
        # [collections/templates] list of filter functions, each having 
        # the following signature: filter_func(s:basestring) -> basestring
        # The functions will be called, in a left-to-right order, after 
        # template is rendered. NOTE: not settable from the conf ini.
        filters=[]
    )
    
    # ZCA register the evoque domain as a utility (not really necessary)
    # set it onto global domain attribute
    global domain
    domain = zca_register_domain(evoque_domain)
    
    # from here on, use newly set global domain
    
    # default template (optional) i.e. 
    # what to receive when calling domain.get_template() with no params
    if evoque_ini.get("evoque.default_template"):
        domain.get_collection().get_template("", 
                src=evoque_ini.get("evoque.default_template"))
    
    # global i18n gettext, bound onto a fixed (domain, language)
    if (evoque_ini.get("evoque.i18n_domain", None) is not None and
        evoque_ini.get("evoque.i18n_lang", None) is not None):
        i18n_domain = evoque_ini.get("evoque.i18n_domain")
        i18n_lang = evoque_ini.get("evoque.i18n_lang")
        domain.set_on_globals(
                    _ViewTemplateBase.i18n_gettext_alias, 
                    get_gettext(i18n_domain, i18n_lang))
    
    # log setup finished
    domain.log.debug(domain.__dict__)


#
# View Templates
#
# !+ z3evoque.browser
# !+ z3evoque/z3evoque.txt 

import threading
class _ViewTemplateBase(object):
    """Evoque template used as method of a view defined as a Python class.
    Should be overridden by subslasses, not meant to be instantiated directly.
    """
    
    # defaults for attributes needed to get the evoque template
    name = None
    src = None
    collection = None
    
    # if set, use this as local i18n domain
    i18n_domain = None
    i18n_gettext_alias = "i18n"
    
    def __init__(self, name, src, collection, i18n_domain):
        if name is not None: self.name = name
        if src is not None: self.src = src
        if collection is not None: self.collection = collection
        if i18n_domain is not None: self.i18n_domain = i18n_domain
        # these are updated each time a caller view gets this ViewTemplate
        _descriptor_view = None
        _descriptor_type = None
        log.debug("%s [%s][%s] %s" % (
            self.__class__.__name__, collection, name, self))
        self.lock = threading.RLock()
    
    def __get__(self, view, type_):
        """Non-data descriptor to grab a reference to the caller view.
        
        For the case of viewlets configured in ZCML, this is an instance of:
            zope.viewlet.metaconfigure.<<SpecificViewletClass>>
        """
        self._descriptor_view = view
        self._descriptor_type = type_
        return self
    
    @property
    def template(self):
        """The evoque template instance."""
        return domain.get_template(self.name, self.src, 
            collection=self.collection)
    
    # !+ support other evoque() params: raw=None, quoting=None
    def __call__(self, *args, **kwds):
        """Wrapper on template.evoque(), to load/evoke a template instance.
        Requests to load/evoke a template instance may be concurrent.
        """
        self.lock.acquire()
        try:
            namespace = self._get_context()
            t = self.template
            log.debug(" __call__ [%s][%s] %s %s %s" % (
                            (t.collection and t.collection.name), t.name, 
                            self, namespace, kwds))
            if args:
                log.warn(" __call__ IGNORING args: %s" % str(args))
            # !+ bungeni+html specific
            if t.collection.domain.globals.get("devmode"):
                return self._devmode_call__(t.evoque(namespace, **kwds))
            return t.evoque(namespace, **kwds)
        finally:
            self.lock.release()
    
    def _devmode_call__(self, s):
        """delineates the generated output between debug-friendly XML comments.
        !+ bungeni+html specific
        !+ an XML doc does should not start with a comment
        """
        t = self.template
        di = "\nVIEW:%s\nTEMPLATE:[%s]%s\n" % (
            self._descriptor_view.__class__, 
            t.collection.name, t.name)
        return """<!--%s-->%s<!--END%s-->""" % (di, s, di)
    
    def _get_context(self):
        view = self._descriptor_view
        namespace = {}
        namespace["view"] = view
        namespace["request"] = view.request
        namespace["context"] = view.context
        namespace['views'] = ViewMapper(view.context, view.request)
        # i18n local bound gettext -- bind to current user language, using 
        # either the local i18n_domain or the global i18n_domain
        i18n_domain = evoque_ini.get("evoque.i18n_domain", None)
        if self.i18n_domain is not None:
            i18n_domain = self.i18n_domain
        if i18n_domain is not None:
            namespace[self.i18n_gettext_alias] = get_gettext(
                    i18n_domain, view.request.locale.getLocaleID())
        return namespace


class ViewTemplateString(_ViewTemplateBase):
    """Evoque string-based template used as method of a view 
    defined as a Python class.
    
    To use: 
    
      >>> from bungeni.ui import z3evoque
      >>> vts = z3evoque.ViewTemplateString("test_vts", "<somemarkup/>")
      >>> vts()
      <somemarkup/>
      
    The last call above is basically a wrapper to fetch the evoque template 
    from the domain and render it:      
    
      >>> z3evoque.domain.get_template("test_vts").evoque()
      <somemarkup/>
    
    """
    def __init__(self, name, src, collection=None, i18n_domain=None):
        """
        name: str
        src: str, template source string
        collection: either(None, str, Collection)
            None implies default collection, else 
            str/Collection refer to an existing collection
        """
        super(ViewTemplateString, self
                                ).__init__(name, src, collection, i18n_domain)
        # templates from string must be explicitly set onto their collection
        domain.set_template(self.name, src=self.src, 
                                collection=self.collection, from_string=True)

class ViewTemplateFile(_ViewTemplateBase):
    """Evoque file-based template used as method of a view 
    defined as a Python class.
    !+ usage/tests
    """
    def __init__(self, name, src=None, collection=None, i18n_domain=None):
        """
        name: str, if no src this is collection-root-relative locator
        src: either(None, str), collection-root-relative locator
        collection: either(None, str, Collection)
            None implies default collection, else 
            str/Collection refer to an existing collection
        """
        super(ViewTemplateFile, self
                                ).__init__(name, src, collection, i18n_domain)

class PageViewTemplateFile(ViewTemplateFile):
    """A ViewTemplateFile for *the* browser page response, thus also 
    handles all browser page-related concerns.
    !+ usage/tests
    """
    content_type = None
    
    def __init__(self, name, src=None, collection=None, i18n_domain=None,
                    content_type=None):
        """
        name, str, collection: same as for ViewTemplateFile
        content_type:str, the content_type for the Page response
        """
        super(PageViewTemplateFile, self
                                ).__init__(name, src, collection, i18n_domain)
        if content_type is not None: self.content_type = content_type

    def __call__(self, *args, **kwds):
        # set content_type only if it has not been set
        if self.content_type is not None:
            response = self._descriptor_view.request.response
            if not response.getHeader("Content-Type"):
                response.setHeader("Content-Type", self.content_type)
        # zope requires that the result that it sets on the HTTP response 
        # is: either(None, str, zope.publisher.http.IResult). Annoyingly, a 
        # subclass of str or basestring (needed by the technique used by evoque
        # for managing guaranteed once-and-only-once automatic escaping of all 
        # template input data) is not acceptable for zope. And, adapting the 
        # result object to an IResult does not help as it anyhow requires that 
        # the object is a str in the first place. But, given that this is the 
        # "final" return in the render chain of a page template, thus no 
        # further escaping will be needed, we can anyhow safely cast the 
        # result to unicode.
        return unicode(super(PageViewTemplateFile, self
                        ).__call__(*args, **kwds))

# ensure public security setting for these attributes
from zope.security.checker import CheckerPublic, Checker, defineChecker
PUBLIC_ATTRS = {'__call__':CheckerPublic}
defineChecker(ViewTemplateString, Checker(PUBLIC_ATTRS))
defineChecker(ViewTemplateFile, Checker(PUBLIC_ATTRS))
defineChecker(PageViewTemplateFile, Checker(PUBLIC_ATTRS))

# View Template Helpers

class ViewMapper(object):
    """from: zope.app.pagetemplate.viewpagetemplatefile.ViewMapper"""
    def __init__(self, ob, request):
        self.ob = ob
        self.request = request
    def __getitem__(self, name):
        return zope.component.getMultiAdapter(
                                        (self.ob, self.request), name=name)

# IViewProvide

class IViewProvide(zope.interface.Interface):
    """A view content provider instance."""
    
    default_provider_name = zope.interface.Attribute("""
        The name for the default content provider (e.g. a viewlet manager, that 
        is providing the viewlets) for this view provider. May be None, in which 
        case a provider_name must be explictly passed to __call__().""")
    provider_interface = zope.interface.Attribute("""
        The interface for the content provider.""")
    _view = zope.interface.Attribute("""The calling view.""")
    
    def __call__(provider_name=None):
        """Get and render the named content provider.
        
        To generalize a zpt-specific feature (the "provider" ZPT keyword) into 
        a generic python call, with provider_name being simply a template 
        variable (thus becoming data-driven AND template-engine independent).
        
        For convenience, a default_provider_name is added to give view 
        templates the ability to call on a view-defined provider without 
        having to hard-wire/specify the provider name in the template itself. 
        
        The default provider_name attribute is factored out as a class attribute 
        to make it easier for view subclasses to specify a provider name.
        
        Thus, as far as TAL would be concerned, this means the ability to 
        replace template calls such as:
             <div tal:replace="structure provider:HARD_WIRED_PROVIDER_NAME" />
           with, if the IViewProvide instance is set on a view attribute 
           called "provide", and called with no provider name (so defaults to
           self.default_provider_name):
             <div tal:replace="structure python:view.provide() />
           or (specify any provider_name we like, here as a literal string): 
             <div tal:replace="structure python:view.provide('my_provider')" />
        
        The Evoque equivalent of this last variation (with an in-place literal 
        provider name) would be:
            ${view.provide("my_provider")}
        """

class ViewProvideBase(object):
    zope.interface.implements(IViewProvide)
    
    default_provider_name = None
    provider_interface = None
    
    def __init__(self, default_provider_name=None, provider_interface=None):
        if default_provider_name is not None: 
            self.default_provider_name = default_provider_name
        if provider_interface is not None: 
            self.provider_interface = provider_interface
        # this is updated each time a caller view gets this ViewProvide
        self._view = None
    
    def __call__(self, provider_name=None):
        if provider_name is None:
            provider_name = self.default_provider_name
        provider = zope.component.getMultiAdapter(
                            (self._view.context, self._view.request, self._view),
                            self.provider_interface,
                            name=provider_name)
        provider.update()
        return provider.render()
    
    def __get__(self, view, type_):
        """Non-data descriptor to grab a reference to the caller view.
        """
        self._view = view
        return self

class ViewProvideViewletManager(ViewProvideBase):
    provider_interface = zope.viewlet.interfaces.IViewletManager 
    

