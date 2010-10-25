from bungeni.core.interfaces import IRSSValues
from bungeni.core.translation import translate_obj
from datetime import datetime
from i18n import _
from zope.app.component.hooks import getSite
from zope.component import getAdapter
from zope.i18n import translate
from zope.publisher.browser import BrowserView
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser import absoluteURL
import re
import xml.dom.minidom as xmllib


class RSSView(BrowserView):
    """ Base class that can generate
        RSS item.
    """

    channel_title = u""
    channel_description = u""
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

        date_element = self.response.createElement("pubDate")
        date_element.appendChild(self.response.createTextNode(self._format_date(pubDate)))
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
        """ Convert a datetime into an RFC 822 formatted date
            In stored objects we have only date of pulication,
            so putting time as 12:00.
        """
        return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (
                ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()],
                dt.day,
                ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Selangp", "Oct", "Nov", "Dec"][dt.month - 1],
                dt.year, dt.hour, dt.minute, dt.second)

    @property
    def values(self):
        return getAdapter(self.context, interface=IRSSValues).values

    def get_title(self, item):
        raise NotImplementedError("Should be implemented in child class")

    def get_description(self, item):
        raise NotImplementedError("Should be implemented in child class")

    def get_date(self, item):
        raise NotImplementedError("Should be implemented in child class")


class BillRSSView(RSSView):
    """ Generates rss views for
        bills.
    """

    channel_title = _(u'Bills')
    channel_description = _(u'Bills')

    def get_title(self, item):
        if item.identifier is None:
            return item.short_name
        return "#%d: %s" % (item.identifier,
                            item.short_name)

    def get_description(self, item):
        return item.body_text or u''

    def get_date(self, item):
        #Since we have only publication date, time will be set to 12:00
        return datetime(item.publication_date.year,
                        item.publication_date.month,
                        item.publication_date.day,
                        12, 0, 0)


class CommitteeRSSView(RSSView):
    """ Generates rss views for
        committees.
    """

    channel_title = _(u'Committees')
    channel_description = _(u'Committees')

    def get_title(self, item):
        return item.full_name

    def get_description(self, item):
        return item.description or u''

    def get_date(self, item):
        return item.status_date


class QuestionRSSView(RSSView):
    """ Generates rss views for
        questions.
    """

    channel_title = _(u'Questions')
    channel_description = _(u'Questions')

    def get_title(self, item):
        if item.question_number is None:
            return item.short_name
        return "#%d: %s" % (
            item.question_number,
            item.short_name)

    def get_description(self, item):
        return item.body_text or u''

    def get_date(self, item):
        return item.status_date


class MotionRSSView(RSSView):
    """ Generates rss views for
        motions.
    """

    channel_title = _(u'Motions')
    channel_description = _(u'Motions')

    def get_title(self, item):
        if item.motion_number is None:
            return item.short_name
        return "#%d: %s" % (
            item.motion_number,
            item.short_name)

    def get_description(self, item):
        return item.body_text or u''

    def get_date(self, item):
        return item.status_date


class TabledDocumentRSSView(RSSView):
    """ Generates rss views for
        tabled documents.
    """

    channel_title = _(u'Tabled documents')
    channel_description = _(u'Tabled documents')

    def get_title(self, item):
        return item.short_name

    def get_description(self, item):
        return item.body_text or u''

    def get_date(self, item):
        return item.status_date


class AgendaItemRSSView(RSSView):
    """ Generates rss views for
        questions.
    """

    channel_title = _(u'Agenda items')
    channel_description = _(u'Agenda items')

    def get_title(self, item):
        return u"%s - %s" % (item.short_name,
                             item.group.short_name)

    def get_description(self, item):
        return item.body_text or u''

    def get_date(self, item):
        return item.status_date


class SittingRSSView(RSSView):
    """ Generates rss views for
        sittings.
    """

    channel_title = _(u'Sittings')
    channel_description = _(u'Sittings')

    def get_title(self, item):
        return "%s %s, %s %s %s" % (_(u"Sitting:"),
                item.group.short_name,
                item.start_date.strftime('%Y-%m-%d, %H:%M'),
                _(u"to"),
                item.end_date.strftime('%H:%M'))

    def get_description(self, item):
        return "%s %s (%s %s %s)" % (_(u"Sitting scheduled for"),
                item.group.short_name,
                item.start_date.strftime('%Y-%m-%d %H:%M'),
                _(u"to"),
                item.end_date.strftime('%H:%M'))

    def get_date(self, item):
        return item.status_date


