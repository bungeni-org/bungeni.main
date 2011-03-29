# encoding: utf-8

# setup in adapters.py
wf = None
states = None

#

log = __import__("logging").getLogger("bungeni.core")

from zope import component
from bungeni.core.workflows.notification import Notification, notifier
from bungeni.core import globalsettings as prefs
from bungeni.core.workflows import dbutils
from bungeni.core.i18n import _
from bungeni.models import domain
from bungeni.alchemist import Session


@notifier("Question", "submitted")
class SendNotificationToClerkUponSubmit(Notification):
    """Send notification to Clerk's office upon submit.

    We need to settings from a global registry to determine whether to
    send this notification and where to send it to.
    """
    body = _("notification_email_to_clerk_upon_submit_of_question",
             default="Question submitted")
    
    def subject(self):
        return "Question submitted: %s" % self.context.short_name
    
    def condition(self):
        return prefs.getClerksOfficeReceiveNotification()
    
    def recipient_address(self):
        return prefs.getClerksOfficeEmail()


@notifier("Question", "received")
class SendNotificationToMemberUponReceipt(Notification):
    
    body = _("notification_email_to_member_upon_receipt_of_question",
             default="Question received")
    
    def subject(self):
        return "Question received: %s" % self.context.short_name
    
    def condition(self):
        return self.context.receive_notification
    
    def from_address(self):
        return prefs.getClerksOfficeEmail()


@notifier("Question", "inadmissible")
class SendNotificationToMemberUponReject(Notification):
    """Issued when a question was rejected by the speakers office.
    Sends a notice that the Question was rejected
    """
    body = _("notification_email_to_member_upon_rejection_of_question",
             default="Question rejected")
    
    def subject(self):
        return "Question rejected: %s" % self.context.short_name
    
    def condition(self):
        return self.context.receive_notification
    
    def from_address(self):
        return prefs.getSpeakersOfficeEmail()


@notifier("Question", "clarification_required")
class SendNotificationToMemberUponNeedsClarification(Notification):
    """Issued when a question needs clarification by the MP
    sends a notice that the question needs clarification
    """
    body = _("notification_email_to_member_upon_need_clarification_of_question",
             default="Your question needs to be clarified")
    
    def subject(self):
        return "Question needs clarification: %s" % self.context.short_name
    
    def condition(self):
        return self.context.receive_notification
    
    def from_address(self):
        return prefs.getClerksOfficeEmail()


@notifier("Question", "scheduled")
class SendNotificationToMemberUponDeferred(Notification):
    """Issued when a question was deferred by Clerk's office.
    """
    body = _("notification_email_to_member_upon_defer_of_question",
             default="Question deferred")
    
    def subject(self):
        return "Question deferred: %s" % self.context.short_name
    
    def condition(self):
        return self.context.receive_notification
    
    def from_address(self):
        return prefs.getSpeakersOfficeEmail()


# !+NOT_WIRED_BUT_TESTED!(mr, mar-2011)
class SendNotificationToMemberUponSchedule(Notification):
    """Issued when a question was scheduled by Speakers office.
    Sends a Notice that the question is scheduled for ... 
    """
    body = _("notification_email_to_member_upon_schedule_of_question",
             default="Question scheduled")
    
    def subject(self):
        return "Question scheduled: %s" % self.context.short_name
    
    def condition(self):
        return self.context.receive_notification
    
    def from_address(self):
        return prefs.getClerksOfficeEmail()

''' !+ remove, grep for: SendNotificationToMemberUponPostponed IQuestionPostponedEvent
class SendNotificationToMemberUponPostponed(Notification):
    """Issued when a question was postponed by the speakers office.
    sends a notice that the question could not be debated and was postponed"""

    component.adapts(interfaces.IQuestionPostponedEvent)

    body = _("notification_email_to_member_upon_postpone_of_question",
             default="Question postponed")
    
    def subject(self):
        return "Question postponed: %s" % self.context.short_name
    
    def condition(self):
        return self.context.receive_notification
    
    def from_address(self):
        return prefs.getClerksOfficeEmail()
'''


