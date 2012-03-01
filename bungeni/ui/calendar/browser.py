# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Calendar and Scheduling Browser and datasource Views

$Id$
"""

log = __import__("logging").getLogger("bungeni.ui.calendar")

import time
import datetime
timedelta = datetime.timedelta

try:
    import json
except ImportError:
    import simplejson as json

from zope.event import notify
from zope.lifecycleevent import (ObjectCreatedEvent, ObjectModifiedEvent, 
    ObjectRemovedEvent
)
from zope import interface
from zope import component
from zope.location.interfaces import ILocation
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.browser import BrowserView
from zope.browsermenu.interfaces import IBrowserMenu
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy
from zope.security.proxy import ProxyFactory
from zope.security import checkPermission
from zope.formlib import form
from zope import schema
from zope.schema.interfaces import IChoice
from zc.resourcelibrary import need

from bungeni.core.location import location_wrapped
from bungeni.core.interfaces import ISchedulingContext
from bungeni.core.schedule import SittingContainerSchedulingContext
from bungeni.core.workflow.interfaces import (IWorkflow, 
    IWorkflowController, InvalidTransitionError
)
from bungeni.core.language import get_default_language
from bungeni.core.translation import translate_i18n

from ploned.ui.interfaces import IStructuralView
from bungeni.ui.browser import BungeniBrowserView
from bungeni.ui.calendar import utils, config, interfaces, data
from bungeni.ui.i18n import _
from bungeni.ui.utils import misc, url, debug, date
from bungeni.ui.menu import get_actions
from bungeni.ui.interfaces import IBusinessSectionLayer
from bungeni.ui.widgets import LanguageLookupWidget
from bungeni.ui.container import ContainerJSONListing

from bungeni.models import domain
from bungeni.models.interfaces import IItemScheduleContainer
from bungeni.alchemist.container import stringKey
from bungeni.alchemist import Session
#from bungeni.ui import vocabulary

from bungeni.utils import register

# Filter key names prefix - for available items listings
FILTER_PREFIX = "filter_"

class TIME_SPAN:
    daily = _(u"Daily")
    weekly = _(u"Weekly")

class EventPartialForm(object):
    """Partial form for event entry form
    """
    form_fields = form.Fields(interfaces.IEventPartial)
    form_fields['select_sitting_lang'].custom_widget = LanguageLookupWidget

    def __init__(self, context, request):
        self.context = context
        self.request = request
    
    def get_widgets(self):
        widgets = form.setUpWidgets(self.form_fields, '', self.context, 
            self.request, ignore_request=True
        )
        for widget in widgets:
            if IChoice.providedBy(widget.context):
                if widget.context.default is None:
                    widget._messageNoValue = _(u"event_form_field_default",
                        default=u"choose ${event_field_title}",
                        mapping={'event_field_title': widget.context.title}
                    )
            yield widget


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
    
    if (sitting.status in IWorkflow(sitting).get_state_ids(
            keys=["draft_agenda", "published_agenda"])
        ):
        order = "planned_order"
    else:
        order = "real_order"
    
    schedulings = map(
        removeSecurityProxy,
        sitting.items.batch(order_by=order, limit=None))
    for scheduling in schedulings:
        item = ProxyFactory(location_wrapped(scheduling.item, sitting))
       
        props = IDCDescriptiveProperties.providedBy(item) and item or \
                IDCDescriptiveProperties(item)

        discussions = tuple(scheduling.discussions.values())
        discussion = discussions and discussions[0] or None
        truncated_discussion = None
        if ((discussion is not None) 
           and (discussion.body_text is not None)):
            #truncate discussion to first hundred characters
            t_discussion = discussion.body_text[0:100]
            try:
                #truncate discussion to first two lines
                index = t_discussion.index("<br>")
                index2 = t_discussion.index("<br>", index+4)
                truncated_discussion = t_discussion[0:index2] + "..."
            except ValueError:
                truncated_discussion = t_discussion + "..."
        state_title = IWorkflow(item).get_state(item.status).title
        item = removeSecurityProxy(item)
        record = {
            'title': props.title,
            'description': props.description,
            'name': stringKey(scheduling),
            'status': item.status,
            'type': item.type.capitalize,
            'state_title': state_title,
            'heading': True if item.type == "heading" else False,
            #'category_id': scheduling.category_id,
            #'category': scheduling.category,
            'discussion': discussion,
            'truncated_discussion': truncated_discussion,
            'delete_url': "%s/delete" % url.absoluteURL(scheduling, request),
            'url': url.absoluteURL(item, request),
        }
        
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
        
        # !+ non-existant permission
        if checkPermission(u"bungeni.agendaitem.wf.schedule", proxied):
            link = "%s/schedule" % url.absoluteURL(sitting, request)
        else:
            link = url.absoluteURL(sitting, request)
        
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

class CalendarView(BungeniBrowserView):
    """Main calendar view."""

    interface.implements(IStructuralView)
    template = ViewPageTemplateFile("templates/dhtmlxcalendar.pt")
    macros_view = ViewPageTemplateFile("templates/calendar-macros.pt")
    short_name = _(u"Scheduling")
    
    def __init__(self, context, request):
        log.debug("CalendarView.__init__: %s" % (context))
        super(CalendarView, self).__init__(
            ISchedulingContext(context), request)
    
    def __call__(self, timestamp=None):
        log.debug("CalendarView.__call__: %s" % (self.context))
        trusted = removeSecurityProxy(self.context)
        trusted.__name__ = self.__name__
        interface.alsoProvides(trusted, ILocation)
        if (IBusinessSectionLayer.providedBy(self.request) and 
            isinstance(trusted, SittingContainerSchedulingContext)):
            self.url = url.absoluteURL(trusted.__parent__.__parent__, self.request)
        else:
            self.url = url.absoluteURL(trusted.__parent__, self.request)
        self.title = ISchedulingContext(self.context).label
        log.debug(debug.interfaces(self))
        log.debug(debug.location_stack(self))
        return self.render()
        
    def publishTraverse(self, request, name):
        traverser = component.getMultiAdapter(
            (self.context, request), IPublishTraverse)
        return traverser.publishTraverse(request, name)

    @property
    def calendar_macros(self):
        return self.macros_view.macros

    @property
    def partial_event_form(self):
        form = EventPartialForm(self.context, self.request)
        return form

    @property
    def venues_data(self):
        venues_vocabulary = component.queryUtility(
            schema.interfaces.IVocabularyFactory, "bungeni.vocabulary.Venues"
        )
        venue_list = [ {"key": venue.value, "label": venue.title}
            for venue in venues_vocabulary()
        ]
        return venue_list

    @property
    def ical_url(self):
        return u"/".join(
            [url.absoluteURL(self.context, self.request), "dhtmlxcalendar.ics"]
        )

    @property
    def calendar_js_globals(self):
        cal_globals = dict(
            ical_url=self.ical_url,
            view_url=self.url,
            venues_view_title=translate_i18n(_(u"Venues")),
            text_group=translate_i18n(_(u"Group")),
            text_start_date=translate_i18n(_(u"Start Date")),
            text_end_date=translate_i18n(_(u"End Date")),
            text_venue=translate_i18n(_(u"Venue")),
            text_activity_type=translate_i18n(_(u"Activity Type")),
            text_meeting_type=translate_i18n(_(u"Meeting Type")),
            text_convocation_type=translate_i18n(_(u"Convocation Type")),
            text_sitting=translate_i18n(_(u"Sitting")),
        )
        return """var cal_globals = %s;var venues_data=%s;""" %(
            json.dumps(cal_globals), json.dumps(self.venues_data)
        )

    def other_calendars(self):
        """A list of URLs to other calendars - Loaded when selected"""
        menu = menu=component.queryUtility(IBrowserMenu,"context_calendar")
        if menu is None:
            return []
        items = menu.getMenuItems(self.context, self.request)
        colors = utils.generate_event_colours(len(items))
        map(lambda item:item[1].update([("color", colors[item[0]])]),
            enumerate(items)
        )
        return items

    def render(self, template=None):
        need("dhtmlxscheduler")
        need("dhtmlxscheduler-recurring")
        need("dhtmlxscheduler-year-view")
        need("dhtmlxscheduler-week-agenda-view")
        need("dhtmlxscheduler-expand")
        need("bungeni-calendar-extensions")
        need("dhtmlxscheduler-timeline")
        need("dhtmlxscheduler-tooltip")
        need("dhtmlxscheduler-minical")
        need("dhtmlxscheduler-multisource")
        need("dhtmlxscheduler-collision")
        need("multi-calendar-actions")
        if template is None:
            template = self.template
        if (not checkPermission(u"bungeni.sitting.Add", self.context)) or \
            (IBusinessSectionLayer.providedBy(self.request)):
            self.edit = False
        else:
            self.edit = True
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

        calendar_url = url.absoluteURL(self.context.__parent__, self.request)
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

class ItemScheduleOrder(BrowserView):
    "Stores new order of schedule items"
    def __call__(self):
        obj = self.request.form['obj[]']
        session = Session()
        if self.context.status == "draft_agenda":
            for i in range(0,len(obj)):
                sch = session.query(domain.ItemSchedule).get(obj[i])
                setattr(sch, 'planned_order', i+1)
        elif self.context.status == "draft_minutes":
            for i in range(0,len(obj)):
                sch = session.query(domain.ItemSchedule).get(obj[i])
                setattr(sch, 'real_order', i+1)
        session.flush()

#
# Group Scheduler New YUI based Stack UI
#
RESOURCE_PERMISSION_MAP = (
    (["bungeni-schedule-discussions", "bungeni-schedule-available-items"], 
        "bungeni.sittingschedule.itemdiscussion.Edit"
    ),
    (["bungeni-schedule-editor"], "bungeni.sittingschedule.Edit"),
    (["bungeni-schedule-preview"], "bungeni.sitting.View"),
)
class GroupSittingScheduleView(BrowserView):
    
    template = ViewPageTemplateFile("templates/scheduler.pt")
    
    def __init__(self, context, request):
        super(GroupSittingScheduleView, self).__init__(context, request)
    
    def sitting_dates(self):
        date_formatter = date.getLocaleFormatter(self.request)
        time_formatter = date.getLocaleFormatter(self.request, "time", "short")
        delta = self.context.end_date - self.context.start_date
        if delta.days == 0:
            localized_start_date = "%s - %s" %(
                date_formatter.format(self.context.start_date),
                time_formatter.format(self.context.start_date)
            )
            localized_end_date = time_formatter.format(self.context.end_date)
        else:
            localized_start_date = "%s, %s" %(
                date_formatter.format(self.context.start_date),
                time_formatter.format(self.context.start_date)
            )
            localized_end_date = "%s, %s" %(
                date_formatter.format(self.context.end_date),
                time_formatter.format(self.context.end_date)
            )
            
        return _("${localized_start_date} to ${localized_end_date}",
            mapping = {
                "localized_start_date" : localized_start_date,
                "localized_end_date" : localized_end_date,
            }
        )
    
    def __call__(self):
        return self.render()
    
    def needed_resources(self):
        """Permission aware resource dependency generation.
        Determines what user interface is rendered for the sitting.
        See resource definitions in `bungeni.ui.resources` inside 
        `configure.zcml`.
        """
        needed = None
        for resource, permission in RESOURCE_PERMISSION_MAP:
            if checkPermission(permission, self.context):
                needed = resource
                break
        return needed
    
    def render(self):
        _needed = self.needed_resources()
        if len(_needed):
            map(need, _needed)
        return self.template()

@register.view(IItemScheduleContainer, name="jsonlisting-schedule",
    protect={"bungeni.sittingschedule.itemdiscussion.Edit": dict(
        attributes=["browserDefault", "__call__"]
    )}
)
class ScheduleJSONListing(ContainerJSONListing):
    """Returns JSON listing with expanded unlisted properties used in
    scheduling user interface setup
    """
    def _json_values(self, nodes):
        items = super(ScheduleJSONListing, self)._json_values(nodes)
        def add_wf_meta(enum):
            index, item = enum
            node = nodes[index]
            wfc = IWorkflowController(node.item, None)
            if wfc is None:
                return
            item["wf_state"] = translate_i18n(
                wfc.state_controller.get_state().title
            )
            item["wf_actions"] = [ 
                dict(
                    value=transition, 
                    text=translate_i18n(
                        wfc.workflow.get_transition(transition).title
                    )
                )
                for transition in wfc.getFireableTransitionIds()
            ]
        map(add_wf_meta, enumerate(items))
        return items

class SchedulableItemsJSON(BrowserView):
    
    def __init__(self, context, request):
        super(SchedulableItemsJSON, self).__init__(context, request)
    
    def get_json_items(self):
        item_type = self.request.form.get("type")
        item_filters = dict(
            [
                (filter_key[7:], self.request.form.get(filter_key)) 
                for filter_key in self.request.form.keys()
                if filter_key.startswith(FILTER_PREFIX)
            ]
        )
        if item_type is None:
            return '{"items":[]}'
        else:
            items_getter = data.SchedulableItemsGetter(self.context,
                item_type, item_filters=item_filters
            )
        return items_getter.as_json()
    
    def __call__(self):
        self.request.response.setHeader("Content-type", "application/json")
        return self.get_json_items()

class SittingCalendarView(CalendarView):
    """Sitting calendar view."""
    
    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)

class DhtmlxCalendarSittingsEdit(form.PageForm):
    """Form to add, edit or delete a sitting that works with
    DHTMLX scheduler"""
    
    #!+ CALENDAR(miano, dec-2010) Add recurrence to the model so that
    # sittings added as part of a recurrence can be modified as a part of that
    # recurrence a la google calendar.
    
    prefix = ""
    xml_template = ViewPageTemplateFile("templates/dhtmlxcalendar_edit_form.pt")
    template_data = []
    
    def __init__(self, context, request):
        #dhtmlxscheduler posts the field names prefixed with the id 
        #of the sitting, the code below removes the prefix and set the action to
        #be performed
        data = request.form
        for key in request.form.keys():
            t = key.partition("_")
            request.form[t[2]] = data[key]
        if "!nativeeditor_status" in request.form.keys():
            if request.form["!nativeeditor_status"] == "inserted":
                request.form["actions.insert"] = "insert"
            elif request.form["!nativeeditor_status"] == "updated":
                request.form["actions.update"] = "update"
            elif request.form["!nativeeditor_status"] == "deleted":
                request.form["actions.delete"] = "delete"
        super(DhtmlxCalendarSittingsEdit, self).__init__(context, request)
                  
    form_fields = form.Fields(interfaces.IDhtmlxCalendarSittingsEditForm)
    def setUpWidgets(self, ignore_request=False):
        class context:
            ids = None
            short_name = None
            start_date = None
            end_date = None
            location = None
            language = None
            venue = None
            rec_type = None
            event_length = None
            nativeeditor_status = None
            activity_type = None
            meeting_type = None
            convocation_type = None
        self.adapters = {
            interfaces.IDhtmlxCalendarSittingsEditForm: context
            }
        self.widgets = form.setUpEditWidgets(
            self.form_fields, "", self.context, self.request,
                    adapters=self.adapters, ignore_request=ignore_request) 
        
    def insert_sitting_failure_handler(self, action, data, errors):
        error_message = _(u"Unable to add a sitting. Please make corrections.")
        error_string = u""
        for error in errors:
            if error.message not in ('', None): 
                error_string += error.message + "\n"
            else:
                error_string += error.__str__() + "\n"
        #!+CALENDAR(mb, oct-2011) Include error messages in XML
        #return "%s \n%s" % (error_message, error_string)
        self.template_data.append(
            dict(action="invalid",
                ids=data["ids"],
                group_sitting_id=data["ids"]
            )
        )
        self.request.response.setHeader("Content-type", "text/xml")
        return self.xml_template()

    # The form action strings below do not need to be translated because they are 
    # not visible in the UI.      
    @form.action(u"insert", failure='insert_sitting_failure_handler')
    def handle_insert(self, action, data):
        session = Session()
        self.template_data = []
        trusted = removeSecurityProxy(ISchedulingContext(self.context))
        if ("rec_type" in data.keys()) and (data["rec_type"] is not None):
            # !+ DATETIME(miano, dec-2010) the datetime widget above returns
            # aware datetime objects while the current database setup only 
            # supports naive objects. The lines below(and in subsequent actions)
            # convert them to naive datetimes
            recurrence_start_date = data["start_date"].replace(tzinfo=None)
            recurrence_end_date = data["end_date"].replace(tzinfo=None)
            length = data["event_length"]
            sitting_length = timedelta(seconds=int(length))
            # 
            # Check the end date of the recurrence
            # The end date is set to be the end date of the current group 
            # or one year from the present date whichever is sooner.   
               
            group = trusted.get_group()
            # If group is none then there is a big problem
            assert group is not None    
            year = timedelta(days=365)
            now = datetime.datetime.now()                          
            if ((group.end_date is not None) and ((now + year) < group.end_date)) or (group.end_date is None):
                end = now + year 
            else:
                end = group.end_date
            if recurrence_end_date > end:
                recurrence_end_date = end 
            dates = utils.generate_recurrence_dates(recurrence_start_date, 
                                            recurrence_end_date, data["rec_type"])
            recurrent_sittings = []
            for date in dates:
                sitting = domain.GroupSitting()
                sitting.group_id = trusted.group_id
                sitting.short_name = data.get("short_name", None)
                sitting.start_date = date
                sitting.end_date = date + sitting_length
                sitting.language = data["language"]
                sitting.venue_id = data["venue"]
                sitting.activity_type = data.get("activity_type", None)
                sitting.meeting_type = data.get("meeting_type", None)
                sitting.convocation_type = data.get("convocation_type", None)
                session.add(sitting)
                recurrent_sittings.append(sitting)
            session.flush()
            for s in recurrent_sittings:    
                notify(ObjectCreatedEvent(s))
                self.template_data.append({"group_sitting_id": s.group_sitting_id, 
                                           "action": "inserted",
                                           "ids": data["ids"]})
            self.request.response.setHeader('Content-type', 'text/xml')
            return self.xml_template()
        else:
            sitting = domain.GroupSitting()
            sitting.short_name = data.get("short_name", None)
            sitting.start_date = data["start_date"].replace(tzinfo=None)
            sitting.end_date = data["end_date"].replace(tzinfo=None)
            sitting.group_id = trusted.group_id
            sitting.language = data["language"]
            sitting.venue_id = data["venue"]
            sitting.activity_type = data.get("activity_type", None)
            sitting.meeting_type = data.get("meeting_type", None)
            sitting.convocation_type = data.get("convocation_type", None)
            session.add(sitting)
            session.flush()
            notify(ObjectCreatedEvent(sitting))
            self.template_data.append({"group_sitting_id": sitting.group_sitting_id, 
                                       "action": "inserted",
                                       "ids": data["ids"]})
            self.request.response.setHeader('Content-type', 'text/xml')
            return self.xml_template()
          
    def update_sitting_failure_handler(self, action, data, errors):
        error_string = u""
        error_message = _(u"Error Updating Sitting")
        for error in errors:
            if error.message not in ('', None): 
                error_string += error.message + "\n"
            else:
                error_string += error.__str__() + "\n"  
        return "%s \n%s" % (error_message, error_string)   
        
    @form.action(u"update", failure='update_sitting_failure_handler')
    def handle_update(self, action, data):
        session = Session()
        self.template_data = []
        sitting = domain.GroupSitting()
        sitting = session.query(domain.GroupSitting).get(data["ids"])
        sitting.start_date = data["start_date"].replace(tzinfo=None)
        sitting.end_date = data["end_date"].replace(tzinfo=None)
        if "language" in data.keys():
            sitting.language = data["language"]
        if "venue" in data.keys():
            sitting.venue_id = data["venue"]
        sitting.short_name = data.get("short_name", None)
        sitting.activity_type = data.get("activity_type", None)
        sitting.meeting_type = data.get("meeting_type", None)
        sitting.convocation_type = data.get("convocation_type", None)
        # set extra data needed by template
        session.flush()
        notify(ObjectModifiedEvent(sitting))
        self.template_data.append({"group_sitting_id": sitting.group_sitting_id, 
                                    "action": "inserted",
                                    "ids": data["ids"]})
        session.flush()
        self.request.response.setHeader('Content-type', 'text/xml')
        return self.xml_template()
        
    def delete_sitting_failure_handler(self, action, data, errors):
        error_string = u""
        for error in errors:
            if error.message not in ('', None): 
                error_string += error.message + "\n"
            else:
                error_string += error.__str__() + "\n"  
        return "%s \n%s" % (error_message, error_string)  
        
    @form.action(u"delete", failure='delete_sitting_failure_handler')
    def handle_delete(self, action, data):
        session = Session()
        self.template_data = []
        sitting = session.query(domain.GroupSitting).get(data["ids"])
        # set extra data needed by template
        self.template_data = []
        if sitting is not None:
            self.request.response.setHeader('Content-type', 'text/xml')
            self.template_data.append({"group_sitting_id": sitting.group_sitting_id, 
                                       "action": "deleted",
                                       "ids": data["ids"]})
            session.delete(sitting)
            session.flush()
            return self.xml_template()

                          
class DhtmlxCalendarSittings(BrowserView):
    """This view returns xml of the sittings for the week and group 
    requested in a format acceptable by DHTMLX scheduler"""
    interface.implements(IStructuralView)
    
    content_mimetype = "text/xml"
    template = ViewPageTemplateFile('templates/dhtmlxcalendarxml.pt')

    def __init__(self, context, request):
        super(DhtmlxCalendarSittings, self).__init__(
            ISchedulingContext(context), request)
        self.context.__name__ = self.__name__
        interface.alsoProvides(self.context, ILocation)
        interface.alsoProvides(self.context, IDCDescriptiveProperties)
        self.__parent__ = context
    
    @property
    def event_colour(self):
        if not hasattr(self, "event_color"):
            rq_color = unicode(self.request.form.get("color", ""))
            assert len(rq_color) <= 6
            self._event_color = rq_color
        return self._event_color
    
    
    def __call__(self):
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
                trusted.text = dict(
                    sitting_status = _(
                        misc.get_wf_state(trusted, trusted.status)
                    )
                )
                self.sittings.append(trusted)
        self.request.response.setHeader('Content-type', self.content_mimetype)
        return self.render()
        
    def render(self, template = None):
        return self.template()



class DhtmlxCalendarSittingsIcal(DhtmlxCalendarSittings):
    """ICS rendering of events in the current calendar view
    """
    content_mimetype = "text/calendar"

    def render(self, template=None):
        """Render ICAL or send WWW-AUTHENTICATE Header
        
        See `bungeni.ui.errors.Unauthorized`
        """
        event_data_list = [ 
            config.ICAL_EVENT_TEMPLATE % dict(
                event_start=sitting.start_date.strftime("%Y%m%dT%H%M%S"),
                event_end=sitting.end_date.strftime("%Y%m%dT%H%M%S"),
                event_venue=(IDCDescriptiveProperties(sitting.venue).title if
                    hasattr(sitting, "venue") else u""
                ),
                event_summary=IDCDescriptiveProperties(sitting).verbose_title,
            )
            for sitting in self.sittings
        ]
        return config.ICAL_DOCUMENT_TEMPLATE % dict(
            event_data = u"\n".join(event_data_list)
        )

def getItemKey(s):
    return s.rstrip("/")

class ScheduleAddView(BrowserView):
    """Custom view to persist schedule items modified client side
    """
    RECORD_KEY = "%s:%d"
    messages = []
    def __init__(self, context, request):
        super(ScheduleAddView, self).__init__(context, request)
        self.sitting = self.context.__parent__
        self.data = json.loads(self.request.form.get("data", "[]"))

    def saveSchedule(self):
        session = Session()
        group_sitting_id = self.sitting.group_sitting_id
        group_id = self.sitting.group_id
        record_keys = []
        for (index, data_item_text) in enumerate(self.data):
            data_item = json.loads(data_item_text)
            actual_index = index + 1
            data_schedule_id = data_item.get("schedule_id")
            data_item_id = data_item.get("item_id")
            data_item_type = data_item.get("item_type")
            data_item_text = data_item.get("item_text")
            data_item_wf_status = data_item.get("wf_status")
            
            if not data_item_id:
                # create text record before inserting into schedule
                if data_item_type == u"text":
                    text_record = domain.ScheduleText(
                        text=data_item_text,
                        group_id=group_id,
                        language=get_default_language()
                    )
                    session.add(text_record)
                    session.flush()
                    notify(ObjectCreatedEvent(text_record))
                    data_item_id = text_record.schedule_text_id
                elif data_item_type == u"heading":
                    heading_record = domain.Heading(
                        text=data_item_text,
                        group_id=group_id,
                        language=get_default_language()
                    )
                    session.add(heading_record)
                    session.flush()
                    notify(ObjectCreatedEvent(heading_record))
                    data_item_id = heading_record.heading_id
                schedule_record = domain.ItemSchedule(
                    item_id=data_item_id,
                    item_type=data_item_type,
                    planned_order=actual_index,
                    group_sitting_id=group_sitting_id
                )
                session.add(schedule_record)
                session.flush()
                notify(ObjectCreatedEvent(schedule_record))
            else:
                if data_schedule_id:
                    current_record = removeSecurityProxy(
                        self.context.get(getItemKey(data_schedule_id))
                    )
                    current_record.planned_order = actual_index
                    session.add(current_record)
                    session.flush()
                    notify(ObjectModifiedEvent(current_record))
                    
                    #workflow operations
                    wfc = IWorkflowController(current_record.item, None)
                    if wfc:
                        if wfc and data_item_wf_status:
                            try:
                                wfc.workflow.get_transition(data_item_wf_status)
                                wfc.fireTransition(data_item_wf_status)
                            except InvalidTransitionError:
                                log.error(
                                    "Invalid transition [%s] for object: [%s] ",
                                    data_item_wf_status, current_record
                                )
                        wfc.fireAutomatic()
                    
                    #update text for text records
                    #!+INTERFACES(Apply this behaviour via shared interface)
                    if data_item_type in [u"text", u"heading"]:
                        text_record = removeSecurityProxy(current_record.item)
                        if text_record.text != data_item_text:
                            text_record.text = data_item_text
                            session.add(text_record)
                            session.flush()
                            notify(ObjectModifiedEvent(text_record))
                else:
                    schedule_record = domain.ItemSchedule(
                        item_id=data_item_id,
                        item_type=data_item_type,
                        planned_order=actual_index,
                        group_sitting_id=group_sitting_id
                    )
                    session.add(schedule_record)
                    session.flush()
                    notify(ObjectCreatedEvent(schedule_record))
            record_keys.append(self.RECORD_KEY % (data_item_type, data_item_id))
        
        records_to_delete = filter(
            lambda item:(self.RECORD_KEY % (item.item_type, item.item_id)
                not in record_keys
            ),
            [removeSecurityProxy(rec) for rec in self.context.values()]
        )
        map(session.delete, records_to_delete)
        map(lambda deleted:notify(ObjectRemovedEvent(deleted)), 
            records_to_delete
        )
        
    def __call__(self):
        self.request.response.setHeader("Content-type", "application/json")
        self.saveSchedule()
        return json.dumps(dict(messages=self.messages))

class DiscussionAddView(BrowserView):
    messages = []
    def __init__(self, context, request):
        super(DiscussionAddView, self).__init__(context, request)
        self.data = json.loads(self.request.form.get("data", "[]"))
    
    def saveDiscussions(self):
        session = Session()
        new_record_keys = []
        domain_model = removeSecurityProxy(self.context.domain_model)
        for record in self.data:
            discussion_text = record.get("body_text", "")
            object_id = record.get("object_id", None)
            if object_id:
                current_record = removeSecurityProxy(
                    self.context.get(getItemKey(object_id))
                )
                current_record.body_text = discussion_text
                session.add(current_record)
                session.flush()
                notify(ObjectModifiedEvent(current_record))
                new_record_keys.append(stringKey(current_record))
            else:
                new_record = domain_model(
                    body_text = discussion_text,
                    language = get_default_language()
                )
                new_record.scheduled_item = removeSecurityProxy(
                    self.context.__parent__
                )
                session.add(new_record)
                session.flush()
                notify(ObjectCreatedEvent(new_record))
                new_record_keys.append(stringKey(new_record))
        records_to_delete = [
            removeSecurityProxy(self.context.get(key))
            for key in self.context.keys() if key not in new_record_keys
        ]
        map(session.delete, records_to_delete)
        map(lambda deleted:notify(ObjectRemovedEvent(deleted)),
            records_to_delete
        )
    
    def __call__(self):
        self.request.response.setHeader("Content-type", "application/json")
        self.saveDiscussions()
        return json.dumps(dict(messages=self.messages))
