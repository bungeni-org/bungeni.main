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
from zope.dublincore.interfaces import IDCDescriptiveProperties
import zope.traversing.interfaces

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from bungeni.alchemist import Session
from bungeni.alchemist.interfaces import IAlchemistContainer
from bungeni.alchemist.model import queryModelDescriptor

from bungeni.models import interfaces
from bungeni.models import domain
from bungeni.core.i18n import _
from bungeni.core.translation import ( is_translation, get_language_by_name,
    get_request_language, get_translation_for, translate_i18n
)

from bungeni.ui.utils import date, misc
from bungeni.utils import register


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


class DescriptiveProperties(object):
    interface.implements(IDCDescriptiveProperties)
    
    title = None
    @property
    def description(self):
        return u""
    
    @property
    def uri(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return (context.uri or "") if hasattr(context, "uri") else ""
    
    def __init__(self, context):
        self.context = context

    def formatDate(self, date_, category="date", length="medium"):
        return date.getLocaleFormatter(None, category, length).format(date_)

    def translate(self, context, name):
        """Gets translated field values
        """
        lang = get_request_language()
        if not lang:
            return getattr(context, name)
        if interfaces.ITranslatable.providedBy(context):
            if context.language != lang:
                translation = get_translation_for(context, lang)
                translation = filter(lambda tr:tr.field_name==name, 
                    translation
                )
                if translation:
                    return translation[0].field_text
        return getattr(context, name)

class DocumentDescriptiveProperties(DescriptiveProperties):
    @property
    def mover(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return translate_i18n(
            IDCDescriptiveProperties(context.owner).title_member
        )


@register.adapter()
class QuestionDescriptiveProperties(DocumentDescriptiveProperties):
    component.adapts(interfaces.IQuestion)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        if context.type_number is None:
            return self.translate(context, "short_title")
        return "#%d: %s" % (
            context.type_number,
            self.translate(context, "short_title"))

    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        text = "%s %s %s" % (_("Submitted by"),
                            context.owner.first_name, context.owner.last_name)
        if context.ministry:
            text += " to %s" % IDCDescriptiveProperties(context.ministry).title
        if context.admissible_date:
            text += " (%s %s)" % (_(u"Approved on"),
                self.formatDate(context.admissible_date))
        return text + "."


@register.adapter()
class BillDescriptiveProperties(DocumentDescriptiveProperties):
    component.adapts(interfaces.IBill)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        if context.type_number is None:
            return self.translate(context, "short_title")
        return "#%d: %s" % (context.type_number, 
            self.translate(context, "short_title")
        )

    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        text = "%s %s %s" % (translate_i18n(_("Submitted by")),
                            context.owner.first_name, context.owner.last_name)
        if context.publication_date:
            text += " (%s %s)" % (translate_i18n(_(u"published on")),
                                  self.formatDate(context.publication_date))
        return text + "."


@register.adapter()
class MotionDescriptiveProperties(DocumentDescriptiveProperties):
    component.adapts(interfaces.IMotion)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        if context.type_number is None:
            return self.translate(context, "short_title")
        return "#%d: %s" % (
            context.type_number,
            self.translate(context, "short_title"))
    
    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        text = "%s %s %s" % (translate_i18n(_(u"Submitted by")),
                            context.owner.first_name, context.owner.last_name)
        if context.notice_date:
            text += " (%s %s)" % (translate_i18n(_(u"notice given on")),
                                  self.formatDate(context.notice_date))
        return text + "."


@register.adapter()
class SittingDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ISitting)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return "%s %s, %s %s %s" % (translate_i18n(_(u"Sitting:")), 
                self.translate(context.group, "short_name"), 
                context.start_date.strftime('%Y-%m-%d, %H:%M'), 
                _(u"to"), 
                context.end_date.strftime('%H:%M'))
    
    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return "%s %s (%s %s %s)" % (translate_i18n(_(u"Sitting scheduled for")),
                self.translate(context.group, "short_name"),
                context.start_date.strftime('%Y-%m-%d %H:%M'), 
                _(u"to"),
                context.end_date.strftime('%H:%M'))

    @property
    def verbose_title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        sitting_title = _("verbose_sitting_title", 
            default=u"Sitting of ${group_name} @ ${sitting_venue}",
            mapping = {
                "group_name": IDCDescriptiveProperties(context.group).title,
                "sitting_venue": IDCDescriptiveProperties(context.venue).title
            }
        )
        return translate_i18n(sitting_title)


@register.adapter()
class ItemScheduleDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IItemSchedule)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return IDCDescriptiveProperties(context.item).title

    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        sitting = context.sitting
        return _(u"Scheduled for sitting ($start to $end)",
                 mapping={'start': sitting.start_date,
                          'end': sitting.end_date})

    @property
    def mover(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return IDCDescriptiveProperties(context.item).mover

@register.adapter()
class EditorialNoteDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IEditorialNote)
    
    @property
    def title(self):
        return self.context.text

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
        return "%s %s" % (translate_i18n(_(u"Last modified")), 
            self.context.change.date
        )


