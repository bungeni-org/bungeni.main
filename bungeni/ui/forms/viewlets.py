# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Forms Viewlets

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.forms.viewlets")

import sys
from dateutil import relativedelta
import datetime, calendar
from zope import interface
from zope.viewlet import viewlet, manager
from zope.app.pagetemplate import ViewPageTemplateFile

from zope.formlib.namedtemplate import NamedTemplate
from zope.formlib import form
from zope.security.proxy import removeSecurityProxy

import sqlalchemy.sql.expression as sql

from alchemist import ui
from ore.alchemist import Session
from ore.alchemist.model import queryModelDescriptor

from bungeni.models import domain, interfaces
from bungeni.models.utils import get_offices_held_for_user_in_parliament
from bungeni.models.utils import get_parliament_for_group_id
from bungeni.models.utils import get_principal_id
from bungeni.ui.i18n import _
import bungeni.core.globalsettings as prefs

from bungeni.ui.tagged import get_states
from bungeni.ui import z3evoque
from bungeni.ui import table
from bungeni.ui.utils import queries, statements, url, misc, date, debug

from fields import BungeniAttributeDisplay
from interfaces import ISubFormViewletManager

''' XXX-INFO-FOR-PLONE - MR - 2010-05-03
class GroupIdViewlet(viewlet.ViewletBase):
    """ display the group and parent group
    principal id """
    parent_group_principal_id = None
    my_group_principal_id = None
    
    def __init__( self,  context, request, view, manager ):
        self.context = context
        self.request = request
        self.__parent__= context
        self.manager = manager
        
    def update(self):
        session = Session()
        trusted = removeSecurityProxy(self.context)
        if interfaces.IParliament.providedBy(trusted):
            self.parent_group_principal_id = trusted.group_principal_id
        else:
            self.parent_group_principal_id = getattr(trusted.parent_group, 'group_principal_id', "")
        self.my_group_principal_id = trusted.group_principal_id
        #session.close()
        
    render = ViewPageTemplateFile('templates/group_id.pt')
'''


''' XXX-INFO-FOR-PLONE - MR - 2010-05-03
class UserIdViewlet(viewlet.ViewletBase):
    """ display the users
    principal id """
    principal_id = None
    
    def __init__( self,  context, request, view, manager ):

        self.context = context
        self.request = request
        self.__parent__= context
        self.manager = manager
        
    def update(self):
        session = Session()
        trusted = removeSecurityProxy(self.context)
        session.merge(trusted)
        try:
            self.principal_id = trusted.user.login
        except:
            pass
        
    render = ViewPageTemplateFile ('templates/user_id.pt')
'''


class AttributesEditViewlet(ui.core.DynamicFields, ui.viewlet.EditFormViewlet):
    mode = "edit"
    template = NamedTemplate('alchemist.subform')
    form_name = _(u"General")

class SubFormViewletManager(manager.WeightOrderedViewletManager):
    """
    display subforms
    """
    interface.implements(ISubFormViewletManager)

    def filter(self, viewlets):
         viewlets = super(SubFormViewletManager, self).filter(viewlets)
         return [(name, viewlet)
                 for name, viewlet in viewlets
                 if viewlet.for_display == True]


class SubformViewlet(table.AjaxContainerListing):
    """
    """
    render = ViewPageTemplateFile ("templates/generic-sub-container.pt")
    for_display = True


class SessionViewlet(SubformViewlet):
    
    def __init__(self, context, request, view, manager):
        self.context = context.sessions
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None


class ConsignatoryViewlet(SubformViewlet):
    
    def __init__(self, context, request, view, manager):
        self.context = context.consignatory
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None
        self.for_display = len(self.context) > 0

class GovernmentViewlet(SubformViewlet):


    def __init__(self, context, request, view, manager):
        self.context = context.governments
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None

class MemberOfParliamentViewlet(SubformViewlet):

    def __init__(self, context, request, view, manager):
        self.context = context.parliamentmembers
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None


class SittingAttendanceViewlet(SubformViewlet):

    def __init__(self, context, request, view, manager):
        self.context = context.attendance
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None
        self.for_display = len(self.context) > 0


class SittingReportsViewlet(SubformViewlet):
    def __init__(self, context, request, view, manager):
        self.context = context.sreports
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None
        self.for_display = len(self.context) > 0


