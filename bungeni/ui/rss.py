from bungeni.core.interfaces import IRSSValues
from bungeni.core.translation import translate_obj
from datetime import datetime
from i18n import _
from zope.component import getAdapter
from zope.i18n import translate
from zope.publisher.browser import BrowserView
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser import absoluteURL
import xml.dom.minidom as xmllib


class RSSView(BrowserView):
    """ Base class that can generate
        RSS item.
    """

    channel_title = u''
    channel_description = u''

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
            item_url = absoluteURL(item, self.request)
            self.channel_element.appendChild(self.generate_item(self.get_title(i18n_item),
                                                                self.get_description(i18n_item),
                                                                item_url,
                                                                self.get_date(i18n_item)))
        return self.response.toxml("utf-8")

    def generate_item(self, title, description, guid, pubDate):
        item_element = self.response.createElement('item')

        title_element = self.response.createElement('title')
        title_element.appendChild(self.response.createTextNode(title))
        item_element.appendChild(title_element)

        description_element = self.response.createElement('description')
        description_element.appendChild(self.response.createTextNode(description))
        item_element.appendChild(description_element)

        guid_element = self.response.createElement('guid')
        guid_element.appendChild(self.response.createTextNode(guid))
        item_element.appendChild(guid_element)

        date_element = self.response.createElement('pubDate')
        date_element.appendChild(self.response.createTextNode(self._format_date(pubDate)))
        item_element.appendChild(date_element)

        return item_element

    def generate_channel(self):
        channel_element = self.response.createElement('channel')

        title = translate(self.channel_title, context=self.request)
        title_element = self.response.createElement('title')
        title_element.appendChild(self.response.createTextNode(title))
        channel_element.appendChild(title_element)

        description = translate(self.channel_title, context=self.request)
        description_element = self.response.createElement('description')
        description_element.appendChild(self.response.createTextNode(description))
        channel_element.appendChild(description_element)

        link_element = self.response.createElement('link')
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
        item_url = absoluteURL(self.context, self.request)
        for item in self.values:
            item = removeSecurityProxy(item)
            self.channel_element.appendChild(self.generate_item(self.get_title(item),
                                                                self.get_description(item),
                                                                item_url,
                                                                self.get_date(item)))
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