class ReportRSSView(RSSView):
    """ Generates rss views for
        reports.
    """

    channel_title = _(u'Reports')
    channel_description = _(u'Reports')

    def get_title(self, item):
        return u'%s: %s - %s' % (item.short_name,
            item.start_date, item.end_date)

    def get_description(self, item):
        return item.body_text

    def get_date(self, item):
        return item.status_date


class TimelineRSSView(RSSView):
    """ Base view for generiting
        feed for timeline of object.
    """

    def __init__(self, context, request):
        self.i18n_context = translate_obj(context, request.locale.id.language)
        super(TimelineRSSView, self).__init__(context, request)

    def __call__(self):
        self.request.response.setHeader('Content-Type', 'application/rss+xml')
        # Taking object url for timeline item
        item_url = self.get_item_url(self.context)
        for item in self.values:
            item = removeSecurityProxy(item)
            self.channel_element.appendChild(self.generate_item(self.get_title(item),
                                                                self.get_description(item),
                                                                item_url,
                                                                self.get_date(item),
                                                                item_url))
        return self.response.toxml("utf-8")

    def format_date(self, date_, category="date", length="medium"):
        formatter = self.request.locale.dates.getFormatter(category, length=length)
        return formatter.format(date_)

    def get_description(self, item):
        return item.description

    def get_date(self, item):
        return item.date_audit

    def get_title(self, item):
        return "%s %s %s" % (self.i18n_context.short_name,
                             _(u"changes from"),
                             self.format_date(item.date_audit))

    @property
    def values(self):
        return getAdapter(self.i18n_context, interface=IRSSValues).values


class BillTimelineRSSView(TimelineRSSView):
    """ View to generate timeline rss for
        bill.
    """

    @property
    def channel_title(self):
        if self.i18n_context.identifier is None:
            return self.i18n_context.short_name
        return "#%d: %s" % (self.i18n_context.identifier,
                            self.i18n_context.short_name)

    @property
    def channel_description(self):
        text = "%s %s %s" % (_("Submitted by"),
                            self.i18n_context.owner.first_name,
                            self.i18n_context.owner.last_name)
        if self.i18n_context.publication_date:
            text += " (%s %s)" % (_(u"published on"),
                                  self.format_date(self.i18n_context.publication_date))
        return text + "."


class QuestionTimelineRSSView(TimelineRSSView):
    """ View to generate timeline rss for
        question.
    """

    @property
    def channel_title(self):
        if self.i18n_context.question_number is None:
            return self.i18n_context.short_name
        return "#%d: %s" % (self.i18n_context.question_number,
                            self.i18n_context.short_name)

    @property
    def channel_description(self):
        text = "%s %s %s" % (_("Submitted by"),
                            self.i18n_context.owner.first_name,
                            self.i18n_context.owner.last_name)
        if self.i18n_context.approval_date:
            text += " (%s %s)" % (_(u"approved on"),
                                  self.format_date(self.i18n_context.approval_date))
        return text + "."


class MotionTimelineRSSView(TimelineRSSView):
    """ View to generate timeline rss for
        motion.
    """

    @property
    def channel_title(self):
        if self.i18n_context.motion_number is None:
            return self.i18n_context.short_name
        return "#%d: %s" % (self.i18n_context.motion_number,
                            self.i18n_context.short_name)

    @property
    def channel_description(self):
        text = "%s %s %s" % (_("Submitted by"),
                            self.i18n_context.owner.first_name,
                            self.i18n_context.owner.last_name)
        if self.i18n_context.notice_date:
            text += " (%s %s)" % (_(u"notice given on"),
                                  self.formatDate(self.i18n_context.notice_date))
        return text + "."


class TabledDocumentTimelineRSSView(TimelineRSSView):
    """ View to generate timeline rss for
        tabled document.
    """

    @property
    def channel_title(self):
        return self.i18n_context.short_name

    @property
    def channel_description(self):
        return "%s %s" % (self.i18n_context.short_name,
                          _(u"timeline"))


class AgendaItemTimelineRSSView(TimelineRSSView):
    """ View to generate timeline rss for
        tabled document.
    """

    @property
    def channel_title(self):
        return u"%s - %s" % (self.i18n_context.short_name,
                             self.i18n_context.group.short_name)

    @property
    def channel_description(self):
        return "%s %s" % (self.i18n_context.short_name,
                          _(u"timeline"))


