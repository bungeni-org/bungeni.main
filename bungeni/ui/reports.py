import os
import time
import operator
import datetime
timedelta = datetime.timedelta
import tempfile
from bungeni.alchemist import Session
from bungeni.models import domain
from bungeni.models.utils import get_db_user_id
from bungeni.models.utils import get_current_parliament
from bungeni.models.interfaces import IGroupSitting
from bungeni.server.interfaces import ISettings
from bungeni.ui import zcml
from bungeni.ui.widgets import SelectDateWidget
from bungeni.ui.calendar import utils
from bungeni.ui.i18n import _
from bungeni.ui.utils import misc, url, queries, debug, date
from bungeni.ui import forms
from bungeni.ui import vocabulary
from bungeni.ui.forms.common import AddForm
from bungeni.ui import container
from bungeni.core.location import location_wrapped
from bungeni.core.interfaces import ISchedulingContext
from bungeni.core.language import get_default_language
from zope.security.proxy import removeSecurityProxy
from zope.publisher.browser import BrowserView
from zope import interface
from zope.formlib import form
from zope.formlib import namedtemplate
from zope.app.pagetemplate import ViewPageTemplateFile
from zope import schema
from zope.schema.vocabulary import SimpleVocabulary
from zope.app.form.browser import MultiCheckBoxWidget as _MultiCheckBoxWidget
from sqlalchemy.orm import eagerload
import sqlalchemy.sql.expression as sql
import operator
from bungeni.models import domain
from bungeni.models.utils import get_db_user_id
from bungeni.models.utils import get_current_parliament
from bungeni.models.interfaces import IGroupSitting
from bungeni.server.interfaces import ISettings
from zope.event import notify
from zope.lifecycleevent import ObjectCreatedEvent
from sqlalchemy.orm import eagerload
from sqlalchemy.sql import expression as sql

from zope.app.component.hooks import getSite

class TIME_SPAN:
    daily = _(u"Daily")
    weekly = _(u"Weekly")

def verticalMultiCheckBoxWidget(field, request):
    vocabulary = field.value_type.vocabulary
    widget = _MultiCheckBoxWidget(field, vocabulary, request)
    widget.cssClass = u"verticalMultiCheckBoxWidget"
    widget.orientation = "vertical"
    return widget

def horizontalMultiCheckBoxWidget(field, request):
    vocabulary = field.value_type.vocabulary
    widget = _MultiCheckBoxWidget(field, vocabulary, request)
    widget.cssClass = u"horizontalMultiCheckBoxWidget"
    widget.orientation = "horizontal"
    return widget

def availableItems(context):
    items = (_(u"Bills"),
                _(u"Agenda Items"),
                _(u"Motions"),
                _(u"Questions"),
                _(u"Tabled Documents"),
                )
    return SimpleVocabulary.fromValues(items)

def billOptions(context):
    items = (_(u"Title"),
             _(u"Summary"),
             _(u"Text"),
             _(u"Owner"),
             _(u"Signatories"),
            )
    return SimpleVocabulary.fromValues(items)

def agendaOptions(context):
    items = (_(u"Title"),
             _(u"Text"),
             _(u"Owner"),
            )
    return SimpleVocabulary.fromValues(items)

def motionOptions(context):
    items = (_(u"Title"),
             _(u"Number"),
             _(u"Text"),
             _(u"Owner"),
             _(u"Signatories"),
            )
    return SimpleVocabulary.fromValues(items)

def tabledDocumentOptions(context):
    items = (_(u"Title"),
             _(u"Number"),
             _(u"Text"),
             _(u"Owner"),
             _(u"Signatories"),
            )
    return SimpleVocabulary.fromValues(items)

def questionOptions(context):
    items = (_(u"Title"),
             _(u"Number"),
             _(u"Text"),
             _(u"Owner"),
             #"Response",
             _(u"Type"),
             _(u"Signatories"),
            )
    return SimpleVocabulary.fromValues(items)


