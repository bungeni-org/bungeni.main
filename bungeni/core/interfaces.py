
from zope import interface, schema
from zope.component.interfaces import IObjectEvent, ObjectEvent
from zope.location.interfaces import ILocation
#from zope.container.interfaces import IContainer
from zope.container.interfaces import IContentContainer
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.container.interfaces import IReadContainer
from zope.configuration import fields

class INavigationProxy(IReadContainer):
    __target__ = interface.Attribute(
        """Navigation target. May be virtual host root and should be
        checked, when computing URLs.""")

class ISection(IContentContainer, IDCDescriptiveProperties):
    """Represents a section in the site, e.g. /business."""

class IAkomaNtosoSection(ISection):
    """Akoma Ntoso section with special traverser"""
    lang = interface.Attribute("Object language")
    type = interface.Attribute("Object type")
    id = interface.Attribute("Object id")
    date = interface.Attribute("Date") 

class ISearchableSection(interface.Interface):
    """Marker interface for searchable sections"""

class IQueryContent(interface.Interface):
    query = interface.Attribute(
        """Query-method which returns a content-item.""")

class IContainerLocation(interface.Interface):
    container = interface.Attribute(
        """Container object for this location type.""")

''' !+ADD_CONTEXT
class IAddContext(IContainer):
    """Marks that a container should get a user interface to add new
    objects.

    The purpose of this interface is to indicate a folder to which
    adding new objects makes sense, as opposed to a folder which has
    report-like behavior (e.g. archive).
    """

class IMotionAddContext(IAddContext):
    """Add-context for motions."""

class IQuestionAddContext(IAddContext):
    """Add-context for questions."""

class IBillAddContext(IAddContext):
    """Add-context for bills."""

class ICommitteeAddContext(IAddContext):
    """Add-context for committees."""

class ISessionAddContext(IAddContext):
    """Add-context for sessions."""

class ITabledDocumentAddContext(IAddContext):
    """Add-context for tabled documents."""

class IAgendaItemAddContext(IAddContext):
    """Add-context for agenda items."""

class IReportAddContext(IAddContext):
    """Add-context for report items."""
'''

class IWorkspaceScheduling(interface.Interface):
    """Marker inteface for workspace scheduling"""
class IWorkspaceTab(interface.Interface):
    """Marker inteface for workspace tabs"""
class IWorkspaceDocuments(interface.Interface):
    """Marker inteface for workspace my-documents"""
class IWorkspaceUnderConsideration(interface.Interface):
    """Marker inteface for workspace under consideration"""
class IWorkspaceTrackedDocuments(interface.Interface):
    """Marker inteface for workspace tracked documents"""
class IWorkspaceGroups(interface.Interface):
    """Marker interfaces for workspace groups tab"""

''' !+OBSOLETE_VERSIONING
#####################
# Versioned Object Interfaces
#
from zope import lifecycleevent
from zope.component.interfaces import IObjectEvent, ObjectEvent
from bungeni.models.interfaces import IVersion

class IVersioned(IContainer):
    """A versioning system interface to an object, versioned is a container 
    of versions.
    """
    def create():
        """Store the existing state of the adapted context as a new version.
        """
    def revert(version):
        """Revert the current state of the adapted object to the values 
        specified in version.
        """

class IVersionEvent(IObjectEvent):
    """A versioning event.
    """
    versioned = schema.Object(IVersioned)
    version = schema.Object(IVersion)
    message = schema.Text(description=u"Message accompanying versioning event")

class VersionEvent(ObjectEvent):
    interface.implements(IVersionEvent)
    def __init__(self, object, versioned, version, msg):
        self.object = object
        self.versioned = versioned
        self.version = version
        self.message = msg

class IVersionCreated(IVersionEvent):
    """A new version was created, but is not yet saved to the db.
    """
class VersionCreated(VersionEvent):
    interface.implements(IVersionCreated)

class IVersionReverted(IVersionEvent, lifecycleevent.IObjectModifiedEvent):
    """The context version was reverted.
    """
class VersionReverted(VersionEvent):
    interface.implements(IVersionReverted)
    descriptions = ()
'''