class MinistersViewlet(SubformViewlet):
    def __init__(self, context, request, view, manager):

        self.context = context.ministers
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None


class BillsViewlet(SubformViewlet):
    def __init__(self, context, request, view, manager):

        self.context = context.bills
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None

class QuestionsViewlet(SubformViewlet):
    def __init__(self, context, request, view, manager):

        self.context = context.questions
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None

class AgendaItemsViewlet(SubformViewlet):
    def __init__(self, context, request, view, manager):

        self.context = context.agendaitems
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None

class AssignedItemsViewlet(SubformViewlet):
    def __init__(self, context, request, view, manager):

        self.context = context.assigneditems
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None
        self.for_display = len(self.context) > 0

class AssignedGroupsViewlet(SubformViewlet):
    def __init__(self, context, request, view, manager):

        self.context = context.assignedgroups
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None
        self.for_display = len(self.context) > 0


class SittingsViewlet(SubformViewlet):
    def __init__(self, context, request, view, manager):

        self.context = context.sittings
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None
        self.for_display = len(self.context) > 0


class MinistriesViewlet(SubformViewlet):


    def __init__(self, context, request, view, manager):

        self.context = context.ministries
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None





class CommitteesViewlet(SubformViewlet):

    def __init__(self, context, request, view, manager):

        self.context = context.committees
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None



class CommitteeStaffViewlet(SubformViewlet):

    def __init__(self, context, request, view, manager):

        self.context = context.committeestaff
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None




class CommitteeMemberViewlet(SubformViewlet):

    def __init__(self, context, request, view, manager):

        self.context = context.committeemembers
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None


class TitleViewlet (SubformViewlet):

    def __init__(self, context, request, view, manager):

        self.context = context.titles
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None

class AddressesViewlet(SubformViewlet):

    def __init__(self, context, request, view, manager):

        self.context = context.addresses
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None

class PoliticalGroupsViewlet(SubformViewlet):
    def __init__(self, context, request, view, manager):

        self.context = context.politicalgroups
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None

class PartyMemberViewlet(SubformViewlet):
    def __init__(self, context, request, view, manager):

        self.context = context.partymembers
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None

class PartyMembershipViewlet(SubformViewlet):
    def __init__(self, context, request, view, manager):

        self.context = context.party
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None

#class ResponseViewlet( SubformViewlet ):
#    def __init__( self,  context, request, view, manager ):
#
#        self.context = context.responses
#        self.request = request
#        self.__parent__= context
#        self.manager = manager
#        self.query = None


class OfficeMembersViewlet(SubformViewlet):
    def __init__(self, context, request, view, manager):

        self.context = context.officemembers
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None



class PersonInfo(BungeniAttributeDisplay):
    """
    Bio Info / personal data about the MP
    """
    for_display = True
    mode = "view"

    form_name = _(u"Personal Info")

    def __init__(self, context, request, view, manager):
        self.context = context
        self.request = request
        self.__parent__ = context.__parent__
        self.manager = manager
        self.query = None
        md = queryModelDescriptor(domain.User)
        self.form_fields = md.fields #.select('user_id', 'start_date', 'end_date')

    def update(self):
        """
        refresh the query
        """
        session = Session()
        user_id = self.context.user_id
        parent = self.context.__parent__
        self.query = session.query(domain.User).filter(domain.User.user_id == user_id)
        self.context = self.query.all()[0]
        self.context.__parent__ = parent
        super(PersonInfo, self).update()
        #session.close()

class ParliamentMembershipInfo(BungeniAttributeDisplay):
    """ for a given user get his last parliament 
    membership"""
    for_display = True
    mode = "view"
    form_name = _(u"Parliament Membership")

    def __init__(self, context, request, view, manager):
        self.context = context
        self.request = request
        self.__parent__ = context.__parent__
        self.manager = manager
        self.query = None
        md = queryModelDescriptor(domain.MemberOfParliament)
        self.form_fields = md.fields
        session = Session()
        trusted = removeSecurityProxy(self.context)
        user_id = self.context.user_id
        parliament_id = trusted.group.parent_group_id
        self.query = session.query(domain.MemberOfParliament).filter(
            sql.and_(
            domain.MemberOfParliament.user_id == user_id,
            domain.MemberOfParliament.group_id == parliament_id)
            ).order_by(
            domain.MemberOfParliament.start_date.desc())
        self.for_display = self.query.count() > 0
        #session.close()

    def update(self):
        """
        refresh the query
        """
        parent = self.context.__parent__
        try:
            self.context = self.query.all()[0]
        except IndexError:
            self.context = None
            return
        self.context.__parent__ = parent
        super(ParliamentMembershipInfo, self).update()


