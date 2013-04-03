# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Calendar and Scheduling Browser and datasource Views

$Id$
"""

log = __import__("logging").getLogger("bungeni.ui.calendar")

from copy import copy
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
from zope.schema.interfaces import IChoice
from zc.resourcelibrary import need
from sqlalchemy import orm
from sqlalchemy.sql.expression import or_

from bungeni.core.interfaces import ISchedulingContext
from bungeni.core.schedule import SittingContainerSchedulingContext
from bungeni.core.workflow.interfaces import (
    IWorkflowController, InvalidTransitionError
)
from bungeni.core.language import get_default_language
from bungeni.core.translation import translate_i18n

from ploned.ui.interfaces import IStructuralView
from bungeni.ui.interfaces import IBusinessSectionLayer
from bungeni.ui.browser import BungeniBrowserView
from bungeni.ui.calendar import utils, config, interfaces, data
from bungeni.ui.i18n import _
from bungeni.ui.utils import misc, url, date
from bungeni.ui.menu import get_actions
from bungeni.ui.widgets import LanguageLookupWidget
from bungeni.ui.container import ContainerJSONListing
from bungeni.ui.forms.common import AddForm, DeleteForm, EditForm
from bungeni.ui.reporting import generators

from bungeni.models import domain
from bungeni.models import interfaces as model_interfaces
from bungeni.alchemist.container import stringKey
from bungeni.alchemist import Session
from bungeni.ui import vocabulary

from bungeni.utils import register, naming

# Filter key names prefix - for available items listings
FILTER_PREFIX = "filter_"

DT_FORMAT = "%Y-%m-%d %H:%M"

#i18n messages
TITLE_VENUES_VIEW = _("scheduler_title_venues_view", default="Venues")
FIELD_GROUP = _("scheduler_field_group", default="Group")
FIELD_START_DATE = _("scheduler_field_start_date", default="Start Date")
FIELD_END_DATE = _("scheduler_field_end_date", default="End Date")
FIELD_VENUE = _("scheduler_field_venue", default="Venue")
TITLE_SITTING = _("scheduler_title_sitting", default="Sitting")
ACTION_VIEW_SITTING = _("scheduler_action_view_sitting", default="View")

def create_id(event):
    """Create an event (sitting or session) identifier of the form <type>-<id>
    """
    mapper = orm.object_mapper(event)
    return "%s-%d" % (naming.polymorphic_identity(event.__class__),
        mapper.primary_key_from_instance(event)[0])

def get_real_id(scheduler_id, default=0):
    """Get actual sitting id from ID of form <type>-<id>.
    Resolves primary key of event created using 
    """
    if not scheduler_id:
        return default
    if type(scheduler_id) is int:
        return scheduler_id
    str_value = (scheduler_id.split("-")[-1] if ("-" in scheduler_id) else 
        scheduler_id)
    return int(str_value)


class TIME_SPAN:
    daily = _(u"Daily")
    weekly = _(u"Weekly")

class EventPartialForm(AddForm):
    """Partial form for event entry form
    """
    omit_fields = ["start_date", "end_date", "sitting_id", "group_id", 
        "sitting_length", "recurring_id", "recurring_type", "status",
            "status_date"
    ]
    
    def update_fields(self):
        self.form_fields = self.form_fields.omit(*self.omit_fields)
        self.form_fields["language"].edit_widget = LanguageLookupWidget
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


def get_sitting_actions(context, request):
    return get_actions("sitting_actions", context, request)

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
        
        if checkPermission("bungeni.sitting.View", proxied):
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


class SessionsRedirect(BrowserView):
    redirect_to = "./sessions/"
    def __call__(self):
        return self.request.response.redirect(self.redirect_to)


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
        sitting = domain.Sitting()
        sitting.__parent__ = self
        form = EventPartialForm(sitting, self.request)
        return form

    @property
    def venues_data(self):
        venue_list = [ {"key": venue.value, "label": venue.title}
            for venue in vocabulary.venue_factory(self.context)
        ]
        return venue_list
    
    @property
    def groups_data(self):
        group_list = []
        try:
            group = self.context.get_group()
            if model_interfaces.ICommittee.providedBy(group):
                group_container = group.parent_group.committees
            else:
                group = self.context.get_group()
                group_container = group.committees
                group_list.append({
                    "key": self.context.group_id,
                    "label": IDCDescriptiveProperties(group).title,
                })
            group_list += [ {"key": comm.committee_id, 
                "label": IDCDescriptiveProperties(comm).title}
                for comm in group_container.values()
                if checkPermission("bungeni.committee_member.Add", comm)
            ]
        except AttributeError:
            log.warn("Context %s has no committees", self.context)
        return group_list        
    
    @property
    def ical_url(self):
        return u"/".join(
            [url.absoluteURL(self.context, self.request), "dhtmlxcalendar.ics"]
        )

    @property
    def calendar_js_globals(self):
        limit_start = ISchedulingContext(self.context).start_date
        limit_end = ISchedulingContext(self.context).end_date
        cal_globals = dict(
            limit_start=limit_start.isoformat() if limit_start else None,
            limit_end=limit_end.isoformat() if limit_end else None,
            ical_url=self.ical_url,
            required_fields=[field.field.getName() 
                for field in self.partial_event_form.form_fields
                if field.field.required
            ],
            view_url=self.url,
            venues_view_title=translate_i18n(TITLE_VENUES_VIEW),
            text_group=translate_i18n(FIELD_GROUP),
            text_start_date=translate_i18n(FIELD_START_DATE),
            text_end_date=translate_i18n(FIELD_END_DATE),
            text_venue=translate_i18n(FIELD_VENUE),
            text_activity_type=translate_i18n(_(u"Activity Type")),
            text_meeting_type=translate_i18n(_(u"Meeting Type")),
            text_convocation_type=translate_i18n(_(u"Convocation Type")),
            text_sitting=translate_i18n(TITLE_SITTING),
            text_view=translate_i18n(ACTION_VIEW_SITTING),
            error_messages=dict(
                default=_(u"Please check the highlighted sittings. " 
                    "Failed to apply changes"),
                updated=_(u"Please review the highlighted sittings." 
                    " Could not apply changes."),
                deleted=_(u"Please review the highlighted events."
                    " Could not be deleted.")
            )
        )
        return """var cal_globals = %s;
            var timeline_data = { venues: %s, combined: %s };
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

