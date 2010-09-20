from zope.i18n import translate

from bungeni.alchemist import Session
from bungeni.models import domain
from bungeni.server.smtp import dispatch

from email.mime.text import MIMEText


def get_owner_email(context):
    session = Session()
    owner = session.query(domain.User).get(context.owner_id)
    return  '"%s %s" <%s>' % (owner.first_name, owner.last_name, owner.email)

class Notification(object):
    def __new__(cls, event):
        notification = object.__new__(cls)
        notification.__init__(event.object)

        if notification.condition:
            notification()
        
    def __init__(self, context):
        self.context = context

    def __call__(self):
        text = translate(self.body)
        msg = MIMEText(text)

        msg['Subject'] = self.subject
        msg['From'] = self.from_address
        msg['To'] = self.recipient_address

        dispatch(msg)
        
    @property
    def from_address(self):
        return get_owner_email(self.context)

    @property
    def recipient_address(self):
        return get_owner_email(self.context)