class IVersionCreatedEvent(IObjectEvent):
    """A new version was created (manually or automatically).
    """
class VersionCreatedEvent(ObjectEvent):
    """
    - The version_created_event.object is the version (change) instance.
    - Client code may need to test whether versionCreated.procedure is "m" (manual)
      or is "a" (automatic) and proceed as desired.
    - The head doc for the version created is available as versionCreated.head.
    """
    interface.implements(IVersionCreatedEvent)


class ITranslatonCreatedEvent(IObjectEvent):
    """A translation of an instance was added.
    """
    language = interface.interface.Attribute(
        "Target language of this translation.")
    translated_attribute_names = interface.interface.Attribute(
        "The list of attribute names that have changed by this translation.")
class TranslationCreatedEvent(ObjectEvent):
    interface.implements(ITranslatonCreatedEvent)
    def __init__(self, obj, language, translated_attribute_names):
        self.object = obj
        self.language = language
        self.translated_attribute_names = translated_attribute_names


class ISchedulingContext(ILocation):
    """A context for which events may be scheduled.

    This may be a committee or the plenary.
    """

    group_id = interface.Attribute(
        """Group identifier.""")

    title = interface.Attribute(
        """Scheduling context title.""")

    label = interface.Attribute(
        """Scheduling context label.""")

    def get_group():
        """Returns group."""

    def get_sittings(start_date=None, end_date=None):
        """Return sittings defined for this context."""

class IDailySchedulingContext(ISchedulingContext):
    """Daily scheduling context."""

    date = interface.Attribute(
        """Date to which this scheduling context is bound.""")

# Interfaces for XML views

class IRSSValues(interface.Interface):
    """Interface to get data for forming rss feed.
    """
    values = interface.Attribute("Values")

class IAkomantosoRSSValues(interface.Interface):
    """Interface to get data for forming rss feed which links to content in 
    Akomantoso format.
    """
    values = interface.Attribute("Values")


# Interfaces for file storage utility

class IFSUtilitySchema(interface.Interface):
    """Schema for file storage utility, which contains only storage path.
    """
    fs_path = schema.TextLine(title=u"Path to file system storage")


class IFSUtilityDirective(IFSUtilitySchema):
    """Interface for fs directive.
    """
    name = schema.TextLine(
        title=u"Name of the registered utility", 
        required=False
    )

class IFSUtility(IFSUtilitySchema):
    """Just stores the path to file storage. 
    Can store and remove files by their names.
    """
    def store(data, filename=None):
        """Stores data with the given filename. If no filename given, 
        generates unique for it.
        """
    def remove(filename):
        """Removes the file with given filename from the storage.
        """
    def get(filename):
        """Returns data by filename. If no files found returns None.
        """

class ILanguageProvider(interface.Interface):
    """Provides a language.
    """
    PRECEDENCE = interface.Attribute("Preference order, first sorting first")
    def getLanguage():
        """Return a language code.
        """

class IWorkspaceContainer(interface.Interface):
    """Workspace containers
    """
class IWorkspaceUnderConsiderationContainer(IWorkspaceContainer):
    """Workspace documents under consideration contatiner
    """
class IWorkspaceTrackedDocumentsContainer(IWorkspaceContainer):
    """Marker interface for tracked documents container"""

class IWorkspaceGroupsContainer(IWorkspaceContainer):
    """Marker interfaces for groups container"""

class IWorkspaceTabsUtility(interface.Interface):
    def get_role_domains(role, tab):
        """Returns a list of domains that a role will since in a specific
        tab of the workspace
        """
    def get_status(role, domain_class, tab):
        """Returns a list of status that are applicable for a certain
        tab for a certain role and domain
        """
    def set_content(role, tab, workflow_name, status):
        """Set workspace info"""
    def register_item_type(domain_class, item_type):
        """Set the domain class and type info that is used to generate URLS"""
    def get_domain(key):
        """Given a type, returns the domain_class"""
    def get_type(key):
        """Given a domain_class, returns the item type"""
    def get_tab(role, domain_class, status):
        """Returns the tab an object should be in, given its domain class,
        status and role
        """

