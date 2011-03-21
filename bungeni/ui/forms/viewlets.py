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
from zope.viewlet import manager, viewlet
from zope.app.pagetemplate import ViewPageTemplateFile

from zope.formlib import form
from zope.security.proxy import removeSecurityProxy

import sqlalchemy.sql.expression as sql

from bungeni.alchemist.ui import DynamicFields, EditFormViewlet
from bungeni.alchemist import Session
from bungeni.alchemist.model import queryModelDescriptor

from bungeni.models import domain, interfaces
from bungeni.models.utils import get_offices_held_for_user_in_parliament
from bungeni.models.utils import get_parliament_for_group_id
from bungeni.models.utils import get_principal_id
from bungeni.ui.i18n import _
import bungeni.core.globalsettings as prefs

from bungeni.ui.tagged import get_states
from bungeni.ui import browser
from bungeni.ui import z3evoque
from bungeni.ui import table
from bungeni.ui.utils import queries, statements, url, misc, debug, date
from bungeni.ui.browser import BungeniViewlet
from fields import BungeniAttributeDisplay
from interfaces import ISubFormViewletManager, ISubformRssSubscriptionViewletManager
from bungeni.ui.interfaces import IAdminSectionLayer

''' XXX-INFO-FOR-PLONE - MR - 2010-05-03
class GroupIdViewlet(browser.BungeniViewlet):
    """ display the group and parent group
    principal id """
    parent_group_principal_id = None
    my_group_principal_id = None
    
    def __init__(self,  context, request, view, manager):
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
            self.parent_group_principal_id = getattr(
                trusted.parent_group, 'group_principal_id', "")
        self.my_group_principal_id = trusted.group_principal_id
        #session.close()
        
    render = ViewPageTemplateFile('templates/group_id.pt')
'''
''' XXX-INFO-FOR-PLONE - MR - 2010-05-03
class UserIdViewlet(browser.BungeniViewlet):
    """ display the users
    principal id """
    principal_id = None
    
    def __init__(self,  context, request, view, manager):

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
        
    render = ViewPageTemplateFile('templates/user_id.pt')
'''


# !+SubformViewlet(mr, oct-2010) in this usage case this this should really
# be made to inherit from browser.BungeniViewlet (but, note that
# table.AjaxContainerListing already inherits from BungeniBrowserView). 

class SubFormViewletManager(manager.WeightOrderedViewletManager):
    """Display subforms.
    """
    interface.implements(ISubFormViewletManager)

    def filter(self, viewlets):
        viewlets = super(SubFormViewletManager, self).filter(viewlets)
        return [ (name, viewlet)
                  for name, viewlet in viewlets
                  if viewlet.for_display == True ]


class SubformViewlet(table.AjaxContainerListing):
    """A container listing of the items indicated by "sub_attr_name". 
    """
    # evoque
    render = z3evoque.ViewTemplateFile("container.html#generic_sub")

    # zpt
    #render = ViewPageTemplateFile("templates/generic-sub-container.pt")

    def __init__(self, context, request, view, manager):
        # The parent for SubformViewlets is the context (not the view)
        self.__parent__ = context
        self._context = context
        # !+_context(mr, oct-2010) using self.__parent__ to get to context 
        # gives recursion error: 
        # zope/publisher/browser.py", line 849, in __getParent 
        # return getattr(self, '_parent', self.context)
        self.request = request
        self.manager = manager

    sub_attr_name = None
    @property
    def context(self):
        return getattr(self._context, self.sub_attr_name)

    @property
    def view_name(self):
        return self.sub_attr_name # self.context.__name__

    @property
    def for_display(self):
        return len(self.context) > 0


class SubformRssSubscriptionViewletManager(manager.WeightOrderedViewletManager):
    """ Displays rss subscription data 
    """
    interface.implements(ISubformRssSubscriptionViewletManager)