class DailyCalendarView(CalendarView):
    """Daily calendar view."""
    
    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)

    def render(self, today, template=None):
        if template is None:
            template = self.template

        calendar_url = url.absoluteURL(self.context.__parent__, self.request)
        cal_date = removeSecurityProxy(self.context.date)

        sittings = self.context.get_sittings()
        return template(
            display="daily",
#            title=_(u"$B $Y", mapping=date),
            title = cal_date,
#
            day={
                "formatted": datetime.datetime.strftime(cal_date, "%A %d"),
                "id": datetime.datetime.strftime(cal_date, "%Y-%m-%d"),
                "today": cal_date == today,
                "url": "%s/%d" % (calendar_url, cal_date.totimestamp()),
                },
            hours=range(6,21),
            week_no=date.isocalendar()[1],
            week_day=date.weekday(),
            links={
                "previous": "%s/%d" % (
                    calendar_url, (cal_date - timedelta(days=1)).totimestamp()),
                "next": "%s/%d" % (
                    calendar_url, (cal_date + timedelta(days=1)).totimestamp()),
                },
            sittings_map = create_sittings_map(sittings, self.request),
            )

#
# Group Scheduler New YUI based Stack UI
#
RESOURCE_PERMISSION_MAP = (
    (["bungeni-schedule-minutes"], "bungeni.item_schedule_discussion.Edit"),
    (["bungeni-schedule-editor"], "bungeni.item_schedule.Edit"),
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
    protect={"bungeni.item_schedule_discussion.View": 
        register.VIEW_DEFAULT_ATTRS})
class ScheduleJSONListing(ContainerJSONListing):
    """Returns JSON listing with expanded unlisted properties used in
    scheduling user interface setup
    """
    def _json_values(self, nodes):
        include_wf = self.request.form.get("add_wf", None)
        items = super(ScheduleJSONListing, self)._json_values(nodes)
        def add_wf_meta(enum):
            index, item = enum
            node = nodes[index]
            item["item_id"] = node.item_id
            if model_interfaces.IScheduleText.providedBy(node.item):
                return
            if not include_wf:
                return
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

@register.view(model_interfaces.IItemScheduleContainer, 
    name="jsonlisting-schedule-documents",
    protect={"bungeni.item_schedule.View": 
        register.VIEW_DEFAULT_ATTRS})