@register.adapter()
class GroupDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IBungeniGroup)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return "%s - %s" % (
            #self.context.type.capitalize(),
            self.translate(context, "short_name"),
            self.translate(context, "full_name"))


@register.adapter()
class ContainerDescriptiveProperties(DescriptiveProperties):
    component.adapts(IAlchemistContainer)

    @property
    def title(self):
        descriptor = queryModelDescriptor(self.context.domain_model)
        return descriptor.container_name


@register.adapter()
class UserDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IBungeniUser)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return "%s %s %s" % (self.translate(context,"titles"),
            context.first_name, context.last_name
        )

    @property
    def title_member(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        mp_user = None
        try:
            mp_user = session.query(domain.MemberOfParliament).filter(
                domain.MemberOfParliament.user_id == context.user_id
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
        return _("member_title_with_provenance",
            default=u"Member of Parliament for ${provenance} (${member})",
            mapping={"provenance": mp_user.provenance, "member": self.title}
        )


@register.adapter()
class GroupMembershipDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IBungeniGroupMembership)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        if context.user:
            return "%s %s %s" % (self.translate(context.user, "titles"),
                context.user.first_name,
                context.user.last_name)
        else:
            return u"New User"


@register.adapter()
class SittingAttendanceDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ISittingAttendance)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        if context.user:
            return "%s %s %s" % (self.translate(context.user, "titles"),
                context.user.first_name,
                context.user.last_name)
        else:
            return u"New User"
    
    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context.attendance_type, 
            "attendance_type"
        )


@register.adapter()
class SignatoryDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ISignatory)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        if context.user:
            return "%s %s %s" % (self.translate(context.user, "titles"),
                context.user.first_name,
                context.user.last_name)
        else:
            return u"New User"
    
    @property
    def status(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return translate_i18n(misc.get_wf_state(context))


@register.adapter()
class ParliamentSessionDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IParliamentSession)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "short_name")
    
    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "full_name")


@register.adapter()
class ItemScheduleDiscussionDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IItemScheduleDiscussion)
    
    @property
    def title(self):
        return _(u"Discussion")


@register.adapter()
class ChangeDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IChange)
    
    @property
    def title(self):
        return self.context.action
    
    @property
    def description(self):
        return "%s (%s)" %(translate_i18n(self.context.description),
                self.formatDate(self.context.date_active))


@register.adapter()
class UserAddressDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IUserAddress)
    
    @property
    def title(self):
        return _(u"Address")


@register.adapter()
class AgendaItemDescriptiveProperties(DocumentDescriptiveProperties):
    component.adapts(interfaces.IAgendaItem)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return u"%s - %s" % (self.translate(context, "short_title"),
            self.translate(context.group, "short_name")
        )


@register.adapter()
class TabledDocumentDescriptiveProperties(DocumentDescriptiveProperties):
    component.adapts(interfaces.ITabledDocument)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "short_title")


@register.adapter()
class MemberTitleDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IMemberTitle)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context.title_type, "title_name")


@register.adapter()
class ReportDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IReport)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return u'%s' % self.translate(context, "short_title")

    @property
    def description(self):
        return self.title

@register.adapter()
class ItemScheduleCategoryDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IItemScheduleCategory)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "short_name")


@register.adapter()
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


@register.adapter()
class EventProperties(DescriptiveProperties):
    component.adapts(interfaces.IEvent)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "short_title")


@register.adapter()
class AttachmentDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IAttachment)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return context.title

    @property
    def description(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return u"%s  (%s)" % (context.name, context.mimetype)

''' !+VERSION_CLASS_PER_TYPE
@register.adapter()
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
'''

@register.adapter()
class HeadingDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IHeading)

    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "text")

''' !+TYPES_CUSTOM
class AddressTypeDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IAddressType)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "address_type_name")

class PostalAddressTypeDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IPostalAddressType)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "postal_address_type_name")

class BillTypeDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IBillType)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "bill_type_name")

class CommitteeTypeDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ICommitteeType)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "committee_type")

class CommitteeTypeStatusDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ICommitteeTypeStatus)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "committee_type_status_name")

class AttendanceTypeDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IAttendanceType)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "attendance_type")
'''


@register.adapter()
class VenueDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IVenue)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "short_name")


''' !+TYPES_CUSTOM
class QuestionTypeDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IQuestionType)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "question_type_name")

class ResponseTypeDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IResponseType)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "response_type_name")

class MemberElectionTypeDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IMemberElectionType)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "member_election_type_name")
'''


@register.adapter()
class TitleTypeDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ITitleType)
    
    @property
    def title(self):
        session = Session()
        context = session.merge(removeSecurityProxy(self.context))
        return self.translate(context, "title_name")


