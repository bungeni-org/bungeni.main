from zope.publisher.interfaces.browser import IBrowserView
from zope.publisher.interfaces.browser import IDefaultBrowserLayer

from ploned.ui.interfaces import IPlonedSkin
from ore.yui.interfaces import IYUILayer

from zope.configuration import fields

class IBungeniSkin(IPlonedSkin, IYUILayer):
    """Bungeni application skin."""
class IBungeniAuthenticatedSkin(IBungeniSkin):
    """Skin for authenticated users."""

from zope import interface
class IWorkspaceContainer(interface.Interface):
    """Marker for a domain object that is also a user's workspace container."""
class IWorkspaceSectionContext(interface.Interface):
    """Marker for a section of a workspace."""
class IWorkspacePIContext(IWorkspaceSectionContext):
    """Marker for the PI section of a workspace."""
class IWorkspaceArchiveContext(IWorkspaceSectionContext):
    """Marker for the Archive section of a workspace."""
class IWorkspaceSchedulingContext(IWorkspaceSectionContext):
    """Marker for the Scheduling section of a workspace."""

class ISpeakerWorkspace(IBrowserView):
    """Speaker's workspace."""
class IClerkWorkspace(IBrowserView):
    """Clerk's workspace."""
class IAdministratorWorkspace(IBrowserView): # !+ remove out
    """Administrator's workspace."""
class IMinisterWorkspace(IBrowserView):
    """Minister's workspace."""
class IMPWorkspace(IBrowserView):
    """MP's workspace."""


class IHomePageLayer(IDefaultBrowserLayer):
    """Requests for the Home Page."""
class IResourceNonLayer(interface.Interface):
    """A fake layer, to mark that the request is for some resource"""
class IFormEditLayer(interface.Interface):
    """Views showing a Form in edit mode."""

class IArchiveSectionLayer(IDefaultBrowserLayer):
    """Requests for an object within the archive."""

class IBusinessSectionLayer(IDefaultBrowserLayer):
    """Requests for an object within the business section."""
class IBusinessWhatsOnSectionLayer(IDefaultBrowserLayer):
    """Requests for an object within the whats on page of the business section."""

class IMembersSectionLayer(IDefaultBrowserLayer):
    """Requests for an object within the members section."""

class IWorkspaceOrAdminSectionLayer(IDefaultBrowserLayer):
    """Requests for an object within the workspace OR admin section."""
class IAdminSectionLayer(IWorkspaceOrAdminSectionLayer):
    """Requests for an object within the admin section."""
class IWorkspaceSectionLayer(IWorkspaceOrAdminSectionLayer):
    """Requests for an object within the workspace section."""
    
class IOpenOfficeConfig(interface.Interface):
    def getPath():
        "Path to the Openoffice Python binary"
    
class IOpenOfficePath(interface.Interface):
    path = fields.Path(
        title=u"OpenOffice.org Python Path",
        description=u"This is the path name of the openoffice to be used to generate pdf reports",
        required=True
        )
