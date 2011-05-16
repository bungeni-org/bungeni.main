
from zope.traversing.browser import absoluteURL
from zope.traversing.browser.absoluteurl import AbsoluteURL
from bungeni.alchemist.container import stringKey
from zope.app.component.hooks import getSite
import bungeni.ui.utils as ui_utils
from zope.security.proxy import removeSecurityProxy
from zope.interface import providedBy
from bungeni.alchemist import Session
from bungeni.models.domain import ParliamentaryItem

class CustomAbsoluteURL(AbsoluteURL):
    section = ""
    subsection = ""
    
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return '%s/%s/%s/%s' % (base_url, self.section, self.subsection,\
               stringKey(self.context))

    __call__ = __str__
    

""" Workspace section
"""

class WorkspaceAbsoluteURLView(AbsoluteURL):
    
    subsection = ''
    
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)
        return '%s/business/%ss/%s/' % (base_url, self.context.type,\
                                                   stringKey(self.context))
    
    __call__ = __str__


""" Business section
"""
class BusinessAbsoluteURLView(CustomAbsoluteURL):
    """ Custom absolute url for business section
    """
    section = "business"

class AttachedFileBusinessAbsoluteURLView(BusinessAbsoluteURLView):
    
    def __str__(self):
        item_id = self.context.item_id
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)
        session = Session()
        item = session.query(ParliamentaryItem).filter(ParliamentaryItem.parliamentary_item_id==item_id).first()
        return '%s/business/%ss/obj-%s/files/%s/' % (base_url, item.type,\
                                                   item_id, stringKey(self.context))
    
    __call__ = __str__

    
class CommitteeBusinessAbsoluteURLView(BusinessAbsoluteURLView):
    """ Custom absolute url for committees in business section
    """
    subsection = "committees"
    

class BillBusinessAbsoluteURLView(BusinessAbsoluteURLView):
    """ Custom absolute url for bills in business section
    """
    subsection = "bills"


class QuestionBusinessAbsoluteURLView(BusinessAbsoluteURLView):
    """ Custom absolute url for questions in business section
    """
    subsection = "questions"


class MotionBusinessAbsoluteURLView(BusinessAbsoluteURLView):
    """ Custom absolute url for motions in business section
    """
    subsection = "motions"
   
    
class TabledDocumentBusinessAbsoluteURLView(BusinessAbsoluteURLView):
    """ Custom absolute url for tabled documents in business section
    """
    subsection = "tableddocuments"
    
    
class AgendaItemBusinessAbsoluteURLView(BusinessAbsoluteURLView):
    """ Custom absolute url for agenda items in business section
    """
    subsection = "agendaitems"

    
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



""" Archives section
"""
class ArchiveAbsoluteURLView(CustomAbsoluteURL):
    """ Custom absolute url for archive section
    """
    section = "archive/browse"
    subsection = ""


class ParliamentsArchiveAbsoluteURLView(ArchiveAbsoluteURLView):
    """ Custom absolute url for parliaments in archive section
    """
    subsection = "parliaments"


class PoliticalGroupsArchiveAbsoluteURLView(ArchiveAbsoluteURLView):
    """ Custom absolute url for political groups in archive section
    """
    subsection = "politicalgroups"
    
    
class ConstituenciesArchiveAbsoluteURLView(ArchiveAbsoluteURLView):
    """ Custom absolute url for constituencies in archive section
    """
    subsection = "constituencies"
    
    
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
        return '%s/archive/browse/parliaments/obj-%s/%s/%s' % \
               (base_url, self.context.parliament_id, self.subsection, stringKey(self.context))

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
        return '%s/archive/browse/parliaments/obj-%s/%s/%s' % \
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

    
class MemberOfParliamentArchiveAbsoluteURLView(AbsoluteURL):
    """ Custom absolute url for parliament members in archive section
    """
    subsection = "parliamentmembers"
    
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return '%s/archive/browse/parliaments/obj-%s/%s/%s' % \
               (base_url, self.context.group_id, self.subsection, stringKey(self.context))

    __call__ = __str__


