# encoding: utf-8
# TODO - Cleanup!!!!

log = __import__("logging").getLogger("bungeni.ui.calendar")


import time
import tempfile
import datetime
timedelta = datetime.timedelta

import operator

from sqlalchemy.orm import eagerload
import sqlalchemy.sql.expression as sql
from zope.event import notify
from zope.lifecycleevent import ObjectCreatedEvent
from zope import interface
from zope import component
from zope import schema
from zope.i18n import translate
from zope.formlib import form
from zope.formlib import namedtemplate
from zope.location.interfaces import ILocation
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.publisher.browser import BrowserView
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.app.component.hooks import getSite
from zope.security.proxy import removeSecurityProxy
from zope.security.proxy import ProxyFactory
from zope.security import checkPermission
import zope.securitypolicy.interfaces
from bungeni.core.translation import get_all_languages
from zope.publisher.interfaces import IPublishTraverse
from zope.schema.vocabulary import SimpleVocabulary
#from zope.schema.vocabulary import SimpleTerm
from zope.app.file.file import File
from zope.datetime import rfc1123_date
from zope.app.form.browser import MultiCheckBoxWidget as _MultiCheckBoxWidget
#from zope.publisher.interfaces.http import IResult, IHTTPRequest
#from zope.publisher.http import DirectResult

from bungeni.ui.widgets import SelectDateWidget
from bungeni.ui.calendar import utils
from bungeni.ui.tagged import get_states
from bungeni.ui.i18n import _
from bungeni.ui.utils import misc, url as ui_url, queries, debug
from bungeni.ui.menu import get_actions
from bungeni.ui.forms.common import set_widget_errors
from bungeni.ui import vocabulary
from bungeni.core.location import location_wrapped
from bungeni.core.interfaces import ISchedulingContext
#from bungeni.core.schedule import PlenarySchedulingContext
from bungeni.core.odf import OpenDocument
from bungeni.models import domain
from bungeni.models.utils import get_principal_id
from bungeni.models.interfaces import IGroupSitting
from bungeni.server.interfaces import ISettings

from ploned.ui.interfaces import IStructuralView
from ore.alchemist.container import stringKey
from ore.alchemist import Session
from ore.workflow.interfaces import IWorkflowInfo

from zc.resourcelibrary import need

from bungeni.core.workflows.groupsitting import states as sitting_wf_state
from dateutil.rrule import *

class TIME_SPAN:
    daily = _(u"Daily")
    weekly = _(u"Weekly")

def get_scheduling_actions(context, request):
    return get_actions("scheduling_actions", context, request)

def get_sitting_actions(context, request):
    return get_actions("sitting_actions", context, request)

def get_discussion_actions(context, request):
    return get_actions("discussion_actions", context, request)

def get_workflow_actions(context, request):
    return get_actions("context_workflow", context, request)

def get_sitting_items(sitting, request, include_actions=False):
    items = []

    if sitting.status in get_states("groupsitting", 
                                keys=["draft_agenda", "published_agenda"]):
        order = "planned_order"
    else:
        order = "real_order"

    schedulings = map(
        removeSecurityProxy,
        sitting.items.batch(order_by=order, limit=None))
    site_url = ui_url.absoluteURL(getSite(), request)
    for scheduling in schedulings:
        item = ProxyFactory(location_wrapped(scheduling.item, sitting))
       
        props = IDCDescriptiveProperties.providedBy(item) and item or \
                IDCDescriptiveProperties(item)

        discussions = tuple(scheduling.discussions.values())
        discussion = discussions and discussions[0] or None

        info = IWorkflowInfo(item, None)
        state_title = info.workflow().workflow.states[item.status].title
        
        record = {
            'title': props.title,
            'description': props.description,
            'name': stringKey(scheduling),
            'status': item.status,
            'type': item.type.capitalize,
            't':item.type,
            'state_title': state_title,
            #'category_id': scheduling.category_id,
            #'category': scheduling.category,
            'discussion': discussion,
            'delete_url': "%s/delete" % ui_url.absoluteURL(scheduling, request),
            'url': ui_url.set_url_context(site_url+('/business/%ss/obj-%s' % (item.type, item.parliamentary_item_id)))}
        
        if include_actions:
            record['actions'] = get_scheduling_actions(scheduling, request)
            record['workflow'] = get_workflow_actions(item, request)

            discussion_actions = get_discussion_actions(discussion, request)
            if discussion_actions:
                assert len(discussion_actions) == 1
                record['discussion_action'] = discussion_actions[0]
            else:
                record['discussion_action'] = None
        items.append(record)
    return items

def create_sittings_map(sittings, request):
    """Returns a dictionary that maps:

      (day, hour) -> {
         'record'   : sitting database record
         'actions'  : actions that apply to this sitting
         'class'    : sitting
         'span'     : span
         }
         
      (day, hour) -> ``None``
      
    If the mapped value is a sitting, then a sitting begins on that
    day and hour, if it's ``None``, then a sitting is reaching into
    this day and hour.
    
    The utility of the returned structure is to aid rendering a
    template with columns spanning several rows.
    """

    mapping = {}
    for sitting in sittings.values():
        day = sitting.start_date.weekday()
        hour = sitting.start_date.hour

        start_date = utils.timedict(
            sitting.start_date.hour,
            sitting.start_date.minute)

        end_date = utils.timedict(
            sitting.end_date.hour,
            sitting.end_date.minute)
        
        status = misc.get_wf_state(sitting)
               
        proxied = ProxyFactory(sitting)
        
        if checkPermission(u"bungeni.agendaitem.Schedule", proxied):
            link = "%s/schedule" % ui_url.absoluteURL(sitting, request)
        else:
            link = ui_url.absoluteURL(sitting, request)
        
        if checkPermission("zope.View", proxied):
            mapping[day, hour] = {
                'url': link,
                'record': sitting,
                'class': u"sitting",
                'actions': get_sitting_actions(sitting, request),
                'span': sitting.end_date.hour - sitting.start_date.hour,
                'formatted_start_time': start_date,
                'formatted_end_time': end_date,
                'status' : status,
            }
            for hour in range(sitting.start_date.hour+1, sitting.end_date.hour):
                mapping[day, hour] = None
        
        # make sure start- and end-date is the same DAY
        assert (sitting.start_date.day == sitting.end_date.day) and \
               (sitting.start_date.month == sitting.end_date.month) and \
               (sitting.start_date.year == sitting.end_date.year)

    return mapping