class ScheduleJSONListingDocuments(ContainerJSONListing):
    """Lists all scheduled documents (excluding headings and notes)
    """
    def query_add_filters(self, query):
        return query.filter(self.domain_model.item_type.in_(
            data.get_schedulable_types(True).keys()
        ))
    

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
        if request.form.get("event_pid"):
            request.form["event_pid"] = get_real_id(request.form["event_pid"])
        if request.form.get("rec_type") == "none":
            request.form["!nativeeditor_status"] = "deleted"
        if "!nativeeditor_status" in request.form.keys():
            if request.form["!nativeeditor_status"] == "inserted":
                request.form["actions.insert"] = "insert"
            elif request.form["!nativeeditor_status"] == "updated":
                request.form["actions.update"] = "update"
            elif request.form["!nativeeditor_status"] == "deleted":
                request.form["actions.delete"] = "delete"
        super(DhtmlxCalendarSittingsEdit, self).__init__(context, request)


    @property
    def sittings_container(self):
        traverser = component.getMultiAdapter((self.context, self.request), 
            IPublishTraverse)
        return traverser.publishTraverse(self.request, "sittings")

                  
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
        context.__parent__ = self.context
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
        log.error(error_message)
        log.error(error_string)
        self.template_data.append(
            dict(action="invalid", ids=data["ids"], sitting_id=data["ids"])
        )
        self.request.response.setHeader("Content-type", "text/xml")
        return self.xml_template()

    def generate_dates(self, data):
        trusted = removeSecurityProxy(ISchedulingContext(self.context))
        recurrence_start_date = data["start_date"].replace(tzinfo=None)
        recurrence_end_date = data["rec_end_date"].replace(tzinfo=None)
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
        data["rec_end_date"] = data["end_date"]
        self.template_data = []
        initial_sitting = None
        length = data["event_length"]
        venue_id = unicode(data["venue"]) if data['venue'] else None
        if data.get("rec_type") not in [None, "none"]:
            data["end_date"] = data["start_date"] + timedelta(seconds=length)
            self.request.form["end_date"] = data["end_date"].strftime(DT_FORMAT)
        data["headless"] = "true"
        self.request.form["venue_id"] = data["venue_id"] = venue_id
        self.request.form["headless"] = "true"
        add_form = AddForm(self.sittings_container, self.request)
        add_form.update()
        if not add_form.errors:
            initial_sitting = removeSecurityProxy(add_form.created_object)
        else:
            return self.insert_sitting_failure_handler(action, data,
                add_form.errors
            )
        if ("rec_type" in data.keys()) and (data["rec_type"] not in [None, "none"]):
            # create recurring sittings
            #base_sitting_length = sitting_length + timedelta(hours=1)
            sitting_length = timedelta(seconds=length)
            base_sitting_length = timedelta(seconds=length) + timedelta(hours=1)
            dates = self.generate_dates(data)
            initial_sitting.recurring_type = data.get("rec_type")
            initial_sitting.recurring_id = 0
            initial_sitting.sitting_length = length
            for count, date in enumerate(dates):
                if not count:
                    #we've already added the initial sitting
                    initial_sitting.recurring_end_date = (
                        dates[len(dates)-1] + base_sitting_length)
                    session.merge(initial_sitting)
                    continue
                
                sitting_data = copy(data)
                sitting_data["start_date"] = date.strftime(DT_FORMAT)
                sitting_data["end_date"] = (date + sitting_length).strftime(DT_FORMAT)
                
                request_copy = copy(self.request)
                request_copy.form = sitting_data
                add_form = AddForm(self.sittings_container, request_copy)
                add_form.update()
                if not add_form.errors:
                    # use finishConstruction API here
                    obj = add_form.created_object                    
                    obj.sitting_length = int(time.mktime(date.timetuple()))
                    obj.recurring_id = initial_sitting.sitting_id
                    session.merge(obj)
        else:
            initial_sitting.recurring_type = data.get("rec_type")
            initial_sitting.recurring_id = data.get("event_pid", 0)
            if data.get("event_length"):
                initial_sitting.sitting_length = data.get("event_length")
            session.merge(initial_sitting)
            wfc = IWorkflowController(initial_sitting)
            wfc.fireAutomatic()
        sitting_action = "inserted"
        if data["rec_type"] == "none":
            sitting_action = "deleted"
            session.merge(initial_sitting)
        self.template_data.append({
                "sitting_id": initial_sitting.sitting_id, 
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
        log.error(error_message)
        log.error(error_string)
        self.template_data.append(
            dict(action="invalid", ids=data["ids"], sitting_id=data["ids"])
        )
        self.request.response.setHeader("Content-type", "text/xml")
        return self.xml_template()

        
    @form.action(u"update", failure="update_sitting_failure_handler")
    def handle_update(self, action, data):
        session = Session()
        self.template_data = []
        venue_id = unicode(data["venue"]) if data['venue'] else None
        data["rec_end_date"] = data["end_date"]
        data["headless"] = 'true'
        self.request.form["venue_id"] = data["venue_id"] = venue_id
        self.request.form["headless"] = "true"
        if ("rec_type" in data.keys()) and (data["rec_type"] is not None):
            # updating recurring events - we assume existing events fall
            # at the beginning of the sequence and offer in place update.
            parent_sitting_id = get_real_id(data["ids"] or data["event_pid"])
            length = data["event_length"]
            sitting_length = timedelta(seconds=length)
            base_sitting_length = sitting_length + timedelta(hours=1)
            siblings_filter = or_(
                domain.Sitting.recurring_id==parent_sitting_id,
                domain.Sitting.sitting_id==parent_sitting_id
            )
            siblings = [ sitting for sitting in
                self.sittings_container.batch(order_by=(domain.Sitting.sitting_id),
                    limit=None, filter=siblings_filter
                )
            ] 
            dates = self.generate_dates(data)
            current_count = len(siblings)
            for count, date in enumerate(dates):
                is_new = not count < current_count
                sitting_data = copy(data)
                sitting_data["start_date"] = date.strftime(DT_FORMAT)
                sitting_data["end_date"] = (date + sitting_length).strftime(DT_FORMAT)
                request_copy = copy(self.request)
                request_copy.form = sitting_data
                if is_new:
                    add_form = AddForm(self.sittings_container, request_copy)
                    add_form.update()
                    if add_form.errors:
                        log.error("Could not add sitting in sequence: %s",
                            sitting_data
                        )
                        continue
                    else:
                        sitting = add_form.created_object
                        sitting.recurring_id = parent_sitting_id
                else:
                    sitting = siblings[count]
                if not count:
                    sitting.recurring_end_date = dates[len(dates)-1] + base_sitting_length
                    sitting.recurring_type = data.get("rec_type")
                    sitting.recurring_id = 0
                    sitting.sitting_length = length
                else:
                    sitting.sitting_length = int(time.mktime(date.timetuple()))
                    sitting.recurring_type = None
                if not is_new:
                    edit_form = EditForm(sitting, request_copy)
                    edit_form.update()
                    if edit_form.errors:
                        continue
                    else:
                        session.merge(edit_form.context)
                else:
                    session.merge(sitting)
                self.template_data.append({
                        "sitting_id": sitting.sitting_id, 
                        "action": (is_new and "inserted" or "updated"),
                        "ids": create_id(sitting)
                })
            #delete any sittings outside recurring bounds
            for del_sibling in siblings[len(dates):]:
                delete_form = DeleteForm(del_sibling, self.request)
                delete_form.update()
                if delete_form.errors:
                    continue
                else:
                    self.template_data.append({
                        "sitting_id": del_sibling.sitting_id,
                        "action": "deleted",
                        "ids": create_id(del_sibling)
                    })
        else:
            sitting_id = get_real_id(data["ids"])
            parent_id = get_real_id(data["event_pid"])
            sitting = self.sittings_container.get(sitting_id)
            if sitting is None:
                sitting = self.sittings_container.get(int(parent_id))
            edit_form = EditForm(sitting, self.request)
            edit_form.update()
            if edit_form.errors:
                return self.update_sitting_failure_handler(action, data,
                    edit_form.errors
                )
            else:
                sitting.sitting_length = data.get("event_length")
                session.merge(sitting)
                self.template_data.append({
                        "sitting_id": sitting.sitting_id, 
                        "action": "updated",
                        "ids": data["ids"],
                    })
        self.request.response.setHeader("Content-type", "text/xml")
        return self.xml_template()
        
    def delete_sitting_failure_handler(self, action, data, errors):
        error_string = u""
        error_message = _(u"Error Deleting Sitting")
        for error in errors:
            if error.message not in ("", None): 
                error_string += error.message + "\n"
            else:
                error_string += error.__str__() + "\n"
        log.error(error_message)
        log.error(error_string)
        self.template_data.append(
            dict(action="inserted", ids=data["ids"], sitting_id=data["ids"])
        )
        self.request.response.setHeader("Content-type", "text/xml")
        return self.xml_template()
        
    @form.action(u"delete", failure="delete_sitting_failure_handler")
    def handle_delete(self, action, data):
        self.template_data = []
        if ISchedulingContext.providedBy(self.context):
            container = removeSecurityProxy(self.context.__parent__).sittings
        else:
            container = self.context.publishTraverse(self.request, "sittings")
        sitting = (container.get(get_real_id(data["ids"])) or
            container.get(get_real_id(self.request.form["event_pid"])))
        self.template_data = []
        if sitting is not None:
            self.request.form["headless"] = "true"
            delete_form = DeleteForm(sitting, self.request)
            delete_form.update()
            if not delete_form.errors:
                self.template_data.append({
                        "sitting_id": sitting.sitting_id, 
                        "action": "deleted",
                        "ids": data["ids"],
                    })
            else:
                return self.delete_sitting_failure_handler(action, data,
                    delete_form.errors
                )
        self.request.response.setHeader("Content-type", "text/xml")
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
        sessions = [ removeSecurityProxy(session) for key, session in 
            self.context.get_group().sessions.items()
            if checkPermission("bungeni.session.View", session)
        ]
        sessions.sort(key=lambda sess:sess.start_date)
        return sessions
    
    def get_colour(self, event):
        hx = event.colour if hasattr(event, "colour") else self.event_colour
        return "#%s" % hx
    
    def get_event_type(self, event):
        return event.__class__.__name__.lower()
    
    def get_event_id(self, event):
        """This ensures no collission between sessions and sittings
        """
        return create_id(event)
    
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
            if checkPermission("bungeni.sitting.View", sitting):
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
                    hasattr(sitting, "venue") and sitting.venue else u""
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
        record_keys = []
        planned_index = 1

        def add_planned_index(obj, index):
            """add planned order key for non text record types
            """
            if not (model_interfaces.IScheduleText.providedBy(obj.item)):
                obj.planned_order = planned_index
                index = index + 1
            return index

        for (index, data_item) in enumerate(self.data):
            real_index = index + 1
            data_schedule_id = data_item.get("schedule_id")
            data_item_id = data_item.get("item_id")
            data_item_type = data_item.get("item_type")
            schedule_item_type = data_item_type
            data_item_text = data_item.get("item_text")
            data_item_wf_status = data_item.get("wf_status")
            
            if not data_item_id:
                # create text record before inserting into schedule
                text_record = domain.AgendaTextRecord(
                    text=data_item_text,
                    record_type = data_item_type,
                    language=get_default_language()
                )
                session.add(text_record)
                session.flush()
                notify(ObjectCreatedEvent(text_record))
                data_item_id = domain.get_mapped_object_id(text_record)
                schedule_item_type = domain.AgendaTextRecord.type
                schedule_record = domain.ItemSchedule(
                    item_id=data_item_id,
                    item_type=schedule_item_type,
                    real_order=real_index,
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
                    current_record.real_order = real_index
                    planned_index = add_planned_index(current_record, 
                        planned_index)
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
                        schedule_item_type = domain.AgendaTextRecord.type
                        if text_record.text != data_item_text:
                            text_record.text = data_item_text
                            session.add(text_record)
                            session.flush()
                            notify(ObjectModifiedEvent(text_record))
                else:
                    schedule_record = domain.ItemSchedule(
                        item_id=data_item_id,
                        item_type=data_item_type,
                        real_order=real_index,
                        sitting_id=sitting_id
                    )
                    planned_index = add_planned_index(schedule_record, 
                        planned_index)
                    session.add(schedule_record)
                    session.flush()
                    notify(ObjectCreatedEvent(schedule_record))
            record_keys.append(self.RECORD_KEY % 
                (schedule_item_type, data_item_id))
        records_to_delete = filter(
            lambda item:(self.RECORD_KEY % (item.item_type, item.item_id)
                not in record_keys
            ),
            [removeSecurityProxy(rec) for rec in self.context.values()]
        )
        map(session.delete, records_to_delete)
        map(lambda deleted:notify(ObjectRemovedEvent(deleted)), 
            records_to_delete)
        
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
        vocab = vocabulary.report_xhtml_template_factory
        report_type = "sitting_agenda"
        #!+TAGS(mb, Feb-2013) Deprecate with tags. Configure as wf/feature.
        if "minutes" in self.context.status:
            report_type = "sitting_minutes"
        term = vocab.getTermByFileName(report_type)
        return term and term.value or vocab.terms[0].value

    def generate_preview(self):
        sitting = removeSecurityProxy(self.context)
        sittings = [data.ExpandedSitting(sitting)]
        generator = generators.ReportGeneratorXHTML(self.get_template())
        #!+TAGS(mb, Feb-2013) Deprecate with tags. Configure as wf/feature.
        if "minutes" in sitting.status:
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