class ReportView(form.PageForm):
    main_result_template = ViewPageTemplateFile("templates/main_reports.pt")
    result_template = ViewPageTemplateFile(
        "templates/default-report_sitting.pt"
    )
    display_minutes = None
    include_text = True

    def __init__(self, context, request):
        self.site_url = url.absoluteURL(getSite(), request)
        super(ReportView, self).__init__(context, request)
    
    def format_date(self, date_time, category="dateTime"):
        formatter = date.getLocaleFormatter(self.request, category=category)
        return formatter.format(date_time)

    def check_option(self, doctype, option=""):
        opt_key = "%s_%s" %(doctype, option) if option else doctype
        return hasattr(self.options, opt_key)

    class IReportForm(interface.Interface):
        short_name = schema.Choice(
                    title=_(u"Document Type"),
                    description=_(u"Type of report to be produced"),
                    values=["Order of the day",
                             "Weekly Business",
                             "Questions of the week"],
                    required=True
                    )
        date = schema.Date(
            title=_(u"Date"),
            description=_(u"Choose a starting date for this report"),
            required=True)
        item_types = schema.List(title=u"Items to include",
            required=False,
            value_type=schema.Choice(
                vocabulary="bungeni.vocabulary.AvailableItems"))
        bills_options = schema.List(title=u"Bill options",
            required=False,
            value_type=schema.Choice(
                vocabulary="bungeni.vocabulary.BillOptions"))
        agenda_items_options = schema.List(title=u"Agenda options",
            required=False,
            value_type=schema.Choice(
                vocabulary="bungeni.vocabulary.AgendaOptions"))
        motions_options = schema.List(title=u"Motion options",
            required=False,
            value_type=schema.Choice(
                vocabulary="bungeni.vocabulary.MotionOptions"))
        questions_options = schema.List(title=u"Question options",
            required=False,
            value_type=schema.Choice(
                vocabulary="bungeni.vocabulary.QuestionOptions"))
        tabled_documents_options = schema.List(title=u"Tabled Document options",
            required=False,
            value_type=schema.Choice(
                vocabulary="bungeni.vocabulary.TabledDocumentOptions"))
        note = schema.TextLine(title=u"Note",
            required=False,
            description=u"Optional note regarding this report")

    template = namedtemplate.NamedTemplate("alchemist.form")
    form_fields = form.Fields(IReportForm)
    form_fields["item_types"].custom_widget = horizontalMultiCheckBoxWidget
    form_fields["bills_options"].custom_widget = verticalMultiCheckBoxWidget
    form_fields["agenda_items_options"].custom_widget = verticalMultiCheckBoxWidget
    form_fields["motions_options"].custom_widget = verticalMultiCheckBoxWidget
    form_fields["questions_options"].custom_widget = verticalMultiCheckBoxWidget
    form_fields["tabled_documents_options"].custom_widget = verticalMultiCheckBoxWidget
    form_fields["date"].custom_widget = SelectDateWidget
    def setUpWidgets(self, ignore_request=False):
        class context:
            item_types = "Bills"
            bills_options = "Title"
            agenda_items_options = "Title"
            questions_options = "Title"
            motions_options = "Title"
            tabled_documents_options = "Title"
            note = None
            date = None
            short_name = _(u"Order of the day")
        self.adapters = {
            self.IReportForm: context
            }
        self.widgets = form.setUpEditWidgets(
            self.form_fields, self.prefix, self.context, self.request,
                    adapters=self.adapters, ignore_request=ignore_request)
    def update(self):
        super(ReportView, self).update()
        forms.common.set_widget_errors(self.widgets, self.errors)
        
    def get_end_date(self, start_date, time_span):
        if time_span is TIME_SPAN.daily:
            return start_date + timedelta(days=1)
        elif time_span is TIME_SPAN.weekly:
            return start_date + timedelta(weeks=1)
        raise RuntimeError("Unknown time span: %s" % time_span)
        
    def time_span(self,data):
        if "short_name" in data:
            if data["short_name"] == u"Order of the day":
                return TIME_SPAN.daily
            elif data["short_name"] == u"Proceedings of the day":
                return TIME_SPAN.daily
            elif data["short_name"] == u"Weekly Business":
                return TIME_SPAN.weekly
            elif data["short_name"] == u"Questions of the week":
                return TIME_SPAN.weekly
        else:
            return TIME_SPAN.daily
    
    def validate(self, action, data):
        errors = super(ReportView, self).validate(action, data)
        time_span = self.time_span(data)
        if IGroupSitting.providedBy(self.context):
            if not self.context.items:
                errors.append(interface.Invalid(
                _(u"The sitting has no scheduled items")))
        else:
            start_date = data["date"] if "date" in data else \
                                                datetime.datetime.today().date()
            end_date = self.get_end_date(start_date, time_span)
            try:
                ctx = ISchedulingContext(self.context)
            except:
                errors.append(interface.Invalid(
                        _(u"You are trying to generate a report "
                            "outside scheduling")
                    )
                )
            sittings = ctx.get_sittings(start_date, end_date).values()
            if not sittings:
                errors.append(interface.Invalid(
                        _(u"The period selected has no sittings"),
                                "date"))
            
            parliament = queries.get_parliament_by_date_range(
                start_date, end_date
            )
            if parliament is None:
                errors.append(interface.Invalid(
                    _(u"A parliament must be active in the period"),
                        "date"))
        return errors
    
    def l10n_dates(self, date_time="", dt_format="dateTime"):
        if date_time:
            try:
                formatter = self.request.locale.dates.getFormatter(dt_format)
                return formatter.format(date_time)
            except AttributeError:
                return date_time
        return date_time
    
    @form.action(_(u"Preview"))
    def handle_preview(self, action, data):
        self.process_form(data)
        self.save_link = url.absoluteURL(self.context, self.request) + "/save-report"
        self.body_text = self.result_template()
        return self.main_result_template()

    def process_form(self, data):
        class optionsobj(object):
            """Object that holds all the options."""
        self.options = optionsobj()
        if not hasattr(self, "short_name"):
            if "short_name" in data:
                self.short_name = data["short_name"]
        self.sittings = []
        if IGroupSitting.providedBy(self.context):
            trusted = removeSecurityProxy(self.context)
            order = "real_order" if self.display_minutes else "planned_order"
            trusted.item_schedule.sort(key=operator.attrgetter(order))
            self.sittings.append(trusted)
            self.start_date = self.context.start_date
            self.end_date = self.get_end_date(self.start_date,
                                                           self.time_span(data))
        else:
            self.start_date = data["date"] if "date" in data else \
                                                datetime.datetime.today().date()
            self.end_date = self.get_end_date(self.start_date, 
                                                           self.time_span(data))
            sittings = ISchedulingContext(self.context).get_sittings(
                                        self.start_date, self.end_date).values()
            self.sittings = map(removeSecurityProxy,sittings)
        self.ids = ""
        for sitting in self.sittings:
            self.ids += str(sitting.group_sitting_id) + ","
        def cleanup(string):
            return string.lower().replace(" ", "_")
        for item_type in data["item_types"]:
            itemtype = cleanup(item_type)
            type_key = itemtype.rstrip("s").replace("_", "")
            setattr(self.options, type_key, True)
            setattr(self.options, itemtype, True)
            for option in data[itemtype + "_options"]:
                opt_key = "".join((cleanup(itemtype.rstrip("s")).replace("_",""),
                    "_", cleanup(option)
                ))
                setattr(self.options, opt_key, True)
        if self.display_minutes:
            self.link = url.absoluteURL(self.context, self.request) \
                                                + "/votes-and-proceedings"
        else :
            self.link = url.absoluteURL(self.context, self.request) + "/agenda"
        try:
            self.group = self.context.group
        except:
            self.group = ISchedulingContext(self.context).get_group()