class CalendarView(BrowserView):
    """Main calendar view."""

    interface.implements(IStructuralView)

    template = ViewPageTemplateFile("dhtmlxcalendar.pt")
    
    short_name = u"Calendar"
    
    def __init__(self, context, request):
        log.debug("CalendarView.__init__: %s" % (context))
        super(CalendarView, self).__init__(
            ISchedulingContext(context), request)
        self.context.__name__ = self.__name__
        self.context.title = self.short_name
        interface.alsoProvides(self.context, ILocation)
        interface.alsoProvides(self.context, IDCDescriptiveProperties)
        self.__parent__ = context
        log.debug(debug.interfaces(self))
        log.debug(debug.location_stack(self))
        
    def __call__(self, timestamp=None):
        return self.render()
        
    def publishTraverse(self, request, name):
        traverser = component.getMultiAdapter(
            (self.context, request), IPublishTraverse)
        return traverser.publishTraverse(request, name)
    
    def render(self, template=None):
        if template is None:
            template = self.template
        if checkPermission(u"bungeni.sitting.Add", self.context):
            self.edit = True
        else:
            self.edit = False
        session = Session()
        venues = session.query(domain.Venue).all()
        languages = get_all_languages()
        sitting_types = session.query(domain.SittingType).all()
        session.close()
        self.display_language = 'en'
        if self.request.get('I18N_LANGUAGES'):
            self.display_language = self.request.get('I18N_LANGUAGES')
        s = '<div class="dhx_cal_ltext" style="height:90px;">' 
        s += '<table><tr><td>Sitting Type</td><td><select id="select_sitting_type">'
        for sitting_type in sitting_types:
		    s += '<option value="'+str(sitting_type.sitting_type_id)+'">'+sitting_type.sitting_type+'</option>'	
        s += '</select></td></tr>'
        s += '<tr><td>Venue</td><td><select id="select_sitting_venue">'
        for venue in venues:
            s += '<option value="'+str(venue.venue_id)+'">'+venue.short_name+'</option>'
        s += '</select></td></tr>'
        s += '<tr><td>Language</td><td><select id="select_sitting_lang">'
        for lang in languages:
            if lang == 'en':
                s += '<option value="'+lang+'" selected>'+lang+'</option>'
            else:
                s += '<option value="'+lang+'">'+lang+'</option>'
        s += '</select></td></tr></table></div>'
        self.sitting_details_form = s
        return template()

class CommitteeCalendarView(CalendarView):
    """Calendar-view for a committee."""

class DailyCalendarView(CalendarView):
    """Daily calendar view."""
    
    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)

    def render(self, today, template=None):
        if template is None:
            template = self.template

        calendar_url = ui_url.absoluteURL(self.context.__parent__, self.request)
        date = removeSecurityProxy(self.context.date)

        sittings = self.context.get_sittings()
        return template(
            display="daily",
#            title=_(u"$B $Y", mapping=date),
            title = date,
#
            day={
                'formatted': datetime.datetime.strftime(date, '%A %d'),
                'id': datetime.datetime.strftime(date, '%Y-%m-%d'),
                'today': date == today,
                'url': "%s/%d" % (calendar_url, date.totimestamp()),
                },
            hours=range(6,21),
            week_no=date.isocalendar()[1],
            week_day=date.weekday(),
            links={
                'previous': "%s/%d" % (
                    calendar_url, (date - timedelta(days=1)).totimestamp()),
                'next': "%s/%d" % (
                    calendar_url, (date + timedelta(days=1)).totimestamp()),
                },
            sittings_map = create_sittings_map(sittings, self.request),
            )

