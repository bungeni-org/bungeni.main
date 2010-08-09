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
        
        