class GroupSittingContextAgendaReportView(ReportView):
    display_minutes = False
    include_text = False
    short_name = _(u"Sitting Agenda")
    note = ""
    form_fields = ReportView.form_fields.omit("short_name", "date")

class GroupSittingContextMinutesReportView(ReportView):
    display_minutes = True
    short_name = "Sitting Votes and Proceedings"
    note = ""
    form_fields = ReportView.form_fields.omit("short_name", "date")

class SchedulingContextAgendaReportView(ReportView):
    result_template = ViewPageTemplateFile(
        "templates/default-report_scheduling.pt"
    )
    display_minutes = False
    include_text = False
    note = ""

class SchedulingContextMinutesReportView(ReportView):
    display_minutes = True
    note = ""

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
                                required=False,
                                description=u"Optional note regarding this report"
                        )
        short_name = schema.TextLine(title=u"Report Type",
                                required=True,
                                description=u"Report Type"
                        )
        body_text = schema.Text(title=u"Report Text",
                                required=True,
                                description=u"Report Type"
                        )
        sittings = schema.TextLine(
                    title=_(u"Sittings included in this report"),
                    description=_(u"Sittings included in this report"),
                    required=False
                               )
    template = namedtemplate.NamedTemplate("alchemist.form")
    form_fields = form.Fields(ISaveReportForm)

    def setUpWidgets(self, ignore_request=False):
        class context:
            start_date = None
            end_date = None
            body_text = None
            note = None
            short_name = None
            sittings = None
        self.adapters = {
            self.ISaveReportForm: context
            }
        self.widgets = form.setUpEditWidgets(
            self.form_fields, self.prefix, self.context, self.request,
                    adapters=self.adapters, ignore_request=ignore_request)

    @form.action(_(u"Save"))
    def handle_save(self, action, data):
        report = domain.Report()
        session = Session()
        report.body_text = data["body_text"]
        report.start_date = data["start_date"]
        report.end_date = data["end_date"]
        report.note = data["note"]
        report.short_name = data["short_name"]
        report.owner_id = get_db_user_id()
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
                    sitting = session.query(domain.GroupSitting).get(sit_id)
                    sr = domain.SittingReport()
                    sr.report = report
                    sr.sitting = sitting
                    session.add(sr)
                    notify(ObjectCreatedEvent(report))
            except:
                #if no sittings are present in report or some other error occurs
                pass
        session.flush()
        
        if IGroupSitting.providedBy(self.context):
            back_link = "./schedule"
        else:
            back_link = "./"
        self.request.response.redirect(back_link)