class GroupSittingScheduleView(BrowserView):
    """Group-sitting scheduling view.

    This view presents a sitting and provides a user interface to
    manage the agenda.
    """

    template = ViewPageTemplateFile("main.pt")
    ajax = ViewPageTemplateFile("ajax.pt")
    
    _macros = ViewPageTemplateFile("macros.pt")
    def __init__(self, context, request):
        super(GroupSittingScheduleView, self).__init__(context, request)
        self.__parent__ = context

    def __call__(self, timestamp=None):
        session = Session()
        if timestamp is None:
            # start the week on the first weekday (e.g. Monday)
            date = utils.datetimedict.fromdate(datetime.date.today())
        else:
            try:
                timestamp = float(timestamp)
            except:
                raise TypeError(
                    "Timestamp must be floating-point (got %s)" % timestamp)
            date = utils.datetimedict.fromtimestamp(timestamp)

        if misc.is_ajax_request(self.request):
            rendered = self.render(date, template=self.ajax)
        rendered = self.render(date)
        session.close()
        return rendered
        
    def reorder_field(self):
        if self.context.status=="draft_agenda":
            return 'planned_order'
        elif self.context.status=="draft_minutes": 
            return 'real_order'
        else:
            return None
            
    def render(self, date, template=None):
        #need('yui-editor')
        need('yui-rte')
        need('yui-resize')
        need('yui-button')
        
        if template is None:
            template = self.template

        container = self.context.__parent__
        #schedule_url = self.request.getURL()
        container_url = ui_url.absoluteURL(container, self.request)
        
        # determine position in container
        key = stringKey(self.context)
        keys = list(container.keys())
        pos = keys.index(key)

        links = {}
        if pos > 0:
            links['previous'] = "%s/%s/%s" % (
                container_url, keys[pos-1], self.__name__)
        if pos < len(keys) - 1:
            links['next'] = "%s/%s/%s" % (
                container_url, keys[pos+1], self.__name__)

        #start_date = utils.datetimedict.fromdatetime(self.context.start_date)
        #end_date = utils.datetimedict.fromdatetime(self.context.end_date)
        
        #session = Session()
        sitting_type_dc = IDCDescriptiveProperties(self.context.sitting_type)

        site_url = ui_url.absoluteURL(getSite(), self.request)

        return template(
            display="sitting",
            #title=_(u"$A $e, $B $Y", mapping=start_date),
            title = "%s: %s - %s" % (self.context.group.short_name, 
                self.context.start_date.strftime('%Y-%m-%d %H:%M'), 
                self.context.end_date.strftime('%H:%M')),
            description=_(u"$type &mdash; ${start}-${end}", mapping={
                'type': translate(sitting_type_dc.title),
                'start': self.context.start_date.strftime('%Y-%m-%d %H:%M'), 
                'end': self.context.end_date.strftime('%H:%M')
                }),
#            title = u"",
#            description = u"",
#
            links=links,
            actions=get_sitting_actions(self.context, self.request),
            items=get_sitting_items(
                self.context, self.request, include_actions=True),
            #categories=vocabulary.ItemScheduleCategories(self.context),
            new_category_url="%s/admin/content/categories/add?next_url=..." % site_url,
            status=self.context.status,
            )
            
    @property
    def macros(self):
        return self._macros.macros

class ItemScheduleOrder(BrowserView):
    "Stores new order of schedule items"
    def __call__(self):
        obj = self.request.form['obj[]']
        '''container = self.context
        schedulings = container.item_schedule
        
        for s in schedulings:
            print "s=>", s, s.planned_order
        for order, id_number in enumerate(obj):
            print "asdfasdf", order, id_number'''
        session = Session()
        for i in range(0,len(obj)):
            sch = session.query(domain.ItemSchedule).get(obj[i])
            setattr(sch, 'planned_order', i+1)
        session.commit()

class SittingCalendarView(CalendarView):
    """Sitting calendar view."""
    
    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)



def verticalMultiCheckBoxWidget(field, request):
    vocabulary = field.value_type.vocabulary
    widget = _MultiCheckBoxWidget(field, vocabulary, request)
    widget.cssClass = u"verticalMultiCheckBoxWidget"
    widget.orientation='vertical'
    return widget 

def horizontalMultiCheckBoxWidget(field, request):
    vocabulary = field.value_type.vocabulary
    widget = _MultiCheckBoxWidget(field, vocabulary, request)
    widget.cssClass = u"horizontalMultiCheckBoxWidget"
    widget.orientation='horizontal'
    return widget 
    
#def MultiCheckBoxWidgetFactory(field, request):
#            return _MultiCheckBoxWidget(
#                field, field.vocabulary, request)
                
def availableItems(context):
    items = ('Bills',
                'Agenda Items',
                'Motions',
                'Questions',
                'Tabled Documents',
                )
    return SimpleVocabulary.fromValues(items)
           
def billOptions(context):
    items = ('Title',
             'Summary', 
             'Text', 
             'Owner',
             'Cosignatories',
            )
    return SimpleVocabulary.fromValues(items)

def agendaOptions(context):
    items = ('Title',
             'Text', 
             'Owner',
            )
    return SimpleVocabulary.fromValues(items)

def motionOptions(context):
    items = ('Title',
             'Number', 
             'Text', 
             'Owner',
            )
    return SimpleVocabulary.fromValues(items)

def tabledDocumentOptions(context):
    items = ('Title',
             'Number', 
             'Text', 
             'Owner',
            )
    return SimpleVocabulary.fromValues(items)

def questionOptions(context):
    items = ('Title',
             'Number', 
             'Text', 
             'Owner',
             #'Response',
             'Type',
            )
    return SimpleVocabulary.fromValues(items)