# View classes for rss feed that links to akomantoso
# item xml representation page

class AkomantosoRSSView(object):
    """ Simple class to set necessary
        view name for item
    """

    view_name = u"/akomantoso.xml"

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

        date_element = self.response.createElement("pubDate")
        date_element.appendChild(self.response.createTextNode(self._format_date(pubDate)))
        item_element.appendChild(date_element)

        return item_element


class AkomantosoBillRSSView(AkomantosoRSSView, BillRSSView):
    """ View to generate RSS that links
        to akomantoso XML representation
        of bill.
    """


class AkomantosoQuestionRSSView(AkomantosoRSSView, QuestionRSSView):
    """ View to generate RSS that links
        to akomantoso XML representation
        of question.
    """


class AkomantosoMotionRSSView(AkomantosoRSSView, MotionRSSView):
    """ View to generate RSS that links
        to akomantoso XML representation
        of motion.
    """


class AkomantosoTabledDocumentRSSView(AkomantosoRSSView, TabledDocumentRSSView):
    """ View to generate RSS that links
        to akomantoso XML representation
        of tabled document.
    """


class AkomantosoAgendaItemRSSView(AkomantosoRSSView, TabledDocumentRSSView):
    """ View to generate RSS that links
        to akomantoso XML representation
        of agenda item.
    """

# Views to form XML in akomantoso format
# for certain objects


class AkomantosoXMLView(BrowserView):
    """ Base class to generate XML
        in akomantoso format
    """

    xmlns = u"http://www.akomantoso.org/1.0"
    document_type = "act" # one of: act, bill, report, judgement, debateRecord, doc

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

        #Identification
        identification_element = self.create_element("identification",
                                                     source="bungeni")
        meta_element.appendChild(identification_element)
        #FRBRWork
        identification_element.appendChild(self.create_frbr_work_element(ob))
        #FRBRExpression
        identification_element.appendChild(self.create_frbr_expression_element(ob))
        #FRBRManifestation
        identification_element.appendChild(self.create_frbr_manifestation_element(ob))

        #Publication
        meta_element.appendChild(self.create_publication_element(ob))

        #Lifecycle
        if hasattr(ob, "event"):
            if len(ob.event) > 0:
                lifecycle_element = self.create_element("lifecycle",
                                                        source="#bungeni")
                for item in ob.event.values():
                    event_element = self.create_element("event",
                                                        id="evn%s" % item.event_item_id,
                                                        type="generation",
                                                        date=item.event_date.strftime("%Y-%m-%d"),
                                                        source="orig")
                    lifecycle_element.appendChild(event_element)

                meta_element.appendChild(lifecycle_element)

        #References
        references_element = self.create_element("references",
                                                 source="#bungeni")
        meta_element.appendChild(references_element)
        #Original
        original_element = self.create_element("original",
                                               href=self.get_frbr_expression_url(ob),
                                               id="orig",
                                               showAs=self.get_title(ob))
        references_element.appendChild(original_element)
        #Parliament TLCOrganization
        tlc_parliament_element = self.create_element("TLCOrganization",
                                                     id="parliament",
                                                     href="/ontology/organization/%s/%s.bungeni" % (country, country),
                                                     showAs="Parliament")
        references_element.appendChild(tlc_parliament_element)
        #Bungeni TLCOrganization
        tlc_bungeni_element = self.create_element("TLCOrganization",
                                                  id="bungeni",
                                                  href="/ontology/organization/%s/%s.parliament" % (country, country),
                                                  showAs="Bungeni")
        references_element.appendChild(tlc_bungeni_element)

        #Body
        body_element = self.create_element("body")
        bill_element.appendChild(body_element)

        #Title
        title_element = self.create_element("title")
        title_element.appendChild(self.response.createTextNode(self.get_title(ob)))
        body_element.appendChild(title_element)

        #Article
        article_element = self.create_element("article")
        article_element.appendChild(self.response.createTextNode(self.get_body(ob)))
        body_element.appendChild(article_element)

        #Files
        if len(ob.files) > 0:
            attachments_element = self.create_element("attachments")
            bill_element.appendChild(attachments_element)
            for file in ob.files.values():
                attachment_element = self.create_element("attachment",
                                                         id="att%s" % file.item_id,
                                                         href=self.get_frbr_expression_url(ob) + "/" + file.file_name,
                                                         showAs=file.file_title)
                attachments_element.appendChild(attachment_element)

        return bill_element

    def create_publication_element(self, ob):
        raise NotImplementedError("Should be implemented in child class")

    def get_frbr_work_url(self, ob):
        raise NotImplementedError("Should be implemented in child class")

    def get_frbr_expression_url(self, ob):
        raise NotImplementedError("Should be implemented in child class")

    def get_frbr_manifestation_url(self, ob):
        raise NotImplementedError("Should be implemented in child class")

    def get_country(self, ob):
        """ No way to determine country
            for the document. Will be
            Kenya for now
        """
        return "ke"

    def get_body(self, item):
        return item.body_text or u''