class InitialQuestionsViewlet(BungeniAttributeDisplay):
    form_name = (u"Initial Questions")


    @property
    def for_display(self):
        return self.context.supplement_parent_id is not None

    def update(self):
        """
        refresh the query
        """
        if self.context.supplement_parent_id is None:
            self.context = self.__parent__
            #self.for_display = False
            return

        session = Session()
        results = session.query(domain.Question).get(self.context.supplement_parent_id)

        if results:
            #parent = self.context.__parent__
            self.context = results
            #self.context.__parent__ = parent
            self.form_name = (u"Initial Questions")
            self.has_data = True
            #self.for_display =True
        else:
            self.has_data = False
            self.context = None

        super(InitialQuestionsViewlet, self).update()
        #session.close()

class ResponseViewlet(BungeniAttributeDisplay):
    """Response to question."""

    mode = "view"
    for_display = True

    form_name = _(u"Response")

    add_action = form.Actions(
        form.Action(_(u'Add response'), success='handle_response_add_action'),
        )

    def __init__(self, context, request, view, manager):
        self.context = context
        self.request = request
        self.__parent__ = view
        self.manager = manager
        self.query = None
        md = queryModelDescriptor(domain.Response)
        self.form_fields = md.fields
        self.add_url = '%s/responses/add' % url.absoluteURL(
            self.context, self.request)

    def handle_response_add_action(self, action, data):
        self.request.response.redirect(self.add_url)

    def update(self):
        context = self.context
        responses = context.responses
        if len(responses):
            self.context = tuple(responses.values())[0]
            self.has_data = True
        else:
            self.context = domain.Response()
            self.has_data = False

        super(ResponseViewlet, self).update()

    def setupActions(self):
        if self.has_data:
            super(ResponseViewlet, self).setupActions()
        else:
            self.actions = self.add_action.actions

class OfficesHeldViewlet(viewlet.ViewletBase):
    for_display = True
    def __init__(self, context, request, view, manager):
        self.context = context
        self.request = request
        self.__parent__ = view
        self.manager = manager
        self.query = None

    def get_offices_held(self):
        office_list = []
        for oh in self.offices_held:
            title = {}
            title['group'] = oh[0] + ' - ' + (oh[1] or'')
            title['group_type'] = oh[2].capitalize()
            if oh[3]:
                title['member_title'] = oh[3]
            else:
                title['member_title'] = _(u"Member")
            if oh[4]:
                title['start_date'] = oh[4]
            else:
                title['start_date'] = oh[6]
            if oh[5]:
                title['end_date'] = oh[5]
            else:
                title['end_date'] = oh[7]
            office_list.append(title)
        return office_list

    def update(self):
        """
        refresh the query
        """
        trusted = removeSecurityProxy(self.context)
        user_id = trusted.user_id
        if interfaces.IMemberOfParliament.providedBy(self.context):
            parliament_id = trusted.group_id
        else:
            parliament = get_parliament_for_group_id(trusted.group_id)
            if parliament:
                parliament_id = parliament.parliament_id
        self.offices_held = get_offices_held_for_user_in_parliament(
                user_id, parliament_id)



    render = ViewPageTemplateFile ('templates/offices_held_viewlet.pt')


