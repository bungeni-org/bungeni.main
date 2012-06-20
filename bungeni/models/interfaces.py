
from zope import interface, schema
from zope.app.container.interfaces import IContainer
from bungeni.alchemist.interfaces import IAlchemistContainer
from ore.wsgiapp.interfaces import IApplication
from i18n import _
from zope.configuration.fields import MessageID

DEBUG = True
ENABLE_LOGGING = False
ENABLE_EVENT_LOGGING = False

if ENABLE_EVENT_LOGGING:
    import eventlog


class IBungeniApplication(IApplication):
    """Bungeni Application.
    """

class IBungeniAdmin(IContainer):
    """Admin Container.
    """

class IAdminUserContainer(interface.Interface):
    """A container that returns object for the admin ui, marked with 
    admin interface markers.
    """

''' !+UNUSED(mr, nov-2010)
class IAdminGroupContainer(interface.Interface):
    pass
'''

class IUserAdmin(interface.Interface):
    """Marker interface attached to user objects viewed in the admin for 
    admin views.
    """

class IGroupAdmin(interface.Interface):
    """Marker interface attached to user objects viewed in the admin for 
    admin views.
    """

# !+NAMING(mr, apr-2011) rename IUser, inconsistent with domain
class IBungeniUser(interface.Interface):
    """A user in bungeni.
    """
IUser = IBungeniUser
# !+NAMING(mr, apr-2011) rename IGroup, inconsistent with domain
class IBungeniGroup(interface.Interface):
    """A group in bungeni.
    """
class IUserContainer(IAlchemistContainer): pass

class IParliament(IBungeniGroup):
    """Marker interface for group parliament.
    """
class IParliamentContainer(IAlchemistContainer): pass

class IGovernment(IBungeniGroup):
    """Marker interface for group Government.
    """
class IGovernmentContainer(IAlchemistContainer): pass

class IMinistry(IBungeniGroup):
    """Marker interface for group ministry """
class IMinistryContainer(IAlchemistContainer): pass

class ICommittee(IBungeniGroup):
    """Marker interface for group ministry.
    """
class ICommitteeContainer(IAlchemistContainer): pass

class IPoliticalGroup(IBungeniGroup):
    """Marker interface for political group (inside parliament).
    """
class IPoliticalGroupContainer(IAlchemistContainer): pass

class IOffice(IBungeniGroup):
    """Marker interface for a parliamentary office.
    """
class IOfficeContainer(IAlchemistContainer): pass

class ICommittee(IBungeniGroup): pass
class ICommitteeContainer(IAlchemistContainer): pass

class IBungeniGroupMembership(interface.Interface):
    """Group membership in bungeni.
    """

class IMemberOfParliament(IBungeniGroupMembership): pass
class IMemberOfParliamentContainer(IAlchemistContainer): pass

class IPoliticalGroupMember(IBungeniGroupMembership):
    pass

class IMinister(IBungeniGroupMembership): pass
class IMinisterContainer(IAlchemistContainer): pass

class ICommitteeMember(IBungeniGroupMembership):
    pass

class ICommitteeStaff(IBungeniGroupMembership):
    pass

class IOfficeMember(IBungeniGroupMembership): pass
class IOfficeMemberContainer(IAlchemistContainer): pass

class IOwned(interface.Interface):
    """Object supports having an "owner" i.e. an owner:user attribute.
    """
    def owner():
        """Get the user instance that is the owner of this item.
        """

class IBungeniContent(IOwned):
    """Parliamentary content
    
    !+IBungeniContent(mr, nov-2011) clarify distinction, 
    in intention and use, between the following interfaces: 
    IBungeniParliamentaryContent -> IBungeniContent -> IAlchemistContent
    Should standardize registration on the appropriate one (or on IWorklfowed).
    """
    # !+ schema attributes ?
    # status: rdb.Unicode(48)
    # status_date: rdb.DateTime(timezone=False)

class IBungeniParliamentaryContent(IBungeniContent):
    """Marker interface for true bungeni parliamentary content"""
    # !+IBungeniContent(mr, may-2012) drop either IBungeniContent or
    # IBungeniParliamentaryContent !

class IBungeniContainer(IAlchemistContainer):
    """Parliamentary container.
    """

class ISittingContainer(IBungeniContainer):
    pass

class IBungeniGroupMembershipContainer(IBungeniContainer):
    pass

class ICommitteeMemberContainer(IBungeniGroupMembershipContainer):
    pass

class ICommitteeStaffContainer(IBungeniGroupMembershipContainer):
    pass

class IVersion(interface.Interface):
    """A version of an object is identical in attributes to the actual 
    object, based on that object's domain schema.
    """
''' !+OBSOLETE_VERSIONING
class IVersionContainer(IBungeniContainer):
    pass
'''
# !+AuditLogView(mr, nov-2011)
#class IChangeContainer(IBungeniContainer): pass


