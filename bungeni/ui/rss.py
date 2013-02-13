# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""RSS and Akoma Ntoso views for bungeni content(and containers)

$Id$
"""
import re
import time
import email
import xml.dom.minidom as xmllib

from zope.component import getAdapter
from zope.i18n import translate
from zope.publisher.browser import BrowserView
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser import absoluteURL

from bungeni.alchemist import Session
from bungeni.alchemist import utils
from bungeni.models.domain import User
from bungeni.models import interfaces as model_interfaces
from bungeni.core.interfaces import IRSSValues
from bungeni.core.translation import translate_obj
from bungeni.core.dc import IDCDescriptiveProperties
from bungeni.capi import capi

from bungeni.ui import audit
import bungeni.ui.adaptors # ensure module is loaded
from bungeni.ui.i18n import _

AKOMA_NTOSO_TYPES = ["act", "bill", "report", "judgement", "debateRecord", "doc"]
CUSTOM_FBR_WORK_NAMES = {
    "bill": "Enactment"
}
def get_fbr_work_name(item_type):
    return CUSTOM_FBR_WORK_NAMES.get(item_type) or "".join(
        map(unicode.capitalize, item_type.split("_"))
    )

class RSSView(BrowserView):
    """ Base class that can generate
        RSS item.
    """

    view_name = u""

    def __init__(self, context, request):
        super(RSSView, self).__init__(context, request)
        self.channel_link = absoluteURL(self.context, self.request)
        self.response = xmllib.Document()
        rss_element = self.response.createElement("rss")
        rss_element.setAttribute("version", "2.0")
        channel_element = self.generate_channel()
        rss_element.appendChild(channel_element)
        self.response.appendChild(rss_element)
        self.channel_element = channel_element

    @property
    def channel_title(self):
        return utils.get_descriptor(
            removeSecurityProxy(self.context).domain_model
        ).container_name
        
    @property
    def channel_description(self):
        return self.channel_title

    @property
    def values(self):
        return getAdapter(self.context, interface=IRSSValues).values

    def get_title(self, item):
        return IDCDescriptiveProperties(item).title

    def get_description(self, item):
        return IDCDescriptiveProperties(item).description

    def get_date(self, item):
        return getattr(item, "publication_date",
            getattr(item, "status_date", None)
        )

    def __call__(self):
        self.request.response.setHeader('Content-Type', 'application/rss+xml')

        for item in self.values:
            #Trying to translate item to the current language
            i18n_item = translate_obj(item, self.request.locale.id.language)
            item_url = self.get_item_url(item)
            self.channel_element.appendChild(self.generate_item(self.get_title(i18n_item),
                                                                self.get_description(i18n_item),
                                                                item_url,
                                                                self.get_date(i18n_item),
                                                                item_url))

        return self.response.toxml("utf-8")

    def get_item_url(self, item):
        return absoluteURL(item, self.request) + self.view_name

    def generate_item(self, title, description, guid, pubDate, link):
        item_element = self.response.createElement("item")

        title_element = self.response.createElement("title")
        title_element.appendChild(self.response.createTextNode(title))
        item_element.appendChild(title_element)

        link_element = self.response.createElement("link")
        link_element.appendChild(self.response.createTextNode(link))
        item_element.appendChild(link_element)

        description_element = self.response.createElement("description")
        description_element.appendChild(self.response.createCDATASection(description))
        item_element.appendChild(description_element)

        guid_element = self.response.createElement("guid")
        guid_element.appendChild(self.response.createTextNode(guid))
        item_element.appendChild(guid_element)

        if pubDate:
            date_element = self.response.createElement("pubDate")
            date_element.appendChild(
                self.response.createTextNode(self._format_date(pubDate))
            )
            item_element.appendChild(date_element)

        return item_element

    def replace_html_entities(self, text):
        """ replaces HTML entities from the text """
        global glEntities
        # replace numeric entities
        _numentities = set(re.findall("(&#\d+;)", text))
        for entity in _numentities:
            code = entity[2:-1]
            text = text.replace(entity, unichr(int(code)))
        # replace character     entities
        _entities = set(re.findall("(&[a-zA-Z0-9]+;)", text))
        for entity in _entities:
            literal = entity[1:-1]
            if literal in glEntities:
                try:
                    text = text.replace(entity, unichr(int("0x%s" % glEntities[literal], 16)))
                except Exception:
                    pass
        return text

    def generate_channel(self):
        channel_element = self.response.createElement("channel")

        title = translate(self.channel_title, context=self.request)
        title_element = self.response.createElement("title")
        title_element.appendChild(self.response.createTextNode(title))
        channel_element.appendChild(title_element)

        description = translate(self.channel_title, context=self.request)
        description_element = self.response.createElement("description")
        description_element.appendChild(self.response.createTextNode(description))
        channel_element.appendChild(description_element)

        link_element = self.response.createElement("link")
        link_element.appendChild(self.response.createTextNode(self.channel_link))
        channel_element.appendChild(link_element)

        return channel_element

    def _format_date(self, dt):
        return email.Utils.formatdate(time.mktime(dt.timetuple()))

class TimelineRSSView(RSSView):
    """ Base view for generiting
        feed for timeline of object.
    """
    
    # !+TIMELINE_RSS(mr, may-2012) seems out of sync data columns available 
    # for Timeline/AuditLog e.g. no indication of change action...
    
    def __init__(self, context, request):
        self.i18n_context = translate_obj(context, request.locale.id.language)
        super(TimelineRSSView, self).__init__(context, request)

    @property
    def values(self):
        return getAdapter(self.i18n_context, interface=IRSSValues).values
    
    @property
    def channel_title(self):
        return IDCDescriptiveProperties(self.context).title

    @property
    def channel_description(self):
        return IDCDescriptiveProperties(self.context).description

    def __call__(self):
        self.request.response.setHeader('Content-Type', 'application/rss+xml')
        # Taking object url for timeline item
        item_url = self.get_item_url(self.context)
        for item in self.values:
            # !+ assert self.context is item.head -> fails !
            #    assert self.context.doc_id is item.head.doc_id -> succeeds !
            item = removeSecurityProxy(item)
            self.channel_element.appendChild(
                self.generate_item(self.get_title(item),
                    self.get_description(item),
                    item_url,
                    self.get_date(item),
                    item_url
                )
            )
        return self.response.toxml("utf-8")

    def format_date(self, date_, category="date", length="medium"):
        formatter = self.request.locale.dates.getFormatter(category, length=length)
        return formatter.format(date_)

    def get_description(self, item):
        return audit.format_description(item, self.context)
    
    def get_date(self, item):
        return item.date_audit

    def get_title(self, item):
        return "%s %s %s" % (self.i18n_context.title,
                             _(u"changes from"),
                             self.format_date(item.date_audit))


# View classes for rss feed that links to akomantoso
# item xml representation page

class AkomantosoRSSView(RSSView):
    """ Simple class to set necessary
        view name for item
    """

    view_name = u"/feed.akomantoso"

    def __call__(self):
        self.request.response.setHeader('Content-Type', 'application/rss+xml')

        for item in self.values:
            #Trying to translate item to the current language
            i18n_item = translate_obj(item, self.request.locale.id.language)
            item_url = self.get_item_url(item)
            self.channel_element.appendChild(self.generate_item(self.get_title(i18n_item),
                                                                item_url,
                                                                self.get_date(i18n_item),
                                                                item_url))
        return self.response.toxml("utf-8")

    def generate_item(self, title, guid, pubDate, link):
        item_element = self.response.createElement("item")

        title_element = self.response.createElement("title")
        title_element.appendChild(self.response.createTextNode(title))
        item_element.appendChild(title_element)

        link_element = self.response.createElement("link")
        link_element.appendChild(self.response.createTextNode(link))
        item_element.appendChild(link_element)

        guid_element = self.response.createElement("guid")
        guid_element.appendChild(self.response.createTextNode(guid))
        item_element.appendChild(guid_element)
        
        if pubDate:
            date_element = self.response.createElement("pubDate")
            date_element.appendChild(
                self.response.createTextNode(self._format_date(pubDate))
            )
            item_element.appendChild(date_element)

        return item_element


# Views to form XML in akomantoso format
# for certain objects


class AkomantosoXMLView(BrowserView):
    """ Base class to generate XML
        in akomantoso format
    """
    
    xmlns = u"http://www.akomantoso.org/1.0"
    
    def __init__(self, context, request):
        super(AkomantosoXMLView, self).__init__(context, request)
        self.response = xmllib.Document()
    
    def __call__(self):
        ob = translate_obj(self.context, self.request.locale.id.language)
        akomantoso_element = self.create_base_structure()
        akomantoso_element.appendChild(self.create_body_structure(ob))
        self.response.appendChild(akomantoso_element)
        self.request.response.setHeader("Content-Type", "text/xml")
        return self.response.toxml("utf-8")
    
    @property
    def document_type(self):
        return self.context.type if type in AKOMA_NTOSO_TYPES else "doc"
    
    def create_base_structure(self):
        """ Simply creates akomaNtoso tag
        """
        akomantoso_element = self.response.createElement("akomaNtoso")
        akomantoso_element.setAttribute("xmlns", self.xmlns)
        return akomantoso_element
    
    def create_element(self, tag, **kwargs):
        element = self.response.createElement(tag)
        for key, value in kwargs.items():
            element.setAttribute(key.replace("_", ""), value)
        return element
    
    def create_body_structure(self, ob):
        """ Creates bill specific akomantoso xml 
        """
        bill_element = self.create_element(self.document_type)
        country = self.get_country(ob)
        meta_element = self.create_element("meta")
        bill_element.appendChild(meta_element)
        
        # Identification
        identification_element = self.create_element("identification", source="bungeni")
        meta_element.appendChild(identification_element)
        # FRBRWork
        identification_element.appendChild(self.create_frbr_work_element(ob))
        # FRBRExpression
        identification_element.appendChild(self.create_frbr_expression_element(ob))
        # FRBRManifestation
        identification_element.appendChild(self.create_frbr_manifestation_element(ob))
        
        # Publication
        meta_element.appendChild(self.create_publication_element(ob))
        
        # Lifecycle
        if hasattr(ob, "events"):
            if len(ob.events) > 0:
                lifecycle_element = self.create_element("lifecycle",
                    source="#bungeni")
                for item in ob.events.values():
                    event_element = self.create_element("event",
                        id="evn%s" % item.doc_id,
                        type="generation",
                        date=item.event_date and item.event_date.strftime("%Y-%m-%d") or "",
                        source="orig")
                    lifecycle_element.appendChild(event_element)
                
                meta_element.appendChild(lifecycle_element)
        
        # References
        references_element = self.create_element("references", source="#bungeni")
        meta_element.appendChild(references_element)
        # Original
        original_element = self.create_element("original", 
            id="orig", 
            href=self.get_frbr_expression_url(ob), 
            showAs=self.get_title(ob))
        references_element.appendChild(original_element)
        # Parliament TLCOrganization
        tlc_parliament_element = self.create_element("TLCOrganization", 
            id="parliament",
            href="/ontology/organization/%s/%s.bungeni" % (country, country),
            showAs="Parliament")
        references_element.appendChild(tlc_parliament_element)
        # Bungeni TLCOrganization
        tlc_bungeni_element = self.create_element("TLCOrganization",
            id="bungeni",
            href="/ontology/organization/%s/%s.parliament" % (country, country),
            showAs="Bungeni")
        references_element.appendChild(tlc_bungeni_element)
        
        # Body
        body_element = self.create_element("body")
        bill_element.appendChild(body_element)
        
        # Title
        title_element = self.create_element("title")
        title_element.appendChild(self.response.createTextNode(self.get_title(ob)))
        body_element.appendChild(title_element)
        
        # Article
        article_element = self.create_element("article")
        article_element.appendChild(self.response.createTextNode(self.get_body(ob)))
        body_element.appendChild(article_element)
        
        # Files
        if model_interfaces.IFeatureAttachment.providedBy(ob):
            files = [f for f in ob.files.values()]
            if len(files) > 0:
                attachments_element = self.create_element("attachments")
                bill_element.appendChild(attachments_element)
                for file in files:
                    attachment_element = self.create_element("attachment",
                        id="att%s" % file.attachment_id,
                        href=(self.get_frbr_expression_url(ob) + 
                            "/" + file.name),
                        showAs=file.title
                    )
                    attachments_element.appendChild(attachment_element)
        
        return bill_element
    
    def create_publication_element(self, ob):
        publication_element = self.create_element("publication",
            name=ob.type,
            showAs="",
            date=self.get_publication_date(ob).strftime("%Y-%m-%d")
        )
        return publication_element
    
    def create_frbr_work_element(self, ob):
        """Creates FRBRWork element with all necessary children.
        """
        frbrwork_element = self.response.createElement("FRBRWork")

        frbrwork_element.appendChild(
            self.create_element("this", value=self.get_frbr_work_url(ob))
        )
        frbrwork_element.appendChild(
            self.create_element("uri", 
                value=self.get_frbr_work_url(ob).replace("/main", "")
            )
        )
        frbrwork_element.appendChild(
            self.create_element("date",
                date=(ob.submission_date or ob.status_date).strftime("%Y-%m-%d"),
                name=get_fbr_work_name(ob.type)
            )
        )
        frbrwork_element.appendChild(
            self.create_element("author", href="#parliament")
        )
        return frbrwork_element

    def create_frbr_expression_element(self, ob):
        """Creates FRBRExpression element with all necessary children.
        """
        frbr_expression_element = self.response.createElement("FRBRExpression")

        frbr_expression_element.appendChild(
            self.create_element("this", value=self.get_frbr_expression_url(ob))
        )
        frbr_expression_element.appendChild(
            self.create_element("uri", 
                value=self.get_frbr_expression_url(ob).replace("/main", "")
            )
        )
        frbr_expression_element.appendChild(
            self.create_element("date",
                date=(ob.submission_date or ob.status_date).strftime("%Y-%m-%d"),
                name="Expression"
            )
        )
        frbr_expression_element.appendChild(
            self.create_element("author", href="#parliament")
        )
        return frbr_expression_element

    def create_frbr_manifestation_element(self, ob):
        """Creates FRBRManifestation element with all necessary children.
        """
        frbr_manifestation_element = self.response.createElement(
            "FRBRManifestation"
        )
        frbr_manifestation_element.appendChild(
            self.create_element("this", 
                value=self.get_frbr_manifestation_url(ob)
            )
        )
        frbr_manifestation_element.appendChild(
            self.create_element("uri", 
                value=self.get_frbr_manifestation_url(ob).replace(
                    "/main", ".akn"
                )
            )
        )
        frbr_manifestation_element.appendChild(
            self.create_element("date",
                date=(ob.submission_date or ob.status_date).strftime("%Y-%m-%d"),
                name="XMLMarkup"
            )
        )
        frbr_manifestation_element.appendChild(
            self.create_element("author", href="#parliament")
        )
        return frbr_manifestation_element

    def get_frbr_work_url(self, ob):
        return "/%s/%s/%s/main" % (self.get_country(ob),
            ob.type,
            self.get_publication_date(ob).strftime("%Y-%m-%d")
        )

    def get_frbr_expression_url(self, ob):
        return "/%s/%s/%s/%s/%s@/main" % (self.get_country(ob),
            ob.type,
            self.get_publication_date(ob).strftime("%Y-%m-%d"),
            ob.registry_number,
            ob.language
        )

    def get_frbr_manifestation_url(self, ob):
        return "/%s/%s/%s/%s@/main.xml" % (self.get_country(ob),
            ob.type,
            self.get_publication_date(ob).strftime("%Y-%m-%d"),
            ob.language
        )
    
    def get_country(self, ob):
        """The 2-letter country code for this bungeni instance.
        """
        return capi.legislature.country_code
    
    def get_publication_date(self, item):
        publication_date = None
        for attr in ["publication_date", "submission_date", "status_date"]:
            publication_date = getattr(item, attr, None)
            if publication_date:
                break
        return publication_date

    def get_title(self, item):
        return IDCDescriptiveProperties(item).title

    def get_body(self, item):
        return item.body or u''

class SubscriptionView(BrowserView):
    """View to manipulate with user's subscriptions (add or remove).
    """

    def subscribe(self):
        session = Session()
        redirect_url = absoluteURL(self.context, self.request)
        user = session.query(User).filter(User.login == self.request.principal.id).first()
        # In case we somewhy couldn't find the user
        if user is None:
            return self.request.response.redirect(redirect_url)
        # Adding context item to user's subscriptions
        trusted = removeSecurityProxy(self.context)
        user.subscriptions.append(trusted)
        # Redirecting back to the item's page
        return self.request.response.redirect(redirect_url)

    def unsubscribe(self):
        session = Session()
        redirect_url = absoluteURL(self.context, self.request)
        user = session.query(User).filter(User.login == self.request.principal.id).first()
        # In case we somewhy couldn't find the user
        if user is None:
            return self.request.response.redirect(redirect_url)
        # Removing context item from user's subscriptions
        trusted = removeSecurityProxy(self.context)
        try:
            user.subscriptions.remove(trusted)
        except ValueError:
            pass
        # Redirecting back to the item's page
        return self.request.response.redirect(redirect_url)