class ReportingView(form.PageForm):
    """Reporting view base class.

    The context of the view is a scheduling context, which always
    relates to a principal group, e.g. 'Plenary'.

    A starting date must be specified, as well as a time span
    parameter, which can be one of the following:

    - Daily
    - Weekly

    The time span parameter is used as title and to generate canonical
    filenames and unique identification strings for publishing the
    reports, e.g.

      'Daily agenda 2009/30/12' (agenda-daily-2009-30-12.pdf)

    It's not enforced that weeks begin on Mondays or any other
    particular day; a week is always 7 days.

    A report is a listing of sittings that take place in the defined
    period. For each sitting, the summary may be different depending
    on the type of report. The ``get_sittings`` method will fetch the
    relevant sittings.
    """

    date = None
    display_minutes = None
    
    def __init__(self, context, request):
        super(ReportingView, self).__init__(context, request)
        
        if IGroupSitting.providedBy(context):
            self.date = datetime.date(
                context.start_date.year,
                context.start_date.month,
                context.start_date.day) 
        '''
        while not ISchedulingContext.providedBy(context):
            context = context.__parent__
            if context is None:
                break;
                #raise RuntimeError(
                #    "No scheduling context found.")
        if context is not None:
            self.scheduling_context = context'''

    class IReportingForm(interface.Interface):
        doc_type = schema.Choice(
                    title = _(u"Document Type"),
                    description = _(u"Type of document to be produced"),
                    values= ['Order of the day',
                             'Proceedings of the day',
                             'Weekly Business',
                             'Questions of the week'],
                    required=True
                    )
        date = schema.Date(
            title=_(u"Date"),
            description=_(u"Choose a starting date for this report"),
            required=True)
            
        item_types = schema.List(title=u'Items to include',
                   required=False,
                   value_type=schema.Choice(
                    vocabulary="Available Items"),
                   )
        bill_options = schema.List( title=u'Bill options',
                       required=False,
                       value_type=schema.Choice(
                       vocabulary='Bill Options'),
                         )
        agenda_options = schema.List( title=u'Agenda options',
                                        required=False,
                                        value_type=schema.Choice(
                                        vocabulary='Agenda Options'),)
        motion_options = schema.List( title=u'Motion options',
                                        required=False,
                                        value_type=schema.Choice(
                                        vocabulary='Motion Options'),)
        question_options = schema.List( title=u'Question options',
                                          required=False,
                                          value_type=schema.Choice(
                                          vocabulary='Question Options'),)
        tabled_document_options = schema.List( title=u'Tabled Document options',
                                          required=False,
                                          value_type=schema.Choice(
                                          vocabulary='Tabled Document Options'),)
        note = schema.TextLine( title = u'Note',
                                required=False,
                                description=u'Optional note regarding this report'
                        )
        draft = schema.Choice(
                    title = _(u"Include draft sittings"),
                    description = _(u"Whether or not to include sittings still in draft"),
                    values= ['Yes',
                             'No'],
                    required=True
                    )
    template = namedtemplate.NamedTemplate('alchemist.form')
    form_fields = form.Fields(IReportingForm)
    form_fields['item_types'].custom_widget = horizontalMultiCheckBoxWidget
    form_fields['date'].custom_widget = SelectDateWidget
    form_fields['bill_options'].custom_widget = verticalMultiCheckBoxWidget
    form_fields['agenda_options'].custom_widget = verticalMultiCheckBoxWidget
    form_fields['motion_options'].custom_widget = verticalMultiCheckBoxWidget
    form_fields['question_options'].custom_widget = verticalMultiCheckBoxWidget
    form_fields['tabled_document_options'].custom_widget = verticalMultiCheckBoxWidget
    odf_filename = None
        
    class IReportingForm2(interface.Interface):
        
        item_types = schema.List(title=u'Items to include',
                   required=False,
                   value_type=schema.Choice(
                    vocabulary="Available Items"),
                   )
        bill_options = schema.List( title=u'Bill options',
                       required=False,
                       value_type=schema.Choice(
                       vocabulary='Bill Options'),
                         )
        agenda_options = schema.List( title=u'Agenda options',
                                        required=False,
                                        value_type=schema.Choice(
                                        vocabulary='Agenda Options'),)
        motion_options = schema.List( title=u'Motion options',
                                        required=False,
                                        value_type=schema.Choice(
                                        vocabulary='Motion Options'),)
        question_options = schema.List( title=u'Question options',
                                          required=False,
                                          value_type=schema.Choice(
                                          vocabulary='Question Options'),)
        tabled_document_options = schema.List( title=u'Tabled Document options',
                                          required=False,
                                          value_type=schema.Choice(
                                          vocabulary='Tabled Document Options'),)
        note = schema.TextLine( title = u'Note',
                                required=False,
                                description=u'Optional note regarding this report'
                        )
                        
    template = namedtemplate.NamedTemplate('alchemist.form')
    form_fields2 = form.Fields(IReportingForm2)
    form_fields2['item_types'].custom_widget = horizontalMultiCheckBoxWidget
    form_fields2['bill_options'].custom_widget = verticalMultiCheckBoxWidget
    form_fields2['agenda_options'].custom_widget = verticalMultiCheckBoxWidget
    form_fields2['motion_options'].custom_widget = verticalMultiCheckBoxWidget
    form_fields2['question_options'].custom_widget = verticalMultiCheckBoxWidget
    form_fields2['tabled_document_options'].custom_widget = verticalMultiCheckBoxWidget
    
   
    def setUpWidgets(self, ignore_request=False):
        if IGroupSitting.providedBy(self.context):
            class context:
                item_types = 'Bills'
                bill_options = 'Title'
                agenda_options = 'Title'
                question_options = 'Title'
                motion_options = 'Title'
                tabled_document_options = 'Title'
                note = None
            self.adapters = {
                    self.IReportingForm2: context
                }
            self.widgets = form.setUpEditWidgets(
                    self.form_fields2, self.prefix, self.context, self.request,
                    adapters=self.adapters, ignore_request=ignore_request)
        elif ISchedulingContext.providedBy(self.context):
            class context:
                date = self.date or datetime.date.today()
                #time_span = TIME_SPAN.daily
                doc_type = 'Order of the day'
                item_types = 'Bills'
                bill_options = 'Title'
                agenda_options = 'Title'
                question_options = 'Title'
                motion_options = 'Title'
                tabled_document_options = 'Title'
                note = None
                draft = 'No'
            self.adapters = {
                    self.IReportingForm: context
                }
            self.widgets = form.setUpEditWidgets(
                self.form_fields, self.prefix, self.context, self.request,
                adapters=self.adapters, ignore_request=ignore_request)
        else:
            raise NotImplementedError
        
        

    def update(self):
        self.status = self.request.get('portal_status_message', '')
        super(ReportingView, self).update()
        set_widget_errors(self.widgets, self.errors)

    def validate(self, action, data):
        errors = super(ReportingView, self).validate(action, data)
        time_span = TIME_SPAN.daily
        if 'doc_type' in data:
            if data['doc_type'] == "Order of the day":
                time_span = TIME_SPAN.daily
            elif data['doc_type'] == "Proceedings of the day":
                time_span = TIME_SPAN.daily
            elif data['doc_type'] == "Weekly Business":
                time_span = TIME_SPAN.weekly
            elif data['doc_type'] == "Questions of the week":
                time_span = TIME_SPAN.weekly
       
        if 'date' in data:
            start_date = data['date']
        else:
            start_date = self.date
        end_date = self.get_end_date(start_date, time_span)

        parliament = queries.get_parliament_by_date_range(self, start_date, end_date)
        session = queries.get_session_by_date_range(self, start_date, end_date)

        if parliament is None:
            errors.append(interface.Invalid(
                _(u"A parliament must be active in the period"),
                "date"))
        #elif session is None:
        #    errors.append(interface.Invalid(
        #        _(u"A session must be active in the period."),
        #        "date"))

        return errors
    
    def process_form(self, data):
        if 'date' in data:
            self.start_date = data['date']
        else:
            self.start_date = self.date
        time_span = TIME_SPAN.daily 
        if 'doc_type' in data:
            self.doc_type = data['doc_type']
        else:
            if self.display_minutes: 
                self.doc_type = "Proceedings of the day"
            else:
                self.doc_type =  "Order of the day"
        if self.doc_type == "Order of the day":
            time_span = TIME_SPAN.daily
        elif self.doc_type == "Weekly Business":
            time_span = TIME_SPAN.weekly
        elif self.doc_type == "Questions of the week":
            time_span = TIME_SPAN.weekly
        elif self.doc_type == "Proceedings of the day":
            time_span = TIME_SPAN.daily
        self.end_date = self.get_end_date(self.start_date, time_span)
        #Hack:Check if called on scheduling page or sitting page. todo : fix this
        if 'date' in data:
            self.sitting_items = self.get_sittings_items(self.start_date, self.end_date)
            self.single="False"
        else:
            session = Session()
            self.sitting_items = []
            st = self.context.sitting_id
            sitting = session.query(domain.GroupSitting).get(st)
            self.sitting_items.append(sitting)
            self.single="True"
        self.item_types = data['item_types']
        self.bill = False
        self.motion = False
        self.agenda = False
        self.question = False
        self.tabled_document = False
        self.bill_options = data['bill_options']
        self.agenda_options = data['agenda_options']
        self.motion_options = data['motion_options']
        self.question_options = data['question_options']
        self.note = data['note']
        self.tabled_document_options = data['tabled_document_options']
        for type in self.item_types:
            if type == 'Bills':
                self.bill_title = False
                self.bill_summary = False
                self.bill_text = False
                self.bill_owner = False
                self.bill_cosignatories = False
                for option in self.bill_options:
                    if option == 'Title':
                        self.bill_title = True
                    elif option == 'Summary':
                        self.bill_summary = True
                    elif option == 'Text':
                        self.bill_text = True
                    elif option == 'Owner':
                        self.bill_owner = True
                    elif option == 'Cosignatories':
                        self.bill_cosignatories = True
                self.bill = True
            elif type == 'Motions':
                self.motion_title = False
                self.motion_number = False
                self.motion_text = False
                self.motion_owner = False
                for option in self.motion_options:
                    if option == 'Title':
                        self.motion_title = True
                    elif option == 'Number':
                        self.motion_number = True
                    elif option == 'Text':
                        self.motion_text = True
                    elif option == 'Owner':
                        self.motion_owner = True
                self.motion = True
            elif type == 'Agenda Items':
                self.agenda_title = False
                self.agenda_text = False
                self.agenda_owner = False
                for option in self.agenda_options:
                    if option == 'Title':
                        self.agenda_title = True
                    elif option == 'Text':
                        self.agenda_text = True
                    elif option == 'Owner':
                        self.agenda_owner = True
                self.agenda = True
            elif type == 'Tabled Documents':
                self.tabled_document_title = False
                self.tabled_document_text = False
                self.tabled_document_owner = False
                self.tabled_document_number = False
                for option in self.tabled_document_options:
                    if option == 'Title':
                        self.tabled_document_title = True
                    elif option == 'Text':
                        self.tabled_document_text = True
                    elif option == 'Owner':
                        self.tabled_document_owner = True
                    elif option == 'Number':
                        self.tabled_document_number = True
                self.tabled_document = True
            elif type == 'Questions':
                self.question_title = False
                self.question_number = False
                self.question_text = False
                self.question_owner = False
                #self.question_response = False
                self.question_type = False
                for option in self.question_options:
                    if option == 'Title':
                        self.question_title = True
                    elif option == 'Number':
                        self.question_number = True
                    elif option == 'Text':
                        self.question_text = True
                    elif option == 'Owner':
                        self.question_owner = True
                    #elif option == 'Response':
                    #    self.question_response = True
                    elif option == 'Type':
                        self.question_type = True
                self.question = True
        #import pdb; pdb.set_trace()
        '''for item in self.sitting_items:
            if item.item_schedule.item.type in item_types:
                opt = item.type + '_option'
                for option in data[opt]:
                    item.options[option] = True
            else:
                self.sitting_items.remove(item) '''
        '''if self.display_minutes:
            if data['draft'] == 'No':
                for sitting in self.sitting_items:
                    items = []
                    for item in sitting.item_schedule:
                        if item.item_status not in ["draft"]:
                            items.append(item)
                    sitting.item_schedule = items'''
        if "draft" in data:
            sitting_items = []
            for sitting in self.sitting_items:
                if data["draft"]=="No":
                    if sitting.status in get_states("groupsitting", 
                                                tagged=["published"]):
                        sitting_items.append(sitting)
                elif data["draft"]=="Yes":
                    if sitting.status in get_states("groupsitting", 
                                                tagged=["draft", "published"]):
                        sitting_items.append(sitting)
            self.sitting_items = sitting_items
        if self.display_minutes:
            self.link = ui_url.absoluteURL(self.context, self.request)+'/votes-and-proceedings'
        else :
            self.link = ui_url.absoluteURL(self.context, self.request)+'/agenda'
        try:
            self.group = self.context.get_group()
        except:
            session = Session()
            self.group = session.query(domain.Group).get(self.context.group_id)
        if IGroupSitting.providedBy(self.context):
            self.back_link = ui_url.absoluteURL(self.context, self.request)  + '/schedule'
        elif ISchedulingContext.providedBy(self.context):
            self.back_link = ui_url.absoluteURL(self.context, self.request)
            
    
        
    @form.action(_(u"Preview"))
    def handle_preview(self, action, data):
        self.process_form(data)
        #import pdb; pdb.set_trace()
        self.save_link = ui_url.absoluteURL(self.context, self.request)+"/save_report"
        self.body_text = self.result_template()
        #import pdb; pdb.set_trace()
        return self.main_result_template()


    def get_end_date(self, start_date, time_span):
        if time_span is TIME_SPAN.daily:
            return start_date + timedelta(days=1)
        elif time_span is TIME_SPAN.weekly:
            return start_date + timedelta(weeks=1)
        
        raise RuntimeError("Unknown time span: %s" % time_span)



