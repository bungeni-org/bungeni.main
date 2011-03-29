# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Workflow Notifications

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflows.notification")

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
    
    def __new__(cls, context):
        notification = object.__new__(cls)
        notification.__init__(context)
        if notification.condition():
            # call to send notification
            notification()
    
    def __init__(self, context):
        self.context = context
    
    def condition(self):
        raise NotImplemented
    
    def __call__(self):
        text = translate(self.body)
        msg = MIMEText(text)
        msg["Subject"] = self.subject()
        msg["From"] = self.from_address()
        msg["To"] = self.recipient_address()
        dispatch(msg)
    
    def from_address(self):
        return get_owner_email(self.context)
    
    def recipient_address(self):
        return get_owner_email(self.context)

# 

def notifier(type_name, status):
    """Decorator to register a callable as a notifier, 
    listening on occurances of (type_name, status).
    """
    def _register_notifier_decorator(notifier):
        ts_notifiers = NOTIFIER_REGISTRY.setdefault(type_name, {}
            ).setdefault(status, [])
        if notifier not in ts_notifiers:
            log.debug("Register Notifier: "
                "[%s/%s/%s]" % (notifier, type_name, status))
            ts_notifiers.append(notifier)
        else:
            log.warn("IGNORING: Register Notifier: already registered "
                "[%s/%s/%s]" % (notifier, type_name, status))
        return notifier
    return _register_notifier_decorator

#

NOTIFIER_REGISTRY = {} # { type_name: { status: [ notifier_callables ] } }

#