class IMessageQueueConfig(interface.Interface):
    def get_message_exchange():
        """Message exchange
        """
    def get_task_exchange():
        """Task exchange
        """
    def get_username():
        """Username to be used to connect to the AMQP server
        """
    def get_password():
        """Password to be used to connect to the AMQP server
        """
    def get_host():
        """AMQP server host
        """
    def get_port():
        """AMQP server port
        """
    def get_virtual_host():
        """AMQP virtual host
        """
    def get_channel_max():
        """Maximum number of channels to allow
        """
    def get_frame_max():
        """Max frame size
        """
    def get_heartbeat():
        """Turn heartbeat checking on or off
        """
    def get_number_of_workers():
        """Get number of task workers
        """
    def get_task_queue():
        """Get name for the task queue
        """


class IMessageQueueConfigSchema(interface.Interface):
    message_exchange=schema.Text(
        title=u"Message Exchange",
        description=u"Fanout Exchange name to be used",
        required=True,
        )
    task_exchange=schema.Text(
        title=u"Task Queue Exchange",
        description=u"Direct task queue exchange name to be used",
        required=True,
        )
    username=schema.Text(
        title=u"Username",
        description=u"Username to be used to connect to the AMQP server",
        required=True,
        default=u"guest"
        )
    password=schema.Text(
        title=u"Password",
        description=u"Password to be used to connect to the AMQP server",
        required=True,
        default=u"guest"
        )
    host=schema.Text(
        title=u"Host",
        description=u"AMQP Server Host",
        required=True,
        default=u"localhost"
        )
    port=schema.Int(
        title=u"Port",
        description=u"AMQP Server Port Number",
        required=True,
        default=5672
        )
    virtual_host=schema.Text(
        title=u"Virtual Host",
        description=u"Virtual host to use",
        required=True,
        default=u"/"
        )
    channel_max=schema.Int(
        title=u"Channel Max",
        description=u"Maximum number of channels to allow",
        required=True,
        min=1,
        max= 65535,
        default=1
        )
    frame_max=schema.Int(
        title=u"Max frame size",
        description=u"The maximum byte size for an AMQP Frame",
        required=True,
        default=131072
        )
    heartbeat=schema.Int(
        title=u"Heartbeat",
        description=u"How often to send hearbeats",
        required=False,
        )
    number_of_workers=schema.Int(
        title=u"Number of worker processes",
        description=u"Number of worker daemon processes",
        required=True,
        default=5
        )
    task_queue=schema.Text(
        title=u"Task queue name",
        description=u"Task queue name",
        required=True,
        default=u"task_queue"
        )
        
class INotificationsUtility(interface.Interface):
    def set_transition_based_notification(domain_class, state, roles):
        """Set the roles to be notified when a document reaches a certain
        state
        """
    def set_time_based_notification(domain_class, state, roles, time):
        """Set the roles to be notified after a certain amount of time has
        elapsed since state was reached
        """  

class IBungeniMailer(interface.Interface):
    """Interface for mailer utility
    """


class INotificationEvent(IObjectEvent):
    """A notification event whose `object` property is a dictionary.
    
    Dictionary format:
        `{
            "subject": "Message subject",
            "body": "Message content",
            "recipients": [] #list of email address,
        }`
    """

class NotificationEvent(ObjectEvent):
    interface.implements(INotificationEvent)

class IDebateRecordConfig(interface.Interface):
    """Interface for debate record configuration
    """

class IDebateRecordConfigSchema(interface.Interface):
    transcriber_role = schema.Text(
        title=u"Transcriber role",
        description=u"Role for the members of staff who do the transcription",
        required=True,
        )
    take_duration = schema.Int(
        title=u"Duration of takes",
        description=u"Take duration",
        required=True,
        )
