import smtplib
import zope.interface
import zope.sendmail.interfaces
import logging

class SMTPMailer(object):
    """A direct mailer for use with zope.sendmail."""

    zope.interface.implements(zope.sendmail.interfaces.ISMTPMailer)

    def send(self, fromaddr, toaddrs, message):
        hostname = 'localhost'
        port = 25
        username = password = None

        connection = smtplib.SMTP(hostname, port)

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
