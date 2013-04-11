# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Forms Viewlets

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.forms.viewlets")

from zope import interface
from zope.i18n import translate
from zope.viewlet import manager, viewlet
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.formlib import form
from zope.security.proxy import removeSecurityProxy
from zc.resourcelibrary import need
from zope.dublincore.interfaces import IDCDescriptiveProperties
import sqlalchemy.sql.expression as sql

#from bungeni.alchemist.ui import DynamicFields, EditFormViewlet
from bungeni.alchemist import Session
from bungeni.alchemist import utils
from bungeni.alchemist.interfaces import IContentViewManager

from bungeni.models import domain, interfaces

from bungeni.ui.i18n import _
from bungeni.ui import browser
from bungeni.ui import table
from bungeni.ui.utils import misc
from fields import BungeniAttributeDisplay
from interfaces import (ISubFormViewletManager,
                        ISubformRssSubscriptionViewletManager)
from bungeni.ui.interfaces import IBungeniAuthenticatedSkin
from bungeni.utils import register
from bungeni.capi import capi

# !+SubformViewlet(mr, oct-2010) in this usage case this this should really
# be made to inherit from browser.BungeniViewlet (but, note that
# table.AjaxContainerListing already inherits from BungeniBrowserView).


@register.viewlet_manager(name="bungeni.subform.manager")
class SubFormViewletManager(manager.WeightOrderedViewletManager):
    """Display subforms.
    """
    interface.implements(ISubFormViewletManager)

    def filter(self, viewlets):
        viewlets = super(SubFormViewletManager, self).filter(viewlets)
        return [
            (name, viewlet) for name, viewlet in viewlets
            if viewlet.for_display ]


class SubformViewlet(table.AjaxContainerListing):
    """A container listing of the items indicated by "sub_attr_name".
    """

    template = ViewPageTemplateFile("templates/generic-sub-container.pt")

    def render(self):
        need("yui-datatable")
        return self.template()

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


# RSS

@register.viewlet_manager(name="bungeni.content.rss")
class SubformRssSubscriptionViewletManager(manager.WeightOrderedViewletManager):
    """Displays rss subscription data."""
    interface.implements(ISubformRssSubscriptionViewletManager)

# !+ IDoc but not IEvent
@register.viewlet(interfaces.IBungeniParliamentaryContent, 
    layer=IBungeniAuthenticatedSkin, 
    manager=ISubformRssSubscriptionViewletManager,
    name="keep-zca-happy-rsslink",
    protect=register.PROTECT_VIEWLET_PUBLIC)
class RssLinkViewlet(viewlet.ViewletBase):
    """Simply renders link for users to subscribe to current paliamentary item.
    """
    render = ViewPageTemplateFile("templates/rss-link.pt")
    
    @property
    def already_subscribed(self):
        """Checks if user has already subscribed to the current item.
        """
        session = Session()
        user = session.query(domain.User).filter(
                domain.User.login == self.request.principal.id).first()
        # If we've not found the user we should not allow to subscribe
        if user is None:
            return True
        return removeSecurityProxy(self.context) in user.subscriptions

#

@register.viewlet(interfaces.IParliament,
    manager=IContentViewManager,
    name="bungeni.viewlet.session",
    protect=register.PROTECT_VIEWLET_PUBLIC)
class SessionViewlet(SubformViewlet):
    sub_attr_name = "sessions"
    weight = 50

class SignatoriesViewlet(SubformViewlet):
    sub_attr_name = "signatories"


@register.viewlet(interfaces.IParliament,
    manager=IContentViewManager,
    name="bungeni.viewlet.member-of-parliament",
    protect=register.PROTECT_VIEWLET_PUBLIC)
class MemberOfParliamentViewlet(SubformViewlet):
    sub_attr_name = "parliamentmembers"
    weight = 20

class SittingAttendanceViewlet(SubformViewlet):
    sub_attr_name = "attendance"
    weight = 55

class SittingReportsViewlet(SubformViewlet):
    form_name = "Reports" # !+
    sub_attr_name = "sreports"
    weight = 60

@register.viewlet(interfaces.ISitting,
    manager=ISubFormViewletManager,
    name="bungeni.viewlet.sitting-items",
    protect={"bungeni.item_schedule.View": register.VIEWLET_DEFAULT_ATTRS})
class SittingScheduleViewlet(SubformViewlet):
    sub_attr_name = "items"
    weight = 70
    form_name = _("items scheduled")
    
    @property
    def formatter(self):
        formatter = super(SittingScheduleViewlet, self).formatter
        formatter.data_view = "/jsonlisting-schedule-documents"
        return formatter

