import smtplib
import zope.interface
import zope.sendmail.interfaces
import logging
from bungeni.core.app import BungeniApp
from bungeni.models.settings import EmailSettings

app = BungeniApp()

class SMTPMailer(object):
    """A direct mailer for use with zope.sendmail."""

    zope.interface.implements(zope.sendmail.interfaces.ISMTPMailer)
    
    def get_settings(self):
        return EmailSettings(app)

    def send(self, fromaddr, toaddrs, message):
        settings = self.get_settings()
        hostname = settings.hostname
        port = settings.port
        username = settings.username or None
        password = settings.password or None
        fromaddr = fromaddr or settings.default_sender

        connection = smtplib.SMTP(hostname, port)
        if settings.use_tls:
            connection.ehlo()
            connection.starttls()
            connection.ehlo()
        # authenticate if needed
        if username is not None and password is not None:
            connection.login(username, password)

        connection.sendmail(fromaddr, toaddrs, message)
        connection.quit()

class DummySMTPMailer(object):
    """A dummy direct mailer for use with zope.sendmail."""

    zope.interface.implements(zope.sendmail.interfaces.ISMTPMailer)

    def send(self, fromaddr, toaddrs, message):
        logging.getLogger("bungeni.server").info(
            "%s -> %s: %s." % (fromaddr, toaddrs, repr(message)))
        
def dispatch(msg):
    delivery = zope.component.getUtility(zope.sendmail.interfaces.IMailDelivery)
    delivery.send(msg['From'], msg['To'], msg.as_string())
