# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Workflow Notifications

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflow.notification")

from zope.i18n import translate
from email.mime.text import MIMEText
from evoque.domain import Domain
from bungeni.alchemist import Session
from bungeni.server.smtp import dispatch
from bungeni.models import domain
from bungeni.core.workflow.states import wrapped_condition
from bungeni.core import globalsettings
from bungeni.core import translation
from bungeni.core.workflows import dbutils
from bungeni.utils.capi import capi


# convenience wrappers for template evaluation

class TemplateNamespaceSite(object):
    """Exposes selected global site settings for convenient usage from within 
    a template. For passing down to template evaluation on *globals* as "site".
    """
    @property
    def clerk_email(self):
        return globalsettings.getClerksOfficeEmail()

    @property
    def speaker_email(self):
        return globalsettings.getSpeakersOfficeEmail()

class TemplateNamespaceItem(object):
    """Adapts context for convenient usage from within a template.
    For passing down to template evaluation on *locals* as "item".
    
    All translatable values are returned translated into target_lang.
    """
    def __init__(self, context, target_lang):
        self.context = context # IBungeniContent
        self.target_lang = target_lang
        self.translated_context = translation.translate_obj(
            context, lang=target_lang) # domain.ObjectTranslation

    def __getattribute__(self, name):
        """Anything not defined on self, pick off self.translated_context, 
        and, failing that, pick off self.context.
        """
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            try:
                return object.__getattribute__(self.translated_context, name)
            except AttributeError:
                return object.__getattribute__(self.context, name)
    
    @property
    def class_name(self):
        return translate(self.context.__class__.__name__, 
            target_language=self.target_lang)
    
    @property
    def owner(self):
        return Session().query(domain.User).get(self.context.owner_id)
    
    @property
    def owner_email(self):
        owner = self.owner
        return  '"%s %s" <%s>' % (
            owner.first_name, owner.last_name, owner.email)

    @property
    def ministry_emails(self):
        ministry = Session().query(domain.Ministry).get(self.context.ministry_id)
        return dbutils.getMinistryEmails(ministry)

# setup evoque template domain

def setup_domain():
    import logging
    domain = Domain(
        # root folder for the default template collection, must be abspath;
        "/tmp",
        # whether evaluation namespace is restricted or not 
        restricted=True,
        # how should any evaluation errors be rendered
        # int 0 to 4, for: [silent, zero, name, render, raise]
        errors=3, 
        # domain logger; additional settings should be specified via the 
        # app's config ini file, just as for any other logger. E.g:
        # [logger_notifications]
        # level = DEBUG
        # handlers =
        # qualname = notifications
        log=logging.getLogger("notifications"),
        # [collections] int, max loaded templates in a collection
        cache_size=0,
        # [collections] int, min seconds to wait between checks for
        # whether a template needs reloading
        auto_reload=0,
        # [collections] bool, consume all whitespace trailing a directive
        slurpy_directives=True,
        # [collections/templates] str or class, to specify the *escaped* 
        # string class that should be used i.e. if any str input is not of 
        # this type, then cast it to this type). 
        # Builtin str key values are: "xml" -> qpy.xml, "str" -> unicode
        quoting="str",
        # [collections/templates] str, preferred encoding to be tried 
        # first when decoding template source. Evoque decodes template
        # strings heuristically, i.e. guesses the input encoding.
        input_encoding="utf-8",
        # [collections/templates] list of filter functions, each having 
        # the following signature: filter_func(s:basestring) -> basestring
        # The functions will be called, in a left-to-right order, after 
        # template is rendered. NOTE: not settable from the conf ini.
        filters=[]
    )
    # add "site" settings on globals
    domain.set_on_globals("site", TemplateNamespaceSite())
    return domain

# evoque template domain singleton 
TEMPLATES = setup_domain()


# utility to set/retrieve a template from string source

def st(src):
    """Set/Retrieve the previously cached instance of the String Template from 
    the domain's default collection, using the src also as the the template's 
    name.
    """
    if not TEMPLATES.has_template(src):
        TEMPLATES.set_template(src, src=src, from_string=True)
    return TEMPLATES.get_template(src)

# notification

class Notification(object):
    """A Notification instance, call-executable on a context instance.
    
    Notifications are typically defined in workflow's XML definition, as part 
    of a <state> and all attribute values are really templates to be evaluated 
    on the given (context, lang). 
    
    The template source of each attribute value is what is stored on the 
    instance; if translatable (subject, body), that template source is 
    translated *prior* to loading the corresponding template for evaluation. 
    
    Note that each template attribute value is defaulted; defining an "empty"
    notification as follows:
    
        <notification />
    
    is exactly equivalent to:
    
        <notification condition="owner_receive_notification"
            subject="${item.class_name} ${item.status}: ${item.short_name}"
            from="${site.clerk_email}"
            to="${item.owner_email}"
            body="${item.class_name} ${item.status}: ${item.short_name}"
        />

    """
    def __init__(self,
        # resolvable python callable
        condition="owner_receive_notification",
        # i18n, template source
        subject="${item.class_name} ${item.status}: ${item.short_name}", 
        # template source 
        from_="${site.clerk_email}",
        # template source 
        to="${item.owner_email}",
        # i18n, template source
        body="${item.class_name} ${item.status}: ${item.short_name}"
    ):
        self.condition = wrapped_condition(
            capi.get_workflow_condition(condition))
        self.subject = subject 
        self.from_ = from_
        self.to = to
        self.body = body
            
    # !+ message language, should be a recipient preference
    # !+ for now, set/retrieve *translated* templates, using app default lang
    def __call__(self, context):
        if not self.condition(context):
            return # do not notify
        # lang, translated subject/body 
        lang = capi.default_language
        # !+DEFAULT(mr, apr-2011) breaks notification tests out of context
        subject = translate(self.subject, target_language=lang,
            # pick subject default value off self.__init__
            #default=self.__init__.func_defaults[1]
        )
        body = translate(self.body, target_language=lang, 
            # pick body default value off self.__init__
            #default=self.__init__.func_defaults[4]
        )
        # evaluation locals namespace
        locals = {
            "item": TemplateNamespaceItem(context, lang)
        }
        # set/retrieve the template for each templated value, and evoque --
        # all translatable template sources are translated **prior** to 
        # setting/retrieving
        msg = MIMEText(st(body).evoque(locals))
        msg["Subject"] = st(subject).evoque(locals)
        msg["From"] = st(self.from_).evoque(locals)
        msg["To"] = st(self.to).evoque(locals)
        dispatch(msg)