class MinistersViewlet(SubformViewlet):
    sub_attr_name = "ministers"

''' !+MINISTRY_DOCS(mr, apr-2013)
class BillsViewlet(SubformViewlet):
    sub_attr_name = "bills"

class QuestionsViewlet(SubformViewlet):
    sub_attr_name = "questions"
'''

class AgendaItemsViewlet(SubformViewlet):
    sub_attr_name = "agendaitems"

class MinistriesViewlet(SubformViewlet):
    sub_attr_name = "ministries"

@register.viewlet(interfaces.IParliament,
    manager=IContentViewManager,
    name="bungeni.viewlet.committees",
    protect=register.PROTECT_VIEWLET_PUBLIC)
class CommitteesViewlet(SubformViewlet):
    sub_attr_name = "committees"
    weight = 10

class CommitteeStaffViewlet(SubformViewlet):
    sub_attr_name = "committeestaff"

class CommitteeMembersViewlet(SubformViewlet):
    sub_attr_name = "committeemembers"


@register.viewlet(interfaces.IBungeniGroup, 
    manager=ISubFormViewletManager,
    name="keep-zca-happy-addresses",
    protect=register.PROTECT_VIEWLET_PUBLIC)
class AddressesViewlet(SubformViewlet):
    sub_attr_name = "addresses"
    weight = 99
    @property
    def form_name(self):
        return _(u"Contacts")


@register.viewlet(interfaces.IParliament,
    manager=IContentViewManager,
    name="bungeni.viewlet.political-groups",
    protect=register.PROTECT_VIEWLET_PUBLIC)
class PoliticalGroupsViewlet(SubformViewlet):
    sub_attr_name = "politicalgroups"
    weight = 30

class OfficeMembersViewlet(SubformViewlet):
    sub_attr_name = "officemembers"

class PoliticalGroupMembersViewlet(SubformViewlet):
    sub_attr_name = "group_members"

class SittingsViewlet(SubformViewlet):
    sub_attr_name = "sittings"

# BungeniAttributeDisplay
# !+BungeniViewlet(mr) make these inherit from browser.BungeniViewlet

class PersonInfo(BungeniAttributeDisplay):
    """Bio Info / personal data about the MP.
    """
    for_display = True
    mode = "view"

    form_name = _(u"Personal Info")
    view_id = "personal-info"

    def __init__(self, context, request, view, manager):
        self.context = context
        self.request = request
        self.__parent__ = context.__parent__
        self.manager = manager
        self.query = None
        md = utils.get_descriptor(domain.User)
        self.form_fields = md.fields #.select("user_id", "start_date", "end_date")

    def update(self):
        user_id = self.context.user_id
        parent = self.context.__parent__
        self.query = Session().query(domain.User
            ).filter(domain.User.user_id == user_id)
        self.context = self.query.all()[0]
        self.context.__parent__ = parent
        super(PersonInfo, self).update()

@register.viewlet(interfaces.IFeatureSchedule,
    manager=ISubFormViewletManager,
    name="doc-minutes",
    protect=register.PROTECT_VIEWLET_PUBLIC)
class DocMinutesViewlet(browser.BungeniItemsViewlet):
    """Render a tree of schedule discussions
    """ 
 
    render = ViewPageTemplateFile("templates/doc-minutes.pt")

    def __init__(self, context, request, view, manager):
        self.request = request
        self.context = context
        self.manager = manager
        trusted = removeSecurityProxy(context)
        try:
            self.item_id = trusted.doc_id
        except AttributeError:
            self.for_display = False
            return

    def _get_items(self):
        item_type = capi.get_type_info(self.context).workflow_key
        query = Session().query(domain.ItemSchedule).filter(
            sql.and_(
                domain.ItemSchedule.item_id == self.item_id,
                domain.ItemSchedule.item_type == item_type
            )
        )
        items = []
        for item in query.all():
            items.append(dict(
                sitting_name=IDCDescriptiveProperties(item.sitting).title,
                sitting_venue=(
                    IDCDescriptiveProperties(item.sitting.venue).title
                    if item.sitting.venue else _(u"Unknown venue")),
                minutes=[ dict(text=minute.body) 
                    for minute in item.itemdiscussions
                ]
            ))
        if not items:
            self.for_display = False
        return items
            
    
    def update(self):
        self.items = self._get_items()
        super(DocMinutesViewlet, self).update()