class TimeLineViewlet(viewlet.ViewletBase):
    """
    tracker/timeline view:
    
    Chronological changes are aggregated from : bill workflow, bill
    audit, bill scheduling and bill event records. 
    """
    # evoque
    render = z3evoque.ViewTemplateFile("workspace_viewlets.html#timeline")

    # zpt
    #render = ViewPageTemplateFile('templates/timeline_viewlet.pt')

    # sqlalchemy give me a rough time sorting a union, 
    # with hand coded sql it is much easier.
    # !+ get rid of the hard-coded sql
    sql_timeline = ""
    add_action = form.Actions(
        form.Action(_(u'add event'), success='handle_event_add_action'),
    )
    for_display = True
    view_name = "Timeline"
    view_id = "unknown-timeline"

    def __init__(self, context, request, view, manager):
        self.context = context
        self.request = request
        self.__parent__ = view
        self.manager = manager
        self.query = None
        self.formatter = date.getLocaleFormatter(self.request, "dateTime", "medium")

    def handle_event_add_action(self, action, data):
        self.request.response.redirect(self.addurl)

    def update(self):
        """Refresh the query.
        """
        # evaluate serialization of a dict, failure returns an empty dict
        def _eval_as_dict(s):
            try:
                d = eval(s)
                assert isinstance(d, dict)
                return d
            except (SyntaxError, TypeError, AssertionError):
                #debug.log_exc(sys.exc_info(), log_handler=log.info)
                return {}

        # NOTE: only *Change records have a "notes" dict attribute and the 
        # content of this depends on the value of "atype" (see core/audit.py)
        item_id = self.context.parliamentary_item_id
        self.results = [ dict(atype=action, item_id=piid, description=desc,
                              adate=date, notes=_eval_as_dict(notes))
                for action, piid, desc, date, notes in
                queries.execute_sql(self.sql_timeline, item_id=item_id) ]

        # Filter out workflow draft items for anonymous users
        if get_principal_id() in ("zope.anybody",):
            _draft_states = ("draft", "working_draft")
            def show_timeline_item(result):
                if result["atype"] == "workflow":
                    if result["notes"].get("destination") in _draft_states:
                        return False
                return True
            self.results = [ result for result in self.results
                             if show_timeline_item(result) ]

        #change_cls = getattr(domain, "%sChange" % (self.context.__class__.__name__))
        for r in self.results:
            # workflow
            if r["atype"] == "workflow":
                # description
                # the workflow transition change log stores the (unlocalized) 
                # human title for the transition's destination workflow state 
                # -- here we just localize what is supplied:
                r["description"] = _(r["description"])
                # NOTE: we could elaborate an entirely custom description 
                # from scratch e.g via interpolation of a template string:
                '''
                if r["notes"].get("destination", ""):
                    description = "%s %s" % (
                                _("some text"),
                                _(misc.get_wf_state(
                                    self.context, r["notes"]["destination"])))
                '''
            # event
            elif r["atype"] == "event":
                # description 
                r["description"] = """<a href="event/obj-%s">%s</a>""" % (
                        r["item_id"], _(r["description"]))
            # version
            elif r["atype"] == "version":
                # description 
                try:
                    r["description"] = """<a href="versions/obj-%s">%s</a>""" % (
                                    r["notes"]["version_id"], _(r["description"]))
                except (KeyError,):
                    # no recorded version_id, just localize what is supplied
                    r["description"] = _(r["description"])
        #
        path = url.absoluteURL(self.context, self.request)
        self.addurl = '%s/event/add' % (path)

class BillTimeLineViewlet(TimeLineViewlet):
    sql_timeline = statements.sql_bill_timeline
    view_name = _("Timeline")
    view_id = "bill-timeline"

class MotionTimeLineViewlet(TimeLineViewlet):
    sql_timeline = statements.sql_motion_timeline
    view_name = _("Timeline")
    view_id = "motion-timeline"

class QuestionTimeLineViewlet(TimeLineViewlet):
    sql_timeline = statements.sql_question_timeline
    view_name = _("Timeline")
    view_id = "question-timeline"

class TableddocumentTimeLineViewlet(TimeLineViewlet):
    sql_timeline = statements.sql_tableddocument_timeline
    view_name = _("Timeline")
    view_id = "tableddocument-timeline"

class AgendaItemTimeLineViewlet(TimeLineViewlet):
    sql_timeline = statements.sql_agendaitem_timeline
    view_name = _("Timeline")
    view_id = "agendaitem-timeline"

