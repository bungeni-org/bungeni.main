# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt
"""Sittings and Calendar report browser views

$Id$
"""

log = __import__("logging").getLogger("bungeni.ui.reports")

import operator
import datetime
timedelta = datetime.timedelta

from zope import interface, component
from zope import schema
from zope.formlib import form
from zope.formlib import namedtemplate
from zope.security.proxy import removeSecurityProxy
from zope.event import notify
from zope.lifecycleevent import ObjectCreatedEvent

from bungeni.alchemist import Session
from bungeni.models import domain
from bungeni.models.utils import get_db_user_id
from bungeni.models.interfaces import ISitting

from bungeni.core.interfaces import ISchedulingContext
from bungeni.core.workflow.interfaces import IWorkflow, IWorkflowTransitionEvent
from bungeni.core.language import get_default_language

from bungeni.ui import widgets
from bungeni.ui.i18n import _
from bungeni.ui.utils import date
from bungeni.ui.interfaces import IWorkspaceReportGeneration
from bungeni.ui.reporting import generators
from bungeni.ui.calendar.data import ExpandedSitting, ReportContext

from bungeni.utils import register

class DateTimeFormatMixin(object):
    """Helper methods to format and localize date and time objects
    """
    def format_date(self, date_time, category="dateTime"):
        formatter = date.getLocaleFormatter(self.request, category=category)
        return formatter.format(date_time)

    def l10n_dates(self, date_time, dt_format="dateTime"):
        if date_time:
            try:
                formatter = self.request.locale.dates.getFormatter(dt_format)
                return formatter.format(date_time)
            except AttributeError:
                return date_time
        return date_time

class IReportBuilder(interface.Interface):
    report_type = schema.Choice(title=_(u"Report Type"),
        description=_(u"Choose template to use in generating Report"),
        vocabulary="bungeni.vocabulary.ReportXHTMLTemplates"
    )
    start_date = schema.Date(title=_(u"Start Date"),
        description=_(u"Start date for this Report")
    )
    publication_number = schema.TextLine(title=_(u"Publication Number"),
        description=_(u"Optional publication number for this Report"),
        required=False
    )

class ReportBuilder(form.Form, DateTimeFormatMixin):
    template = namedtemplate.NamedTemplate("alchemist.form")
    form_fields = form.fields(IReportBuilder)
    form_fields["start_date"].custom_widget = widgets.SelectDateWidget
    sittings = []
    publication_date = datetime.datetime.today().date()
    publication_number = ""
    title = _(u"Report Title")
    generated_content = None
    show_preview = False
    language = None

    def __init__(self, context, request):
        self.context = context
        self.request = request
        interface.declarations.alsoProvides(removeSecurityProxy(self.context), 
            IWorkspaceReportGeneration
        )
        super(ReportBuilder, self).__init__(context, request)
    
    def get_end_date(self, start_date, hours):
        end_date = start_date + datetime.timedelta(seconds=hours*3600)
        return end_date

    def buildSittings(self, start_date, end_date):
        if ISitting.providedBy(self.context):
            trusted = removeSecurityProxy(self.context)
            order="real_order"
            trusted.item_schedule.sort(key=operator.attrgetter(order))
            self.sittings.append(trusted)
        else:
            sittings = ISchedulingContext(self.context).get_sittings(
                start_date, end_date
            ).values()
            self.sittings = map(removeSecurityProxy, sittings)
        self.sittings = [ ExpandedSitting(sitting) 
            for sitting in self.sittings 
        ]

    def generateContent(self, data):
        self.start_date = (data.get("start_date") or 
            datetime.datetime.today().date()
        )
        generator = generators.ReportGeneratorXHTML(data.get("report_type"))
        self.language = generator.language
        self.title = generator.title
        self.language = generator.language
        self.publication_number = data.get("publication_number")
        self.end_date = self.get_end_date(self.start_date, generator.coverage)
        self.buildSittings(self.start_date, self.end_date)
        generator.context = self
        return generator.generateReport()

    @form.action(_(u"Preview"), name="preview")
    def handle_preview(self, action, data):
        """Generate preview of the report
        """
        self.show_preview = True
        self.generated_content = self.generateContent(data)
        self.status = _(u"See the preview of the report below")
        return self.template()

    @form.action(_(u"Publish"), name="publish")
    def handle_publish(self, action, data):
        self.generated_content = self.generateContent(data)
        
        if not hasattr(self.context, "group_id"):
            context_group_id = ISchedulingContext(self.context).group_id
        else:
            context_group_id = self.context.group_id
        
        report = domain.Report(
            short_title=self.title,
            start_date=self.start_date,
            end_date=self.end_date,
            body=self.generated_content,
            owner_id=get_db_user_id(), # !+GROUP_AS_OWNER
            language=self.language,
            group_id=context_group_id
        )
        session = Session()
        session.add(report)
        session.flush()
        notify(ObjectCreatedEvent(report))
        self.status = _(u"Report has been processed and saved")
        
        return self.template()