class OfficesHeldViewlet(browser.BungeniItemsViewlet):

    render = ViewPageTemplateFile("templates/offices-held-viewlet.pt")

    def _get_items(self):
        formatter = self.get_date_formatter("date", "long")
        trusted = removeSecurityProxy(self.context)
        session = Session()
        memberships = session.query(domain.GroupMembership
            ).join(domain.User
            ).filter(domain.User.user_id == trusted.user_id).all()
        items = []

        def get_relevant_date(date_type, title=None):
            if title and getattr(title, date_type, None):
                return formatter.format(getattr(title, date_type))
            elif getattr(mb, date_type, None):
                return formatter.format(getattr(mb, date_type))
            elif getattr(mb.group, date_type, None):
                return formatter.format(getattr(mb.group, date_type))
            else:
                return ""

        for mb in memberships:
            item = {}
            item["group"] = IDCDescriptiveProperties(mb.group).title
            item["group_type"] = translate(mb.group.type, context=self.request)
            if mb.member_titles:
                for title in mb.member_titles:
                    final_item = dict(item)
                    final_item["member_title"] = _(title.title_type.title_name)
                    final_item["start_date"] = get_relevant_date(
                        "start_date", title)
                    final_item["end_date"] = get_relevant_date(
                        "end_date", title)
                    items.append(final_item)
            else:
                item["member_title"] = _(u"Member")
                item["start_date"] = get_relevant_date("start_date")
                item["end_date"] = get_relevant_date("end_date")
                items.append(item)
        return items

    def update(self):
        self.items = self._get_items()



def _get_public_states_for(*tis):
    ps = set()
    for ti in tis:
        ps.update(ti.workflow.get_state_ids(tagged=["public"]))
    return list(ps)

class MemberItemsViewlet(browser.BungeniItemsViewlet):
    """A tab with bills, motions etc for an MP 
    (the "parliamentary activities" tab of of the "member" view)
    """
    states = _get_public_states_for( *[ ti 
        for (key, ti) in capi.iter_type_info() 
        if ti.custom and issubclass(ti.domain_model, domain.Doc) ] )
    
    render = ViewPageTemplateFile("templates/mp-item-viewlet.pt")

    def __init__(self, context, request, view, manager):
        super(MemberItemsViewlet, self).__init__(
            context, request, view, manager)
        user_id = self.context.user_id
        parliament_id = self.context.group_id
        self.query = Session().query(domain.Doc).filter(
            sql.and_(
                domain.Doc.owner_id == user_id,
                domain.Doc.parliament_id == parliament_id,
                domain.Doc.status.in_(self.states),
            ))
        #self.for_display = (self.query.count() > 0)
        self.formatter = self.get_date_formatter("date", "medium")
    
    def update(self):
        user_id = self.context.user_id
        parliament_id = self.context.group_id
        wf = capi.get_type_info("signatory").workflow
        session = Session()
        # add cosigned items
        signed_pi_ids = [sgn.head_id for sgn in
            session.query(domain.Signatory).filter(
                sql.and_(domain.Signatory.user_id == user_id,
                    domain.Signatory.status.in_(
                        wf.get_state_ids(tagged=["public"])
                    ),
                )
            ).all()
        ]
        if len(signed_pi_ids) > 0:
            self.query = self.query.union(
                session.query(domain.Doc).filter(
                    sql.and_(
                        domain.Doc.parliament_id == parliament_id,
                        domain.Doc.status.in_(self.states),
                        domain.Doc.doc_id.in_(
                            signed_pi_ids
                        )
                    )
                )
            )
        self.query = self.query.order_by(
            domain.Doc.doc_id.desc()
        )
    
    @property
    def items(self):
        for item in self.query.all():
            _url = "/business/%ss/obj-%i" % (item.type,
                item.doc_id)
            yield {"type": item.type,
                "title": item.title,
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
            descriptor = utils.get_descriptor(self.factory)
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
        descriptor = utils.get_descriptor(self.factory)
        return descriptor.display_name

@register.viewlet(interfaces.IItemSchedule,
    manager=IContentViewManager,
    name="bungeni.viewlet.scheduling-item-discussions",
    protect=register.PROTECT_VIEWLET_PUBLIC)
class SchedulingMinutesViewlet(SubformViewlet):
    sub_attr_name = "discussions"

@register.viewlet(interfaces.IItemSchedule,
    manager=IContentViewManager,
    name="bungeni.viewlet.scheduling-item-votes",
    protect=register.PROTECT_VIEWLET_PUBLIC)
class SchedulingVotesViewlet(SubformViewlet):
    sub_attr_name = "votes"
    form_name = _("vote records")

    @property
    def for_display(self):
        """Only display viewlet for doc types"""
        if not interfaces.IDoc.providedBy(self.context.__parent__.item):
            return False
        return super(SchedulingVotesViewlet, self).for_display

