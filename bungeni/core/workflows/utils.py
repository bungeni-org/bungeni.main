log = __import__("logging").getLogger("bungeni.core.workflow.utils")

import sys
import datetime

from zope.security.proxy import removeSecurityProxy
from zope.securitypolicy.interfaces import IPrincipalRoleMap

from ore.workflow.interfaces import IWorkflowInfo
from ore.workflow.interfaces import NoTransitionAvailableError

import bungeni.models.interfaces as interfaces
#import bungeni.models.domain as domain
from bungeni.models.utils import get_principal_id
from bungeni.core.app import BungeniApp
import bungeni.core.interfaces
import bungeni.core.globalsettings as prefs
from bungeni.ui.utils import debug

import dbutils

class conditions(object):
    """Commonly used transition conditions.
    """
    
    # the condition for the transition from "" (None) to either "draft" or to 
    # "working_draft" seems to need the explicit condition (and negation of 
    # condition) on each of the two transition options 
    @staticmethod
    def user_is_not_context_owner(info, context):
        return not conditions.user_is_context_owner(info, context)
    @staticmethod
    def user_is_context_owner(info, context):
        def user_is_context_owner(context):
            """Test if current user is the context owner e.g. to check if someone 
            manipulating the context object is other than the owner of the object.
            """
            user_id = get_principal_id()
            owner_id = getOwnerId(context)
            return user_id==owner_id
        return user_is_context_owner(context)
    
    @staticmethod
    def is_scheduled(info, context):
        return dbutils.isItemScheduled(context.parliamentary_item_id)

#

''' !+UNUSED(mr, mar-2011)
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
'''

# common
def getOwnerId(context):
    if context:
        owner_id = getattr(context, "owner_id", None)
        return dbutils.get_user_login(owner_id)

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

# !+WorkflowInfo(mr, mar-2011) drop passing this (unused) param everywhere here?

def createVersion(info, context):
    """Create a new version of an object and return it."""
    instance = removeSecurityProxy(context)
    # capi.template_message_version_transition
    message_template = "New version on workflow transition from: %(status)s"
    message = message_template % instance.__dict__
    versions = bungeni.core.interfaces.IVersioned(instance)
    versions.create(message)

def setRegistryNumber(info, context):
    """A parliamentary_item's registry_number should be set on the item being 
    submitted to parliament.
    """
    instance = removeSecurityProxy(context)
    if instance.registry_number == None:
        dbutils.setRegistryNumber(instance)

# question
def setQuestionDefaults(info, context):
    """get the default values for a question. current parliament, ... 
    
    !+setQuestionDefaults(mr, mar-2011) creating a question via UI does not 
    seem to need this, but... a unit test fails without it!
    """ 
    instance = removeSecurityProxy(context)
    dbutils.setQuestionParliamentId(instance)

def setMinistrySubmissionDate(info, context):
    instance = removeSecurityProxy(context)
    if instance.ministry_submit_date == None:
        instance.ministry_submit_date = datetime.date.today()

# !+QuestionScheduleHistory(mr, mar-2011) rename appropriately e.g. "unschedule"
# !+QuestionScheduleHistory(mr, mar-2011) only pertinent if question is 
# transiting from a shceduled state... is this needed anyway?
def setQuestionScheduleHistory(info, context):
    question_id = context.question_id
    dbutils.removeQuestionFromItemSchedule(question_id)

''' !+UNUSUED (and incorrect) :
def getQuestionSchedule(info, context):
    question_id = context.question_id
    return dbutils.isItemScheduled(question_id)

def getMotionSchedule(info, context):
    motion_id = context.motion_id
    return dbutils.isItemScheduled(motion_id)

def getQuestionSubmissionAllowed(info, context):
    return prefs.getQuestionSubmissionAllowed()
'''

# bill
def setBillPublicationDate( info, context ):
    instance = removeSecurityProxy(context)
    if instance.publication_date == None:
        instance.publication_date = datetime.date.today()

# motion, bill, agendaitem, tableddocument
# !+ParliamentID(mr, mar-2011) this is used in "create" transitions... 
# why is this needed here (as part fo transition logic... should be part of 
# the object creation logic, and then why is it not used for all types 
# e.g. not used for question?
def setParliamentId(info, context):
    instance = removeSecurityProxy(context)
    if not instance.parliament_id:
        parliamentId = prefs.getCurrentParliamentId()
        instance.parliament_id = parliamentId

# tableddocument
def setTabledDocumentHistory(info, context):
    pass

# groups
def _set_group_local_role(context, unset=False):
    def get_group_local_role(group):
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
            return group.office_role
        else:
            return "bungeni.GroupMember"
    def get_group_context(context):
        if interfaces.IOffice.providedBy(context):
            return BungeniApp() #get_parliament(context)
        else:
            return removeSecurityProxy(context)
    role = get_group_local_role(context)
    group = removeSecurityProxy(context)
    ctx = get_group_context(context)
    prm = IPrincipalRoleMap(ctx)
    if not unset:
        prm.assignRoleToPrincipal(role, group.group_principal_id)
    else:
        prm.unsetRoleForPrincipal(role, group.group_principal_id)
        
def set_group_local_role(context):
    _set_group_local_role(context, unset=False)
            
def unset_group_local_role(context):
    _set_group_local_role(context, unset=True)

def dissolveChildGroups(groups, context):
    for group in groups:
        IWorkflowInfo(group).fireTransition("active-dissolved", 
            check_security=False)
        
# groupsitting
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


