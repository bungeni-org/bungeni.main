from zope import interface, schema, lifecycleevent
from zope.component.interfaces import IObjectEvent, ObjectEvent
from zope.location.interfaces import ILocation
from zope.container.interfaces import IContainer
from zope.container.interfaces import IContentContainer
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.container.interfaces import IReadContainer

from bungeni.models.interfaces import IVersion

class INavigationProxy(IReadContainer):
    __target__ = interface.Attribute(
        """Navigation target. May be virtual host root and should be
        checked, when computing URLs.""")

class ISection(IContentContainer, IDCDescriptiveProperties):
    """Represents a section in the site, e.g. /business."""

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
####################
# Feature - Marker Interfaces 
# 
# declare implemented to apply feature to a domain model

class IAuditable(interface.Interface):
    """
    marker interface to apply auditing/object log feature
    """

class ISubscribable(interface.Interface):
    """
    marker interface to add a subscription to an object
    """

class IVersionable(interface.Interface):
    """
    marker interface to apply versioning feature ( requires iauditable / object log)
    """

#####################
# Versioned Object Interfaces
#
class IVersioned(IContainer):
    """ a versioning system interface to an object, versioned is a container
        of versions.
    """

    def create():
        """
        store the existing state of the adapted context as a new version
        """

    def revert(version):
        """
        revert the current state of the adapted object to the values specified
        in version.
        """

class IVersionEvent(IObjectEvent):
    """
    a versioning event
    """

    versioned = schema.Object(IVersioned)
    version = schema.Object(IVersion)
    message = schema.Text(description=u"Message accompanying versioning event")

class VersionEvent(ObjectEvent):
    """
    """
    interface.implements(IVersionEvent)

    def __init__(self, object, versioned, version, msg):
        self.object = object
        self.versioned = versioned
        self.version = version
        self.message = msg

class IVersionCreated(IVersionEvent):
    """ a new version was created, but is not yet
    saved to the db
    """

class VersionCreated(VersionEvent):

    interface.implements(IVersionCreated)




class IVersionReverted(IVersionEvent, lifecycleevent.IObjectModifiedEvent):
    """
    the context version was reverted
    """

class VersionReverted(VersionEvent):

    interface.implements(IVersionReverted)

    descriptions = ()


class IFilePathChooser(interface.Interface):

    def path():
        """
        return the path to store a context's files within the repo 
        """

########################
# Versioned Files

class IVersionedFileRepository(interface.Interface):

    def locations(context):
        """
        get all the directory locations for this content
        """

    def new(context, path=None):
        """create a new directory location for context
        """

    def get(path):
        """
        fetch the versioned directory for the given repository
        path
        """

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
