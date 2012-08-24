# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Calendar and Scheduling Browser and datasource Views

$Id$
"""

log = __import__("logging").getLogger("bungeni.ui.calendar")

import time
import random
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
from sqlalchemy.sql.expression import or_

from bungeni.core.location import location_wrapped
from bungeni.core.interfaces import ISchedulingContext
from bungeni.core.schedule import SittingContainerSchedulingContext
from bungeni.core.workflow.interfaces import (IWorkflow, 
    IWorkflowController, InvalidTransitionError
)
from bungeni.core.language import get_default_language
from bungeni.core.translation import translate_i18n

from ploned.ui.interfaces import IStructuralView
from bungeni.ui.interfaces import IBusinessSectionLayer
from bungeni.ui.browser import BungeniBrowserView
from bungeni.ui.calendar import utils, config, interfaces, data
from bungeni.ui.i18n import _
from bungeni.ui.utils import misc, url, debug, date
from bungeni.ui.menu import get_actions
from bungeni.ui.widgets import LanguageLookupWidget
from bungeni.ui.container import ContainerJSONListing
from bungeni.ui.forms.common import AddForm
from bungeni.ui.reporting import generators

from bungeni.models import domain
from bungeni.models import interfaces as model_interfaces
from bungeni.alchemist.container import stringKey
from bungeni.alchemist import Session
from bungeni.ui import vocabulary

from bungeni.utils import register
from bungeni.utils.capi import capi

# Filter key names prefix - for available items listings
FILTER_PREFIX = "filter_"

class TIME_SPAN:
    daily = _(u"Daily")
    weekly = _(u"Weekly")

class EventPartialForm(AddForm):
    """Partial form for event entry form
    """
    omit_fields = ["start_date", "end_date", "sitting_id", "group_id", "sitting_length","recurring_id","recurring_type","status","status_date"]
    
    def update_fields(self):
        # !+PERMISSIONS_ON_PARTIAL_CONTEXT(mr, aug-2012)
        # Using self.model_descriptor._mode_columns(mode) checks columns for
        # mode for current principal, but as we are dealing with a dummy sitting
        # instance as context, this will evaluate incorrectly... in particlar,
        # the call to self.model_descriptor._mode_columns("add") that is 
        # triggered when setting up the form_fields here in the standard way, 
        # will give strange results (since "add" localizable mode changes on 
        # certain fields that have been introduced since r9722.
        #
        # We could bypass the descriptor mechanism, by working with all fields,
        # i.e. something like:
        #from bungeni.alchemist.model import queryModelInterface
        #domain_interface = queryModelInterface(self.context.__class__)
        #self.form_fields = form.Fields(domain_interface)
        # but that means also deal with further filtering, order etc.
        # 
        # So, the field lookup fails when EventPartialForm is ANYWAY not needed 
        # in the first place! So, for now, we just ignore the error...
        #
        self.form_fields = self.form_fields.omit(*self.omit_fields)
        # /PERMISSIONS_ON_PARTIAL_CONTEXT
        try:
            self.form_fields["language"].edit_widget = LanguageLookupWidget
        except KeyError, e:
            # !+PERMISSIONS_ON_PARTIAL_CONTEXT "language" field not included... 
            # permission for tor this field in "add" mode has been denied for
            # current user!
            from bungeni.models.utils import get_principal_id
            log.error("!+PERMISSIONS_ON_PARTIAL_CONTEXT: user=%r error=%r" % (
                get_principal_id(), e))
        self.form_fields = self.form_fields.omit(*self.omit_fields)
    
    def get_widgets(self):
        self.update_fields()
        widgets = form.setUpWidgets(self.form_fields, "", self.context, 
            self.request, ignore_request=True
        )
        for widget in widgets:
            if IChoice.providedBy(widget.context):
                if widget.context.default is None:
                    widget._messageNoValue = _(u"event_form_field_default",
                        default=u"choose ${event_field_title}",
                        mapping={"event_field_title": widget.context.title}
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
           and (discussion.body is not None)):
            #truncate discussion to first hundred characters
            t_discussion = discussion.body[0:100]
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
            "title": props.title,
            "description": props.description,
            "name": stringKey(scheduling),
            "status": item.status,
            "type": item.type.capitalize,
            "state_title": state_title,
            "heading": True if item.type == "heading" else False,
            #"category_id": scheduling.category_id,
            #"category": scheduling.category,
            "discussion": discussion,
            "truncated_discussion": truncated_discussion,
            "delete_url": "%s/delete" % url.absoluteURL(scheduling, request),
            "url": url.absoluteURL(item, request),
        }
        
        if include_actions:
            record["actions"] = get_scheduling_actions(scheduling, request)
            record["workflow"] = get_workflow_actions(item, request)

            discussion_actions = get_discussion_actions(discussion, request)
            if discussion_actions:
                assert len(discussion_actions) == 1
                record["discussion_action"] = discussion_actions[0]
            else:
                record["discussion_action"] = None
        items.append(record)
    return items

def create_sittings_map(sittings, request):
    """Returns a dictionary that maps:

        (day, hour) -> {
            "record"   : sitting database record
            "actions"  : actions that apply to this sitting
            "class"    : sitting
            "span"     : span
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
        if checkPermission(u"bungeni.agenda_item.wf.schedule", proxied):
            link = "%s/schedule" % url.absoluteURL(sitting, request)
        else:
            link = url.absoluteURL(sitting, request)
        
        if checkPermission("zope.View", proxied):
            mapping[day, hour] = {
                "url": link,
                "record": sitting,
                "class": u"sitting",
                "actions": get_sitting_actions(sitting, request),
                "span": sitting.end_date.hour - sitting.start_date.hour,
                "formatted_start_time": start_date,
                "formatted_end_time": end_date,
                "status" : status,
            }
            for hour in range(sitting.start_date.hour+1, sitting.end_date.hour):
                mapping[day, hour] = None
        
        # make sure start- and end-date is the same DAY
        assert (sitting.start_date.day == sitting.end_date.day) and \
               (sitting.start_date.month == sitting.end_date.month) and \
               (sitting.start_date.year == sitting.end_date.year)

    return mapping


@register.view(model_interfaces.ISittingContainer, 
    layer=IBusinessSectionLayer, 
    name="index",
    protect=register.PROTECT_VIEW_PUBLIC)
class CalendarView(BungeniBrowserView):
    """Main calendar view."""

    interface.implements(IStructuralView)
    template = ViewPageTemplateFile("templates/dhtmlxcalendar.pt")
    macros_view = ViewPageTemplateFile("templates/calendar-macros.pt")
    short_name = _(u"Scheduling")
    
    def __init__(self, context, request):
        super(CalendarView, self).__init__(
            ISchedulingContext(context), request)
    
    def __call__(self, timestamp=None):
        trusted = removeSecurityProxy(self.context)
        trusted.__name__ = self.__name__
        interface.alsoProvides(trusted, ILocation)
        if (IBusinessSectionLayer.providedBy(self.request) and 
            isinstance(trusted, SittingContainerSchedulingContext)):
            self.url = url.absoluteURL(trusted.__parent__.__parent__, self.request)
        else:
            self.url = url.absoluteURL(trusted.__parent__, self.request)
        self.title = ISchedulingContext(self.context).label
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
        # !+PERMISSIONS_ON_PARTIAL_CONTEXT the sitting instance below is only
        # partially defined (e.g. no sitting_id, parliament_id, status), plus 
        # not being in any traversal context -- so checking of 
        # permissions/roles on it will give incorrect results.
        # 
        # But, in addition, for when the failure was happening, the instantiation
        # of EventPartialForm is ANYWAY not needed in the first place! 
        # I.e. should not be done when Member loads the calendar, as Member is 
        # categorically NOT allowed to add sittings, and so the context 
        # necessary to add sittings SHOULD not be made available in the 
        # first place. And, doing the (business logic) call to instantiate the 
        # EventPartialForm from within the UI template entangles 
        # buisness with UI logic...
        # 
        # So, the intent and the implementation of the business logic of why 
        # this form is instantiated may need to be reviewed...
        form = EventPartialForm(domain.Sitting(), self.request)
        return form

    @property
    def venues_data(self):
        venue_list = [ {"key": venue.value, "label": venue.title}
            for venue in vocabulary.venue_factory()
        ]
        return venue_list
    
    @property
    def groups_data(self):
        group_list = [ {"key": comm.committee_id, 
            "label": IDCDescriptiveProperties(comm).title}
            for comm in Session().query(domain.Committee).all()
            if comm.committee_id is not self.context.group_id
        ]
        return group_list        
    
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
            text_view=translate_i18n(_(u"View")),
        )
        return """var cal_globals = %s;
            var timeline_data = { venues: %s, committees: %s };
            var group_urls= %s;""" %(
            json.dumps(cal_globals), 
            json.dumps(self.venues_data),
            json.dumps(self.groups_data),
            json.dumps(self.calendar_urls())
        )

    def calendar_urls(self):
        """A list of URLs to other calendars - Loaded when selected"""
        menu = component.queryUtility(IBrowserMenu, "context_calendar")
        if menu is None:
            return []
        items = menu.getMenuItems(self.context, self.request)
        colors = utils.generate_event_colours(len(items))
        return [ { "url": item[1]["action"], "color": colors[item[0]] }
            for item in enumerate(items)
        ]

    def render(self, template=None):
        need("bungeni-calendar-bundle")
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
                "formatted": datetime.datetime.strftime(date, "%A %d"),
                "id": datetime.datetime.strftime(date, "%Y-%m-%d"),
                "today": date == today,
                "url": "%s/%d" % (calendar_url, date.totimestamp()),
                },
            hours=range(6,21),
            week_no=date.isocalendar()[1],
            week_day=date.weekday(),
            links={
                "previous": "%s/%d" % (
                    calendar_url, (date - timedelta(days=1)).totimestamp()),
                "next": "%s/%d" % (
                    calendar_url, (date + timedelta(days=1)).totimestamp()),
                },
            sittings_map = create_sittings_map(sittings, self.request),
            )