class IHeading(interface.Interface): pass
class IHeadingContainer(IAlchemistContainer): pass

class IEvent(IBungeniContent): pass
class IEventContainer(IBungeniContainer): pass


# !+IITEMVersion(mr, sep-2011): should IITEMVersion exist at all? if so, 
# should it inherit from IITEM, or from IVersion? Note that 
# IITEMVersionContainer inherits from IVersionContainer (is used by alchemist).

class IQuestion(IBungeniContent):
    """Parliamentary Question.
    """
class IQuestionContainer(IBungeniContainer): pass
# !+IITEMVersion
#class IQuestionVersion(IQuestion): pass
#!+OBSOLETE_VERSIONING class IQuestionVersionContainer(IVersionContainer): pass

class IBill(IBungeniContent):
    """Parliamentary Bill.
    """
class IBillContainer(IBungeniContainer): pass
# !+IITEMVersion
#class IBillVersion(IBill): pass
#!+OBSOLETE_VERSIONING class IBillVersionContainer(IVersionContainer): pass

class IMotion(IBungeniContent):
    """Parliamentary Motion.
    """
class IMotionContainer(IBungeniContainer): pass
# !+IITEMVersion
#class IMotionVersion(IMotion): pass
#!+OBSOLETE_VERSIONING class IMotionVersionContainer(IVersionContainer): pass


class ISitting(interface.Interface):
    pass

class ISittingAttendance(interface.Interface): pass
class ISittingAttendanceContainer(IAlchemistContainer): pass
    
class IItemSchedule(interface.Interface): pass
class IItemScheduleContainer(IAlchemistContainer): pass

class IEditorialNote(interface.Interface):
    """Marker interface for editorial notes in a sitting's agenda"""

class IScheduleText(interface.Interface):
    """Marker interface for text records e.g. in agenda.
    This covers `IHeading` and `IEditorialNote'` at this point.
    """

class IItemScheduleDiscussion(interface.Interface): pass
class IItemScheduleDiscussionContainer(IAlchemistContainer): pass

class ITabledDocument(IBungeniContent):
    """Tabled document.
    """
class ITabledDocumentContainer(IBungeniContainer): pass
# !+IITEMVersion
#class ITabledDocumentVersion(ITabledDocument): pass
#!+OBSOLETE_VERSIONING class ITabledDocumentVersionContainer(IVersionContainer): pass

class IAgendaItem(IBungeniContent): pass
class IAgendaItemContainer(IBungeniContainer): pass
# !+IITEMVersion
#class IAgendaItemVersion(IAgendaItem): pass
#!+OBSOLETE_VERSIONING class IAgendaItemVersionContainer(IVersionContainer): pass

class IParliamentSession(interface.Interface): pass
class IParliamentSessionContainer(IAlchemistContainer): pass

class IBungeniSetup(interface.Interface):

    def setUp(app):
        """Setup the application on server start.
        """

class IBungeniSettings(interface.Interface):
    speakers_office_email = schema.TextLine(
        title=_(u"Speaker's Office Email"),
        default=u"speakers.office@parliament.go.tld"
    )
    speakers_office_notification = schema.Bool(
        title=_(u"Speaker's Office Notification"),
        description=_(u"Alert the speaker's office when a document is "
            "submitted"
        ),
        default=False
    )
    clerks_office_notification = schema.Bool(
        title=_(u"Clerk's Office Notification"),
        description=_(u"Alert the clerk's office by e-mail when a document is "
            "submitted"
        ),
        default=False
    )
    clerks_office_email = schema.TextLine(
        title=_(u"Clerks's Office Email"),
        default=u"clerks.office@parliament.go.tld"
    )
    ministries_notification = schema.Bool(
        title=_(u"Ministries Notification"),
        description=_(u"Notify concerned ministries by e-mail when a document "
            "is submitted"
        ),
        default=False
    )
    administrators_email = schema.TextLine(
            title=_(u"Administrator's Email"),
            default=u"admin@parliament.go.tld"
    )
    question_submission_allowed = schema.Bool(
        title=_(u"Allow Question Submission"),
        default=True
    )
    days_to_defer_question = schema.Int(
        title=_(u"Days to Defer Question"),
        description=_(u"number of days after which admissible questions are "
            "automatically deferred"
        ),
        default=10
    )
    days_to_notify_ministry_unanswered = schema.Int(
        title=_(u"Days to Notify Ministry of Pending Response"),
        description=_(u"Days after which to notify concerned ministry and  "
            "clerk's office of questions with pending responses"
        ),
        default=5
    )
    days_before_question_schedule = schema.Int(
        title=_(u"Days before question scheduled"),
        default=3
    )
    days_before_bill_schedule = schema.Int(
        title=_(u"Days before bill scheduled"),
        default=3
    )
    max_questions_sitting = schema.Int(
        title=_(u"Maximum Questions Per Sitting"),
        default=15
    )
    max_mp_questions_sitting = schema.Int(
        title=_(u"Maximum Questions Per Sitting Per MP"),
        default=1
    )
    max_sittings_in_business = schema.Int(
        title=_(u"Number of sittings to include in what's business section"),
        default=5,
        min=1
    )
    bill_signatories_min = schema.Int(
        title=_(u"Minimum consented signatories for a bill"), default=0
    )
    bill_signatories_max = schema.Int(
        title=_(u"Maximum consented signatories for a bill"), default=0
    )
    question_signatories_min = schema.Int(
        title=_(u"Minimum consented signatories for a question"), default=0
    )
    question_signatories_max = schema.Int(
        title=_(u"Maximum consented signatories for a question"), default=0
    )
    motion_signatories_min = schema.Int(
        title=_(u"Minimum consented signatories for a motion"), default=0
    )
    motion_signatories_max = schema.Int(
        title=_(u"Maximum consented signatories for a motion"), default=0
    )
    agendaitem_signatories_min = schema.Int(
        title=_(u"Minimum consented signatories for an agenda item"), default=0
    )
    agendaitem_signatories_max = schema.Int(
        title=_(u"Maximum consented signatories for an agenda item"), default=0
    )
    tableddocument_signatories_min = schema.Int(
        title=_(u"Minimum consented signatories for a tabled document"), 
        default=0
    )
    tableddocument_signatories_max = schema.Int(
        title=_(u"Maximum consented signatories for a tabled document"), 
        default=0
    )