class AgendaReportingView(ReportingView):
    """Agenda report"""
    
    form_name = _(u"Agenda")
    report_name = _(u"ORDER OF THE DAY")
    form_description = _(u"This form generates the agenda report")
    odf_filename = "agenda.odt"
    display_minutes = False
    main_result_template = ViewPageTemplateFile('main_reports.pt')
    result_template = ViewPageTemplateFile('reports.pt')
    
    
    def get_sittings_items(self, start, end):
            """ return the sittings with scheduled items for 
                the given daterange"""
            session = Session()
            query = session.query(domain.GroupSitting).filter(
                sql.and_(
                    domain.GroupSitting.start_date.between(start,end),
                    domain.GroupSitting.group_id == self.context.group_id)
                    ).order_by(domain.GroupSitting.start_date
                    ).options(
                        eagerload('sitting_type'),
                        eagerload('item_schedule'), 
                        eagerload('item_schedule.item'),
                        eagerload('item_schedule.discussion'),
                        eagerload('item_schedule.category'))
            items = query.all()
        #items.sort(key=operator.attrgetter('start_date'))
            for item in items:
                if self.display_minutes:
                    item.item_schedule.sort(key=operator.attrgetter('real_order'))
                else:
                    item.item_schedule.sort(key=operator.attrgetter('planned_order'))
                    item.sitting_type.sitting_type = item.sitting_type.sitting_type.capitalize() 
                    #s = queries.get_session_by_date_range(self, item.start_date, item.end_date)
                
            return items
            