class AkomantosoBillXMLView(AkomantosoXMLView):
    """ View for generating XML in akomantoso
        format for bill object
    """

    document_type = "bill"

    def get_title(self, item):
        if item.identifier is None:
            return item.short_name
        return "#%d: %s" % (item.identifier,
                            item.short_name)

    def get_frbr_work_url(self, ob):
        return "/%s/bill/%s/main" % (self.get_country(ob),
                                     ob.publication_date.strftime("%Y-%m-%d"))

    def get_frbr_expression_url(self, ob):
        return "/%s/bill/%s/%s@/main" % (self.get_country(ob),
                                         ob.publication_date.strftime("%Y-%m-%d"),
                                         ob.language)

    def get_frbr_manifestation_url(self, ob):
        return "/%s/bill/%s/%s@/main.xml" % (self.get_country(ob),
                                             ob.publication_date.strftime("%Y-%m-%d"),
                                             ob.language)

    def create_frbr_work_element(self, ob):
        """ Creates FRBRWork element with all
            necessary children
        """
        frbrwork_element = self.response.createElement("FRBRWork")

        frbrwork_element.appendChild(self.create_element("this",
                                                         value=self.get_frbr_work_url(ob)))
        frbrwork_element.appendChild(self.create_element("uri",
                                                         value=self.get_frbr_work_url(ob).replace("/main", "")))
        frbrwork_element.appendChild(self.create_element("date",
                                                         date=ob.status_date.strftime("%Y-%m-%d"),
                                                         name="Enactment"))
        frbrwork_element.appendChild(self.create_element("author",
                                                         href="#parliament"))
        return frbrwork_element

    def create_frbr_expression_element(self, ob):
        """ Creates FRBRExpression element with all
            necessary children
        """
        frbr_expression_element = self.response.createElement("FRBRExpression")

        frbr_expression_element.appendChild(self.create_element("this",
                                                         value=self.get_frbr_expression_url(ob)))
        frbr_expression_element.appendChild(self.create_element("uri",
                                                         value=self.get_frbr_expression_url(ob).replace("/main", "")))
        frbr_expression_element.appendChild(self.create_element("date",
                                                         date=ob.status_date.strftime("%Y-%m-%d"),
                                                         name="Expression"))
        frbr_expression_element.appendChild(self.create_element("author",
                                                         href="#parliament"))
        return frbr_expression_element

    def create_frbr_manifestation_element(self, ob):
        """ Creates FRBRManifestation element with all
            necessary children
        """
        frbr_manifestation_element = self.response.createElement("FRBRManifestation")
        frbr_manifestation_element.appendChild(self.create_element("this",
                                                         value=self.get_frbr_manifestation_url(ob)))
        frbr_manifestation_element.appendChild(self.create_element("uri",
                                                         value=self.get_frbr_manifestation_url(ob).replace("/main", ".akn")))
        frbr_manifestation_element.appendChild(self.create_element("date",
                                                         date=ob.status_date.strftime("%Y-%m-%d"),
                                                         name="XMLMarkup"))
        frbr_manifestation_element.appendChild(self.create_element("author",
                                                         href="#parliament"))

        return frbr_manifestation_element

    def create_publication_element(self, ob):
        publication_element = self.create_element("publication",
                                                  name="bill",
                                                  showAs="",
                                                  date=ob.publication_date.strftime("%Y-%m-%d"))
        return publication_element


