
from zope import interface, schema
from zope.app.container.interfaces import IContainer
from bungeni.alchemist.interfaces import IAlchemistContent
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

class IAdminGroupContainer(interface.Interface):
    pass

class IUserAdmin(interface.Interface):
    """Marker interface attached to user objects viewed in the admin for 
    admin views.
    """

class IGroupAdmin(interface.Interface):
    """Marker interface attached to user objects viewed in the admin for 
    admin views.
    """

# !+NAMING(mr, apr-2011) rename, inconsistent with domain
class IBungeniUser(interface.Interface):
    """A user in bungeni.
    """

# !+NAMING(mr, apr-2011) rename, inconsistent with domain
class IBungeniGroup(interface.Interface):
    """A group in bungeni.
    """

class IParliament(IBungeniGroup):
    """Marker interface for group parliament.
    """

class IGovernment(IBungeniGroup):
    """Marker interface for group Government.
    """

class IMinistry(IBungeniGroup):
    """ marker interface for group ministry """

class ICommittee(IBungeniGroup):
    """Marker interface for group ministry.
    """

class IPoliticalGroup(IBungeniGroup):
    """Marker interface for political group (inside parliament).
    """
class IPoliticalParty(IBungeniGroup):
    """Marker interface for political party (outside parliament).
    """

class IOffice(IBungeniGroup):
    """Marker interface for a parliamentary office.
    """

class ICommittee(IBungeniGroup):
    pass

class IBungeniGroupMembership(interface.Interface):
    """Group membership in bungeni.
    """

class IMemberOfParliament(IBungeniGroupMembership):
    pass

class IPartyMember(IBungeniGroupMembership):
    pass

class IMinister(IBungeniGroupMembership):
    pass

class ICommitteeMember(IBungeniGroupMembership):
    pass

class ICommitteeStaff(IBungeniGroupMembership):
    pass

class IOfficeMember(IBungeniGroupMembership):
    pass


class IBungeniContent(interface.Interface):
    """Parliamentary content
    """
    # !+ schema attributes ?
    # status: rdb.Unicode(48)
    # status_date: rdb.DateTime(timezone=False)

class IBungeniParliamentaryContent(interface.Interface):
    """Marker interface for true bungeni parliamentary content"""

class IBungeniContainer(IAlchemistContainer):
    """Parliamentary container.
    """

class IGroupSittingContainer(IBungeniContainer):
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
class IVersionContainer(IBungeniContainer):
    pass


class IHeading(IBungeniContent):
    pass

class IEventItem(IBungeniContent):
    pass

# !+IITEMVersion(mr, sep-2011): should IITEMVersion exist at all? if so, 
# should it inherit from IITEM, or from IVersion? Note that 
# IITEMVersionContainer inherits from IVersionContainer (is used by alchemist).

class IQuestion(IBungeniContent):
    """Parliamentary Question.
    """
# !+IITEMVersion
#class IQuestionVersion(IQuestion): pass
class IQuestionVersionContainer(IVersionContainer): pass


class IBill(IBungeniContent):
    """Parliamentary Bill.
    """
# !+IITEMVersion
#class IBillVersion(IBill): pass
class IBillVersionContainer(IVersionContainer): pass

class IMotion(IBungeniContent):
    """Parliamentary Motion.
    """
# !+IITEMVersion
#class IMotionVersion(IMotion): pass
class IMotionVersionContainer(IVersionContainer): pass


class IGroupSitting(interface.Interface):
    pass

class IGroupSittingAttendance(interface.Interface):
    pass
    
class IGroupSittingType(interface.Interface):
    pass

class IItemSchedule(interface.Interface):
    pass

class ISittingType(interface.Interface):
    pass


class IItemScheduleDiscussion(interface.Interface):
    pass

class ITabledDocument(IBungeniContent):
    """Tabled document.
    """
# !+IITEMVersion
#class ITabledDocumentVersion(ITabledDocument): pass
class ITabledDocumentVersionContainer(IVersionContainer): pass

class IAgendaItem(IBungeniContent): pass
# !+IITEMVersion
#class IAgendaItemVersion(IAgendaItem): pass
class IAgendaItemVersionContainer(IVersionContainer): pass

