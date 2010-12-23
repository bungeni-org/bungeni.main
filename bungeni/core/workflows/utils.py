log = __import__("logging").getLogger("bungeni.core.workflow.utils")

import sys
import datetime

from zope import component
from zope import interface
from zope.security.proxy import removeSecurityProxy
from zope.securitypolicy.interfaces import IPrincipalRoleMap
from zope.security.management import getInteraction
from zope.publisher.interfaces import IRequest

from bungeni.alchemist import Session
from ore.workflow.interfaces import IWorkflowInfo, InvalidTransitionError
from ore.workflow.interfaces import NoTransitionAvailableError
import ore.workflow.workflow

import bungeni.models.interfaces as interfaces
import bungeni.models.domain as domain
from bungeni.models.utils import get_principal_id
from bungeni.core.app import BungeniApp
import bungeni.core.interfaces
import bungeni.core.globalsettings as prefs
from bungeni.ui.utils import common, debug
from bungeni.ui.interfaces import IFormEditLayer

import dbutils

class conditions(object):
    """Commonly used transition conditions.
    """
    
    # the condition for the transition from "" (None) to either "draft" or to 
    # "working_draft" seems to need the explicit condition (and negation of 
    # condition) on each of the two transition options 
    @staticmethod
    def user_is_not_context_owner(info, context):
        return not user_is_context_owner(context)
    @staticmethod
    def user_is_context_owner(info, context):
        return user_is_context_owner(context)


def get_parliament(context):
    """go up until we find a parliament """
    parent = context.__parent__
    while parent:
        if  interfaces.IParliament.providedBy(parent):
            return parent
        else:
            try:
                parent = parent.__parent__
            except:
                parent = None
    if not parent:
        parliament_id = context.parliament_id
        session = Session()
        parliament = session.query(domain.Parliament).get(parliament_id)
        return parliament
        

def _get_group_local_role(group):
    if interfaces.IParliament.providedBy(group):
        return "bungeni.MP"
    elif interfaces.IMinistry.providedBy(group):
        return "bungeni.Minister"
    elif interfaces.ICommittee.providedBy(group): 
        return "bungeni.CommitteeMember"
    elif interfaces.IPoliticalGroup.providedBy(group):
        return "bungeni.PartyMember"
    elif interfaces.IGovernment.providedBy(group):
        return "bungeni.Government"
    elif interfaces.IOffice.providedBy(group):
        if group.office_type == "S":
            return "bungeni.Speaker"
        elif group.office_type == "C":
            return "bungeni.Clerk"
        elif group.office_type == "T":
            return "bungeni.Translator"
        else: 
            raise NotImplementedError 
    else:
        return "bungeni.GroupMember"
        
def _get_group_context(context):
    if interfaces.IOffice.providedBy(context):
        return BungeniApp() #get_parliament(context)
    else:
        return removeSecurityProxy(context)

def set_group_local_role(context):
    role = _get_group_local_role(context)
    group = removeSecurityProxy(context)
    ctx = _get_group_context(context) 
    IPrincipalRoleMap(ctx).assignRoleToPrincipal(
            role, group.group_principal_id)
            
def unset_group_local_role(context):
    role = _get_group_local_role(context)
    group = removeSecurityProxy(context)
    ctx = _get_group_context(context)
    IPrincipalRoleMap(ctx).unsetRoleForPrincipal(
            role, group.group_principal_id)

def getOwnerId(context):
    if context:
        owner_id = getattr(context, 'owner_id', None)
        return dbutils.get_user_login(owner_id)

def user_is_context_owner(context):
    """Test if current user is the context owner e.g. to check if someone 
    manipulating the context object is other than the owner of the object.
    """
    user_id = get_principal_id()
    owner_id = getOwnerId(context)
    return user_id==owner_id
    
def setBungeniOwner(context):
    user_id = get_principal_id()
    if not user_id: 
        user_id = "-"
    owner_id = getOwnerId(context)
    log.debug("setBungeniOwner [%s] user_id:%s owner_id:%s" % (
                                                context, user_id, owner_id))
    if user_id:
        IPrincipalRoleMap(context).assignRoleToPrincipal(u'bungeni.Owner', user_id)
    if owner_id and (owner_id!=user_id):
        IPrincipalRoleMap(context).assignRoleToPrincipal(u'bungeni.Owner', owner_id)


