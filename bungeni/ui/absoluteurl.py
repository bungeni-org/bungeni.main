# !+ CLEAN UP THIS FILE, MINIMALLY AT LEAST THE SRC CODE FORMATTING !

from zope.traversing.browser.absoluteurl import AbsoluteURL
from zope.app.component.hooks import getSite
from zope.security.proxy import removeSecurityProxy
from zope.component import getUtility
import bungeni.ui.utils as ui_utils
from bungeni.alchemist.container import stringKey
from bungeni.models.roles import ROLES_DIRECTLY_DEFINED_ON_OBJECTS
from bungeni.core import workspace
from bungeni.ui.utils.common import get_workspace_roles
from bungeni.core.interfaces import IWorkspaceTabsUtility
from bungeni.utils import naming


''' !+UNUSED
class CustomAbsoluteURL(AbsoluteURL):
    section = ""
    subsection = ""
    
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return '%s/%s/%s/%s' % (base_url, self.section, self.subsection,\
               stringKey(self.context))
    
    __call__ = __str__
'''


class WorkspaceAbsoluteURLView(AbsoluteURL):
    """Workspace section.
    """
    subsection = ""
    
    def __str__(self):
        tabs_utility = getUtility(IWorkspaceTabsUtility)
        domain_class = self.context.__class__
        status = self.context.status
        roles = get_workspace_roles() + ROLES_DIRECTLY_DEFINED_ON_OBJECTS
        tab = None
        for role in roles:
            tab = tabs_utility.get_tab(role, domain_class, status)
            if tab:
                base_url = ui_utils.url.absoluteURL(getSite(), self.request)
                key = workspace.WorkspaceBaseContainer.string_key(self.context)
                return '%s/workspace/my-documents/%s/%s' % (base_url, tab, key)
        else:
            return None
            
    __call__ = __str__


    
''' !+MEMBERS

""" Members section
"""
class MembersAbsoluteURLView(CustomAbsoluteURL):
    """ Custom absolute url for members of parliament in members section
    """
    section = "members"
    subsection = "current"
    
class PoliticalGroupMembersAbsoluteURLView(CustomAbsoluteURL):
    """ Custom absolute url for political group in members section
    """    
    section = "members"
    subsection = "political-groups"
'''



''' !+ARCHIVE

""" Archives section
"""
class ArchiveAbsoluteURLView(CustomAbsoluteURL):
    """ Custom absolute url for archive section
    """
    section = "archive/browse"
    subsection = ""


class ParliamentsArchiveAbsoluteURLView(ArchiveAbsoluteURLView):
    """ Custom absolute url for chambers in archive section
    """
    subsection = "chambers"


class PoliticalGroupsArchiveAbsoluteURLView(ArchiveAbsoluteURLView):
    """ Custom absolute url for political groups in archive section
    """
    subsection = "politicalgroups"


class CommitteesArchiveAbsoluteURLView(ArchiveAbsoluteURLView):
    """ Custom absolute url for committees in archive section
    """
    subsection = "committees"
    
    
class ArchiveSectionParliamentItem(AbsoluteURL):
    """ Custom absolute url for parliament items in archive section
    """
    subsection = ""
    
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return '%s/archive/browse/chambers/obj-%s/%s/%s' % \
               (base_url, self.context.chamber_id, self.subsection, stringKey(self.context))

    __call__ = __str__


class QuestionArchiveAbsoluteURLView(ArchiveSectionParliamentItem):
    """ Custom absolute url for questions in archive section
    """
    subsection = "questions"
    
    
class ReportArchiveAbsoluteURLView(AbsoluteURL):
    """ Custom absolute url for reports in archive section
    """
    subsection = "preports"
    
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return '%s/archive/browse/chambers/obj-%s/%s/%s' % \
               (base_url, self.context.group_id, self.subsection, stringKey(self.context))

    __call__ = __str__


class TabledDocumentArchiveAbsoluteURLView(ArchiveSectionParliamentItem):
    """ Custom absolute url for tabled documents in archive section
    """
    subsection = "tableddocuments"
    

class MotionArchiveAbsoluteURLView(ArchiveSectionParliamentItem):
    """ Custom absolute url for motions in archive section
    """
    subsection = "motions"
    

class BillArchiveAbsoluteURLView():
    """ Custom absolute url for bills in archive section
    """
    subsection = "bills"

    
class MemberArchiveAbsoluteURLView(AbsoluteURL):
    """ Custom absolute url for parliament members in archive section
    """
    subsection = "members"
    
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return '%s/archive/browse/chambers/obj-%s/%s/%s' % \
               (base_url, self.context.group_id, self.subsection, stringKey(self.context))

    __call__ = __str__


class OfficeArchiveAbsoluteURLView(AbsoluteURL):
    """ Custom absolute url for offices in archive section
    """
    subsection = "offices"
    
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return '%s/archive/browse/chambers/obj-%s/%s/%s' % \
               (base_url, self.context.parent_group_id, self.subsection, stringKey(self.context))

    __call__ = __str__


class AgendaItemArchiveAbsoluteURLView(ArchiveSectionParliamentItem):
    """ Custom absolute url for agenda items in archive section
    """
    subsection = "agendaitems"
'''



# Admin section

class DocAdminSectionURLView(AbsoluteURL):
    """Custom absolute url for doc in admin section
    """
    def __str__(self):
        doc = removeSecurityProxy(self.context)
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return "%s/admin/content/chambers/obj-%s/%s/%s" % (
                    base_url, 
                    doc.chamber_id, 
                    naming.plural(naming.polymorphic_identity(type(doc))), 
                    stringKey(doc))
    __call__ = __str__

class GroupAdminAbsoluteURLView(AbsoluteURL):
    """Custom absolute url for groups in admin section
    """
    def _group_url_path(self, group):
        url_comps = []
        group = removeSecurityProxy(group)
        while group:
            url_comps.insert(0, "%s/%s" % (
                    naming.plural(naming.polymorphic_identity(type(group))),
                    stringKey(group)))
            group = removeSecurityProxy(group.parent_group)
        return "/".join(url_comps)
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return "%s/admin/content/%s" % (base_url, self._group_url_path(self.context))
    __call__ = __str__

class GroupMemberAdminAbsoluteURLView(GroupAdminAbsoluteURLView):
    """Custom absolute url for group members in admin section
    """
    def __str__(self):
        member = removeSecurityProxy(self.context)
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return "%s/%s/%s/%s" % (
            base_url,
            super(GroupMemberAdminAbsoluteURLView, self)._group_url_path(member.group),
            naming.plural(naming.polymorphic_identity(type(member))),
            stringKey(member))
    __call__ = __str__

class UserAdminAbsoluteURLView(AbsoluteURL):
    """Custom absolute url for users in admin section.
    """
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return "%s/admin/content/users/%s" % (base_url, stringKey(self.context))
    __call__ = __str__


