from zope import interface
from zope import component
from zope.security.proxy import removeSecurityProxy
from zope.dublincore.interfaces import IDCDescriptiveProperties
from bungeni.alchemist import Session
from bungeni.alchemist.interfaces import IAlchemistContainer
from bungeni.alchemist.model import queryModelDescriptor

#from marginalia.interfaces import IMarginaliaAnnotation

from bungeni.models import interfaces
from bungeni.models import domain
from bungeni.core.translation import is_translation
from bungeni.core.translation import get_language_by_name
from bungeni.core.i18n import _
from bungeni.ui.utils import date

from zope.securitypolicy.interfaces import IPrincipalRoleMap


class DublinCoreMetadataAdapter(object):
    """Generic dublin core metadata adapter which will retrieve
    metadata attributes lazily.

    Suitable for use as traversal path adapter (which can be used
    directly in templates using the ':' notation).
    """
    interfaces = IDCDescriptiveProperties,

    __slots__ = "context", "adapters"

    def __init__(self, context):
        self.context = context
        self.adapters = {}

    def __getattr__(self, attribute):
        for iface in self.interfaces:
            if attribute in iface.names():
                adapter = self.adapters.get(iface)
                if adapter is None:
                    adapter = self.adapters[iface] = iface(self.context)

                return getattr(adapter, attribute)

        raise AttributeError(attribute)


def get_descriptive_properties(context):
    return IDCDescriptiveProperties(context)


class DescriptiveProperties(object):
    interface.implements(IDCDescriptiveProperties)
    
    title = None
    @property
    def description(self):
        return u""
    
    def __init__(self, context):
        self.context = context

    def formatDate(self, date_, category="date", length="medium"):
        return date.getLocaleFormatter(None, category, length).format(date_)


class QuestionDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IQuestion)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        if context.question_number is None:
            return context.short_name
        return "#%d: %s" % (
            context.question_number,
            context.short_name)

    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        text = "%s %s %s" % (_("Submitted by"),
                            context.owner.first_name, context.owner.last_name)
        if context.approval_date:
            text += " (%s %s)" % (_(u"approved on"),
                                  self.formatDate(context.approval_date))
        return text + "."


class BillDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IBill)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        if context.identifier is None:
            return context.short_name
        return "#%d: %s" % (context.identifier, context.short_name)

    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        text = "%s %s %s" % (_("Submitted by"),
                            context.owner.first_name, context.owner.last_name)
        if context.publication_date:
            text += " (%s %s)" % (_(u"published on"),
                                  self.formatDate(context.publication_date))
        return text + "."


class MotionDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IMotion)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        if context.motion_number is None:
            return context.short_name
        return "#%d: %s" % (
            context.motion_number,
            context.short_name)

    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        text = "%s %s %s" % (_("Submitted by"),
                            context.owner.first_name, context.owner.last_name)
        if context.notice_date:
            text += " (%s %s)" % (_(u"notice given on"),
                                  self.formatDate(context.notice_date))
        return text + "."


class SittingDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IGroupSitting)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return "%s %s, %s %s %s" % (_(u"Sitting:"), 
                context.group.short_name, 
                context.start_date.strftime('%Y-%m-%d, %H:%M'), 
                _(u"to"), 
                context.end_date.strftime('%H:%M'))
    
    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return "%s %s (%s %s %s)" % (_(u"Sitting scheduled for"),
                context.group.short_name,
                context.start_date.strftime('%Y-%m-%d %H:%M'), 
                _(u"to"),
                context.end_date.strftime('%H:%M'))


class ItemScheduleDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IItemSchedule)

    @property
    def title(self):
        return _(u"Item scheduling")

    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        sitting = context.sitting
        return _(u"Scheduled for sitting ($start to $end)",
                 mapping={'start': sitting.start_date,
                          'end': sitting.end_date})


class VersionDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IVersion)
    
    @property
    def title(self):
        if is_translation(self.context):
            language = get_language_by_name(self.context.language)['name']
            return "%s %s" % (language, _(u"translation"))
        return "%s %s" % (_(u"Version"), self.context.version_id)
    
    @property
    def description(self):
        return "%s %s" % (_(u"Last modified"), self.context.change.date)


class GroupDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IBungeniGroup)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return "%s - %s" % (
            #self.context.type.capitalize(),
            context.short_name,
            context.full_name)


class ContainerDescriptiveProperties(DescriptiveProperties):
    component.adapts(IAlchemistContainer)

    @property
    def title(self):
        descriptor = queryModelDescriptor(self.context.domain_model)
        return descriptor.container_name


class UserDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IBungeniUser)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return "%s %s %s" % (context.titles,
                context.first_name,
                context.last_name)


class GroupMembershipDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IBungeniGroupMembership)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        if context.user:
            return "%s %s %s" % (context.user.titles,
                context.user.first_name,
                context.user.last_name)
        else:
            return u"New User"


class GroupSittingAttendanceDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IGroupSittingAttendance)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        if context.user:
            return "%s %s %s" % (context.user.titles,
                context.user.first_name,
                context.user.last_name)
        else:
            return u"New User"
    
    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return context.attendance_type.attendance_type


class CosignatoryDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ICosignatory)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        if context.user:
            return "%s %s %s" % (context.user.titles,
                context.user.first_name,
                context.user.last_name)
        else:
            return u"New User"


class ParliamentSessionDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IParliamentSession)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return context.short_name
    
    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return context.full_name


class ConstituencyDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IConstituency)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return context.name


class ProvinceDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IProvince)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return context.province


class RegionDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IRegion)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return context.region


class ItemScheduleDiscussionDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IItemScheduleDiscussion)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        time = context.sitting_time
        if time is not None:
            return "%s (%s)" % (_(u"Discussion"), context.sitting_time)
        return _(u"Discussion")


class SittingTypeDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ISittingType)

    @property
    def title(self):
        return self.context.group_sitting_type


class ChangeDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IChange)
    
    @property
    def title(self):
        return self.context.action


class UserAddressDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IUserAddress)
    
    @property
    def title(self):
        return u"Address"


class AgendaItemDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IAgendaItem)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return u"%s - %s" % (context.short_name, context.group.short_name)


class TabledDocumentDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ITabledDocument)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return context.short_name


class ConstituencyDetailsDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IConstituencyDetail)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return '%s - %i' % (context.constituency.name,
            context.date.year)


class GroupItemAssignmentDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IGroupItemAssignment)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return '%s - %s ' % (context.item.short_name, context.group.short_name)


class MemberRoleTitleDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IMemberRoleTitle)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return context.title_name.user_role_name



class ReportDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IReport)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return u'%s: %s - %s' % (context.short_name,
            context.start_date, context.end_date)

    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return u"Covers %s to %s" % (context.start_date.strftime('%Y-%m-%d'),
            context.end_date.strftime('%Y-%m-%d'))

class ItemScheduleCategoryDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IItemScheduleCategory)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return context.short_name


class UserDelegationDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IUserDelegation)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        if getattr(context, 'delegation', None):
            return u'%s %s' % (context.delegation.first_name,
                context.delegation.last_name)
        else:
            return u""


class EventItemProperties(DescriptiveProperties):
    component.adapts(interfaces.IEventItem)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return context.short_name


class AttachedFileDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IAttachedFile)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return context.file_title

    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return u"%s  (%s)" % (context.file_name, context.file_mimetype)


class AttachedFileVersionDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IAttachedFileVersion)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return context.file_title

    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return u"%s  (%s)" % (context.file_name, context.file_mimetype)


class HeadingDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IHeading)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return context.short_name

    @property
    def description(self):
        return ""