class SaveReportView(form.PageForm):

    def __init__(self, context, request):
        super(SaveReportView, self).__init__(context, request)

    class ISaveReportForm(interface.Interface):
        start_date = schema.Date(
            title=_(u"Date"),
            description=_(u"Choose a starting date for this report"),
            required=True)
        end_date = schema.Date(
            title=_(u"Date"),
            description=_(u"Choose an end date for this report"),
            required=True)
        note = schema.TextLine(title=u"Note",
            description=u"Optional note regarding this report",
            required=False)
        short_name = schema.TextLine(title=u"Report Type",
            description=u"Report Type",
            required=True)
        body = schema.Text(title=u"Report Text",
            description=u"Report Type",
            required=True)
        sittings = schema.TextLine(title=_(u"Sittings included in this report"),
            description=_(u"Sittings included in this report"),
            required=False)
    template = namedtemplate.NamedTemplate("alchemist.form")
    form_fields = form.Fields(ISaveReportForm)
    
    def setUpWidgets(self, ignore_request=False):
        class context:
            start_date = None
            end_date = None
            body = None
            note = None
            short_name = None
            sittings = None
        self.adapters = {self.ISaveReportForm: context}
        self.widgets = form.setUpEditWidgets(
            self.form_fields, 
            self.prefix, 
            self.context, 
            self.request,
            adapters=self.adapters, 
            ignore_request=ignore_request
        )
    
    @form.action(_(u"Save"), name="save")
    def handle_save(self, action, data):
        report = domain.Report()
        session = Session()
        report.body = data["body"]
        report.start_date = data["start_date"]
        report.end_date = data["end_date"]
        report.note = data["note"]
        report.short_name = data["short_name"]
        report.owner_id = get_db_user_id() # !+GROUP_AS_OWNER
        report.language = get_default_language()
        report.created_date = datetime.datetime.now()
        if not hasattr(self.context, "group_id"):
            report.group_id = ISchedulingContext(self.context).group_id
        else:
            report.group_id = self.context.group_id
        session.add(report)
        session.flush()
        notify(ObjectCreatedEvent(report))
        if "sittings" in data.keys():
            try:
                ids = data["sittings"].split(",")
                for id_number in ids:
                    sit_id = int(id_number)
                    sitting = session.query(domain.Sitting).get(sit_id)
                    sr = domain.SittingReport()
                    sr.report = report
                    sr.sitting = sitting
                    session.add(sr)
                    notify(ObjectCreatedEvent(report))
            except:
                #if no sittings are present in report or some other error occurs
                pass
        session.flush()
        
        if ISitting.providedBy(self.context):
            back_link = "./schedule"
        else:
            back_link = "./"
        self.request.response.redirect(back_link)

# Event handler that publishes reports on sitting status change
# if the status is published_agenda or published_minutes
# it generates report based on the default template and publishes it
@register.handler(adapts=(ISitting, IWorkflowTransitionEvent))
def default_reports(sitting, event):
    wf = IWorkflow(sitting)
    if sitting.status in wf.get_state_ids(tagged=["published"]):
        sitting = removeSecurityProxy(sitting)
        report_type = "sitting_agenda"
        report_title = _(u"Sitting Agenda")
        if sitting.status in wf.get_state_ids(tagged=["publishedminutes"]):
            report_type = "sitting_minutes"
            report_title =  _(u"Sitting Votes and Proceedings")
        sittings = [ExpandedSitting(sitting)]
        report_context = ReportContext(sittings=sittings)
        report = domain.Report()
        report.short_title = report_title
        session = Session()
        # !+GROUP_AS_OWNER(mr, apr-2012) we assume for now that the "owner" of
        # the report is the currently logged in user.
        report.owner_id = get_db_user_id()
        report.created_date = datetime.datetime.now()
        report.group_id = sitting.group_id
        # generate using html template in bungeni_custom
        vocabulary = component.queryUtility(
            schema.interfaces.IVocabularyFactory, 
            "bungeni.vocabulary.ReportXHTMLTemplates"
        )
        term = vocabulary.getTermByFileName(report_type)
        doc_template = term and term.value or vocabulary.terms[0].value
        generator = generators.ReportGeneratorXHTML(doc_template)
        generator.title = report_title
        generator.context = report_context
        report.language = generator.language
        report.body = generator.generateReport()
        session.add(report)
        session.flush()
        notify(ObjectCreatedEvent(report))
        sr = domain.SittingReport()
        sr.report = report
        sr.sitting = sitting
        session.add(sr)
        session.flush()
        notify(ObjectCreatedEvent(sr))