class VotesAndProceedingsReportingView(AgendaReportingView):
    form_name = _(u"Votes and proceedings")
    form_description = _(u"This form generates the “votes and proceedings” report")
    report_name = _(u"VOTES AND PROCEEDINGS")
    display_minutes = True

class DhtmlxCalendarSittingsEdit(BrowserView):
    '''Add, edit or delete sitting from calendar'''
    def __init__(self, context, request):
        super(DhtmlxCalendarSittingsEdit, self).__init__(
            ISchedulingContext(context), request)
        interface.alsoProvides(self.context, ILocation)
        interface.alsoProvides(self.context, IDCDescriptiveProperties)

    def generate_recurrence_dates(self, recurrence_start_date, recurrence_end_date, recurrence_type):
        '''This function generates the sitting recurrence dates 
        based on the input from dhtmlxscheduler
        to know more http://docs.dhtmlx.com/doku.php?id=dhtmlxscheduler:recurring_events
        '''
        rec_args = recurrence_type.split("_")
        #rec_type - type of repeating “day”,”week”,”month”,”year”
        rec_type = rec_args[0]
        #count - how much intervals of “type” come between events
        count  = rec_args[1]
        #count2 and day - used to define day of month ( first Monday, third Friday, etc )
        day = rec_args[2]
        count2 = rec_args[3]
        #days - comma separated list of affected week days
        days = rec_args[4].split("#")[0]
        #extra - extra info
        extra  = rec_args[4].split("#")[1]
        rrule_count = None
        if (extra != "no") and (extra != ""):
            try:
                rrule_count = int(extra)
            except TypeError:
                rrule_count = None
        freq_map = {"day":DAILY,"week":WEEKLY,"month":MONTHLY,"year":YEARLY}
        freq = freq_map[rec_type]
        if count != "":
            interval = int(count)
        else:
            interval = 1
        byweekday=None
        day_map = {0:SU,1:MO,2:TU,3:WE,4:TU,5:FR,6:SA}
        if (count2 != "") and (day != ""):    
            byweekday = day_map[int(day)](+int(count2))
        elif (days != ""):
            byweekday = map(int,days.split(","))
        if rrule_count is not None:
            if byweekday is not None:
                return list(rrule(freq, dtstart=recurrence_start_date, until=recurrence_end_date, count=rrule_count, byweekday=byweekday, interval=interval))  
            else:
                return list(rrule(freq, dtstart=recurrence_start_date, until=recurrence_end_date, count=rrule_count, interval=interval))
        else:
            if byweekday is not None:
                return list(rrule(freq, dtstart=recurrence_start_date, until=recurrence_end_date, byweekday=byweekday, interval=interval))  
            else:
                return list(rrule(freq, dtstart=recurrence_start_date, until=recurrence_end_date, interval=interval))
    def __call__(self):
        ids = self.request.form['ids']
        action = self.request.form[ids+"_!nativeeditor_status"]
        session = Session()
        sitting = domain.GroupSitting()
        trusted = removeSecurityProxy(self.context)
        sitting.group_id = trusted.group_id
        group = session.query(domain.Group).get(trusted.group_id)
        if action == "inserted":
            if (ids+"_rec_type" not in self.request.form.keys()) or (self.request.form[ids+"_rec_type"] == ""):
                sitting.start_date = datetime.datetime.strptime(self.request.form[ids+"_start_date"], '%Y-%m-%d %H:%M')
                sitting.end_date = datetime.datetime.strptime(self.request.form[ids+"_end_date"], '%Y-%m-%d %H:%M')
                sitting.sitting_type_id = self.request.form[ids+"_type"]
                sitting.status = None
                if ids+"_type" in self.request.form.keys():
                    sitting.sitting_type_id = self.request.form[ids+"_type"]
                if ids+"_language" in self.request.form.keys():
                    sitting.language = self.request.form[ids+"_language"]
                if ids+"_venue" in self.request.form.keys():
                    sitting.venue_id = self.request.form[ids+"_venue"]
                session.add(sitting)
                notify(ObjectCreatedEvent(sitting))
                session.commit()
                self.request.response.setHeader('Content-type', 'text/xml')
                return '<data><action type="inserted" sid="'+str(ids)+'" tid="'+str(sitting.sitting_id)+'" /></data>'
            else:
                try:
                    recurrence_start_date = datetime.datetime.strptime(self.request.form[ids+"_start_date"], '%Y-%m-%d %H:%M')
                    recurrence_end_date = datetime.datetime.strptime(self.request.form[ids+"_end_date"], '%Y-%m-%d %H:%M')
                except:
                    print "Date is not in the correct format"
                year = timedelta(days=365)
                #max end date is one year from now or end_date of the group which is sooner
                if (group is not None) and (group.end_date is not None):
                    if (datetime.datetime.now() + year) < group.end_date:
                        end = datetime.datetime.now() + year 
                    else:
                        end = group.end_date
                    if recurrence_end_date > end:
                        recurrence_end_date = end 
                else:
                    if recurrence_end_date > (datetime.datetime.now() + year):
                        recurrence_end_date = datetime.datetime.now() + year
                recurrence_type = self.request.form[ids+"_rec_type"]
                length = self.request.form[ids+"_event_length"]
                sitting_length = timedelta(seconds=int(length))
                dates = self.generate_recurrence_dates(recurrence_start_date, recurrence_end_date, recurrence_type)
                output = '<data>'
                for date in dates:
                    sitting = domain.GroupSitting()
                    sitting.group_id = trusted.group_id
                    sitting.start_date = date
                    sitting.end_date = date + sitting_length
                    sitting.sitting_type_id = self.request.form[ids+"_type"]
                    sitting.status = None
                    if ids+"_type" in self.request.form.keys():
                        sitting.sitting_type_id = self.request.form[ids+"_type"]
                    if ids+"_language" in self.request.form.keys():
                        sitting.language = self.request.form[ids+"_language"]
                    if ids+"_venue" in self.request.form.keys():
                        sitting.venue_id = self.request.form[ids+"_venue"]
                    session.add(sitting)
                    notify(ObjectCreatedEvent(sitting))
                    output = output+'<action type="inserted" sid="'+str(ids)+'" tid="'+str(sitting.sitting_id)+'" />'
                session.commit()
                output = output + '</data>'
                self.request.response.setHeader('Content-type', 'text/xml')
                return output
        elif action == "updated":
            sitting = session.query(domain.GroupSitting).get(ids)
            sitting.start_date = self.request.form[ids+"_start_date"]
            sitting.end_date = self.request.form[ids+"_end_date"]
            if ids+"_type" in self.request.form.keys():
                sitting.sitting_type_id = self.request.form[ids+"_type"]
            if ids+"_language" in self.request.form.keys():
                sitting.language = self.request.form[ids+"_language"]
            if ids+"_venue" in self.request.form.keys():
                sitting.venue_id = self.request.form[ids+"_venue"]
            session.update(sitting)
            session.commit()
            self.request.response.setHeader('Content-type', 'text/xml')
            return '<data><action type="updated" sid="'+str(ids)+'" tid="'+str(sitting.sitting_id)+'" /></data>'
        elif action == "deleted":
            sitting = session.query(domain.GroupSitting).get(ids)
            session.delete(sitting)
            session.commit()
            self.request.response.setHeader('Content-type', 'text/xml')
            return '<data><action type="deleted" sid="'+str(ids)+'" tid="'+str(sitting.sitting_id)+'" /></data>'
      

                          
