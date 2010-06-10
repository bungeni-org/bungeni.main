# encoding: utf-8

from zope import component
from bungeni.core.workflows.notification import Notification
from bungeni.core.workflows import interfaces
from bungeni.core import globalsettings as prefs
from bungeni.core.i18n import _
import zope.securitypolicy.interfaces
from bungeni.core.workflows import dbutils, utils

class conditions:
    @staticmethod
    def is_scheduled(info, context):
        return dbutils.isItemScheduled(context.tabled_document_id)
    
    @staticmethod
    def user_is_not_context_owner(info, context):
        return not utils.user_is_context_owner(context)

class actions:
    @staticmethod
    def denyAllWrites(tabled_document):
        """
        remove all rights to change the question from all involved roles
        """
    
    @staticmethod
    def postpone(info,context):
        utils.setTabledDocumentHistory(info,context)

    @staticmethod
    def create( info, context ):
        utils.setParliamentId(info, context)
        utils.setBungeniOwner(context)
    
    @staticmethod
    def submit( info, context ):
        utils.setSubmissionDate(info, context)


    @staticmethod
    def received_by_clerk( info, context ):
        utils.createVersion(info, context)

    @staticmethod
    def require_edit_by_mp( info, context ):
        utils.createVersion(info,context)


    @staticmethod
    def complete( info, context ):
        utils.createVersion(info,context)
        utils.setSubmissionDate(info, context)
 

    @staticmethod
    def approve( info, context ):
        utils.setApprovalDate(info,context)

    @staticmethod
    def reject( info, context ):
        pass

    @staticmethod
    def require_amendment( info, context ):
        utils.createVersion(info,context)
    
    @staticmethod
    def complete_clarify( info, context ):
        utils.createVersion(info,context)


    @staticmethod
    def mp_clarify( info, context ):
        utils.createVersion(info,context)


    @staticmethod
    def schedule( info, context ):
        pass

    @staticmethod
    def defer( info, context):
        pass

    @staticmethod
    def elapse( info, context ):
        pass

    @staticmethod
    def schedule( info, context ):
        pass

    @staticmethod
    def debate( info, context ):
        pass

    @staticmethod
    def withdraw( info, context ):
        pass

class SendNotificationToMemberUponReceipt(Notification):
    component.adapts(interfaces.ITabledDocumentReceivedEvent)

    body = _('notification_email_to_member_upon_receipt_of_tabled_document',
             default="Tabled document received")
    
    @property
    def subject(self):
        return u'Tabled document received: %s' % self.context.short_name

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

    component.adapts(interfaces.ITabledDocumentSubmittedEvent)

    body = _('notification_email_to_clerk_upon_submit_of_tabled_document',
             default="Tabled document submitted")

    @property
    def subject(self):
        return u'Tabled document submitted: %s' % self.context.short_name

    @property
    def condition(self):
        return prefs.getClerksOfficeRecieveNotification()
    
    @property
    def recipient_address(self):
        return prefs.getClerksOfficeEmail()

class SendNotificationToMemberUponReject(Notification):
    """Issued when a tabled_document was rejected by the speakers office.
    Sends a notice that the TabledDocument was rejected"""

    component.adapts(interfaces.ITabledDocumentRejectedEvent)

    body = _('notification_email_to_member_upon_rejection_of_tabled_document',
             default="Tabled document rejected")

    @property
    def subject(self):
        return u'Tabled document rejected: %s' % self.context.short_name

    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getSpeakersOfficeEmail()

class SendNotificationToMemberUponNeedsClarification(Notification):
    """Issued when a tabled_document needs clarification by the MP
    sends a notice that the tabled_document needs clarification"""

    component.adapts(interfaces.ITabledDocumentClarifyEvent)

    body = _('notification_email_to_member_upon_need_clarification_of_tabled_document',
             default="Your tabled document needs to be clarified")

    @property
    def subject(self):
        return u'Tabled document needs clarification: %s' % self.context.short_name

    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()

class SendNotificationToMemberUponDeferred(Notification):
    """Issued when a tabled document was deferred by Clerk's office."""

    component.adapts(interfaces.ITabledDocumentDeferredEvent)

    body = _('notification_email_to_member_upon_defer_of_tabled_document',
             default="Tabled document deferred")

    @property
    def subject(self):
        return u'Tabled document deferred: %s' % self.context.short_name

    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getSpeakersOfficeEmail()

class SendNotificationToMemberUponSchedule(Notification):
    """Issued when a tabled document was scheduled by Speakers office.
    Sends a Notice that the tabled_document is scheduled for ... """

    component.adapts(interfaces.ITabledDocumentScheduledEvent)

    body = _('notification_email_to_member_upon_schedule_of_tabled_document',
             default="Tabled document scheduled")

    @property
    def subject(self):
        return u'Tabled document scheduled: %s' % self.context.short_name

    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()

class SendNotificationToMemberUponPostponed(Notification):
    """Issued when a tabled_document was postponed by the speakers office.
    sends a notice that the tabled_document could not be debated and was postponed"""

    component.adapts(interfaces.ITabledDocumentPostponedEvent)

    body = _('notification_email_to_member_upon_postpone_of_tabled_document',
             default="Tabled document postponed")

    @property
    def subject(self):
        return u'Tabled document postponed: %s' % self.context.short_name

    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()

class SendNotificationToMemberUponDebated(Notification):
    """Issued when a tabled_document was debated"""

    component.adapts(interfaces.ITabledDocumentDebatedEvent)

    body = _('notification_email_to_member_upon_debate_of_tabled_document',
             default=u"Tabled document was debated")
    @property
    def subject(self):
        return u'Tabled document was debated: %s' % self.context.short_name

    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()

