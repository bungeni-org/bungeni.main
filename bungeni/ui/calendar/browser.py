# encoding: utf-8
# TODO - Cleanup!!!!

log = __import__("logging").getLogger("bungeni.ui.calendar")


import time
import datetime
timedelta = datetime.timedelta

from zope.event import notify
from zope.lifecycleevent import ObjectCreatedEvent, ObjectModifiedEvent
from zope import interface
from zope import component
from zope.i18n import translate
from zope.location.interfaces import ILocation
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.publisher.browser import BrowserView
from bungeni.ui.browser import BungeniBrowserView
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.app.component.hooks import getSite
from zope.security.proxy import removeSecurityProxy
from zope.security.proxy import ProxyFactory
from zope.security import checkPermission
from bungeni.core.translation import get_all_languages
from zope.publisher.interfaces import IPublishTraverse

from bungeni.ui.calendar import utils
from bungeni.ui.tagged import get_states
from bungeni.ui.i18n import _
from bungeni.ui.utils import misc, url, debug
from bungeni.ui.menu import get_actions
from bungeni.ui.forms import common
from bungeni.core.location import location_wrapped
from bungeni.core.interfaces import ISchedulingContext
from bungeni.core.schedule import SittingContainerSchedulingContext
from bungeni.ui.interfaces import IBusinessSectionLayer

from bungeni.models import domain
from bungeni.models.interfaces import IGroupSitting
from ploned.ui.interfaces import IStructuralView
from bungeni.alchemist.container import stringKey
from bungeni.alchemist import Session
from ore.workflow.interfaces import IWorkflowInfo
from zope.formlib import form
from zope import schema
from zope.formlib import namedtemplate
from zc.resourcelibrary import need
from sqlalchemy.orm import eagerload
from bungeni.ui import vocabulary
from bungeni.core.translation import get_default_language
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
    site_url = url.absoluteURL(getSite(), request)
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
            'truncated_discussion': truncated_discussion,
            'delete_url': "%s/delete" % url.absoluteURL(scheduling, request),
            'url': url.set_url_context(site_url+('/business/%ss/obj-%s' % (item.type, item.parliamentary_item_id)))}
        
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
    
    short_name = u"Scheduling"
    
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
    
    def render(self, template=None):
        if template is None:
            template = self.template
        if (not checkPermission(u"bungeni.sitting.Add", self.context)) or \
            (IBusinessSectionLayer.providedBy(self.request)):
            self.edit = False
        else:
            self.edit = True
        session = Session()
        venues = session.query(domain.Venue).all()
        languages = get_all_languages()
        session.close()
        self.display_language = get_default_language()
        if self.request.get("I18N_LANGUAGE"):
            self.display_language = self.request.get("I18N_LANGUAGE")
        #html is hardcoded in here because doing it in the template
        #would have been a colossal pain
        #TODO: FIX THIS
        s = '<div class="dhx_cal_ltext" style="height:90px;">' 
        s += '<table>'
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