class DhtmlxCalendarSittings(BrowserView):
    
    interface.implements(IStructuralView)
    
    template = ViewPageTemplateFile('dhtmlxcalendarxml.pt')
    def __init__(self, context, request):
        super(DhtmlxCalendarSittings, self).__init__(
            ISchedulingContext(context), request)
        self.context.__name__ = self.__name__
        interface.alsoProvides(self.context, ILocation)
        interface.alsoProvides(self.context, IDCDescriptiveProperties)
        self.__parent__ = context
               
                          
    def __call__(self):
        '''date = utils.datetimedict.fromdate(datetime.date.today())
        date = date - timedelta(days=date.weekday())
        days = tuple(date + timedelta(days=d) for d in range(7))
        sittings = self.context.get_sittings(
            start_date=date,
            end_date=days[-1],
            )'''
        try:
            date = self.request.get('from')
            dateobj = datetime.datetime(*time.strptime(date, "%Y-%m-%d")[0:5])
            start_date = utils.datetimedict.fromdate(dateobj)
        except:
            start_date = None
            
        try:
            date = self.request.get('to')
            dateobj = datetime.datetime(*time.strptime(date, "%Y-%m-%d")[0:5])
            end_date = utils.datetimedict.fromdate(dateobj)
        except:
            end_date = None
        
        if start_date is None:
            start_date = utils.datetimedict.fromdate(datetime.date.today())
            days = tuple(start_date + timedelta(days=d) for d in range(7))
            end_date = days[-1]
        elif end_date is None:
            start_date = utils.datetimedict.fromdate(datetime.date.today())
            days = tuple(start_date + timedelta(days=d) for d in range(7))
            end_date = days[-1]
        sittings = self.context.get_sittings(
            start_date,
            end_date,
            )
        self.sittings = []
        for sitting in sittings.values():
            if checkPermission("zope.View", sitting):
                trusted = removeSecurityProxy(sitting)
                self.sittings.append(trusted)
        self.request.response.setHeader('Content-type', 'text/xml')
        return self.render()
        #return super(DhtmlxCalendarSittings, self).__call__() 
        
    def render(self, template = None):
        return self.template()
        
        