class ItemScheduleOrder(BrowserView):
    "Stores new order of schedule items"
    def __call__(self):
        obj = self.request.form["obj[]"]
        session = Session()
        if self.context.status == "draft_agenda":
            for i in range(0,len(obj)):
                sch = session.query(domain.ItemSchedule).get(obj[i])
                setattr(sch, "planned_order", i+1)
        elif self.context.status == "draft_minutes":
            for i in range(0,len(obj)):
                sch = session.query(domain.ItemSchedule).get(obj[i])
                setattr(sch, "real_order", i+1)
        session.flush()

#
# Group Scheduler New YUI based Stack UI
#
RESOURCE_PERMISSION_MAP = (
    (["bungeni-schedule-minutes"], "bungeni.sittingschedule.itemdiscussion.Edit"),
    (["bungeni-schedule-editor"], "bungeni.sittingschedule.Edit"),
    (["bungeni-schedule-preview"], "bungeni.sitting.View"),
)
class SittingScheduleView(BrowserView):
    
    template = ViewPageTemplateFile("templates/scheduler.pt")
    
    def __init__(self, context, request):
        super(SittingScheduleView, self).__init__(context, request)
    
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

@register.view(model_interfaces.IItemScheduleContainer, 
    name="jsonlisting-schedule",
    protect={"bungeni.sittingschedule.itemdiscussion.Edit": 
        register.VIEW_DEFAULT_ATTRS})
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
            #!+SCHEDULING_FILTERS(mb, mar-2012) Find a more elegant way to do this
            # perhaps as a workflow feature
            if not len(wfc.workflow.get_state_ids(keys=["draft"], restrict=False)):
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
            return """{"items":[]}"""
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
            event_pid = None
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
            if error.message not in ("", None): 
                error_string += error.message + "\n"
            else:
                error_string += error.__str__() + "\n"
        #!+CALENDAR(mb, oct-2011) Include error messages in XML
        #return "%s \n%s" % (error_message, error_string)
        self.template_data.append(
            dict(action="invalid", ids=data["ids"], sitting_id=data["ids"])
        )
        self.request.response.setHeader("Content-type", "text/xml")
        return self.xml_template()

    def generate_dates(self, data):
        trusted = removeSecurityProxy(ISchedulingContext(self.context))
        recurrence_start_date = data["start_date"].replace(tzinfo=None)
        recurrence_end_date = data["end_date"].replace(tzinfo=None)
        group = trusted.get_group()
        # If group is none then there is a big problem
        assert group is not None
        year = timedelta(days=365)
        now = datetime.datetime.now()                          
        if (((group.end_date is not None) and ((now + year) < group.end_date)) 
            or (group.end_date is None)):
            end = now + year 
        else:
            end = group.end_date
        if recurrence_end_date > end:
            recurrence_end_date = end 
        return utils.generate_recurrence_dates(recurrence_start_date, 
                                        recurrence_end_date, data["rec_type"])

    # The form action strings below do not need to be translated because they are 
    # not visible in the UI.      
    @form.action(u"insert", failure="insert_sitting_failure_handler")
    def handle_insert(self, action, data):
        session = Session()
        self.template_data = []
        trusted = removeSecurityProxy(ISchedulingContext(self.context))
        if ("rec_type" in data.keys()) and (data["rec_type"] not in [None, "none"]):
            # !+ DATETIME(miano, dec-2010) the datetime widget above returns
            # aware datetime objects while the current database setup only 
            # supports naive objects. The lines below(and in subsequent actions)
            # convert them to naive datetimes
            length = data["event_length"]
            sitting_length = timedelta(seconds=length)
            base_sitting_length = sitting_length + timedelta(hours=1)
            initial_sitting = None
            recurrent_sittings = []
            dates = self.generate_dates(data)
            for count, date in enumerate(dates):
                sitting = domain.Sitting()
                sitting.group_id = trusted.group_id
                sitting.short_name = data.get("short_name", None)
                sitting.start_date = date
                sitting.language = data["language"]
                sitting.venue_id = data["venue"]
                sitting.activity_type = data.get("activity_type", None)
                sitting.meeting_type = data.get("meeting_type", None)
                sitting.convocation_type = data.get("convocation_type", None)
                if not count:
                    sitting.end_date = dates[len(dates)-1] + base_sitting_length
                    sitting.recurring_type = data.get("rec_type")
                    sitting.recurring_id = 0
                    sitting.sitting_length = length
                    session.add(sitting)
                    session.flush()
                    initial_sitting = sitting
                else:
                    end_date = date + sitting_length
                    sitting.end_date = end_date
                    sitting.sitting_length = int(time.mktime(date.timetuple()))
                    sitting.recurring_id = initial_sitting.sitting_id
                    session.add(sitting)
                    recurrent_sittings.append(sitting)
            session.flush()
            for s in ([initial_sitting] + recurrent_sittings):
                notify(ObjectCreatedEvent(s))
                self.template_data.append({
                        "sitting_id": s.sitting_id, 
                        "action": "inserted",
                        "ids": data["ids"],
                    })
            self.request.response.setHeader("Content-type", "text/xml")
            return self.xml_template()
        else:
            sitting = domain.Sitting()
            sitting.short_name = data.get("short_name", None)
            sitting.start_date = data["start_date"].replace(tzinfo=None)
            sitting.end_date = data["end_date"].replace(tzinfo=None)
            sitting.recurring_type = data["rec_type"]
            sitting.sitting_length = data.get("event_length")
            sitting.recurring_id = data.get("event_pid")
            sitting.group_id = trusted.group_id
            sitting.language = data["language"]
            sitting.venue_id = data["venue"]
            sitting.activity_type = data.get("activity_type", None)
            sitting.meeting_type = data.get("meeting_type", None)
            sitting.convocation_type = data.get("convocation_type", None)
            session.add(sitting)
            session.flush()
            notify(ObjectCreatedEvent(sitting))
            sitting_action = "inserted"
            if data["rec_type"] == "none":
                sitting_action = "deleted"
            self.template_data.append({
                    "sitting_id": sitting.sitting_id, 
                    "action": sitting_action,
                    "ids": data["ids"],
                })
            self.request.response.setHeader("Content-type", "text/xml")
            return self.xml_template()
          
    def update_sitting_failure_handler(self, action, data, errors):
        error_string = u""
        error_message = _(u"Error Updating Sitting")
        for error in errors:
            if error.message not in ("", None): 
                error_string += error.message + "\n"
            else:
                error_string += error.__str__() + "\n"  
        return "%s \n%s" % (error_message, error_string)   
        
    @form.action(u"update", failure="update_sitting_failure_handler")
    def handle_update(self, action, data):
        session = Session()
        self.template_data = []
        trusted = removeSecurityProxy(ISchedulingContext(self.context))
        if ("rec_type" in data.keys()) and (data["rec_type"] is not None):
            # updating recurring events - we assume existing events fall
            # at the beginning of the sequence and offer in place update.
            parent_sitting_id = int(data["ids"]) or data["event_pid"]
            length = data["event_length"]
            sitting_length = timedelta(seconds=length)
            base_sitting_length = sitting_length + timedelta(hours=1)
            siblings = session.query(domain.Sitting).filter(or_(
                domain.Sitting.recurring_id==parent_sitting_id,
                domain.Sitting.sitting_id==parent_sitting_id
            )).order_by(domain.Sitting.sitting_id).all()
            dates = self.generate_dates(data)
            current_count = len(siblings)
            for count, date in enumerate(dates):
                is_new = not count < current_count
                if is_new:
                    sitting = domain.Sitting()
                else:
                    sitting = siblings[count]
                sitting.start_date = date
                if not count:
                    sitting.end_date = dates[len(dates)-1] + base_sitting_length
                    sitting.recurring_type = data.get("rec_type")
                    sitting.recurring_id = 0
                    sitting.sitting_length = length
                else:
                    end_date = date + sitting_length
                    sitting.end_date = end_date
                    sitting.sitting_length = int(time.mktime(date.timetuple()))
                #apply changes to parent and siblings new or existing
                sitting.short_name = data.get("short_name", None)
                sitting.venue_id = data["venue"]
                sitting.language = data["language"]
                sitting.activity_type = data.get("activity_type", None)
                sitting.meeting_type = data.get("meeting_type", None)
                sitting.convocation_type = data.get("convocation_type", None)
                if is_new:
                    sitting.group_id = trusted.group_id
                    sitting.recurring_id = parent_sitting_id
                    session.add(sitting)
                    session.flush()
                    notify(ObjectCreatedEvent(sitting))
                else:
                    session.flush()
                    notify(ObjectModifiedEvent(sitting))
                self.template_data.append({
                        "sitting_id": sitting.sitting_id, 
                        "action": (is_new and "inserted" or "updated"),
                        "ids": sitting.sitting_id,
                })
            #delete any sittings outside recurring bounds
            for del_sibling in siblings[len(dates):]:
                session.delete(del_sibling)
                del_id = del_sibling.sitting_id
                notify(ObjectRemovedEvent(del_sibling))
                self.template_data.append({
                    "sitting_id": del_id,
                    "action": "deleted",
                    "ids": del_id
                })
        else:
            sitting_id = int(data["ids"])
            parent_id = data["event_pid"]
            sitting = session.query(domain.Sitting).get(sitting_id)
            if sitting is None:
                sitting = session.query(domain.Sitting).get(parent_id)
            sitting.start_date = data["start_date"].replace(tzinfo=None)
            sitting.end_date = data["end_date"].replace(tzinfo=None)
            sitting.sitting_length = data.get("event_length")
            if "language" in data.keys():
                sitting.language = data["language"]
            if "venue" in data.keys():
                sitting.venue_id = data["venue"]
            sitting.short_name = data.get("short_name", None)
            sitting.activity_type = data.get("activity_type", None)
            sitting.meeting_type = data.get("meeting_type", None)
            sitting.convocation_type = data.get("convocation_type", None)
            session.flush()
            notify(ObjectModifiedEvent(sitting))
            self.template_data.append({
                    "sitting_id": sitting.sitting_id, 
                    "action": "updated",
                    "ids": data["ids"],
                })
        self.request.response.setHeader("Content-type", "text/xml")
        return self.xml_template()
        
    def delete_sitting_failure_handler(self, action, data, errors):
        error_string = u""
        for error in errors:
            if error.message not in ("", None): 
                error_string += error.message + "\n"
            else:
                error_string += error.__str__() + "\n"  
        return "%s \n%s" % (error_message, error_string)  
        
    @form.action(u"delete", failure="delete_sitting_failure_handler")
    def handle_delete(self, action, data):
        session = Session()
        self.template_data = []
        sitting = session.query(domain.Sitting).get(data["ids"])
        # set extra data needed by template
        self.template_data = []
        if sitting is not None:
            self.request.response.setHeader("Content-type", "text/xml")
            self.template_data.append({
                    "sitting_id": sitting.sitting_id, 
                    "action": "deleted",
                    "ids": data["ids"],
                })
            session.delete(sitting)
            session.flush()
            return self.xml_template()