class DefaultReportView(BrowserView):

    template = ViewPageTemplateFile("templates/default-report_sitting.pt")

    def __init__(self, context, request, include_text=True):
        self.context = context
        self.request = request
        self.include_text = include_text
        self.site_url = url.absoluteURL(getSite(), request)
        
    def __call__(self):
        return self.template() 

class DefaultReportContent:
    def __init__(self, sittings, short_name, display_minutes):
        self.sittings = sittings
        self.short_name = short_name
        self.display_minutes = display_minutes

# Event handler that publishes reports on sitting status change
# if the status is published_agenda or published_minutes
# it generates report based on the default template and publishes it
# To disable remove the lines below from ui/configure.zcml
# <subscriber
#        for="bungeni.models.interfaces.IGroupSitting
#          zope.lifecycleevent.interfaces.IObjectModifiedEvent"
#        handler=".reports.default_reports"
#     />       

def default_reports(sitting, event):
    if sitting.status in ("published_agenda", "published_minutes"):
        sitting = removeSecurityProxy(sitting)
        sittings = []
        sittings.append(sitting)
        report = domain.Report()
        session = Session()
        #!+REPORTS(miano, dec-2010) using test request here is not quite right
        # TODO : fix this.
        from zope.publisher.browser import TestRequest
        report.start_date = sitting.start_date
        report.end_date = sitting.end_date
        # The owner ID is the ID of the user that performed the last workflow
        # change
        for change in reversed(sitting.changes):
            if change.action == "workflow":
                owner_id = change.user_id
                break
        assert owner_id is not None, _("No user is defined. Are you logged in as Admin?")
        report.owner_id = owner_id
        report.language = get_default_language()
        report.created_date = datetime.datetime.now()
        report.group_id = sitting.group_id
        if sitting.status == 'published_agenda':
            report.short_name = _(u"Sitting Agenda")
            drc = DefaultReportContent(sittings, report.short_name, False)
            report.body_text = DefaultReportView(drc, TestRequest())()
        elif sitting.status == 'published_minutes':
            report.short_name = _(u"Sitting Votes and Proceedings")
            drc = DefaultReportContent(sittings, report.short_name, True)
            report.body_text = DefaultReportView(drc, TestRequest(), False)()
        session.add(report)
        session.flush()
        notify(ObjectCreatedEvent(report))
        sr = domain.SittingReport()
        sr.report = report
        sr.sitting = sitting
        session.add(sr)
        session.flush()
        notify(ObjectCreatedEvent(sr))
