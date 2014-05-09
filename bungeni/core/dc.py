# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Dublin core metadata adapters for various types

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.dc")

from zope import interface
from zope import component
from zope.security.proxy import removeSecurityProxy
from zope.securitypolicy.role import IRole
from zope.dublincore.interfaces import IDCDescriptiveProperties
import zope.traversing.interfaces

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from bungeni.alchemist import Session, utils
from bungeni.alchemist.interfaces import IAlchemistContainer

from bungeni.models import interfaces
from bungeni.models import domain
from bungeni import _
from bungeni.core.translation import (
    is_translation,
    get_field_translations,
)
from bungeni.core.language import get_default_language, get_language_by_name

from bungeni.ui.utils import date, misc
from bungeni.utils import register
from bungeni.capi import capi
from bungeni import translate


def _merged(context):
    return Session().merge(removeSecurityProxy(context))


@register.adapter(adapts=(interface.Interface,), # for="*"
    provides=zope.traversing.interfaces.IPathAdapter, name="dc")
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
            adapter = self.adapters.get(iface)
            if adapter is None:
                adapter = self.adapters[iface] = iface(self.context)
            if adapter is None:
                break
            return getattr(adapter, attribute)                
        raise AttributeError(attribute)


def get_descriptive_properties(context):
    return IDCDescriptiveProperties(context)


# All DC property text values e.g. title, description, are ALWAYS translated.

class DescriptiveProperties(object):
    interface.implements(IDCDescriptiveProperties)
    
    title = None
    @property
    def description(self):
        return u""
    
    @property
    def uri(self):
        context = _merged(self.context)
        return (context.uri or "") if hasattr(context, "uri") else ""
    
    def __init__(self, context):
        self.context = context
    
    def formatDate(self, date_, category="date", length="medium"):
        return date.getLocaleFormatter(None, category, length).format(date_)
    
    def translate(self, context, name):
        """Gets translated field values
        """
        lang = get_default_language()
        if not lang:
            return getattr(context, name, "")
        if interfaces.ITranslatable.providedBy(context):
            if context.language != lang:
                translation = get_field_translations(context, lang)
                if translation:
                    translation = filter(lambda tr:tr.field_name==name, 
                        translation)
                    if translation[0].field_text:
                        return translation[0].field_text
        return getattr(context, name)


# doc 

@register.adapter()
class DocDescriptiveProperties(DescriptiveProperties):
    """A base DC adapter for instances of Doc-archetyped types.
    !+ all DC adapters for custom docs and groups must go away / to configuration
    """
    component.adapts(interfaces.IDoc)
    
    @property
    def mover(self):
        context = _merged(self.context)
        # !+TRANSLATE_MESS(mr, oct-2012) this is content data and NOT a UI msgid?
        # Should then be using translated ?!
        return translate(IDCDescriptiveProperties(context.owner).title_member)
    
    @property
    def title(self):
        doc = _merged(self.context)
        doc_title = self.translate(doc, "title")
        if doc.type_number is not None:
            return "#%d: %s" % (doc.type_number, doc_title)
        # !+AgendaItem_group(mr, dec-2012) am dropping inclusion of group.short_name
        # in DC title for all docs (previously included only for AgendaItem).
        # !+Selenium(mr, dec-2012) UI testing sometimes uses this value 
        # (e.g breadcrumb trail link label) to follow onto the view for a
        # modified object -- those tests should be using non-language dependent
        # critria such as the url component for the object identifier. 
        #if doc.group is not None:
        #    t.append(" - %s" % (self.translate(doc.group, "short_name")))
        return doc_title
    
    @property
    def description(self):
        doc = _merged(self.context)
        return self.translate(doc, "description")


