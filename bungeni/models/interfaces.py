
from zope import interface, schema, lifecycleevent
from zope.component.interfaces import IObjectEvent, ObjectEvent
from zope.app.container.interfaces import IContainer
from bungeni.alchemist.interfaces import IAlchemistContent
from bungeni.alchemist.interfaces import IAlchemistContainer
from ore.wsgiapp.interfaces import IApplication
from i18n import _


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

class IBungeniUser(interface.Interface):
    """A user in bungeni.
    """

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
    !+ is this equivalent IWorkflowable ? see:
       ui.browser.BungeniBrowserView.is_workflowed()
    """
    # !+ schema attributes ?
    # status: rdb.Unicode(48)
    # status_date: rdb.DateTime(timezone=False)


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

class IVersionContainer(IBungeniContainer):
    pass


class IHeading(IBungeniContent):
    pass

class IEventItem(IBungeniContent):
    pass

class IQuestion(IBungeniContent):
    """Parliamentary Question.
    """

class IQuestionVersion(IQuestion):
    pass

class IQuestionVersionContainer(IVersionContainer):
    pass


class IBill(IBungeniContent):
    """Parliamentary Bill.
    """

class IBillVersion(IBill):
    pass

class IBillVersionContainer(IVersionContainer):
    pass

class IMotion(IBungeniContent):
    """Parliamentary Motion.
    """

class IMotionVersion(IMotion):
    pass

class IMotionVersionContainer(IVersionContainer):
    pass



class IGroupSitting(interface.Interface):
    pass

class IGroupSittingAttendance(interface.Interface):
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
class ITabledDocumentVersion(ITabledDocument):
    pass

class ITabledDocumentVersionContainer(IVersionContainer):
    pass

class IAgendaItem(IBungeniContent):
    pass

class IAgendaItemVersion(IAgendaItem):
    pass

class IAgendaItemVersionContainer(IVersionContainer):
    pass

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
        description=_(u"true if the Speakers office wants to be alerted by "
            "mail whenever a bill, motion, question is submitted"),
        default=False
    )
    clerks_office_notification = schema.Bool(
        title=_("Clerk's Office Notification"),
        description=_(u"true if the clerks office wants to be alerted by mail"
            u"whenever a bill, motion, question is submitted"),
        default=False
    )
    clerks_office_email = schema.TextLine(
        title=_(u"Clerks's Office Email"),
        default=u"clerks.office@parliament.go.tld"
    )
    administrators_email = schema.TextLine(title=_(u"Administrator's Email"))
    question_submission_allowed = schema.Bool(
        title=_(u"Allow Question Submission"),
        default=True
    )
    days_to_defer_question = schema.Int(
        title=_(u"Days to Defer Question"),
        description=_(u"Time after which admissible questions are "
            "automatically deferred"),
        default=10
    )
    days_to_notify_ministry_unanswered = schema.Int(
        title=_(u"Days to Notify Ministry of Pending Response"),
        description=_(u"Timeframe after which the clerksoffice and the "
            "ministry is alerted that questions that are pending response "
            "are not yet answered")
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
        title=_(u"Max Questions Per Sitting"),
        default=15
    )
    max_mp_questions_sitting = schema.Int(
        title=_(u"Max Questions Per Sitting Per MP"),
        default=1
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
        title = _("Use TLS to connect"),
        default = False,
    )


class IAssignment(IAlchemistContent):

    content = schema.Object(IAlchemistContent)
    context = schema.Object(IAlchemistContent)
    title = schema.TextLine(title=_(u"Name of the Assignment"))
    start_date = schema.Date(title=_(u"Start Date of the Assignment"))
    end_date = schema.Date(title=_(u"End Date of the Assignment"))
    type = schema.TextLine(title=_(u"Assignment Type"), readonly=True)
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

class IAttachedFile(interface.Interface):
    pass

class IAttachedFileVersionContainer(IVersionContainer):
    pass

class ICosignatory(interface.Interface):
    """Cosignatories for bills, motions, ...
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

class IVersion(interface.Interface):
    """A version of an object is identical in attributes to the actual 
    object, based on that object's domain schema.
    """

class IAttachedFileVersion(IVersion):
    pass


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

class IMemberRoleTitle(interface.Interface):
    pass


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