class IBungeniRegistrySettings(interface.Interface):

    global_number = schema.Bool(
        title=_(u"Reset global registry number"),
        default=False
    )
    questions_number = schema.Bool(
        title=_(u"Reset questions registry number"),
        default=False
    )
    motions_number = schema.Bool(
        title=_(u"Reset motions registry number"),
        default=False
    )
    agendaitems_number = schema.Bool(
        title=_(u"Reset agenda items registry number"),
        default=False
    )
    bills_number = schema.Bool(
        title=_(u"Reset bills registry number"),
        default=False
    )
    reports_number = schema.Bool(
        title=_(u"Reset reports registry number"),
        default=False
    )
    tableddocuments_number = schema.Bool(
        title=_(u"Reset tabled documents registry number"),
        default=False
    )
    
    

class IBungeniUserSettings(interface.Interface):

    # examples
    email_delivery = schema.Bool(
        title=_(u"Email Notifications Enabled?"),
        default=True
    )

class IBungeniEmailSettings(interface.Interface):
    hostname = schema.TextLine(
        title = _("Email server hostname or IP address"),
        default = u"localhost",
    )
    port = schema.Int(
        title = _("Email server port"),
        default = 25,
    )
    username = schema.TextLine(
        title = _("Email server login name"),
        default = u"",
    )
    password = schema.Password(
        title = _("Email server password"),
        default = u"",
    )
    default_sender = schema.TextLine(
        title = _("Default sender address"),
        default = u"",
    )
    use_tls = schema.Bool(
        title = _("Connect securely to mail server (using TLS)"),
        default = False,
    )

class IAttachment(IOwned): pass
class IAttachmentContainer(IAlchemistContainer): pass
# !+VERSION_CLASS_PER_TYPE
class IAttachedFileVersion(interface.Interface): pass 
# !+OBSOLETE_VERSIONING
#class IAttachedFileVersionContainer(IVersionContainer): pass

class ISignatory(interface.Interface):
    """Signatories for bills, motions, ...
    """
class ISignatoryContainer(IAlchemistContainer): pass

class ISignatoriesValidator(interface.Interface):
    """Validation machinery for iterms with signatories"""

    signatories = interface.Attribute("""signatories iteratable""")
    
    min_signatories = interface.Attribute("""minimum consented signatories""")

    max_signatories = interface.Attribute("""maximum consented signatories""")

    signatories_count = interface.Attribute("""number of signatories""")
    
    consented_signatories = interface.Attribute("""number of consented """)
    
    # !+naming(mr, oct-2011) please follow standard python naming conventions!
    
    def validateSignatories():
        """Validate signatories count on parliamentary item i.e. number added
        """

    def requireSignatures():
        """Does the document or object require signatures
        """

    def validateConsentedSignatories():
        """Validate number of consented signatories against min and max
        """

    def allowSignature():
        """Check that the current user has the right to consent on document 
        """
    
    def documentSubmitted():
        """Check that the document has been submitted
        """
    
    def documentInDraft():
        """Check that the document is in draft stage
        """
    
    def expireSignatures():
        """Should pending signatures be archived
        """