class RssLinkViewlet(viewlet.ViewletBase):
    """ Simply renders link for users to subscribe
        to the current paliamentary item
    """
    render = ViewPageTemplateFile("templates/rss_link.pt")

    @property
    def already_subscribed(self):
        """ Checks if user has already
            subscribed to the current
            item
        """
        session = Session()
        user = session.query(domain.User).filter(domain.User.login == self.request.principal.id).first()
        # If we've hot found the user we should not allow to subscribe
        if user is None:
            return True
        return removeSecurityProxy(self.context) in user.subscriptions


class SessionViewlet(SubformViewlet):
    sub_attr_name = "sessions"

class CosignatoryViewlet(SubformViewlet):
    sub_attr_name = "cosignatory"

class GovernmentViewlet(SubformViewlet):
    sub_attr_name = "governments"

class MemberOfParliamentViewlet(SubformViewlet):
    sub_attr_name = "parliamentmembers"

class SittingAttendanceViewlet(SubformViewlet):
    sub_attr_name = "attendance"

class SittingReportsViewlet(SubformViewlet):
    form_name = "Reports" # !+
    sub_attr_name = "sreports"

class MinistersViewlet(SubformViewlet):
    sub_attr_name = "ministers"

class BillsViewlet(SubformViewlet):
    sub_attr_name = "bills"

class QuestionsViewlet(SubformViewlet):
    sub_attr_name = "questions"

class AgendaItemsViewlet(SubformViewlet):
    sub_attr_name = "agendaitems"

class AssignedItemsViewlet(SubformViewlet):
    sub_attr_name = "assigneditems"

class AssignedGroupsViewlet(SubformViewlet):
    sub_attr_name = "assignedgroups"

class MinistriesViewlet(SubformViewlet):
    sub_attr_name = "ministries"

class CommitteesViewlet(SubformViewlet):
    sub_attr_name = "committees"

class CommitteeStaffViewlet(SubformViewlet):
    sub_attr_name = "committeestaff"

class AddressesViewlet(SubformViewlet):
    sub_attr_name = "addresses"

class PoliticalGroupsViewlet(SubformViewlet):
    sub_attr_name = "politicalgroups"

class PartyMemberViewlet(SubformViewlet):
    sub_attr_name = "partymembers"

class OfficeMembersViewlet(SubformViewlet):
    sub_attr_name = "officemembers"


# BungeniAttributeDisplay
# !+BungeniViewlet(mr) make these inherit from BungeniViewlet

