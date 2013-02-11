log = __import__("logging").getLogger("bungeni.core.emailnotifications")

import os
import simplejson
import smtplib
import socket
from email.mime.text import MIMEText
from threading import Thread
from lxml import etree
from zope import component
from zope import interface
from bungeni.utils import common
from zope.pagetemplate.pagetemplatefile import PageTemplate
from zope.cachedescriptors.property import CachedProperty
from bungeni.alchemist import Session
from bungeni.core.interfaces import (IMessageQueueConfig, IBungeniMailer,
    INotificationEvent
)
from bungeni.core.notifications import get_mq_connection
from bungeni.models import domain
from bungeni.models.settings import EmailSettings
from bungeni.capi import capi
from bungeni.utils import register
from bungeni.ui.reporting.generators import get_attr


class EmailError(Exception):
    """Raised when there is a problem with the email configuration
    """


class BungeniSMTPMailer(object):

    interface.implements(IBungeniMailer)

    @CachedProperty
    def settings(self):
        return EmailSettings(common.get_application())

    def send(self, msg, recipients):
        msg["From"] = self.settings.default_sender
        msg["To"] = ",".join(recipients)
        hostname = self.settings.hostname
        port = self.settings.port
        username = self.settings.username or None
        password = self.settings.password or None
        try:
            connection = smtplib.SMTP(hostname, port)
        except smtplib.SMTPConnectError:
            log.error("Error occurred during establishment of"
                      " a connection with the SMTP server.")
            return
        except socket.error, v:
            log.error("Connection to SMTP server failed with error code: %s"
                % v[0])
            return
        if self.settings.use_tls:
            connection.ehlo()
            connection.starttls()
            connection.ehlo()
        # authenticate if needed
        if username is not None and password is not None:
            try:
                connection.login(username, password)
            except smtplib.SMTPAuthenticationError:
                log.error("Error occured when establishing connection"
                          " with SMTP server")
        try:
            connection.sendmail(msg["From"], recipients, msg.as_string())
        except smtplib.SMTPSenderRefused:
            log.error("Email sender address refused")
        except smtplib.SMTPRecipientsRefused:
            log.error("Email recipient addresses refused.")
        except smtplib.SMTPDataError:
            log.error("The SMTP server refused to accept the message data.")
        connection.quit()


class BungeniDummySMTPMailer(BungeniSMTPMailer):

    interface.implements(IBungeniMailer)

    def send(self, msg, recipients):
        msg["From"] = self.settings.default_sender
        msg["To"] = ",".join(recipients)
        log.info("%s -> %s: %s." % (
                msg["From"], msg["To"], msg.as_string()))


def get_principals(principal_ids):
    session = Session()
    return session.query(domain.User).filter(
        domain.User.login.in_(principal_ids)).all()


def get_recipients(principal_ids):
    if principal_ids:
        users = get_principals(principal_ids)
        return [user.email for user in users]
    return []


def get_template(file_name):
    path = capi.get_path_for("email", "templates")
    file_path = os.path.join(path, file_name)
    if os.path.exists(file_path):
        template_file = open(file_path)
        file_string = template_file.read()
        template = etree.fromstring(file_string)
        template_file.close()
        return template
    else:
        raise EmailError("Email template %s does not exist" % file_name)


def is_html(template):
    html = get_attr(template, "html")
    if not html or html.lower() == "true":
        return True
    else:
        return False


class EmailTemplate(PageTemplate):
    def pt_getContext(self, args=(), options={}, **kw):
        rval = PageTemplate.pt_getContext(self, args=args)
        options.update(rval)
        return options


class Item:
    def __init__(self, message):
        self.message = message

    def __getitem__(self, name):
        if name in self.message.keys():
            return self.message[name]
        else:
            log.warning()
            return "None"


class EmailBlock(object):
    def __init__(self, template, message):
        self.template = template
        self.message = message
        self.status = message["status"]["value"]
        self.type = message["notification_type"]
        self.time_string = message.get("notification_time_string")

    def get_email(self):
        def get_node_content(element):
            return (element.text +
                    "".join(map(etree.tostring, element))).strip()

        subject, body = None, None
        for _, element in etree.iterwalk(self.template, tag="block"):
            if (element.get("onstate", None) == self.status):
                subject = get_node_content(element.find("subject"))
                body = get_node_content(element.find("body"))
            elif ((element.get("afterstate", None) == self.status) and
                  (element.get("time", None) == self.time_string)):
                subject = get_node_content(element.find("subject"))
                body = get_node_content(element.find("body"))
            element.clear()
        # get defaults
        if not subject:
            subject = "Item Notification: %s" % (self.message["title"])
            log.warn("Missing subject template for %s:%s. Using default" % (
                    self.message["type"], self.message["status"]))
        if not body:
            body = "Item, %s, type: %s, status: %s" % (self.message["title"],
                self.message["type"], self.message["status"]["value"])
            log.warn("Missing body template for %s:%s. Using default" % (
                    self.message["type"], self.message["status"]))
        subject_template = EmailTemplate()
        body_template = EmailTemplate()
        subject_template.write(subject)
        body_template.write(body)
        return (subject_template(item=Item(self.message)),
                body_template(item=Item(self.message)))


#@capi.bungeni_custom_errors
def email_notifications_callback(channel, method, properties, body):
    message = simplejson.loads(body)
    ti = capi.get_type_info(message["type"])
    workflow = ti.workflow
    if workflow and workflow.has_feature("email"):
        recipients = get_recipients(message.get("principal_ids", None))
        template = get_template(message["type"] + ".xml")
        email_block = EmailBlock(template, message)
        subject, body = email_block.get_email()
        if is_html(template):
            msg = MIMEText(body, "html")
        else:
            msg = MIMEText(body, "text")
        msg["Subject"] = subject
        component.getUtility(IBungeniMailer).send(msg, recipients)
    channel.basic_ack(delivery_tag=method.delivery_tag)


def email_worker():
    connection = get_mq_connection()
    if not connection:
        return
    channel = connection.channel()
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(email_notifications_callback,
                          queue="bungeni_email_queue")
    channel.start_consuming()


@capi.bungeni_custom_errors
def load_email():
    for type_key, ti in capi.iter_type_info():
        workflow = ti.workflow
        if workflow and workflow.has_feature("email"):
            if not workflow.has_feature("notification"):
                raise EmailError("Email notifications feature for %r cannot be "
                    "enabled without first enabling the notification "
                    "feature" % (type_key)) # !+FEATURE_DEPENDENCIES
    mq_utility = component.getUtility(IMessageQueueConfig)
    connection = get_mq_connection()
    if not connection:
        return
    channel = connection.channel()
    channel.queue_declare(queue="bungeni_email_queue", durable=True)
    channel.queue_bind(queue="bungeni_email_queue",
                       exchange=str(mq_utility.get_message_exchange()),
                       routing_key="")
    for i in range(mq_utility.get_number_of_workers()):
        task_thread = Thread(target=email_worker)
        task_thread.daemon = True
        task_thread.start()


@register.handler(adapts=(INotificationEvent,))
def notify_users(event):
    """Send an email to recipients set up in event.object
    See `INotificationEvent` docs
    """
    #!+performance(mb, oct-2012) this should run in a thread
    message = event.object
    msg = MIMEText(message.get("body"))
    msg["Subject"] = message.get("subject")
    if message.get("recipients"):
        component.getUtility(IBungeniMailer).send(
            msg, message.get("recipients"))
    else:
        log.warn("Could not send notification message. No recipient")
    