class DhtmlxCalendarSittings(BrowserView):
    """This view returns xml of the sittings for the week and group 
    requested in a format acceptable by DHTMLX scheduler"""
    interface.implements(IStructuralView)
    
    content_mimetype = "text/xml"
    template = ViewPageTemplateFile("templates/dhtmlxcalendarxml.pt")

    def __init__(self, context, request):
        super(DhtmlxCalendarSittings, self).__init__(
            ISchedulingContext(context), request)
        self.context.__name__ = self.__name__
        interface.alsoProvides(self.context, ILocation)
        interface.alsoProvides(self.context, IDCDescriptiveProperties)
        self.__parent__ = context
          
    def get_sessions(self):
        sessions = [ removeSecurityProxy(session) for session in
            Session().query(domain.Session).all()
        ]
        colours = utils.generate_event_colours(len(sessions))
        for (index, sess) in enumerate(sessions):
            sess.colour = colours[index]
        return sessions
    
    def get_colour(self, event):
        hx = event.colour if hasattr(event, "colour") else self.event_colour
        return "#%s" % hx
    
    def get_event_type(self, event):
        return event.__class__.__name__.lower()
    
    @property
    def event_colour(self):
        if not hasattr(self, "event_color"):
            rq_color = unicode(self.request.form.get("color", ""))
            if rq_color:
                assert len(rq_color) <= 6
                self._event_color = rq_color
        return self._event_color if hasattr(self, "_event_color") else ""
    
    
    @property
    def sittings_and_sessions(self):
        event_list = []
        try:
            date = self.request.get("from")
            dateobj = datetime.datetime(*time.strptime(date, "%Y-%m-%d")[0:5])
            start_date = utils.datetimedict.fromdate(dateobj)
        except:
            start_date = None
            
        try:
            date = self.request.get("to")
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
        sittings = self.context.get_sittings(start_date, end_date)
        for sitting in sittings.values():
            if checkPermission("zope.View", sitting):
                trusted = removeSecurityProxy(sitting)
                trusted.text = dict(
                    sitting_status = _(
                        misc.get_wf_state(trusted, trusted.status)
                    )
                )
                event_list.append(trusted)
        if model_interfaces.IParliament.providedBy(self.context.get_group()):
            return event_list + self.get_sessions()
        else:
            return event_list

    def __call__(self):
        self.request.response.setHeader("Content-type", self.content_mimetype)
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
            for sitting in self.sittings_and_sessions
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
        sitting_id = self.sitting.sitting_id
        group_id = self.sitting.group_id
        record_keys = []
        for (index, data_item) in enumerate(self.data):
            actual_index = index + 1
            data_schedule_id = data_item.get("schedule_id")
            data_item_id = data_item.get("item_id")
            data_item_type = data_item.get("item_type")
            data_item_text = data_item.get("item_text")
            data_item_wf_status = data_item.get("wf_status")
            
            if not data_item_id:
                # create text record before inserting into schedule
                kls = capi.get_type_info(data_item_type).domain_model
                text_record = kls(
                    text=data_item_text,
                    group_id=group_id,
                    language=get_default_language()
                )
                session.add(text_record)
                session.flush()
                notify(ObjectCreatedEvent(text_record))
                data_item_id = domain.get_mapped_object_id(text_record)
                schedule_record = domain.ItemSchedule(
                    item_id=data_item_id,
                    item_type=data_item_type,
                    planned_order=actual_index,
                    sitting_id=sitting_id
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
                    text_record = removeSecurityProxy(current_record.item)
                    if model_interfaces.IScheduleText.providedBy(text_record):                        
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
                        sitting_id=sitting_id
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
            discussion_text = record.get("body", "")
            object_id = record.get("object_id", None)
            if object_id:
                current_record = removeSecurityProxy(
                    self.context.get(getItemKey(object_id))
                )
                current_record.body = discussion_text
                session.add(current_record)
                session.flush()
                notify(ObjectModifiedEvent(current_record))
                new_record_keys.append(stringKey(current_record))
            else:
                new_record = domain_model(
                    body=discussion_text,
                    language=get_default_language()
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

class AgendaPreview(BrowserView):
    """View to display an agenda preview using HTML template in bungeni_custom
    """
    def __init__(self, context, request):
        super(AgendaPreview, self).__init__(context, request)

    def get_template(self):
        wf = IWorkflow(self.context)
        vocab = vocabulary.report_xhtml_template_factory
        report_type = "sitting_agenda"
        if self.context.status in wf.get_state_ids(tagged=["publishedminutes"]):
            report_type = "sitting_minutes"
        term = vocab.getTermByFileName(report_type)
        return term and term.value or vocab.terms[0].value

    def generate_preview(self):
        sitting = removeSecurityProxy(self.context)
        wf = IWorkflow(sitting)
        sittings = [data.ExpandedSitting(sitting)]
        generator = generators.ReportGeneratorXHTML(self.get_template())
        if sitting.status in wf.get_state_ids(tagged=["publishedminutes"]):
            title = generator.title = _(u"Sitting Votes and Proceedings")
        else:
            title = generator.title = _(u"Sitting Agenda")
        generator.context = data.ReportContext(
            sittings=sittings, title=title
        )
        return generator.generateReport()

    def __call__(self):
        self.request.response.setHeader("Content-type", "text/html")
        return self.generate_preview()
