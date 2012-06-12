from zope import interface, schema
from zope.location.interfaces import ILocation
from zope.container.interfaces import IContainer
from zope.container.interfaces import IContentContainer
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.container.interfaces import IReadContainer


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

class IWorkspaceScheduling(interface.Interface):
    """Marker inteface for workspace scheduling"""
class IWorkspaceInbox(interface.Interface):
    """Marker inteface for workspace inbox"""
class IWorkspaceDraft(interface.Interface):
    """Marker inteface for workspace draft"""
class IWorkspaceSent(interface.Interface):
    """Marker inteface for workspace sent"""
class IWorkspaceArchive(interface.Interface):
    """Marker inteface for workspace archive"""
class IWorkspaceDocuments(interface.Interface):
    """Marker inteface for workspace archive"""


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
    def getLanguage():
        """Return a language code.
        """

class IWorkspaceContainer(interface.Interface):
    """Workspace containers
    """

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