@register.adapter()
class SittingDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ISitting)

    @property
    def title(self):
        context = _merged(self.context)
        return "%s %s, %s %s %s" % (translate(_(u"Sitting:")), 
                self.translate(context.group, "short_name"), 
                context.start_date.strftime('%Y-%m-%d, %H:%M'), 
                _(u"to"), 
                context.end_date.strftime('%H:%M'))
    
    @property
    def duration(self):
        return "%s &rarr; %s" % (
            self.formatDate(self.context.start_date, "dateTime"),
            self.formatDate(self.context.end_date, "dateTime"))
    
    @property
    def description(self):
        context = _merged(self.context)
        return "%s %s (%s %s %s)" % (translate(_(u"Sitting scheduled for")),
                self.translate(context.group, "short_name"),
                context.start_date.strftime('%Y-%m-%d %H:%M'), 
                _(u"to"),
                context.end_date.strftime('%H:%M'))

    @property
    def verbose_title(self):
        context = _merged(self.context)
        sitting_title = _("verbose_sitting_title", 
            default=u"Sitting of ${group_name} @ ${sitting_venue}",
            mapping = {
                "group_name": IDCDescriptiveProperties(context.group).title,
                "sitting_venue": (
                    IDCDescriptiveProperties(context.venue).title 
                    if context.venue else translate(_(u"no venue"))
                )
            }
        )
        return translate(sitting_title)

@register.adapter()
class DebateRecordDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IDebateRecord)

    @property
    def title(self):
        context = _merged(self.context)
        return "%s %s, %s %s %s" % (translate(_(u"Debate Record:")), 
                self.translate(context.sitting, "short_name"), 
                context.sitting.start_date.strftime('%Y-%m-%d, %H:%M'), 
                _(u"to"), 
                context.sitting.end_date.strftime('%H:%M'))
    
    @property
    def description(self):
        context = _merged(self.context)
        return "%s %s (%s %s %s)" % (translate(_(u"Debate record of ")),
                self.translate(context.sitting, "short_name"),
                context.sitting.start_date.strftime('%Y-%m-%d %H:%M'), 
                _(u"to"),
                context.sitting.end_date.strftime('%H:%M'))


@register.adapter()
class ItemScheduleDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IItemSchedule)

    @property
    def title(self):
        context = _merged(self.context)
        return IDCDescriptiveProperties(context.item).title

    @property
    def description(self):
        context = _merged(self.context)
        sitting = context.sitting
        return _(u"Scheduled for sitting ($start to $end)",
                 mapping={'start': sitting.start_date,
                          'end': sitting.end_date})

    @property
    def mover(self):
        context = _merged(self.context)
        return IDCDescriptiveProperties(context.item).mover

@register.adapter()
class EditorialNoteDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IEditorialNote)
    
    @property
    def title(self):
        return translate(capi.get_type_info(self.context).descriptor_model.display_name)
    
    @property
    def description(self):
        return ""

@register.adapter()
class AgendaTextRecordDescriptiveProperties(DescriptiveProperties):
      component.adapts(interfaces.IAgendaTextRecord)
      
      @property
      def title(self):
          return self.context.text

      @property
      def description(self):
          return self.title

@register.adapter()
class VersionDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IVersion)
    
    @property
    def title(self):
        if is_translation(self.context):
            language = get_language_by_name(self.context.language)["name"]
            return "%s %s" % (language, _("translation"))
        return "%s %s" % (_("Version"), self.context.seq)
    
    @property
    def description(self):
        return "%s %s" % (translate(_(u"Last modified")), 
            self.context.change.date
        )


@register.adapter()
class GroupDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IGroup)
    
    @property
    def title(self):
        group = _merged(self.context)
        #!+return group.combined_name
        return self.translate(group, "full_name")

    @property
    def short_title(self):
        group = _merged(self.context)
        #!+return group.combined_name
        return self.translate(group, "short_name")


@register.adapter()
class GroupAssignmentDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IGroupAssignment)
    
    @property
    def title(self):
        group_assignment = _merged(self.context)
        group = group_assignment.principal
        #!+GROUP_ASSIGNMENT.GROUP assert isinstance(group, domain.Group), group
        #!+return group.combined_name
        return "%s" % (self.translate(group, "short_name"))


@register.adapter()
class ContainerDescriptiveProperties(DescriptiveProperties):
    component.adapts(IAlchemistContainer)

    @property
    def title(self):
        descriptor = utils.get_descriptor(self.context.domain_model)
        return descriptor.container_name


@register.adapter()
class UserDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IBungeniUser)
    
    @property
    def title(self):
        context = _merged(self.context)
        return context.combined_name
    
    @property
    def title_member(self):
        context = _merged(self.context)
        mp_user = None # !+ generalize to all group_member types
        try:
            mp_user = Session().query(domain.Member).filter(
                domain.Member.user_id == context.user_id
            ).one()
        except NoResultFound:
            #this user has no associated MP record
            pass
        except MultipleResultsFound:
            # this should not happen
            log.error("Multiple MP objects found for : %s", context.__str__())
        finally:
            if mp_user is None:
                return self.title
        if mp_user.representation_geo or mp_user.representation_sig:
            return _("member_title_with_representation",
                default=u"Member of Parliament for ${representation}"
                " (${member})",
                mapping={"representation": ", ".join([
                        mp_user.representation_geo, mp_user.representation_sig]),
                    "member": self.title
                }
            )
        return self.title