class SaveView(AgendaReportingView):
    def __call__(self):
        body_text = self.request.form['body_text']
        session = Session()
        report = domain.Report()
        start_date = self.request.form['start_date']
        end_date = self.request.form['end_date']
        report.start_date = start_date
        report.end_date = end_date
        report.created_date = datetime.datetime.now()
        report.note = self.request.form['note']
        report.report_type = self.request.form['report_type']
        report.body_text = body_text
        report.user_id = get_principal_id()
        report.group_id = self.context.group_id
        report.language = "en"
        session.add(report)
        
        
        if self.request.form['single']=="False":
            self.sitting_items = self.get_sittings_items(start_date, end_date)
        else:
            self.sitting_items = []
            st = self.context.sitting_id
            sitting = session.query(domain.GroupSitting).get(st)
            self.sitting_items.append(sitting)
        
        for sitting in self.sitting_items:
            sr = domain.SittingReport()
            sr.report = report
            sr.sitting = sitting
            session.add(sr)
        session.flush()
        
        rpm = zope.securitypolicy.interfaces.IRolePermissionMap( report )
        rpm.grantPermissionToRole( u'zope.View', 'bungeni.Anybody' )
        
        
        if IGroupSitting.providedBy(self.context):
            back_link =  './schedule'
        elif ISchedulingContext.providedBy(self.context):
            back_link = './'
        else:
            raise NotImplementedError
        self.request.response.redirect(back_link) 
                                            
                    
class StoreReportView(BrowserView):
    template = ViewPageTemplateFile('save-reports.pt')
          
    def __call__(self):
        date = datetime.datetime.strptime(self.request.form['date'],
                '%Y-%m-%d').date()
        self.display_minutes = (self.request.form['display_minutes'] == "True")
        time_span = self.request.form['time_span']
        if time_span == TIME_SPAN.daily:
            time_span = TIME_SPAN.daily
        elif time_span == TIME_SPAN.weekly:
            time_span = TIME_SPAN.weekly
        end = self.get_end_date(date, time_span)
        body_text = super(StoreReportView, self).__call__()
        sitting_items = []
        for sitting in self.sitting_items:
            if self.display_minutes:
                if sitting.status in ["published_minutes"]:
                    sitting_items.append(sitting)
            else:
                if sitting.status in ["published_agenda", "draft_minutes", 
                                      "published_minutes"]:
                    sitting_items.append(sitting)
        if len(sitting_items) == 0:
            referer = self.request.getHeader('HTTP_REFERER')
            if referer:
                referer=referer.split('?')[0]
            else:
                referer = ""
            self.request.response.redirect(referer + "?portal_status_message=No data found")
            return
        self.sitting_items = sitting_items
        session = Session()
        report = domain.Report()
        report.start_date = date
        report.end_date = end
        report.created_date = datetime.datetime.now()
        if self.display_minutes:
            report.report_type = 'minutes'
        else:
            report.report_type = 'agenda'
        report.body_text = body_text
        report.user_id = get_principal_id()
        report.group_id = self.group.group_id
        session.add(report)
        for sitting in self.sitting_items:
            sr = domain.SittingReport()
            sr.report = report
            sr.sitting = sitting
            session.add(sr)
        session.flush()

        rpm = zope.securitypolicy.interfaces.IRolePermissionMap( report )
        rpm.grantPermissionToRole( u'zope.View', 'bungeni.Anybody' )
        
        if IGroupSitting.providedBy(self.context):
            back_link = ui_url.absoluteURL(self.context, self.request)  + '/schedule'
        elif ISchedulingContext.providedBy(self.context):
            back_link = ui_url.absoluteURL(self.context, self.request)
        else:
            raise NotImplementedError
        self.request.response.redirect(back_link)
        session.close()