class IParliamentSession(interface.Interface):
    pass

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
        title = _(u"Clerks's Office Email"),
        default = u"clerks.office@parliament.go.tld"
    )
    ministries_notification = schema.Bool(
        title = _(u"Ministries Notification"),
        description = _(u"Notify concerned ministries by e-mail when a document "
        "is submitted"),
        default = False
    )
    administrators_email = schema.TextLine(
            title=_(u"Administrator's Email"),
            default = u"admin@parliament.go.tld"
            )
    question_submission_allowed = schema.Bool(
        title=_(u"Allow Question Submission"),
        default = True
    )
    days_to_defer_question = schema.Int(
        title=_(u"Days to Defer Question"),
        description=_(u"number of days after which admissible questions are "
        "automatically deferred"),
        default = 10
    )
    days_to_notify_ministry_unanswered = schema.Int(
        title=_(u"Days to Notify Ministry of Pending Response"),
        description=_(u"Days after which to notify concerned ministry and  "
            "clerk's office of questions with pending responses"
        ),
        default = 5
    )
    days_before_question_schedule = schema.Int(
        title=_(u"Days before question scheduled"),
        default = 3
    )
    days_before_bill_schedule = schema.Int(
        title=_(u"Days before bill scheduled"),
        default = 3
    )
    max_questions_sitting = schema.Int(
        title=_(u"Maximum Questions Per Sitting"),
        default = 15
    )
    max_mp_questions_sitting = schema.Int(
        title=_(u"Maximum Questions Per Sitting Per MP"),
        default = 1
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


class IAssignment(IAlchemistContent):

    content = schema.Object(IAlchemistContent)
    context = schema.Object(IAlchemistContent)
    title = schema.TextLine(
        title=_(u"Title of document assignment to group or committee")
    )
    start_date = schema.Date(title=_(u"Start date of document assignment"))
    end_date = schema.Date(title=_(u"End date of document assignment"))
    type = schema.TextLine(title=_(u"Document assignment type"), readonly=True)
    status = schema.TextLine(title=_(u"Status"), readonly=True)
    notes = schema.Text(title=_(u"Notes"), description=_(u"Notes"))

class IContentAssignments(interface.Interface):
    """Assignments of this content to different contexts.
    """
    def __iter__():
        """Iterate over assignments for this context.
        """

class IContextAssignments(interface.Interface):
    """Content assignments for the given context/group.
    """
    def __iter__():
        """Iterate over assignments for this context.
        """

class IAssignmentFactory(interface.Interface):
    """Assignment factory.
    """
    def new(**kw):
        """Create a new assignment.
        """

class IAttachedFile(interface.Interface): pass
class IAttachedFileVersion(IVersion): pass
class IAttachedFileVersionContainer(IVersionContainer): pass

class ISignatory(interface.Interface):
    """Signatories for bills, motions, ...
    """

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

class IConstituency(interface.Interface):
    """Constituencies.
    """

class IConstituencyDetail(interface.Interface):
    pass

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

# feature markers - apply to a domain model, to declare it implements feature

class IAuditable(interface.Interface):
    """Marker interface to apply audit feature.
    """
class IVersionable(interface.Interface):
    """Marker to apply version feature (requires IAuditable/audit.
    """
class IAttachmentable(interface.Interface):
    """Marker to apply attachment feature.
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
    
class ITitleType(interface.Interface):
    """Title types"""

class _IAddress(interface.Interface):
    """Base marker interface for an Address
    """
class IGroupAddress(_IAddress):
    """Marker interface addresses of a group.
    """
class IUserAddress(_IAddress):
    """Marker interface addresses of a user.
    """


class IGroupItemAssignment(interface.Interface):
    pass

class IGroupGroupItemAssignment(IGroupItemAssignment):
    pass

class IItemGroupItemAssignment(IGroupItemAssignment):
    pass

class IReport(IBungeniContent):
    pass
class IReport4Sitting(IBungeniContent):
    pass
class IUserDelegation(interface.Interface):
    pass

class IProvince(interface.Interface):
    pass

class IRegion(interface.Interface):
    pass

class ITranslatable(interface.Interface):
    """Marker Interface if an object is translatable.
    """
    language = interface.Attribute("The language of the values of the "
        "translatable attributes of the instance")

class IBungeniVocabulary(interface.Interface):
    """Marker interface for vocabularies managed in admin UI."""

class IAddressType(IBungeniVocabulary):
    """Marker interface for address types vocabulary"""

class IBillType(IBungeniVocabulary):
    """Marker interface for bill types vocabulary"""

class ICommitteeType(IBungeniVocabulary):
    """Marker interface for committee types vocabulary"""

class IAttendanceType(IBungeniVocabulary):
    """Marker interface for attendance types vocabulary"""

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
class IQuestionType(IBungeniVocabulary):
    """Marker interface for question types"""

class IResponseType(IBungeniVocabulary):
    """Marker interface for response types"""

class IMemberElectionType(IBungeniVocabulary):
    """Marker interface for member election types"""
class ISubRoleAnnotations(interface.Interface):
    sub_roles = interface.Attribute('Sub_Roles')
    is_sub_role = interface.Attribute('Sub_Roles')

class IPostalAddressType(IBungeniVocabulary):
    """Marker interface for address postal types"""

class ICommitteeTypeStatus(IBungeniVocabulary):
    """Marker interface for committe type statuses"""

class ICountry(interface.Interface):
    """Marker interface for Country"""

class IWorkspaceContainer(interface.Interface):
    pass
