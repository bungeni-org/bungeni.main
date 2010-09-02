log = __import__("logging").getLogger("bungeni.core.schedule")
import datetime
import time

from zope import interface
from zope import component
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.security.proxy import removeSecurityProxy
from zope.security.proxy import ProxyFactory
from zope.publisher.interfaces.browser import IHTTPRequest
from zope.publisher.interfaces import IPublishTraverse
from zope.location.interfaces import ILocation
from zope.app.publication.traversers import SimpleComponentTraverser

from bungeni.models.interfaces import IBungeniApplication
from bungeni.models.interfaces import ICommittee
from bungeni.models.interfaces import IGroupSittingContainer
from bungeni.models.domain import Group
from bungeni.models.domain import GroupSitting
from bungeni.models import domain
from bungeni.core.interfaces import ISchedulingContext
from bungeni.core.interfaces import IWorkspaceScheduling
from bungeni.core.interfaces import IDailySchedulingContext
from bungeni.core.interfaces import ISection
from bungeni.core.globalsettings import getCurrentParliamentId
from bungeni.core.i18n import _
from bungeni.core.proxy import LocationProxy
from bungeni.ui.calendar import utils

from ore.alchemist import Session
from sqlalchemy import sql

def format_date(date):
    return time.strftime("%Y-%m-%d %H:%M:%S", date.timetuple())

class SchedulingContextTraverser(SimpleComponentTraverser):
    """Custom scheduling context traverser which allows traversing to
    calendar days (using integer timestamps) or a ``get_%s`` method
    from the scheduling context class.
    """
    
    component.adapts(ISchedulingContext, IHTTPRequest)
    interface.implementsOnly(IPublishTraverse)
    
    def publishTraverse(self, request, name):
        try:
            timestamp = int(name)
            obj = DailySchedulingContext(
                self.context, utils.datetimedict.fromtimestamp(timestamp))
        except (ValueError, TypeError):
            # this is the primary condition; traverse to ``name`` by
            # looking up methods on this class
            try:
                method = getattr(self.context, 'get_%s' % name)
            except AttributeError:
                # fall back to default traversal (view lookup)
                def method():
                    return super(
                        SchedulingContextTraverser, self).publishTraverse(
                        request, name)

            obj = method()
            assert ILocation.providedBy(obj)
        log.debug("SchedulingContextTraverser.publishTraverse: " \
            "self=%s context=%s name=%s obj=%s" % (self, self.context, name, obj))
        return ProxyFactory(LocationProxy(
            removeSecurityProxy(obj), container=self.context, name=name))

class PrincipalGroupSchedulingContext(object):
    interface.implements(ISchedulingContext)

    group_id = None
    
    def __init__(self, context):
        self.__parent__ = context

    @property
    def label(self):
        group = self.get_group()
        if group is not None:
            return u"%s (%s)" % (group.short_name, group.full_name)
        return _(u"Unknown principal group")
    
    def get_group(self, name="group"):
        if self.group_id is None:
            return
        try:
            session = Session()
            group = session.query(domain.Group).filter_by(group_id=self.group_id)[0]
        except IndexError:
            raise RuntimeError("Group not found (%d)." % self.group_id)
        return group
    
    def get_sittings(self, start_date=None, end_date=None):
        try: 
            sittings = self.get_group().sittings
        except (AttributeError,):
            # e.g. ministry has no sittings attribute
            return {} # !+ should be a bungeni.models.domain.ManagedContainer
            # !+ could add sittings to a ministry
            #    could not have calendar appear for ministries
        if start_date is None and end_date is None:
            return sittings
        assert start_date and end_date
        unproxied = removeSecurityProxy(sittings)
        unproxied.subset_query = sql.and_(
            unproxied.subset_query,
            domain.GroupSitting.start_date.between(
                format_date(start_date),
                format_date(end_date))
            )
        unproxied.__parent__ = ProxyFactory(LocationProxy(
            unproxied.__parent__, container=self, name="group"))
        return sittings
    
    def get_categories(self):
        return domain.ItemScheduleCategoryContainer()

class PlenarySchedulingContext(PrincipalGroupSchedulingContext):
    component.adapts(IBungeniApplication)

    label = _(u"Plenary")
    
    @property
    def group_id(self):
        """Return current parliament's group id."""
        return getCurrentParliamentId()
    
class CommitteeSchedulingContext(PrincipalGroupSchedulingContext):
    component.adapts(ICommittee)

    @property
    def group_id(self):
        """Return committee's group id."""

        return self.__parent__.group_id

    def get_group(self, name=None):
        assert name is None
        return self.__parent__

class SittingContainerSchedulingContext(PrincipalGroupSchedulingContext):
    component.adapts(IGroupSittingContainer)

    @property
    def group_id(self):
        """Return committee's group id."""

        return self.__parent__.__parent__.group_id

    def get_group(self, name=None):
        assert name is None
        return self.__parent__.__parent__

class WorkspaceSchedulingContext(PrincipalGroupSchedulingContext):
    component.adapts(ISection)

    @property
    def group_id(self):
        return getCurrentParliamentId()


class DailySchedulingContext(object):
    interface.implements(IDailySchedulingContext, IDCDescriptiveProperties)

    description = None
    
    def __init__(self, context, date):
        self.context = context
        self.date = date
        
    @property
    def title(self):
        return _(u"$x", mapping=self.date)

    @property
    def label(self):
        return self.context.label
    
    def get_group(self):
        return self.context.get_group()
    
    def get_sittings(self):
        return self.context.get_sittings(
            start_date=self.date, end_date=self.date + datetime.timedelta(days=1))
    
