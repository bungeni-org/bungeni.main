# -*- coding: utf-8 -*-
"""$Id$
"""

from zope.viewlet.interfaces import IViewlet
from zope.viewlet.interfaces import IViewletManager
from zope.publisher.interfaces.browser import IBrowserView


class IWorkspaceManager(IViewletManager):
    """Workspace viewlet manager."""


class IWorkspaceArchiveManager(IViewletManager):
    """Workspace-archive viewlet manager."""


class IWorkspaceMIManager(IViewletManager):
    """ Workspace viewlet manager for my interests
        section.
    """

class ISchedulingManager(IViewletManager):
    """Scheduling viewlet manager."""


class ISchedulingViewlet(IViewlet):
    """A scheduling viewlet renders table rows corresponding to
    schedulable items.

    Must render columns in order:

    - Type name
    - Title
    - Workflow state
    - Modification date

    The ``title`` should be linked to the URL of the item.
    """