class IItemScheduleCategory(interface.Interface):
    pass


class IDirectoryLocation(interface.Interface):

    repo_path = schema.ASCIILine()
    object_id = schema.Int()
    object_type = schema.ASCIILine()

class IProxiedDirectory(interface.Interface):
    """An interface for a contained directory we can attach menu links
    to that point back to our parent.
    """

# IFeature marker interfaces -- apply to a domain model, to declare that it 
# implements the feature. To avoid "english language anomalies of derived names" 
# e.g "schedule" -> ISchedulable, adopt a very KISS feature->interface naming 
# convention: "schedule"->IFeatureSchedule

class IFeature(interface.Interface):
    """Base feature marker interface.
    """
class IFeatureAudit(IFeature):
    """Marks support for "audit" feature.
    """
class IFeatureVersion(IFeature):
    """Marks support for "version" feature (requires "audit").
    """
class IFeatureAttachment(IFeature):
    """Marks support for "attachment" feature.
    """
class IFeatureEvent(IFeature):
    """Marks support for "event" feature.
    """
class IFeatureSignatory(IFeature):
    """Marks support for "signatory" feature.
    """
class IFeatureSchedule(IFeature):
    """Marks support for "schedule" feature.
    """
class IFeatureAddress(IFeature):
    """Marks support for "address" feature.
    """
class IFeatureWorkspace(IFeature):
    """Marks support for "workspace" feature.
    """
#

''' !+DATERANGEFILTER(mr, dec-2010) disabled until intention is understood
class IDateRangeFilter(interface.Interface):
    """Adapts a model container instance and a SQLAlchemy query
    object, applies a date range filter and returns a query.

    Parameters: ``start_date``, ``end_date``.

    These must be bound before the query is executed.
    """
'''


class IChange(interface.Interface):
    """Marker for Change (log table).
    """

class IMemberTitle(interface.Interface):
    """Marker for member titles"""
class IMemberTitleContainer(IAlchemistContainer): pass

class ITitleType(interface.Interface):
    """Title types"""
class ITitleTypeContainer(IAlchemistContainer): pass

class IAddress(interface.Interface):
    """Base marker interface for an Address
    """
class IAddressContainer(IAlchemistContainer): pass
class IGroupAddress(IAddress):
    """Marker interface addresses of a group.
    """
class IGroupAddressContainer(IAlchemistContainer): pass
class IUserAddress(IAddress):
    """Marker interface addresses of a user.
    """
class IUserAddressContainer(IAlchemistContainer): pass

class IReport(IBungeniContent): pass
class IReportContainer(IAlchemistContainer): pass

class IReport4Sitting(IBungeniContent): pass

class IUserDelegation(interface.Interface): pass
class IUserDelegationContainer(IAlchemistContainer): pass

class ITranslatable(interface.Interface):
    """Marker Interface if an object is translatable.
    """
    language = interface.Attribute("The language of the values of the "
        "translatable attributes of the instance")

class IBungeniVocabulary(interface.Interface):
    """Marker interface for vocabularies managed in admin UI."""

'''!+TYPES_CUSTOM
class IAddressType(IBungeniVocabulary):
    """Marker interface for address types vocabulary"""
class IPostalAddressType(IBungeniVocabulary):
    """Marker interface for address postal types"""

class IBillType(IBungeniVocabulary):
    """Marker interface for bill types vocabulary"""

class IQuestionType(IBungeniVocabulary):
    """Marker interface for question types"""
class IResponseType(IBungeniVocabulary):
    """Marker interface for response types"""

class ICommitteeType(IBungeniVocabulary):
    """Marker interface for committee types vocabulary"""

class ICommitteeTypeStatus(IBungeniVocabulary):
    """Marker interface for committe type statuses"""
class IAttendanceType(IBungeniVocabulary):
    """Marker interface for attendance types vocabulary"""
class IMemberElectionType(IBungeniVocabulary):
    """Marker interface for member election types"""
'''

class IVenue(IBungeniVocabulary):
    """Marker interface for venues vocabulary"""
class ISubRoleDirective(interface.Interface):
    """Define a new sub role."""
    id = schema.Id(
        title=u"Id",
        description=u"Id as which this object will be known and used.",
        required=True)

    title = MessageID(
        title=u"Title",
        description=u"Provides a title for the object.",
        required=True)

    description = MessageID(
        title=u"Description",
        description=u"Provides a description for the object.",
        required=False)
        
    role = schema.Id(
        title=u"Parent Role ID",
        description=u"Role ID for role which this subrole extends",
        required=True)

class ISubRoleAnnotations(interface.Interface):
    sub_roles = interface.Attribute('Sub_Roles')
    is_sub_role = interface.Attribute('Sub_Roles')

class ICountry(interface.Interface):
    """Marker interface for Country"""