def createVersion(info, context, 
    message="New version created upon workflow transition."
):
    """Create a new version of an object and return it."""
    instance = removeSecurityProxy(context)
    versions =  bungeni.core.interfaces.IVersioned(instance)
    versions.create(message)

def setQuestionDefaults(info, context):
    """get the default values for a question.
    current parliament, ... """ 
    instance = removeSecurityProxy(context)
    dbutils.setQuestionParliamentId(instance)
    dbutils.setQuestionMinistryId(instance)

def setRegistryNumber(info, context):
    """A parliamentary_item's registry_number should be set on the item being 
    submitted to parliament.
    """
    instance = removeSecurityProxy(context)
    if instance.registry_number == None:
        dbutils.setRegistryNumber(instance)

def setMinistrySubmissionDate(info, context):
    instance = removeSecurityProxy(context)
    if instance.ministry_submit_date == None:
        instance.ministry_submit_date = datetime.date.today()

def setQuestionScheduleHistory(info, context):
    question_id = context.question_id
    dbutils.removeQuestionFromItemSchedule(question_id)
  

def getQuestionMinistry(info, context):
    ministry_id = context.ministry_id
    return ministry_id != None

''' UNUSUED (and incorrect) :
def getQuestionSchedule(info, context):
    question_id = context.question_id
    return dbutils.isItemScheduled(question_id)

def getMotionSchedule(info, context):
    motion_id = context.motion_id
    return dbutils.isItemScheduled(motion_id)
'''

def getQuestionSubmissionAllowed(info, context):
    return prefs.getQuestionSubmissionAllowed()

def setBillPublicationDate( info, context ):
    instance = removeSecurityProxy(context)
    if instance.publication_date == None:
        instance.publication_date = datetime.date.today()

def setAgendaItemHistory(info, context):
    pass
    
def setTabledDocumentHistory(info, context):
    pass


def setParliamentId(info, context):
    instance = removeSecurityProxy(context)
    if not instance.parliament_id:
        parliamentId = prefs.getCurrentParliamentId()
        instance.parliament_id = parliamentId
    
def response_allow_submit(info, context):
    instance = removeSecurityProxy(context)
    # The "submit_response" workflow transition should NOT be displayed when 
    # the UI is displaying the question in "edit" mode (as this transition
    # will cause deny of bungeni.Question.Edit to the Minister).
    request = common.get_request()
    if IFormEditLayer.providedBy(request):
        return False
    if instance.response_text is None:
        return False
    else:
        return True
            
def dissolveChildGroups(groups, context):
    for group in groups:
        IWorkflowInfo(group).fireTransition('dissolve', check_security=False)
        
          
def schedule_sitting_items(info, context):
    
    # !+fireTransitionToward(mr, dec-2010) sequence of fireTransitionToward 
    # calls was introduced in r5818, 28-jan-2010 -- here the code is reworked
    # to be somewhat more sane, and added logging of both SUCCESS and of 
    # FAILURE of each call to fireTransitionToward().
    #
    # The check/logging should be removed once it is understood whether
    # NoTransitionAvailableError is *always* raised (i.e. fireTransitionToward is
    # broken) or it is indeed raised correctly when it should be.
    
    def fireTransitionScheduled(item, check_security=False):
        try:
            IWorkflowInfo(item).fireTransitionToward("scheduled", 
                    check_security=False)
            raise RuntimeWarning(
                """It has WORKED !!! fireTransitionToward("scheduled")""")
        except (NoTransitionAvailableError, RuntimeWarning):
            debug.log_exc_info(sys.exc_info(), log.error)
    
    for schedule in removeSecurityProxy(context).item_schedule:
        item = schedule.item
        if interfaces.IQuestion.providedBy(item):
            fireTransitionScheduled(item)
        elif interfaces.IMotion.providedBy(item):
            fireTransitionScheduled(item)
        elif interfaces.IAgendaItem.providedBy(item):
            fireTransitionScheduled(item)
        elif interfaces.ITabledDocument.providedBy(item):
            fireTransitionScheduled(item)


