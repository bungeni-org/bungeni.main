log = __import__("logging").getLogger("bungeni.core.workspace")
from zope.interface import implements
from bungeni.core.workflow import interfaces
TABS = ["draft", "inbox", "sent", "archive"]

class WorkspaceTabsUtility():
    implements(interfaces.IWorkspaceTabsUtility)
    
    workspaces = {}
    
    def getDomainAndStatuses(self, role, tab):
        """Returns a dictionary with the interfaces as keys. the value for each 
        key is a dictionary of applicable statuses"""
        try:
            return self.workspaces[role][tab]
        except KeyError:
            log.exception("No such role or tab")
            
    def setClassInterface(self, workflow_name, class_interface):
        for role in self.workspaces.keys():
            for tab in self.workspaces[role].keys():
                if workflow_name in self.workspaces[role][tab].keys():
                    statuses = self.workspaces[role][tab][workflow_name]
                    del self.workspaces[role][tab][workflow_name]
                    self.workspaces[role][tab][class_interface] = statuses
                    
                
    def setContent(self, role, tab, workflow_name, status):
        if role not in self.workspaces:
            self.workspaces[role] = {}
        assert tab in TABS, "Incorrect tab - %s" % tab
        if tab not in self.workspaces[role]:
            self.workspaces[role][tab] = {}
        if workflow_name not in self.workspaces[role][tab]:
            self.workspaces[role][tab][workflow_name] = []
        self.workspaces[role][tab][workflow_name].append(status)