class PersonInfo(BungeniAttributeDisplay):
    """Bio Info / personal data about the MP.
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
        self.form_fields = md.fields #.select("user_id", "start_date", "end_date")

    def update(self):
        user_id = self.context.user_id
        parent = self.context.__parent__
        self.query = Session().query(domain.User
            ).filter(domain.User.user_id == user_id)
        self.context = self.query.all()[0]
        self.context.__parent__ = parent
        super(PersonInfo, self).update()


'''
class ParliamentMembershipInfo(BungeniAttributeDisplay):
    """ for a given user get his last parliament 
    membership.
    """
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
        trusted = removeSecurityProxy(self.context)
        user_id = self.context.user_id
        parliament_id = trusted.group.parent_group_id
        self.query = Session().query(domain.MemberOfParliament).filter(
            sql.and_(
                domain.MemberOfParliament.user_id == user_id,
                domain.MemberOfParliament.group_id == parliament_id)
            ).order_by(
                domain.MemberOfParliament.start_date.desc()
            )
        self.for_display = self.query.count() > 0
    
    def update(self):
        parent = self.context.__parent__
        try:
            self.context = self.query.all()[0]
        except IndexError:
            self.context = None
            return
        self.context.__parent__ = parent
        super(ParliamentMembershipInfo, self).update()
'''

class ParliamentaryItemMinutesViewlet(BungeniAttributeDisplay):

    mode = "view"
    for_display = True

    form_name = _(u"Minutes")

    def __init__(self, context, request, view, manager):
        self.request = request
        self.context = context
        self.manager = manager
        trusted = removeSecurityProxy(context)
        try:
            item_id = trusted.parliamentary_item_id
        except AttributeError:
            self.for_display = False
            return
        self.query = Session().query(domain.ItemScheduleDiscussion).filter(
            sql.and_(
                domain.ItemScheduleDiscussion.schedule_id == \
                    domain.ItemSchedule.schedule_id,
                domain.ItemSchedule.item_id == item_id
            )
        )
        #self.context = self.query.all()[0]
        self.for_display = self.query.count() > 0

    def update(self):
        parent = self.context.__parent__
        try:
            self.context = self.query.all()[0]
        except IndexError:
            self.context = None
            return

        self.context.__parent__ = parent
        super(ParliamentaryItemMinutesViewlet, self).update()


class InitialQuestionsViewlet(BungeniAttributeDisplay):
    form_name = (u"Initial Questions")

    @property
    def for_display(self):
        return self.context.supplement_parent_id is not None

    def update(self):
        if self.context.supplement_parent_id is None:
            self.context = self.__parent__
            #self.for_display = False
            return
        results = Session().query(domain.Question
            ).get(self.context.supplement_parent_id)
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

'''
class ResponseViewlet(BungeniAttributeDisplay):
    """Response to question.
    """
    mode = "view"
    for_display = True
    
    form_name = _(u"Response")
    
    add_action = form.Actions(
        form.Action(_(u"Add response"), success="handle_response_add_action"),
    )
    
    def __init__(self, context, request, view, manager):
        self.context = context
        self.request = request
        self.__parent__ = view
        self.manager = manager
        self.query = None
        md = queryModelDescriptor(domain.Response)
        self.form_fields = md.fields
        self.add_url = "%s/responses/add" % url.absoluteURL(
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
'''


class WrittenQuestionResponseViewlet(BungeniViewlet):

    mode = "view"
    for_display = True
    form_name = _(u"Response")
    render = ViewPageTemplateFile("templates/written_question_response.pt")
    def __init__(self, context, request, view, manager):
        self.request = request
        self.context = context
        self.manager = manager
        self.question = removeSecurityProxy(context)
        # Check type of question. Only written questions get this viewlet
        if self.question.response_type == 'O':
            self.for_display = False
        else:
            if self.question.response_text in (None,""):
                self.for_display = False
        
class GroupMembersViewlet(browser.BungeniItemsViewlet):

    # evoque
    render = z3evoque.ViewTemplateFile("workspace_viewlets.html#group_members")

    view_title = _("Members")
    view_id = "group-members"

    def build_member_url(self, member):
        return url.absoluteURL(member, self.request)

    def _get_members(self):
        """Get the list of members of the context group.
        """
        raise NotImplementedError("Must be implemented by subclass.")

    def update(self):
        session = Session()
        group_members = self._get_members()
        mpkls = domain.MemberOfParliament
        formatter = self.get_date_formatter("date", "long")
        self.items = [{
                "fullname": m.user.fullname,
                "url": self.build_member_url(m),
                "start_date":
                    m.start_date and formatter.format(m.start_date) or None,
                "end_date":
                    m.end_date and formatter.format(m.end_date) or None
            }
            for m in group_members
        ]

class CommitteeMembersViewlet(GroupMembersViewlet):
        
    def _get_members(self):
        trusted = removeSecurityProxy(self.context)
        return list(trusted.committeemembers.values())

class PoliticalGroupMembersViewlet(GroupMembersViewlet):

    @property
    def members_container_url(self):
        # !+traversal(murithi, mar-2010) ideally no urls should be
        # hardcoded here. absoluteURL should work for memberships or
        # members of groups [ to improve on getting urls of children ]
        if IAdminSectionLayer.providedBy(self.request):
            trusted = removeSecurityProxy(self.context)
            m_container = trusted.__parent__.__parent__.parliamentmembers
            return url.absoluteURL(m_container, self.request)
        return "/members/current"

    def build_member_url(self, member):
        if IAdminSectionLayer.providedBy(self.request):
            return super(PoliticalGroupMembersViewlet, self).build_member_url(
                member
            )
        session = Session()
        mpkls = domain.MemberOfParliament
        member_url = "%s/obj-%d/" % (self.members_container_url, 
            session.query(mpkls).filter(mpkls.user_id == member.user_id).one(
            ).membership_id
        )
        return member_url

    def _get_members(self):
        trusted = removeSecurityProxy(self.context)
        return list(trusted.partymembers.values())

class GroupSittingsViewlet(browser.BungeniItemsViewlet):
    """Display the sittings of a group. 
    
    Note 1: to be able to customize the URL for each sitting, this custom 
    viewlet replaces the previous model-introspected container listing:
        class GroupSittingsViewlet(SubformViewlet):
            sub_attr_name = "sittings"
    so replacing a url of the form: 
            .../committees/obj-59/sittings/obj-17/
    with:   /business/sittings/obj-17
    
    Note 2: this viewlet should probably be merged or better share the 
    implementation at: ui.workspace.DraftSittingsViewlet
    
    !+CustomListingURL(mr, oct-2010) an alternative way to do this is to 
    essentially stuff all the logic below into a custom column_listing to be 
    used when listing the column -- for an example of this see how the 
    listing of the column "owner_id" (moved by) is configured in:
    descriptor.ParliamentaryItemDescriptor
    
    !+ManagedContainer(mr, oct-2010) this would have been a lot simpler if
    the Group.sittings attribute was simply returning the list of sitting
    objects.
    """

    # evoque
    render = z3evoque.ViewTemplateFile("workspace_viewlets.html#group_sittings")

    view_title = "Sittings"
    view_id = "sittings"

    def _get_items(self):
        def _format_from_to(item):
            start = item.start_date
            if start:
                start = dt_formatter.format(start)
            end = item.end_date
            if end:
                end = t_formatter.format(end)
            return u"%s - %s" % (start, end)
        dt_formatter = self.get_date_formatter("dateTime", "medium")
        t_formatter = self.get_date_formatter("time", "medium")
        def _format_venue(item):
            return item.venue and _(item.venue.short_name) or ""
        #
        trusted_context = removeSecurityProxy(self.context)
        sittings = Session().query(domain.GroupSitting
            ).filter(domain.GroupSitting.group == trusted_context
            ).order_by(domain.GroupSitting.start_date.desc())
        return [{"url": "/business/sittings/obj-%s" % (item.group_sitting_id),
                 "date_from_to": _format_from_to(item),
                 "venue": _format_venue(item)
                } for item in sittings ]

    def update(self):
        self.items = self._get_items()


class OfficesHeldViewlet(browser.BungeniItemsViewlet):

    # evoque
    render = z3evoque.ViewTemplateFile("workspace_viewlets.html#offices_held")

    # zpt
    #render = ViewPageTemplateFile("templates/offices_held_viewlet.pt")

    view_title = "Offices held"
    view_id = "offices-held"

    def _get_items(self):
        formatter = self.get_date_formatter("date", "long")
        trusted = removeSecurityProxy(self.context)
        user_id = trusted.user_id
        office_list = []
        if interfaces.IMemberOfParliament.providedBy(self.context):
            parliament_id = trusted.group_id
        else:
            parliament = get_parliament_for_group_id(trusted.group_id)
            if parliament:
                parliament_id = parliament.parliament_id
            else:
                return office_list
        for oh in get_offices_held_for_user_in_parliament(user_id):
            title = {}
            # !+FULL_NAME(mr, oct-2010) this should probably make use of 
            # the GroupDescriptor (combined) listing Field full_name
            title["group"] = "%s - %s" % (_(oh[0]), oh[1] and _(oh[1]) or "")
            title["group_type"] = _(oh[2])
            if oh[3]:
                title["member_title"] = _(oh[3])
            else:
                title["member_title"] = _(u"Member")
            title["start_date"] = None
            if oh[4]:
                title["start_date"] = formatter.format(oh[4])
            elif oh[6]:
                title["start_date"] = formatter.format(oh[6])
            title["end_date"] = None
            if oh[5]:
                title["end_date"] = formatter.format(oh[5])
            elif oh[7]:
                title["end_date"] = formatter.format(oh[7])
            office_list.append(title)
        return office_list

    def update(self):
        self.items = self._get_items()



class TimeLineViewlet(browser.BungeniItemsViewlet):
    """
    tracker/timeline view:
    
    Chronological changes are aggregated from : bill workflow, bill
    audit, bill scheduling and bill event records. 
    """
    # evoque
    render = z3evoque.ViewTemplateFile("workspace_viewlets.html#timeline")

    # zpt
    #render = ViewPageTemplateFile("templates/timeline_viewlet.pt")

    # sqlalchemy give me a rough time sorting a union, 
    # with hand coded sql it is much easier.
    # !+ get rid of the hard-coded sql
    sql_timeline = ""
    add_action = form.Actions(
        form.Action(_(u"add event"), success="handle_event_add_action"),
    )
    view_title = "Timeline"
    view_id = "unknown-timeline"

    def __init__(self, context, request, view, manager):
        super(TimeLineViewlet, self).__init__(context, request, view, manager)
        self.formatter = self.get_date_formatter("dateTime", "medium")

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

        # !+CHANGE_EXTRAS(mr, dec-2010)
        # only *Change records have an extras dict (as "notes" str attr) and the 
        # content of this depends on the value of "atype" (see core/audit.py)
        item_id = self.context.parliamentary_item_id
        self.items = [ dict(atype=action, item_id=piid, description=desc,
                              adate=date, notes=_eval_as_dict(notes))
                for action, piid, desc, date, notes in
                queries.execute_sql(self.sql_timeline, item_id=item_id) ]

        # Filter out workflow draft items for anonymous users
        if get_principal_id() in ("zope.anybody",):
            _draft_states = ("draft", "working_draft")
            def show_timeline_item(item):
                if item["atype"] == "workflow":
                    if item["notes"].get("destination") in _draft_states:
                        return False
                return True
            self.items = [ item for item in self.items
                             if show_timeline_item(item) ]

        #change_cls = getattr(domain, "%sChange" % (self.context.__class__.__name__))
        for r in self.items:
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
        self.addurl = "%s/event/add" % (path)


class BillTimeLineViewlet(TimeLineViewlet):
    sql_timeline = statements.sql_bill_timeline
    view_id = "bill-timeline"


class MotionTimeLineViewlet(TimeLineViewlet):
    sql_timeline = statements.sql_motion_timeline
    view_id = "motion-timeline"


class QuestionTimeLineViewlet(TimeLineViewlet):
    sql_timeline = statements.sql_question_timeline
    view_id = "question-timeline"


class TableddocumentTimeLineViewlet(TimeLineViewlet):
    sql_timeline = statements.sql_tableddocument_timeline
    view_id = "tableddocument-timeline"


class AgendaItemTimeLineViewlet(TimeLineViewlet):
    sql_timeline = statements.sql_agendaitem_timeline
    view_id = "agendaitem-timeline"


class MemberItemsViewlet(browser.BungeniItemsViewlet):
    """A tab with bills, motions etc for an MP 
    (the "parliamentary activities" tab of of the "member" view)
    """
    states = \
        get_states("agendaitem", tagged=["public"]) + \
        get_states("bill", not_tagged=["private"]) + \
        get_states("motion", tagged=["public"]) + \
        get_states("question", tagged=["public"]) + \
        get_states("tableddocument", tagged=["public"])

    view_title = "Parliamentary activities"
    view_id = "mp-items"

    # evoque
    render = z3evoque.ViewTemplateFile("workspace_viewlets.html#mp_items")

    # zpt
    #render = ViewPageTemplateFile("templates/mp_item_viewlet.pt")

    def __init__(self, context, request, view, manager):
        super(MemberItemsViewlet, self).__init__(
            context, request, view, manager)
        user_id = self.context.user_id
        parliament_id = self.context.group_id
        self.query = Session().query(domain.ParliamentaryItem).filter(
            sql.and_(
                domain.ParliamentaryItem.owner_id == user_id,
                domain.ParliamentaryItem.parliament_id == parliament_id,
                domain.ParliamentaryItem.status.in_(self.states),
            )).order_by(domain.ParliamentaryItem.parliamentary_item_id.desc())
        #self.for_display = (self.query.count() > 0)
        self.formatter = self.get_date_formatter("date", "medium")

    @property
    def items(self):
        for item in self.query.all():
            _url = "/business/%ss/obj-%i" % (item.type,
                item.parliamentary_item_id)
            yield {"type": item.type,
                "short_name": item.short_name,
                "status": misc.get_wf_state(item),
                "submission_date" : item.submission_date,
                "url": _url }


class DisplayViewlet(BungeniAttributeDisplay):
    """Display a target object; if the object is `None`, the user is
    prompted to add it.
    """

    mode = "view"
    for_display = True
    query = None
    factory = None
    has_data = False
    form_fields = form.Fields()

    add_action = form.Actions(
        form.Action(_(u"Add"), success="handle_add"),
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
    factory = domain.ItemScheduleDiscussion

    def get_target(self):
        return self.context.discussion

    def set_target(self, target):
        self.context.discussion = target

    def get_add_url(self):
        return "%s/discussions/add" % url.absoluteURL(
            self.context, self.request)


class SessionCalendarViewlet(browser.BungeniItemsViewlet):
    """Display a monthly calendar with all sittings for a session.
    """
    def __init__(self, context, request, view, manager):
        super(SessionCalendarViewlet, self).__init__(
            context, request, view, manager)
        self.query = None
        self.Date = datetime.date.today() # !+ self.today
        self.type_query = Session().query(domain.GroupSittingType)

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

        s_filter = sql.and_(
            domain.GroupSitting.group_id == group_id,
            sql.between(
                domain.GroupSitting.start_date,
                start_date, end_date
            )
        )
        return Session().query(domain.GroupSitting).filter(s_filter).order_by(
                domain.GroupSitting.start_date)

    def previous(self):
        """Return link to the previous month, 
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
            return """<a href="?date=%s"> &lt;&lt; </a>""" % (
                datetime.date.strftime(prevdate, "%Y-%m-%d"))
        else:
            return ""

    def next(self):
        """Return link to the next month if the end date,
        if the session is after the 1st of the next month
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
        return """<a href="?date=%s"> &gt;&gt; </a>""" % (
            datetime.date.strftime(nextdate, "%Y-%m-%d"))

    def _get_items(self):
        """
        return the data of the query
        """
        sit_types = {}
        type_results = self.type_query.all()
        #Sitting type is commented out below because it is not set during
        #creation of a sitting but is left here because it may be used in the
        #future related to r7243
        #for sit_type in type_results:
        #    sit_types[sit_type.group_sitting_type_id] = sit_type.group_sitting_type
        data_list = []
        path = "/calendar/group/sittings/"
        formatter = self.get_date_formatter("time", "short")
        for result in self.query.all():
            data = {}
            data["sittingid"] = ("sid_" + str(result.group_sitting_id))
            data["sid"] = result.group_sitting_id
            data["short_name"] = "%s - %s" % (
                formatter.format(result.start_date),
                formatter.format(result.end_date)
            )
            data["start_date"] = result.start_date
            data["end_date"] = result.end_date
            data["start_time"] = result.start_date.time()
            data["end_time"] = result.end_date.time()
            data["day"] = result.start_date.date()
            data["url"] = (path + "obj-" + str(result.group_sitting_id))
            data["did"] = ("dlid_" +
                datetime.datetime.strftime(result.start_date, "%Y-%m-%d")
                # +"_stid_" + str(result.group_sitting_type)
            )
            data_list.append(data)
        return data_list

    def getTdId(self, date):
        """
        return an Id for that td element:
        consiting of tdid- + date
        like tdid-2008-01-17
        """
        return "tdid-" + datetime.date.strftime(date, "%Y-%m-%d")

    def getDayClass(self, Date):
        """Return the class settings for that calendar day.
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
        query = Session().query(domain.HoliDay
            ).filter(domain.HoliDay.holiday_date == Date)
        results = query.all()
        if results:
            css_class = css_class + "holyday-date "
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
        for data in self.items:
            if data["day"] == Date:
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
        self.monthcalendar = calendar.Calendar(prefs.getFirstDayOfWeek()
            ).monthdatescalendar(self.Date.year, self.Date.month)
        self.monthname = datetime.date.strftime(self.Date, "%B %Y")
        self.items = self._get_items()

    render = ViewPageTemplateFile("templates/session_calendar_viewlet.pt")