class AkomantosoQuestionXMLView(AkomantosoXMLView):
    """ View for generating XML in akomantoso
        format for question object
    """

    document_type = "doc"

    def get_title(self, item):
        if item.question_number is None:
            return item.short_name
        return "#%d: %s" % (
            item.question_number,
            item.short_name)

    def get_frbr_work_url(self, ob):
        return "/%s/question/%s/main" % (self.get_country(ob),
                                         ob.submission_date.strftime("%Y-%m-%d"))

    def get_frbr_expression_url(self, ob):
        return "/%s/bill/%s/%s@/main" % (self.get_country(ob),
                                         ob.submission_date.strftime("%Y-%m-%d"),
                                         ob.language)

    def get_frbr_manifestation_url(self, ob):
        return "/%s/bill/%s/%s@/main.xml" % (self.get_country(ob),
                                             ob.submission_date.strftime("%Y-%m-%d"),
                                             ob.language)

    def create_frbr_work_element(self, ob):
        """ Creates FRBRWork element with all
            necessary children
        """
        frbrwork_element = self.response.createElement("FRBRWork")

        frbrwork_element.appendChild(self.create_element("this",
                                                         value=self.get_frbr_work_url(ob)))
        frbrwork_element.appendChild(self.create_element("uri",
                                                         value=self.get_frbr_work_url(ob).replace("/main", "")))
        frbrwork_element.appendChild(self.create_element("date",
                                                         date=ob.submission_date.strftime("%Y-%m-%d"),
                                                         name="Question"))
        frbrwork_element.appendChild(self.create_element("author",
                                                         href="#parliament"))
        return frbrwork_element

    def create_frbr_expression_element(self, ob):
        """ Creates FRBRExpression element with all
            necessary children
        """
        frbr_expression_element = self.response.createElement("FRBRExpression")

        frbr_expression_element.appendChild(self.create_element("this",
                                                         value=self.get_frbr_expression_url(ob)))
        frbr_expression_element.appendChild(self.create_element("uri",
                                                         value=self.get_frbr_expression_url(ob).replace("/main", "")))
        frbr_expression_element.appendChild(self.create_element("date",
                                                         date=ob.submission_date.strftime("%Y-%m-%d"),
                                                         name="Expression"))
        frbr_expression_element.appendChild(self.create_element("author",
                                                         href="#parliament"))
        return frbr_expression_element

    def create_frbr_manifestation_element(self, ob):
        """ Creates FRBRManifestation element with all
            necessary children
        """
        frbr_manifestation_element = self.response.createElement("FRBRManifestation")
        frbr_manifestation_element.appendChild(self.create_element("this",
                                                         value=self.get_frbr_manifestation_url(ob)))
        frbr_manifestation_element.appendChild(self.create_element("uri",
                                                         value=self.get_frbr_manifestation_url(ob).replace("/main", ".akn")))
        frbr_manifestation_element.appendChild(self.create_element("date",
                                                         date=ob.submission_date.strftime("%Y-%m-%d"),
                                                         name="XMLMarkup"))
        frbr_manifestation_element.appendChild(self.create_element("author",
                                                         href="#parliament"))

        return frbr_manifestation_element

    def create_publication_element(self, ob):
        publication_element = self.create_element("publication",
                                                  name="question",
                                                  showAs="",
                                                  date=ob.submission_date.strftime("%Y-%m-%d"))
        return publication_element


