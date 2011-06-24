log = __import__("logging").getLogger("bungeni.core.workspace")
import os
from lxml import etree

from zope.interface import implements
from zope.app.publication.traversers import SimpleComponentTraverser
from zope.security.proxy import removeSecurityProxy
from zope.component import getUtility
from zope.app.publisher.browser import getDefaultViewName
from zope.publisher.interfaces import NotFound
from zope.component import queryMultiAdapter
from bungeni.utils.capi import capi
from bungeni.models.workspace import stringKey
from bungeni.core.workflow import interfaces
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
           then checks if the name refers to an item in this container, 
           else raises a NotFound
        """
        workspace = removeSecurityProxy(self.context)
        view = queryMultiAdapter((workspace, request), name=name)
        if view:
            return view
        ob = workspace.get(name)    
        if ob:
            return ob 
        raise NotFound(workspace, name)   
                     
class WorkspaceTabsUtility():
    """This is utility stores the workflow configuration
    """
    implements(interfaces.IWorkspaceTabsUtility)
    
    workspaces = {}
    domain_type = {}
    
    def getDomainAndStatuses(self, role, tab):
        """Returns a dictionary with the domain classes as keys. the value for 
        each key is a dictionary of applicable statuses"""
        if role in self.workspaces.keys():
            if tab in self.workspaces[role].keys():
                return self.workspaces[role][tab]
        return None    
                
    def setContent(self, role, tab, domain_class, status):
        """ Sets the 
        """
        if role not in self.workspaces:
            self.workspaces[role] = {}
        if tab not in self.workspaces[role]:
            self.workspaces[role][tab] = {}
        if domain_class not in self.workspaces[role][tab]:
            self.workspaces[role][tab][domain_class] = []
        self.workspaces[role][tab][domain_class].append(status)

    def registerItemType(self, domain_class, item_type):
        """ Stores domain_class -> item_type and vice versa in a dictionary eg.
            domain.Bill -> bill. Used by the Workspace Container to set the 
            contained object names and to retrieve the contained objects given 
            a name.
        """
        if item_type in self.domain_type.keys():
            raise ValueError("Multiple workspace declarations with same name - %s", item_type)
        if domain_class in self.domain_type.keys():
            raise ValueError("Multiple workspace domain classes with same name - %s", item_type)
        self.domain_type[item_type] = domain_class
        self.domain_type[domain_class] = item_type 
    
    def getDomainOrType(self, key):
        """Passed either a domain_class or an item type, returns an item_type
        or domain_class respectively"""
        return self.domain_type[key]
        
def load_workspace(file_name, domain_class):
    """Loads the workspace configuration for each documemnt"""
    workspace_tabs = getUtility(interfaces.IWorkspaceTabsUtility)
    path = capi.get_path_for("workspace")
    file_path = os.path.join(path, file_name)
    item_type = file_name.split(".")[0]
    workspace_tabs.registerItemType(domain_class, item_type)
    workspace = etree.fromstring(open(file_path).read())
    for state in workspace.iterchildren("state"):
        for tab in state.iterchildren():
            if tab.get("id") in TABS:
                if tab.get("roles"):
                    roles = tab.get("roles").split()
                    for role in roles:
                        workspace_tabs.setContent(role, tab.get("id"), domain_class, state.get("id"))
            else:
                raise ValueError("Invalid tab - %s", tab.get("id"))
                            
def load_workspaces(application, event):
    load_workspace("bill.xml", domain.Bill)
    load_workspace("tableddocument.xml", domain.TabledDocument)
    load_workspace("agendaitem.xml", domain.AgendaItem)
    load_workspace("motion.xml", domain.Motion)
    load_workspace("question.xml", domain.Question)    