@register.adapter()
class GroupMemberDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IGroupMember)
    
    @property
    def title(self):
        context = _merged(self.context)
        user = context.user
        if user:
            return user.combined_name
        else:
            return "New User"


@register.adapter()
class SittingAttendanceDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ISittingAttendance)
    
    @property
    def title(self):
        context = _merged(self.context)
        user = context.member
        if user:
            return user.combined_name
        else:
            return "New User"
    
    @property
    def description(self):
        context = _merged(self.context)
        return self.translate(context.attendance_type, "attendance_type")


@register.adapter()
class SignatoryDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ISignatory)
    
    @property
    def title(self):
        context = _merged(self.context)
        user = context.user
        if user: 
            return user.combined_name
        else:
            return "New User"
    
    @property
    def status(self):
        context = _merged(self.context)
        return translate(misc.get_wf_state(context))


@register.adapter()
class SessionDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ISession)
    
    @property
    def title(self):
        context = _merged(self.context)
        return self.translate(context, "short_name")
    
    @property
    def description(self):
        context = _merged(self.context)
        return self.translate(context, "full_name")
    
    verbose_title = description

@register.adapter()
class ItemScheduleDiscussionDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IItemScheduleDiscussion)
    
    @property
    def title(self):
        return _(u"Discussion")

@register.adapter()
class ItemScheduleVoteDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IItemScheduleVote)
    
    @property
    def title(self):
        return _(u"Vote record")

@register.adapter()
class ChangeDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IChange)
    
    @property
    def title(self):
        return self.context.action
    
    @property
    def description(self):
        return "%s (%s)" %(translate(self.context.description),
                self.formatDate(self.context.date_active))


@register.adapter()
class AddressDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IAddress)
    
    @property
    def title(self):
        return _(u"Address")


@register.adapter()
class MemberTitleDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IMemberTitle)
    
    @property
    def title(self):
        context = _merged(self.context)
        return self.translate(context.title_type, "title_name")


@register.adapter()
class ReportDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IReport)
    
    @property
    def title(self):
        context = _merged(self.context)
        return u'%s' % self.translate(context, "title")

@register.adapter()
class SittingReportDescriptiveProperties(ReportDescriptiveProperties):
    component.adapts(interfaces.ISittingReport)

@register.adapter()
class UserDelegationDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IUserDelegation)
    
    @property
    def title(self):
        context = _merged(self.context)
        if getattr(context, 'delegation', None):
            return u'%s %s' % (context.delegation.first_name,
                context.delegation.last_name)
        else:
            return u""


@register.adapter()
class AttachmentDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IAttachment)
    
    @property
    def title(self):
        context = _merged(self.context)
        return context.title
    
    @property
    def description(self):
        context = _merged(self.context)
        return u"%s  (%s)" % (context.name, context.mimetype)

''' !+VERSION_CLASS_PER_TYPE
@register.adapter()
class AttachedFileVersionDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IAttachedFileVersion)

    @property
    def title(self):
        context = _merged(self.context)
        return context.file_title

    @property
    def description(self):
        context = _merged(self.context)
        return u"%s  (%s)" % (context.file_name, context.file_mimetype)
'''

@register.adapter()
class HeadingDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IHeading)
    
    @property
    def title(self):
        context = _merged(self.context)
        return self.translate(context, "text")


@register.adapter()
class VenueDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IVenue)
    
    @property
    def title(self):
        context = _merged(self.context)
        return self.translate(context, "short_name")


@register.adapter()
class TitleTypeDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ITitleType)
    
    @property
    def title(self):
        context = _merged(self.context)
        return self.translate(context, "title_name")

@register.adapter()
class MemberRoleDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IMemberRole)
    
    @property
    def title(self):
        context = _merged(self.context)
        return component.getUtility(IRole, context.role_id).title

@register.adapter()
class OAuthApplicationDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IOAuthApplication)

    @property
    def title(self):
        context = _merged(self.context)
        return context.name