@notifier("Question", "completed")
class SendNotificationToMemberUponComplete(Notification):
    """The question is marked as “completed” and is made available forwarded 
    to the Speaker's Office for reviewing and to make it "admissible".
    """
    body = _("notification_email_to_member_upon_complete_of_question",
             default="Question completed for review at the speakers office")
    
    def subject(self):
        return "Question forwarded to Speaker's Office: %s" % self.context.short_name
    
    def condition(self):
        return self.context.receive_notification
    
    def from_address(self):
        return prefs.getClerksOfficeEmail()


@notifier("Question", "completed")
class SendNotificationToMinistryUponComplete(Notification):
    """At the same time the question is also forwarded to the
    ministry.
    """
    body = _("notification_email_to_ministry_upon_complete_question",
             default="Question assigned to ministry")
    
    def subject(self):
        return "Question asked to ministry: %s" % self.context.short_name
    
    def condition(self):
        """
        First check if the ministries notification receive system parameter
        is set to true. if its set to true, check if there is a valid ministry
        id - and return true if there is a valid ministry id
        """
        notif_param = prefs.getMinistriesReceiveNotification()
        if notif_param == True:
            # if the ministry id is set then notif_param will still evaluate to true
            # if its not set it will evaluate to false
            notif_param = self.context.ministry_id
        return notif_param
    
    def from_address(self):
        return prefs.getClerksOfficeEmail()
    
    def recipient_address(self):
        session = Session()
        ministry = session.query(domain.Ministry).get(
            self.context.ministry_id)
        return dbutils.getMinsiteryEmails(ministry)


@notifier("Question", "response_pending")
class SendNotificationToMemberUponSentToMinistry(Notification):
    """Issued when a question was sent to a ministry for written
    response.  sends a notice that the question was sent to the
    ministry ... for a written response
    """
    body = _("notification_email_to_member_upon_sent_to_ministry_of_question",
             default="Question sent to ministry for a written answer")
    
    def subject(self):
        return "Question sent to ministry: %s" % self.context.short_name
    
    def condition(self):
        return self.context.receive_notification
    
    def from_address(self):
        return prefs.getClerksOfficeEmail()


# !+NOT_WIRED_BUT_TESTED!(mr, mar-2011)
class SendNotificationToMemberUponAnswer(Notification):
    """Issued when a questions answer was reviewed by Clerk's office.
    sends a notice that the question was either debated or received a
    written answer by the ministry and that the answer is available
    """
    body = _("notification_email_to_member_upon_answer_of_question",
             default="Question answered")
    
    def subject(self):
        return "Question answered: %s" % self.context.short_name
    
    def condition(self):
        return self.context.receive_notification
    
    def from_address(self):
        return prefs.getClerksOfficeEmail()


@notifier("Question", "debated")
class SendNotificationToMemberUponDebate(Notification):
    """Issued when a questions answer was reviewed by Clerk's office.
    sends a notice that the question was either debated or received a
    written answer by the ministry and that the answer is available
    """
    body = _("notification_email_to_member_upon_debate_question",
             default="Question debated")
    
    def subject(self):
        return "Question debated: %s" % self.context.short_name
    
    def condition(self):
        return self.context.receive_notification
    
    def from_address(self):
        return prefs.getClerksOfficeEmail()


''' 
Add to question.txt tests, equivalent set of tests running as the clerk:

  >>> zope.security.management.newInteraction(create_participation(clerk))

  >>> question = add_content(
  ...     domain.Question,
  ...     short_name="My subject - clerk",
  ...     body_text="The question - clerk on behalf of an MP",
  ...     owner_id=mp_1.user_id,
  ...     language="en")
  >>> question.__parent__ = app
  
  >>> wf = IWorkflow(question)
  >>> verify_workflow(wf)

  >>> info = IWorkflowController(question)

Transition "create_on_behalf_of". 
Assigns the role of "Owner" and sets the parliament id.
  
  >>> info.fireTransition("-create_on_behalf_of")
  >>> question.status
  'working_draft'
  >>> question.parliament_id == parliament.parliament_id
  True
  
  >>> tuple(IPrincipalRoleMap(question).getRolesForPrincipal("member"))
  ((u'bungeni.Owner', PermissionSetting: Allow),)

'''