class AkomantosoMotionXMLView(AkomantosoXMLView):
    """ View for generating XML in akomantoso
        format for motion object
    """

    document_type = "doc"

    def get_title(self, item):
        if item.motion_number is None:
            return item.short_name
        return "#%d: %s" % (
            item.motion_number,
            item.short_name)

    def get_frbr_work_url(self, ob):
        return "/%s/motion/%s/main" % (self.get_country(ob),
                                       ob.submission_date.strftime("%Y-%m-%d"))

    def get_frbr_expression_url(self, ob):
        return "/%s/motion/%s/%s@/main" % (self.get_country(ob),
                                           ob.submission_date.strftime("%Y-%m-%d"),
                                           ob.language)

    def get_frbr_manifestation_url(self, ob):
        return "/%s/motion/%s/%s@/main.xml" % (self.get_country(ob),
                                               ob.submission_date.strftime("%Y-%m-%d"),
                                               ob.language)

    def create_frbr_work_element(self, ob):
        """ Creates FRBRWork element with all
            necessary children
        """
        frbrwork_element = self.response.createElement("FRBRWork")

        frbrwork_element.appendChild(self.create_element("this",
                                                         value=self.get_frbr_work_url(ob)))
        frbrwork_element.appendChild(self.create_element("uri",
                                                         value=self.get_frbr_work_url(ob).replace("/main", "")))
        frbrwork_element.appendChild(self.create_element("date",
                                                         date=ob.submission_date.strftime("%Y-%m-%d"),
                                                         name="Motion"))
        frbrwork_element.appendChild(self.create_element("author",
                                                         href="#parliament"))
        return frbrwork_element

    def create_frbr_expression_element(self, ob):
        """ Creates FRBRExpression element with all
            necessary children
        """
        frbr_expression_element = self.response.createElement("FRBRExpression")

        frbr_expression_element.appendChild(self.create_element("this",
                                                         value=self.get_frbr_expression_url(ob)))
        frbr_expression_element.appendChild(self.create_element("uri",
                                                         value=self.get_frbr_expression_url(ob).replace("/main", "")))
        frbr_expression_element.appendChild(self.create_element("date",
                                                         date=ob.submission_date.strftime("%Y-%m-%d"),
                                                         name="Expression"))
        frbr_expression_element.appendChild(self.create_element("author",
                                                         href="#parliament"))
        return frbr_expression_element

    def create_frbr_manifestation_element(self, ob):
        """ Creates FRBRManifestation element with all
            necessary children
        """
        frbr_manifestation_element = self.response.createElement("FRBRManifestation")
        frbr_manifestation_element.appendChild(self.create_element("this",
                                                         value=self.get_frbr_manifestation_url(ob)))
        frbr_manifestation_element.appendChild(self.create_element("uri",
                                                         value=self.get_frbr_manifestation_url(ob).replace("/main", ".akn")))
        frbr_manifestation_element.appendChild(self.create_element("date",
                                                         date=ob.submission_date.strftime("%Y-%m-%d"),
                                                         name="XMLMarkup"))
        frbr_manifestation_element.appendChild(self.create_element("author",
                                                         href="#parliament"))

        return frbr_manifestation_element

    def create_publication_element(self, ob):
        publication_element = self.create_element("publication",
                                                  name="motion",
                                                  showAs="",
                                                  date=ob.submission_date.strftime("%Y-%m-%d"))
        return publication_element


class AkomantosoTabledDocumentXMLView(AkomantosoXMLView):
    """ View for generating XML in akomantoso
        format for tabled document object
    """

    document_type = "doc"

    def get_title(self, item):
        return item.short_name

    def get_frbr_work_url(self, ob):
        return "/%s/tableddocument/%s/main" % (self.get_country(ob),
                                               ob.submission_date.strftime("%Y-%m-%d"))

    def get_frbr_expression_url(self, ob):
        return "/%s/tableddocument/%s/%s@/main" % (self.get_country(ob),
                                                   ob.submission_date.strftime("%Y-%m-%d"),
                                                   ob.language)

    def get_frbr_manifestation_url(self, ob):
        return "/%s/tableddocument/%s/%s@/main.xml" % (self.get_country(ob),
                                                       ob.submission_date.strftime("%Y-%m-%d"),
                                                       ob.language)

    def create_frbr_work_element(self, ob):
        """ Creates FRBRWork element with all
            necessary children
        """
        frbrwork_element = self.response.createElement("FRBRWork")

        frbrwork_element.appendChild(self.create_element("this",
                                                         value=self.get_frbr_work_url(ob)))
        frbrwork_element.appendChild(self.create_element("uri",
                                                         value=self.get_frbr_work_url(ob).replace("/main", "")))
        frbrwork_element.appendChild(self.create_element("date",
                                                         date=ob.submission_date.strftime("%Y-%m-%d"),
                                                         name="TabledDocument"))
        frbrwork_element.appendChild(self.create_element("author",
                                                         href="#parliament"))
        return frbrwork_element

    def create_frbr_expression_element(self, ob):
        """ Creates FRBRExpression element with all
            necessary children
        """
        frbr_expression_element = self.response.createElement("FRBRExpression")

        frbr_expression_element.appendChild(self.create_element("this",
                                                         value=self.get_frbr_expression_url(ob)))
        frbr_expression_element.appendChild(self.create_element("uri",
                                                         value=self.get_frbr_expression_url(ob).replace("/main", "")))
        frbr_expression_element.appendChild(self.create_element("date",
                                                         date=ob.submission_date.strftime("%Y-%m-%d"),
                                                         name="Expression"))
        frbr_expression_element.appendChild(self.create_element("author",
                                                         href="#parliament"))
        return frbr_expression_element

    def create_frbr_manifestation_element(self, ob):
        """ Creates FRBRManifestation element with all
            necessary children
        """
        frbr_manifestation_element = self.response.createElement("FRBRManifestation")
        frbr_manifestation_element.appendChild(self.create_element("this",
                                                         value=self.get_frbr_manifestation_url(ob)))
        frbr_manifestation_element.appendChild(self.create_element("uri",
                                                         value=self.get_frbr_manifestation_url(ob).replace("/main", ".akn")))
        frbr_manifestation_element.appendChild(self.create_element("date",
                                                         date=ob.submission_date.strftime("%Y-%m-%d"),
                                                         name="XMLMarkup"))
        frbr_manifestation_element.appendChild(self.create_element("author",
                                                         href="#parliament"))

        return frbr_manifestation_element

    def create_publication_element(self, ob):
        publication_element = self.create_element("publication",
                                                  name="tableddocument",
                                                  showAs="",
                                                  date=ob.submission_date.strftime("%Y-%m-%d"))
        return publication_element


