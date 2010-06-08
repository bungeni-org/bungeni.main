# encoding: utf-8

log = __import__("logging").getLogger("bungeni.core")

from zope import component
from bungeni.core.workflows.notification import Notification
from bungeni.core.workflows import interfaces
from bungeni.core import globalsettings as prefs
from bungeni.core.workflows import dbutils
from bungeni.core.i18n import _
from bungeni.models import domain
from ore.alchemist import Session

from bungeni.models.utils import get_principal_id
import bungeni.core.workflows.utils as utils
import zope.securitypolicy.interfaces

class conditions(object):
    @staticmethod
    def is_scheduled(info, context):
        return dbutils.isItemScheduled(context.question_id)

    @staticmethod
    def is_ministry_set(info, context):
        return context.ministry_id is not None
        
    @staticmethod
    def is_written_response(info, context):
        return (context.ministry_id is not None) and (
            context.response_type == u"W")

    @staticmethod
    def is_oral_response(info, context):
        return context.response_type == u"O"

    @staticmethod
    def user_is_not_context_owner(info, context):
        return utils.user_is_not_context_owner(context)

class actions(object):
    @staticmethod
    def denyAllWrites(question):
        """Remove all rights to change the question from all involved roles.
        """
        pass
    
    @staticmethod
    def create(info, context):
        """Create a question -> state.draft, grant all rights to owner
        deny right to add supplementary questions.
        """
        q = context # context is the newly created question
        log.debug("[QUESTION CREATE] [%s] [%s]" % (info, q))
        utils.setQuestionDefaults(info, q)
        user_id = get_principal_id()
        if user_id:
            zope.securitypolicy.interfaces.IPrincipalRoleMap(q
                            ).assignRoleToPrincipal( u'bungeni.Owner', user_id) 
        owner_id = utils.getOwnerId(q)
        log.debug("        user_id:%s owner_id:%s" % (user_id, owner_id))
        if owner_id and (owner_id!=user_id):
            zope.securitypolicy.interfaces.IPrincipalRoleMap(q
                ).assignRoleToPrincipal(u'bungeni.Owner', owner_id)
    
    '''
    @staticmethod
    def makePrivate(info, context):
        """A question that is not being asked.
        """
        pass

    @staticmethod
    def reDraft(info, context):
        """
        """
        pass
    '''
    
    @staticmethod
    def submit_to_clerk(info, context):
        """A question submitted to the clerks office, the owner cannot edit it 
        anymore the clerk has no edit rights until it is recieved.
        """
        utils.setSubmissionDate(info, context)
    
    @staticmethod
    def received_by_clerk(info, context):
        """The question is recieved by the clerks office, 
        the clerk can edit the question.
        """
        utils.createVersion(info, context)
    
    @staticmethod
    def withdraw(info, context):
        """A question can be withdrawn by the owner, it is visible to ...
        and cannot be edited by anyone.
        """
        utils.setQuestionScheduleHistory(info, context)
    
    @staticmethod
    def elapse(info, context):
        """A question that could not be answered or debated, 
        it is visible to ... and cannot be edited.
        """
        pass
    
    @staticmethod
    def defer(info, context):
        """A question that cannot be debated it is available for scheduling
        but cannot be edited.
        """
        pass
    
    @staticmethod
    def send_to_ministry(info, context):
        """A question sent to a ministry for a written answer, 
        it cannot be edited, the ministry can add a written response.
        """
        utils.setMinistrySubmissionDate(info, context)
    
    @staticmethod
    def respondWriting(info, context):
        """A written response from a ministry.
        """
        pass
    
    @staticmethod
    def require_edit_by_mp(info, context):
        """A question is unclear and requires edits/amendments by the MP
        Only the MP is able to edit it, the clerks office looses edit rights.
        """
        utils.createVersion(info, context)
    
    @staticmethod
    def require_amendment(info, context):
        """A question is send back from the speakers office 
        the clerks office for clarification.
        """
        utils.createVersion(info, context)
    
    @staticmethod
    def reject(info, context):
        """A question that is not admissible, 
        Nobody is allowed to edit it.
        """
        pass
    
    @staticmethod
    def postpone(info, context):
        """A question that was scheduled but could not be debated,
        it is available for rescheduling.
        """
        utils.setQuestionScheduleHistory(info, context)
    
    @staticmethod
    def complete(info, context):
        """A question is marked as complete by the clerks office, 
        it is available to the speakers office for review.
        """
        utils.createVersion(info, context)
        utils.setSubmissionDate(info, context)
    
    @staticmethod
    def schedule(info, context):
        """The question gets scheduled no one can edit the question,
        a response may be added.
        """
        pass
    
    @staticmethod
    def complete_clarify(info, context):
        """A question that requires clarification/amendmends,
        is resubmitted by the clerks office to the speakers office.
        """
        utils.createVersion(info, context)
    
    @staticmethod
    def respondSitting(info, context):
        """A question was debated, the question cannot be edited, 
        the clerks office can add a response.
        """
        pass
    
    @staticmethod
    def answer(info, context):
        """The response was reviewed by the clerks office, 
        the question is visible, if the question was a written question
        supplementary question now can be asked. 
        """
        pass
    
    @staticmethod
    def mp_clarify(info, context):
        """Send from the clerks office to the mp for clarification 
        the MP can edit it the clerk cannot.
        """
        utils.createVersion(info, context)
    
    @staticmethod
    def approve(info, context):
        """The question is admissible and can be send to ministry,
        or is available for scheduling in a sitting.
        """
        utils.setApprovalDate(info, context)


