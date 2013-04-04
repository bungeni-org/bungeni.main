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
from bungeni.core.i18n import _
from bungeni.core.translation import ( is_translation, get_language_by_name,
    get_request_language, get_translation_for, translate_i18n
)

from bungeni.ui.utils import date, misc
from bungeni.utils import register
from bungeni.capi import capi


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
        lang = (get_request_language(default=None) or 
            getattr(context, "language", None))
        if not lang:
            return getattr(context, name, "")
        if interfaces.ITranslatable.providedBy(context):
            if context.language != lang:
                translation = get_translation_for(context, lang)
                translation = filter(lambda tr:tr.field_name==name, translation)
                if translation:
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
        # Should then be using translate_obj ?!
        return translate_i18n(
            IDCDescriptiveProperties(context.owner).title_member)
    
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


''' !+CUSTOM
@register.adapter()
class QuestionDescriptiveProperties(DocDescriptiveProperties):
    component.adapts(interfaces.IQuestion)
    
    @property
    def description(self):
        context = _merged(self.context)
        text = "%s %s %s" % (translate_i18n(_("Submitted by")),
                            context.owner.first_name, context.owner.last_name)
        if context.group:
            text += " to %s" % IDCDescriptiveProperties(context.group).title
        return text + "."


@register.adapter()
class BillDescriptiveProperties(DocDescriptiveProperties):
    component.adapts(interfaces.IBill)
    
    @property
    def description(self):
        context = _merged(self.context)
        text = "%s %s %s" % (translate_i18n(_("Submitted by")),
                            context.owner.first_name, context.owner.last_name)
        if context.publication_date:
            text += " (%s %s)" % (translate_i18n(_(u"published on")),
                                  self.formatDate(context.publication_date))
        return text + "."


@register.adapter()
class MotionDescriptiveProperties(DocDescriptiveProperties):
    component.adapts(interfaces.IMotion)
    
    @property
    def description(self):
        context = _merged(self.context)
        text = "%s %s %s" % (translate_i18n(_(u"Submitted by")),
                            context.owner.first_name, context.owner.last_name)
        if context.notice_date:
            text += " (%s %s)" % (translate_i18n(_(u"notice given on")),
                                  self.formatDate(context.notice_date))
        return text + "."
'''

# AgendaItem
# TabledDocument
# Event


@register.adapter()
class SittingDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ISitting)

    @property
    def title(self):
        context = _merged(self.context)
        return "%s %s, %s %s %s" % (translate_i18n(_(u"Sitting:")), 
                self.translate(context.group, "short_name"), 
                context.start_date.strftime('%Y-%m-%d, %H:%M'), 
                _(u"to"), 
                context.end_date.strftime('%H:%M'))
    
    @property
    def description(self):
        context = _merged(self.context)
        return "%s %s (%s %s %s)" % (translate_i18n(_(u"Sitting scheduled for")),
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
                    if context.venue else translate_i18n(_(u"no venue"))
                )
            }
        )
        return translate_i18n(sitting_title)

@register.adapter()
class DebateRecordDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IDebateRecord)

    @property
    def title(self):
        context = _merged(self.context)
        return "%s %s, %s %s %s" % (translate_i18n(_(u"Debate Record:")), 
                self.translate(context.sitting, "short_name"), 
                context.sitting.start_date.strftime('%Y-%m-%d, %H:%M'), 
                _(u"to"), 
                context.sitting.end_date.strftime('%H:%M'))
    
    @property
    def description(self):
        context = _merged(self.context)
        return "%s %s (%s %s %s)" % (translate_i18n(_(u"Debate record of ")),
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
        return translate_i18n(
            capi.get_type_info(self.context).descriptor_model.display_name)
    
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
        return "%s %s" % (translate_i18n(_(u"Last modified")), 
            self.context.change.date
        )


@register.adapter()
class GroupDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IBungeniGroup)
    
    @property
    def title(self):
        group = _merged(self.context)
        return self.translate(group, "full_name")


@register.adapter()
class GroupDocumentAssignmentDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IGroupDocumentAssignment)
    
    @property
    def title(self):
        context = _merged(self.context)
        return "%s" % ( self.translate(context.group, "short_name"))


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
        return "%s %s %s".strip() % (
            (self.translate(context, "salutation") if context.salutation else ""),
            context.first_name, context.last_name
        )
    
    @property
    def title_member(self):
        context = _merged(self.context)
        mp_user = None
        try:
            mp_user = Session().query(domain.MemberOfParliament).filter(
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
        if mp_user.representation:
            return _("member_title_with_representation",
                default=u"Member of Parliament for ${representation}"
                " (${member})",
                mapping={"representation": mp_user.representation, 
                    "member": self.title
                }
            )
        return self.title


@register.adapter()
class GroupMembershipDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IBungeniGroupMembership)
    
    @property
    def title(self):
        context = _merged(self.context)
        if context.user:
            return "%s %s %s" % (self.translate(context.user, "salutation"),
                context.user.first_name,
                context.user.last_name)
        else:
            return u"New User"


@register.adapter()
class SittingAttendanceDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ISittingAttendance)
    
    @property
    def title(self):
        context = _merged(self.context)
        if context.member:
            user = context.member
            return "%s %s %s" % (self.translate(user, "salutation"),
                user.first_name, user.last_name)
        else:
            return u"New User"
    
    @property
    def description(self):
        context = _merged(self.context)
        return self.translate(context.attendance_type, 
            "attendance_type"
        )


@register.adapter()
class SignatoryDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.ISignatory)
    
    @property
    def title(self):
        context = _merged(self.context)
        if context.user:
            return "%s %s %s" % (self.translate(context.user, "salutation"),
                context.user.first_name,
                context.user.last_name)
        else:
            return u"New User"
    
    @property
    def status(self):
        context = _merged(self.context)
        return translate_i18n(misc.get_wf_state(context))


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
        return "%s (%s)" %(translate_i18n(self.context.description),
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
    
    @property
    def description(self):
        return self.title

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
class GroupMembershipRoleDescriptiveProperties(DescriptiveProperties):
    component.adapts(interfaces.IGroupMembershipRole)
    
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