class MemberItemsViewlet(viewlet.ViewletBase):
    """A tab with bills, motions etc for an MP 
    (the "parliamentary activities" tab of of the "member" view)
    """
    for_display = True
    states = \
        get_states("agendaitem", tagged=["public"]) + \
        get_states("bill", not_tagged=["private"]) + \
        get_states("motion", tagged=["public"]) + \
        get_states("question", tagged=["public"]) + \
        get_states("tableddocument", tagged=["public"])

    def __init__(self, context, request, view, manager):
        print "MemberItemsViewlet.INIT", vars()
        session = Session()
        self.context = context
        user_id = self.context.user_id
        parliament_id = self.context.group_id
        self.request = request
        self.__parent__ = view
        self.manager = manager
        self.query = session.query(domain.ParliamentaryItem).filter(
            sql.and_(
                domain.ParliamentaryItem.owner_id == user_id,
                domain.ParliamentaryItem.parliament_id == parliament_id,
                domain.ParliamentaryItem.status.in_(self.states),
            )).order_by(domain.ParliamentaryItem.parliamentary_item_id.desc())
        #self.for_display = (self.query.count() > 0)
        #session.close()

    def results(self):
        for result in self.query.all():
            _url = '/business/%ss/obj-%i' % (result.type,
                result.parliamentary_item_id)
            yield {'type': result.type,
                'short_name': result.short_name,
                'status': misc.get_wf_state(result),
                'submission_date' : result.submission_date.strftime('%Y-%m-%d'),
                'url': _url }

    render = ViewPageTemplateFile ('templates/mp_item_viewlet.pt')

class DisplayViewlet(BungeniAttributeDisplay):
    """Display a target object; if the object is `None`, the user is
    prompted to add it."""

    render = ViewPageTemplateFile ('templates/display_form.pt')
    mode = 'view'
    for_display = True
    query = None
    factory = None
    has_data = False
    form_fields = form.Fields()

    add_action = form.Actions(
        form.Action(_(u"Add"), success='handle_add'),
        )

    def __init__(self, context, request, view, manager):
        super(DisplayViewlet, self).__init__(
            context, request, view, manager)

        # set add url before we change context
        self.add_url = self.get_add_url()

        target = self.get_target()
        if target is None:
            self.status = _(u"No item has been set")
        else:
            self.context = target
            self.has_data = True

            assert self.factory is not None
            descriptor = queryModelDescriptor(self.factory)
            self.form_fields = descriptor.fields

    def update(self):
        # only if there's data to display do we update using our
        # immediate superclass
        if self.has_data:
            super(DisplayViewlet, self).update()
        else:
            self.setupActions()
            super(form.SubPageDisplayForm, self).update()

    def handle_add(self, action, data):
        self.request.response.redirect(self.add_url)

    def get_add_url(self):
        raise NotImplementedError("Must be implemented by subclass.")

    def get_target(self):
        raise NotImplementedError("Must be implemented by subclass.")

    def set_target(self, target):
        raise NotImplementedError("Must be implemented by subclass.")

    def setupActions(self):
        if self.has_data:
            super(DisplayViewlet, self).setupActions()
        else:
            self.actions = self.add_action.actions

    @property
    def form_name(self):
        descriptor = queryModelDescriptor(self.factory)
        return descriptor.display_name


class SchedulingMinutesViewlet(DisplayViewlet):
    factory = domain.ScheduledItemDiscussion

    def get_target(self):
        return self.context.discussion

    def set_target(self, target):
        self.context.discussion = target

    def get_add_url(self):
        return '%s/discussions/add' % url.absoluteURL(
            self.context, self.request)