class SendNotificationToMemberUponReceipt(Notification):
    component.adapts(interfaces.IQuestionReceivedEvent)

    body = _('notification_email_to_member_upon_receipt_of_question',
             default="Question received")
    
    @property
    def subject(self):
        return u'Question received: %s' % self.context.short_name
    
    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()
    
class SendNotificationToClerkUponSubmit(Notification):
    """Send notification to Clerk's office upon submit.

    We need to settings from a global registry to determine whether to
    send this notification and where to send it to.
    """
    
    component.adapts(interfaces.IQuestionSubmittedEvent)
    
    body = _('notification_email_to_clerk_upon_submit_of_question',
             default="Question submitted")
    
    @property
    def subject(self):
        return u'Question submitted: %s' % self.context.short_name
    
    @property
    def condition(self):
        return prefs.getClerksOfficeRecieveNotification()
    
    @property
    def recipient_address(self):
        return prefs.getClerksOfficeEmail()

class SendNotificationToMemberUponReject(Notification):
    """Issued when a question was rejected by the speakers office.
    Sends a notice that the Question was rejected"""
    
    component.adapts(interfaces.IQuestionRejectedEvent)
    
    body = _('notification_email_to_member_upon_rejection_of_question',
             default="Question rejected")
    
    @property
    def subject(self):
        return u'Question rejected: %s' % self.context.short_name
    
    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getSpeakersOfficeEmail()

class SendNotificationToMemberUponNeedsClarification(Notification):
    """Issued when a question needs clarification by the MP
    sends a notice that the question needs clarification"""
    
    component.adapts(interfaces.IQuestionClarifyEvent)
    
    body = _('notification_email_to_member_upon_need_clarification_of_question',
             default="Your question needs to be clarified")
    
    @property
    def subject(self):
        return u'Question needs clarification: %s' % self.context.short_name
    
    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()

class SendNotificationToMemberUponDeferred(Notification):
    """Issued when a question was deferred by Clerk's office."""

    component.adapts(interfaces.IQuestionDeferredEvent)

    body = _('notification_email_to_member_upon_defer_of_question',
             default="Question deferred")

    @property
    def subject(self):
        return u'Question deferred: %s' % self.context.short_name

    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getSpeakersOfficeEmail()

class SendNotificationToMemberUponSchedule(Notification):
    """Issued when a question was scheduled by Speakers office.
    Sends a Notice that the question is scheduled for ... """

    component.adapts(interfaces.IQuestionScheduledEvent)

    body = _('notification_email_to_member_upon_schedule_of_question',
             default="Question scheduled")

    @property
    def subject(self):
        return u'Question scheduled: %s' % self.context.short_name

    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()

class SendNotificationToMemberUponPostponed(Notification):
    """Issued when a question was postponed by the speakers office.
    sends a notice that the question could not be debated and was postponed"""

    component.adapts(interfaces.IQuestionPostponedEvent)

    body = _('notification_email_to_member_upon_postpone_of_question',
             default="Question postponed")

    @property
    def subject(self):
        return u'Question postponed: %s' % self.context.short_name

    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()

class SendNotificationToMemberUponComplete(Notification):
    """The question is marked as “complete” and is made available /
    forwarded to the Speaker's Office for reviewing and to make it
    “admissible”."""
    
    component.adapts(interfaces.IQuestionCompleteEvent)

    body = _('notification_email_to_member_upon_complete_of_question',
             default="Question completed for review at the speakers office")
    
    @property
    def subject(self):
        return u"Question forwarded to Speaker's Office: %s" % self.context.short_name

    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()

class SendNotificationToMinistryUponComplete(Notification):
    """At the same time the question is also forwarded to the
    ministry."""

    component.adapts(interfaces.IQuestionCompleteEvent)
    
    body = _('notification_email_to_ministry_upon_complete_question',
             default=u"Question assigned to ministry")

    @property
    def subject(self):
        return u'Question asked to ministry: %s' % self.context.short_name

    @property
    def condition(self):
        return self.context.ministry_id
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()

    @property
    def recipient_address(self):
        session = Session()
        ministry = session.query(domain.Ministry).get(
            self.context.ministry_id)
        return dbutils.getMinsiteryEmails(ministry)

class SendNotificationToMemberUponSentToMinistry(Notification):
    """Issued when a question was sent to a ministry for written
    response.  sends a notice that the question was sent to the
    ministry ... for a written response"""
    
    component.adapts(interfaces.IQuestionSentToMinistryEvent)

    body = _('notification_email_to_member_upon_sent_to_ministry_of_question',
             default="Question sent to ministry for a written answer")
    
    @property
    def subject(self):
        return u"Question sent to ministry: %s" % self.context.short_name

    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()

class SendNotificationToMemberUponAnswer(Notification):
    """Issued when a questions answer was reviewed by Clerk's office.
    sends a notice that the question was either debated or recieved a
    written answer by the ministry and that the answer is available
    ..."""
    
    component.adapts(interfaces.IQuestionAnsweredEvent)

    body = _('notification_email_to_member_upon_answer_of_question',
             default="Question answered")
    
    @property
    def subject(self):
        return u"Question answered: %s" % self.context.short_name

    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()

class SendNotificationToMemberUponDebate(Notification):
    """Issued when a questions answer was reviewed by Clerk's office.
    sends a notice that the question was either debated or recieved a
    written answer by the ministry and that the answer is available
    ..."""
    
    component.adapts(interfaces.IQuestionDebatedEvent)

    body = _('notification_email_to_member_upon_debate_question',
             default="Question debated")
    
    @property
    def subject(self):
        return u"Question debated: %s" % self.context.short_name

    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()
        
                
