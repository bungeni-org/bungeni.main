log = __import__("logging").getLogger("bungeni.core.emailnotifications")

import os
import simplejson
import smtplib
from email.mime.text import MIMEText
from threading import Thread
from zope import component
from zope import interface
from zope.app.component.hooks import getSite
from zope.pagetemplate.pagetemplatefile import PageTemplateFile
from bungeni.alchemist import Session
from bungeni.core.interfaces import IMessageQueueConfig, IBungeniMailer
from bungeni.core.notifications import get_mq_connection
from bungeni.models import domain
from bungeni.models.settings import EmailSettings
from bungeni.utils.capi import capi, bungeni_custom_errors


class BungeniSMTPMailer(object):

    interface.implements(IBungeniMailer)

    def send(self, msg):
        settings = EmailSettings(getSite())
        msg["From"] = settings.default_sender
        hostname = settings.hostname
        port = settings.port
        username = settings.username or None
        password = settings.password or None
        connection = smtplib.SMTP(hostname, port)
        if settings.use_tls:
            connection.ehlo()
            connection.starttls()
            connection.ehlo()
        # authenticate if needed
        if username is not None and password is not None:
            connection.login(username, password)
        connection.sendmail(msg["From"], msg["To"], msg.as_string())
        connection.quit()


class BungeniDummySMTPMailer(object):

    interface.implements(IBungeniMailer)

    def send(self, msg):
        log.info("%s -> %s: %s." % (msg["From"], msg["To"], msg.as_string()))


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
    return PageTemplateFile(file_path)


def get_email_body_text(template, message):
    body_macro = template.macros[message["status"] + "-body"]
    body_template = get_template("body.pt")
    return body_template(body_macro=body_macro, **message)


def get_email_subject_text(template, message):
    subject_macro = template.macros[message["status"] + "-subject"]
    subject_template = get_template("subject.pt")
    return subject_template(subject_macro=subject_macro, **message)


@bungeni_custom_errors
def email_notifications_callback(channel, method, properties, body):
    message = simplejson.loads(body)
    recipients = get_recipients(message.get("principal_ids", None))
    template = get_template(message["type"] + ".pt")
    msg = MIMEText(get_email_body_text(template, message))
    msg["Subject"] = get_email_subject_text(template, message)
    msg["To"] = ', '.join(recipients)
    component.getUtility(IBungeniMailer).send(msg)
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


def email_notifications():
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