class AkomantosoAgendaItemXMLView(AkomantosoXMLView):
    """ View for generating XML in akomantoso
        format for agenda item object
    """

    document_type = "doc"

    def get_title(self, item):
        return u"%s - %s" % (item.short_name,
                             item.group.short_name)

    def get_frbr_work_url(self, ob):
        return "/%s/agendaitem/%s/main" % (self.get_country(ob),
                                           ob.submission_date.strftime("%Y-%m-%d"))

    def get_frbr_expression_url(self, ob):
        return "/%s/agendaitem/%s/%s@/main" % (self.get_country(ob),
                                               ob.submission_date.strftime("%Y-%m-%d"),
                                               ob.language)

    def get_frbr_manifestation_url(self, ob):
        return "/%s/agendaitem/%s/%s@/main.xml" % (self.get_country(ob),
                                                   ob.submission_date.strftime("%Y-%m-%d"),
                                                   ob.language)

    def create_frbr_work_element(self, ob):
        """ Creates FRBRWork element with all
            necessary children
        """
        frbrwork_element = self.response.createElement("FRBRWork")

        frbrwork_element.appendChild(self.create_element("this",
                                                         value=self.get_frbr_work_url(ob)))
        frbrwork_element.appendChild(self.create_element("uri",
                                                         value=self.get_frbr_work_url(ob).replace("/main", "")))
        frbrwork_element.appendChild(self.create_element("date",
                                                         date=ob.submission_date.strftime("%Y-%m-%d"),
                                                         name="AgendaItem"))
        frbrwork_element.appendChild(self.create_element("author",
                                                         href="#parliament"))
        return frbrwork_element

    def create_frbr_expression_element(self, ob):
        """ Creates FRBRExpression element with all
            necessary children
        """
        frbr_expression_element = self.response.createElement("FRBRExpression")

        frbr_expression_element.appendChild(self.create_element("this",
                                                         value=self.get_frbr_expression_url(ob)))
        frbr_expression_element.appendChild(self.create_element("uri",
                                                         value=self.get_frbr_expression_url(ob).replace("/main", "")))
        frbr_expression_element.appendChild(self.create_element("date",
                                                         date=ob.submission_date.strftime("%Y-%m-%d"),
                                                         name="Expression"))
        frbr_expression_element.appendChild(self.create_element("author",
                                                         href="#parliament"))
        return frbr_expression_element

    def create_frbr_manifestation_element(self, ob):
        """ Creates FRBRManifestation element with all
            necessary children
        """
        frbr_manifestation_element = self.response.createElement("FRBRManifestation")
        frbr_manifestation_element.appendChild(self.create_element("this",
                                                         value=self.get_frbr_manifestation_url(ob)))
        frbr_manifestation_element.appendChild(self.create_element("uri",
                                                         value=self.get_frbr_manifestation_url(ob).replace("/main", ".akn")))
        frbr_manifestation_element.appendChild(self.create_element("date",
                                                         date=ob.submission_date.strftime("%Y-%m-%d"),
                                                         name="XMLMarkup"))
        frbr_manifestation_element.appendChild(self.create_element("author",
                                                         href="#parliament"))

        return frbr_manifestation_element

    def create_publication_element(self, ob):
        publication_element = self.create_element("publication",
                                                  name="agendaitem",
                                                  showAs="",
                                                  date=ob.submission_date.strftime("%Y-%m-%d"))
        return publication_element
