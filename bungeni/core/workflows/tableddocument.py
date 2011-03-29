
# setup in adapters.py
wf = None
states = None

#

from bungeni.core.workflows.notification import Notification, notifier
from bungeni.core import globalsettings as prefs
from bungeni.core.i18n import _


@notifier("TabledDocument", "received")
class SendNotificationToMemberUponReceipt(Notification):
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


@notifier("TabledDocument", "submitted")
class SendNotificationToClerkUponSubmit(Notification):
    """Send notification to Clerk's office upon submit.

    We need to settings from a global registry to determine whether to
    send this notification and where to send it to.
    """
    body = _('notification_email_to_clerk_upon_submit_of_tabled_document',
             default="Tabled document submitted")

    @property
    def subject(self):
        return u'Tabled document submitted: %s' % self.context.short_name

    @property
    def condition(self):
        return prefs.getClerksOfficeReceiveNotification()
    
    @property
    def recipient_address(self):
        return prefs.getClerksOfficeEmail()


@notifier("TabledDocument", "inadmissible")
class SendNotificationToMemberUponReject(Notification):
    """Issued when a tabled_document was rejected by the speakers office.
    Sends a notice that the TabledDocument was rejected
    """
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


@notifier("TabledDocument", "clarification_required")
class SendNotificationToMemberUponNeedsClarification(Notification):
    """Issued when a tabled_document needs clarification by the MP
    sends a notice that the tabled_document needs clarification
    """
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


@notifier("TabledDocument", "scheduled")
class SendNotificationToMemberUponSchedule(Notification):
    """Issued when a tabled document was scheduled by Speakers office.
    Sends a Notice that the tabled_document is scheduled for ... 
    """
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


@notifier("TabledDocument", "adjourned")
class SendNotificationToMemberUponAdjourned(Notification):
    """Issued when a tabled_document was adjourned by the speakers office.
    sends a notice that the tabled_document could not be debated and was adjourned
    """
    body = _('notification_email_to_member_upon_postpone_of_tabled_document',
             default="Tabled document adjourned")

    @property
    def subject(self):
        return u'Tabled document adjourned: %s' % self.context.short_name

    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()


