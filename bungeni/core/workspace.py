log = __import__("logging").getLogger("bungeni.core.workspace")
import os
from lxml import etree

from zope.interface import implements
from zope.app.publication.traversers import SimpleComponentTraverser
from zope.security.proxy import removeSecurityProxy
from zope.component import getUtility
from zope.publisher.interfaces import NotFound
from zope.component import queryMultiAdapter
from bungeni.utils.capi import capi
from bungeni.core.interfaces import IWorkspaceTabsUtility
from bungeni.models import domain


# Tabs that are available in the workspace
# All logged in users get a workspace with these tabs
TABS = ["draft", "inbox", "sent", "archive"]


class WorkspaceContainerTraverser(SimpleComponentTraverser):
    """Traverser for workspace containers"""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        """First checks if the name refers to a view of this container,
           then checks if the me refers to an item in this container,
           else raises a NotFound
        """
        workspace = removeSecurityProxy(self.context)
        view = queryMultiAdapter((workspace, request), name=name)
        if view:
            return view
        ob = workspace.get(name)
        if ob:
            return ob
        log.error("Workspace - Object does not exist - %s", name)
        raise NotFound(workspace, name)


class WorkspaceTabsUtility():
    """This is utility stores the workflow configuration
    """
    implements(IWorkspaceTabsUtility)

    workspaces = {}
    domain_type = {}

    def set_content(self, role, tab, domain_class, status):
        """ Sets the workspace info
        """
        if role not in self.workspaces:
            self.workspaces[role] = {}
        if tab not in self.workspaces[role]:
            self.workspaces[role][tab] = {}
        if domain_class not in self.workspaces[role][tab]:
            self.workspaces[role][tab][domain_class] = []
        self.workspaces[role][tab][domain_class].append(status)

    def register_item_type(self, domain_class, item_type):
        """ Stores domain_class -> item_type and vice versa in a dictionary eg.
        domain.Bill -> bill. Used by the Workspace Container to set the
        contained object names and to retrieve the contained objects given
        a name.
        """
        if item_type in self.domain_type.keys():
            raise ValueError("Multiple workspace declarations"
                             "with same name - %s") % (item_type)
        if domain_class in self.domain_type.keys():
            raise ValueError("Multiple workspace domain classes"
                             "with same name - %s") % (domain_class)
        self.domain_type[item_type] = domain_class
        self.domain_type[domain_class] = item_type

    def get_role_domains(self, role, tab):
        """Returns a list of domain classes that a role will see for a
        certain tab
        """
        if role in self.workspaces.keys():
            if tab in self.workspaces[role].keys():
                return list(self.workspaces[role][tab].keys())
        return None

    def get_domain(self, key):
        """Passed a type string returns the domain class"""
        if key in self.domain_type:
            return self.domain_type[key]
        return None

    def get_type(self, key):
        """Passed a domain class returns a string"""
        if key in self.domain_type:
            return self.domain_type[key]
        return None

    def get_tab(self, role, domain_class, status):
        """Returns the tab an object should be in, given its domain class,
        status and role
        """
        if role in self.workspaces:
            for tab in self.workspaces[role]:
                if (domain_class in self.workspaces[role][tab] and
                    status in self.workspaces[role][tab][domain_class]
                    ):
                        return tab
        return None

    def get_status(self, role, domain_class, tab):
        """Returns all applicable statuses given the role,
        domain_class and tab
        """
        if role in self.workspaces:
            if tab in self.workspaces[role]:
                if domain_class in self.workspaces[role][tab]:
                    return self.workspaces[role][tab][domain_class]


def load_workspace(file_name, domain_class):
    """Loads the workspace configuration for each documemnt"""
    workspace_tabs = getUtility(IWorkspaceTabsUtility)
    path = capi.get_path_for("workspace")
    file_path = os.path.join(path, file_name)
    item_type = file_name.split(".")[0]
    workspace_tabs.register_item_type(domain_class, item_type)
    workspace = etree.fromstring(open(file_path).read())
    for state in workspace.iterchildren("state"):
        for tab in state.iterchildren():
            if tab.get("id") in TABS:
                if tab.get("roles"):
                    roles = tab.get("roles").split()
                    for role in roles:
                        workspace_tabs.set_content(
                            role, tab.get("id"), domain_class, state.get("id")
                            )
            else:
                raise ValueError("Invalid tab - %s", tab.get("id"))


def load_workspaces(application, event):
    load_workspace("bill.xml", domain.Bill)
    load_workspace("tableddocument.xml", domain.TabledDocument)
    load_workspace("agendaitem.xml", domain.AgendaItem)
    load_workspace("motion.xml", domain.Motion)
    load_workspace("question.xml", domain.Question)