class SessionCalendarViewlet(viewlet.ViewletBase):
    """
    display a monthly calendar with all sittings for a session
    """
    def __init__(self, context, request, view, manager):
        self.context = context
        self.request = request
        self.__parent__ = view
        self.manager = manager
        self.query = None
        self.Date = datetime.date.today()
        self.Data = []
        session = Session()
        self.type_query = session.query(domain.SittingType)
        #session.close()

    def _getDisplayDate(self, request):
        display_date = date.getDisplayDate(self.request)
        session = self.context
        if display_date:
            if session.end_date:
                if display_date > session.end_date:
                    display_date = session.end_date
            if session.start_date > display_date:
                display_date = session.start_date
        else:
            display_date = session.end_date
        return display_date

    def current_sittings_query(self, date):
        session = removeSecurityProxy(self.context)
        group_id = session.parliament_id
        start_date = session.start_date
        if start_date.month < date.month:
            start_date = datetime.date(date.year, date.month, 1)
        end_date = session.end_date
        if end_date:
            if end_date.month > date.month:
                end_date = date + relativedelta.relativedelta(day=31)
        else:
            end_date = date + relativedelta.relativedelta(day=31)
        session = Session()

        s_filter = sql.and_(
                domain.GroupSitting.group_id == group_id,
                sql.between(
                    domain.GroupSitting.start_date,
                    start_date, end_date)
                    )
        return session.query(domain.GroupSitting).filter(s_filter).order_by(
                domain.GroupSitting.start_date)


    def previous(self):
        """
        return link to the previous month 
        if the session start date is prior to the current month
        """
        session = self.context
        if self.Date.month == 1:
            month = 12
            year = self.Date.year - 1
        else:
            month = self.Date.month - 1
            year = self.Date.year
        try:
            prevdate = datetime.date(year, month, self.Date.day)
        except:
            # in case we try to move to Feb 31st (or so)
            prevdate = datetime.date(year, month, 15)
        if session.start_date < datetime.date(
                self.Date.year, self.Date.month, 1):
            return ('<a href="?date='
                + datetime.date.strftime(prevdate, '%Y-%m-%d')
                + '"> &lt;&lt; </a>')
        else:
            return ""

    def next(self):
        """
        return link to the next month if the end date
        of the session is after the 1st of the next month
        """
        session = self.context
        if self.Date.month == 12:
            month = 1
            year = self.Date.year + 1
        else:
            month = self.Date.month + 1
            year = self.Date.year
        try:
            nextdate = datetime.date(year, month, self.Date.day)
        except:
            # if we try to move from 31 of jan to 31 of feb or so
            nextdate = datetime.date(year, month, 15)
        if session:
            if session.end_date:
                if session.end_date < datetime.date(year, month, 1):
                    return ""
        return ('<a href="?date='
                + datetime.date.strftime(nextdate, '%Y-%m-%d')
                + '"> &gt;&gt; </a>')


    def getData(self):
        """
        return the data of the query
        """
        sit_types = {}
        type_results = self.type_query.all()
        for sit_type in type_results:
            sit_types[sit_type.sitting_type_id] = sit_type.sitting_type
        data_list = []
        path = '/calendar/group/sittings/'
        results = self.query.all()
        for result in results:
            data = {}
            data['sittingid'] = ('sid_' + str(result.sitting_id))
            data['sid'] = result.sitting_id
            data['short_name'] = (datetime.datetime.strftime(result.start_date, '%H:%M')
                                    + ' - ' + datetime.datetime.strftime(result.end_date, '%H:%M')
                                    + ' (' + sit_types[result.sitting_type_id] + ')')
            data['start_date'] = result.start_date
            data['end_date'] = result.end_date
            data['start_time'] = result.start_date.time()
            data['end_time'] = result.end_date.time()
            data['day'] = result.start_date.date()
            data['url'] = (path + 'obj-' + str(result.sitting_id))
            data['did'] = ('dlid_' + datetime.datetime.strftime(result.start_date, '%Y-%m-%d') +
                           '_stid_' + str(result.sitting_type))
            data_list.append(data)
        return data_list

    def getTdId(self, Date):
        """
        return an Id for that td element:
        consiting of tdid- + date
        like tdid-2008-01-17
        """
        return 'tdid-' + datetime.date.strftime(Date, '%Y-%m-%d')

    def getDayClass(self, Date):
        """
        return the class settings for that calendar day
        """
        css_class = ""
        if self.Date.month != Date.month:
            css_class = css_class + "other-month "
        if Date < datetime.date.today():
            css_class = css_class + "past-date "
        if Date == datetime.date.today():
            css_class = css_class + "current-date "
        if Date.weekday() in prefs.getWeekendDays():
            css_class = css_class + "weekend-date "
        session = Session()
        query = session.query(domain.HoliDay).filter(domain.HoliDay.holiday_date == Date)
        results = query.all()
        if results:
            css_class = css_class + "holyday-date "
        #session.close()
        return css_class.strip()

    def getWeekNo(self, Date):
        """
        return the weeknumber for a given date
        """
        return Date.isocalendar()[1]


    def getSittings4Day(self, Date):
        """
        return the sittings for that day
        """
        day_data = []
        for data in self.Data:
            if data['day'] == Date:
                day_data.append(data)
        return day_data


    def update(self):
        """
        refresh the query
        """
        self.Date = self._getDisplayDate(self.request)
        if not self.Date:
            self.Date = datetime.date.today()
        self.query = self.current_sittings_query(self.Date)
        self.monthcalendar = calendar.Calendar(prefs.getFirstDayOfWeek()).monthdatescalendar(self.Date.year, self.Date.month)
        self.monthname = datetime.date.strftime(self.Date, '%B %Y')
        self.Data = self.getData()

    render = ViewPageTemplateFile ('templates/session_calendar_viewlet.pt')