class GroupSittingScheduleView(BrowserView):
    """Group-sitting scheduling view.

    This view presents a sitting and provides a user interface to
    manage the agenda.
    """

    template = ViewPageTemplateFile("templates/main.pt")
    ajax = ViewPageTemplateFile("templates/ajax.pt")
    
    _macros = ViewPageTemplateFile("templates/macros.pt")
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
        container_url = url.absoluteURL(container, self.request)
        
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
        

        site_url = url.absoluteURL(getSite(), self.request)

        return template(
            display="sitting",
            #title=_(u"$A $e, $B $Y", mapping=start_date),
            title = "%s: %s - %s" % (self.context.group.short_name, 
                self.context.start_date.strftime('%Y-%m-%d %H:%M'), 
                self.context.end_date.strftime('%H:%M')),
            description=_(u"Sitting Info"),
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
    
    class DhtmlxCalendarSittingsEditForm(interface.Interface):
        ids = schema.TextLine(title=u'ID',
                                required=False,
                                description=u'Sitting ID'
                        )
        start_date = schema.TextLine(title=_(u"Start Date"),
                            description=_(u"Choose a start date and time"),
                            required=False)
        end_date = schema.TextLine(title=_(u"End Date"),
                            description=_(u"Choose an end date and time"),
                            required=False)
        venue = schema.Choice(title=_(u"Venue"),
                              source="bungeni.vocabulary.Venues",
                              description=_(u"Venues"),
                             required=False)
        language = schema.Choice(title=_(u"Language"),
                    default=get_default_language(),
                    vocabulary="language_vocabulary",
                    description=_(u'Language')
        )
        rec_type = schema.TextLine( title = u'Recurrence Type',
                                    required=False,
                                    description = u"A string that contains the \
                                            rules for reccurent sittings if any"
                        )         
        event_length = schema.TextLine( title = u'Event Length',
                                    required=False,
                                    description = u'Length of event'
                        )      
        nativeeditor_status = schema.TextLine( title = u'editor status',
                                    required=False,
                                    description = u'Editor Status'
                        ) 
                        
    form_fields = form.Fields(DhtmlxCalendarSittingsEditForm)

    def setUpWidgets(self, ignore_request=False):
        class context:
            ids = None
            start_date = None
            end_date = None
            location = None
            language = None
            venue = None
            rec_type = None
            event_length = None
            nativeeditor_status = None
        self.adapters = {
            self.DhtmlxCalendarSittingsEditForm: context
            }
        self.widgets = form.setUpEditWidgets(
            self.form_fields, "", self.context, self.request,
                    adapters=self.adapters, ignore_request=ignore_request)


    
                
    def validate(self, action, data):
        errors = super(DhtmlxCalendarSittingsEdit, self).validate(action, data)
        return errors         
        
    @form.action(u"insert")
    def handle_insert(self, action, data):
        session = Session()
        trusted = removeSecurityProxy(ISchedulingContext(self.context))
        if ("rec_type" in data.keys()) and (data["rec_type"] is not None):
            try:
                recurrence_start_date = datetime.datetime \
                        .strptime(data["start_date"], '%Y-%m-%d %H:%M')
            except:
                log.error("The start date of the recurrence  \
                                    is not in the correct format")
            try:
                recurrence_end_date = datetime.datetime.strptime(
                                            data["end_date"], '%Y-%m-%d %H:%M')
            except:
                log.error("The start date of the recurrence is not in \
                                                        the correct format")   
            length = data["event_length"]
            sitting_length = timedelta(seconds=int(length))
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
            for date in dates:
                sitting = domain.GroupSitting()
                sitting.group_id = trusted.group_id
                sitting.start_date = date
                sitting.end_date = date + sitting_length
                sitting.status = None
                if "language" in data.keys():
                    sitting.language = data["language"]
                if "venue" in data.keys():
                    sitting.venue_id = data["venue"]
                # set extra data needed by template
                sitting.ids = data["ids"]
                sitting.action = 'inserted'
                session.add(sitting)
                # commiting after adding a sitting is incredibly inefficient
                # but thats the only way to get the sitting id.
                # Adding recurrring sittings is not a recurrent activity (see,
                # what I did there :)) so we can live with it.
                session.commit(sitting)
                notify(ObjectCreatedEvent(sitting))
                self.template_data.append({"group_sitting_id": sitting.group_sitting_id, 
                                           "action": "inserted",
                                           "ids": data["ids"]})
            self.request.response.setHeader('Content-type', 'text/xml')
            return self.xml_template()
        else:
            sitting = domain.GroupSitting()
            try:
                sitting.start_date = datetime.datetime.strptime(
                                            data["start_date"], '%Y-%m-%d %H:%M')
            except:
                log.error("The start date of the sitting \
                                    is not in the correct format")
            try:
                sitting.end_date = datetime.datetime.strptime(data["end_date"], 
                                                                '%Y-%m-%d %H:%M')
            except:
                log.error("The end date of the sitting is not in the correct format")
                
            sitting.group_id = trusted.group_id
            if "language" in data.keys():
                sitting.language = data["language"]
            if "venue" in data.keys():
                sitting.venue_id = data["venue"]
            
            # set extra data needed by template
            sitting.ids = data["ids"]
            sitting.action = 'inserted'
            session.add(sitting)
            session.commit()
            notify(ObjectCreatedEvent(sitting))
            self.template_data.append({"group_sitting_id": sitting.group_sitting_id, 
                                       "action": "inserted",
                                       "ids": data["ids"]})
            
            self.request.response.setHeader('Content-type', 'text/xml')
            return self.xml_template()
               
    @form.action(u"update")
    def handle_update(self, action, data):
        session = Session()
        sitting = domain.GroupSitting()
        sitting = session.query(domain.GroupSitting).get(data["ids"])
        sitting.start_date = data["start_date"]
        sitting.end_date = data["end_date"]
        if "language" in data.keys():
            sitting.language = data["language"]
        if "venue" in data.keys():
            sitting.venue_id = data["venue"]
        # set extra data needed by template
        session.update(sitting)
        notify(ObjectModifiedEvent(sitting))
        self.template_data.append({"group_sitting_id": sitting.group_sitting_id, 
                                    "action": "inserted",
                                    "ids": data["ids"]})
        session.commit()
        self.request.response.setHeader('Content-type', 'text/xml')
        return self.xml_template()
        
        
    @form.action(u"delete")
    def handle_delete(self, action, data):
        session = Session()
        sitting = session.query(domain.GroupSitting).get(data["ids"])
        # set extra data needed by template
        self.template_data = []
        if sitting is not None:
            self.request.response.setHeader('Content-type', 'text/xml')
            self.template_data.append({"group_sitting_id": sitting.group_sitting_id, 
                                       "action": "deleted",
                                       "ids": data["ids"]})
            session.delete(sitting)
            session.commit()
            return self.xml_template()

                          
class DhtmlxCalendarSittings(BrowserView):
    """This view returns xml of the sittings for the week and group 
    requested in a format acceptable by DHTMLX scheduler"""
    interface.implements(IStructuralView)
    
    template = ViewPageTemplateFile('templates/dhtmlxcalendarxml.pt')
    def __init__(self, context, request):
        super(DhtmlxCalendarSittings, self).__init__(
            ISchedulingContext(context), request)
        self.context.__name__ = self.__name__
        interface.alsoProvides(self.context, ILocation)
        interface.alsoProvides(self.context, IDCDescriptiveProperties)
        self.__parent__ = context
               
                          
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
                if trusted.venue:
                    trusted.text = '<![CDATA[<b>Venue:</b></br>' \
                                + trusted.venue.short_name + '</br>' \
                                + '<b>Status:</b>' + '</br>' \
                                + trusted.status + ']]>'
                else:
                    trusted.text = '<![CDATA[<b>Status:</b>' + '</br>' \
                                + trusted.status + ']]>'
                self.sittings.append(trusted)
        self.request.response.setHeader('Content-type', 'text/xml')
        return self.render()
        #return super(DhtmlxCalendarSittings, self).__call__() 
        
    def render(self, template = None):
        return self.template()