class OfficeArchiveAbsoluteURLView(AbsoluteURL):
    """ Custom absolute url for offices in archive section
    """
    subsection = "offices"
    
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return '%s/archive/browse/parliaments/obj-%s/%s/%s' % \
               (base_url, self.context.parent_group_id, self.subsection, stringKey(self.context))

    __call__ = __str__


class AgendaItemArchiveAbsoluteURLView(ArchiveSectionParliamentItem):
    """ Custom absolute url for agenda items in archive section
    """
    subsection = "agendaitems"

    
    
""" Admin section
"""
class ParliamentAdminAbsoluteURLView(AbsoluteURL):
    """ Custom absolute url for parliaments in admin section
    """   
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return '%s/admin/content/parliaments/%s' % (base_url, stringKey(self.context))

    __call__ = __str__
    

class AdminSectionParliamentItem(AbsoluteURL):
    """ Custom absolute url for parliament items in admin section
    """
    subsection = ""
    
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return '%s/admin/content/parliaments/obj-%s/%s/%s' % \
               (base_url, self.context.parliament_id, self.subsection, stringKey(self.context))

    __call__ = __str__


class QuestionAdminAbsoluteURLView(AdminSectionParliamentItem):
    """ Custom absolute url for questions in admin section
    """
    subsection = "questions"
    
    
class ReportAdminAbsoluteURLView(AbsoluteURL):
    """ Custom absolute url for reports in admin section
    """
    subsection = "preports"
    
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return '%s/admin/content/parliaments/obj-%s/%s/%s' % \
               (base_url, self.context.group_id, self.subsection, stringKey(self.context))

    __call__ = __str__


class TabledDocumentAdminAbsoluteURLView(AdminSectionParliamentItem):
    """ Custom absolute url for tabled documents in admin section
    """
    subsection = "tableddocuments"
    

class MotionAdminAbsoluteURLView(AdminSectionParliamentItem):
    """ Custom absolute url for motions in admin section
    """
    subsection = "motions"
    

class BillAdminAbsoluteURLView(AdminSectionParliamentItem):
    """ Custom absolute url for bills in admin section
    """
    subsection = "bills"
    
    
class CommitteeAdminAbsoluteURLView(AbsoluteURL):
    """ Custom absolute url for committees in admin section
    """
    subsection = "committees"
    
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return '%s/admin/content/parliaments/obj-%s/%s/%s' % \
               (base_url, self.context.parent_group_id, self.subsection, stringKey(self.context))

    __call__ = __str__
    
    
class MemberOfParliamentAdminAbsoluteURLView(AbsoluteURL):
    """ Custom absolute url for parliament members in admin section
    """
    subsection = "parliamentmembers"
    
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return '%s/admin/content/parliaments/obj-%s/%s/%s' % \
               (base_url, self.context.group_id, self.subsection, stringKey(self.context))

    __call__ = __str__


class OfficeAdminAbsoluteURLView(AbsoluteURL):
    """ Custom absolute url for offices in admin section
    """
    
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return '%s/admin/content/offices/%s' % \
               (base_url, stringKey(self.context))

    __call__ = __str__


class AgendaItemAdminAbsoluteURLView(AdminSectionParliamentItem):
    """ Custom absolute url for agenda items in admin section
    """
    subsection = "agendaitems"
    

class UserAdminAbsoluteURLView(AbsoluteURL):
    """ Custom absolute url for users in admin section
    """
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return '%s/admin/content/users/%s' % (base_url, stringKey(self.context))

    __call__ = __str__
    

class PoliticalPartyAbsoluteURLView(AbsoluteURL):
    """ Custom absolute url for users in admin section
    """
    def __str__(self):
        base_url = ui_utils.url.absoluteURL(getSite(), self.request)        
        return '%s/admin/content/parties/%s' % (base_url, stringKey(self.context))

    __call__ = __str__
