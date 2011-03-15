
# setup in adapters.py
wf = None
states = None

#

from zope import component
from bungeni.core.workflows.notification import Notification
from bungeni.core.workflows import interfaces
from bungeni.core import globalsettings as prefs
from bungeni.core.i18n import _
    
class SendNotificationToMemberUponReceipt(Notification):
    component.adapts(interfaces.IAgendaItemReceivedEvent)
    
    body = _('notification_email_to_member_upon_receipt_of_agenda_item',
             default="Agenda Item received")
    
    @property
    def subject(self):
        return u'Agenda Item received: %s' % self.context.short_name
    
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
    component.adapts(interfaces.IAgendaItemSubmittedEvent)
    
    body = _('notification_email_to_clerk_upon_submit_of_agenda_item',
             default="Agenda Item submitted")
    
    @property
    def subject(self):
        return u'Agenda Item submitted: %s' % self.context.short_name
    
    @property
    def condition(self):
        return prefs.getClerksOfficeReceiveNotification()
    
    @property
    def recipient_address(self):
        return prefs.getClerksOfficeEmail()

class SendNotificationToMemberUponReject(Notification):
    """Issued when a agenda_item was rejected by the speakers office.
    Sends a notice that the Agenda Item was rejected.
    """
    component.adapts(interfaces.IAgendaItemRejectedEvent)
    
    body = _('notification_email_to_member_upon_rejection_of_agenda_item',
             default="Agenda Item rejected")
    
    @property
    def subject(self):
        return u'Agenda Item rejected: %s' % self.context.short_name
    
    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getSpeakersOfficeEmail()

class SendNotificationToMemberUponNeedsClarification(Notification):
    """Issued when a agenda_item needs clarification by the MP
    sends a notice that the agenda_item needs clarification.
    """
    component.adapts(interfaces.IAgendaItemClarifyEvent)
    
    body = _('notification_email_to_member_upon_need_clarification_of_agenda_item',
             default="Your agenda_item needs to be clarified")
    
    @property
    def subject(self):
        return u'Agenda Item needs clarification: %s' % self.context.short_name
    
    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()

class SendNotificationToMemberUponDeferred(Notification):
    """Issued when a agenda_item was deferred by Clerk's office.
    """
    component.adapts(interfaces.IAgendaItemDeferredEvent)
    
    body = _('notification_email_to_member_upon_defer_of_agenda_item',
             default="Agenda Item deferred")
    
    @property
    def subject(self):
        return u'Agenda Item deferred: %s' % self.context.short_name
    
    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getSpeakersOfficeEmail()

class SendNotificationToMemberUponSchedule(Notification):
    """Issued when a agenda_item was scheduled by Speakers office.
    Sends a Notice that the agenda_item is scheduled for ... 
    """
    component.adapts(interfaces.IAgendaItemScheduledEvent)
    
    body = _('notification_email_to_member_upon_schedule_of_agenda_item',
             default="Agenda Item scheduled")
    
    @property
    def subject(self):
        return u'Agenda Item scheduled: %s' % self.context.short_name
    
    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()

''' !+ remove, grep for: SendNotificationToMemberUponPostponed IQuestionPostponedEvent
class SendNotificationToMemberUponPostponed(Notification):
    """Issued when a agenda_item was postponed by the speakers office.
    sends a notice that the agenda_item could not be debated and was postponed.
    """
    component.adapts(interfaces.IAgendaItemPostponedEvent)
    
    body = _('notification_email_to_member_upon_postpone_of_agenda_item',
             default="Agenda Item postponed")
    
    @property
    def subject(self):
        return u'Agenda Item postponed: %s' % self.context.short_name
    
    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()
'''

class SendNotificationToMemberUponDebated(Notification):
    """Issued when a agenda_item was debated.
    """
    component.adapts(interfaces.IAgendaItemDebatedEvent)
    
    body = _('notification_email_to_member_upon_debate_of_agenda_item',
             default=u"Agenda Item was debated")
    @property
    def subject(self):
        return u'Agenda Item was debated: %s' % self.context.short_name
    
    @property
    def condition(self):
        return self.context.receive_notification
    
    @property
    def from_address(self):
        return prefs.getClerksOfficeEmail()

