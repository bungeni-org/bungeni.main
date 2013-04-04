# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni notifications
Sets up notification machinery for each document type.
 
$Id$
"""

log = __import__("logging").getLogger("bungeni.core.notifications")

import os
import pika
import simplejson
import datetime
from threading import Thread
from sqlalchemy import orm
from zope.interface import implements
from zope import component
from zope.security.proxy import removeSecurityProxy
from zope.securitypolicy.interfaces import IPrincipalRoleMap, IRole
from zope.component.zcml import handler
from bungeni.capi import capi
from bungeni.utils import common, naming
from bungeni.core.interfaces import INotificationsUtility, IMessageQueueConfig
from bungeni.core.workflow.interfaces import IWorkflowTransitionEvent
from bungeni.alchemist import Session
from bungeni.models import domain
from bungeni.models.roles import ROLES_DIRECTLY_DEFINED_ON_OBJECTS
# this module will be moved to bungeni.utils
from bungeni.ui.utils import report_tools
from bungeni.core import kronos
import bungeni.core
import transaction


class MessageQueueConfig(object):

    implements(IMessageQueueConfig)

    def __init__(self, message_exchange, task_exchange, username, password,
                 host, port, virtual_host, channel_max, frame_max, heartbeat,
                 number_of_workers, task_queue):
        self.message_exchange = message_exchange
        self.task_exchange = task_exchange
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.virtual_host = virtual_host
        self.channel_max = channel_max
        self.frame_max = frame_max
        self.heartbeat = heartbeat
        self.number_of_workers = number_of_workers
        self.task_queue = task_queue

    def get_message_exchange(self):
        return self.message_exchange

    def get_task_exchange(self):
        return self.task_exchange

    def get_username(self):
        return self.username

    def get_password(self):
        return self.password

    def get_host(self):
        return self.host

    def get_port(self):
        return self.port

    def get_virtual_host(self):
        return self.virtual_host

    def get_channel_max(self):
        return self.channel_max

    def get_frame_max(self):
        return self.frame_max

    def get_heartbeat(self):
        return self.heartbeat

    def get_number_of_workers(self):
        return self.number_of_workers

    def get_task_queue(self):
        return self.task_queue


def registerMessageQueueConfig(context, message_exchange, task_exchange,
    username="", password="", host="", port=None, virtual_host="",
    channel_max=None, frame_max=None, heartbeat=None, number_of_workers=0,
    task_queue=""):
    context.action(discriminator=('RegisterMessageQueueConfig'),
        callable=handler,
        args=('registerUtility',
            MessageQueueConfig(message_exchange, task_exchange,
                username, password, host, port, virtual_host,
                channel_max, frame_max, heartbeat, number_of_workers,
                task_queue),
            IMessageQueueConfig)
    )


def get_mq_parameters():
    mq_utility = component.getUtility(IMessageQueueConfig)
    credentials = pika.PlainCredentials(str(mq_utility.get_username()),
        str(mq_utility.get_password()))
    connection_parameters = pika.ConnectionParameters(
        host=str(mq_utility.get_host()),
        port=mq_utility.get_port(),
        virtual_host=str(mq_utility.get_virtual_host()),
        credentials=credentials,
        channel_max=mq_utility.get_channel_max(),
        frame_max=mq_utility.get_frame_max(),
        heartbeat_interval=mq_utility.get_heartbeat()
    )
    return connection_parameters


def get_mq_connection():
    try:
        return pika.BlockingConnection(parameters=get_mq_parameters())
    except pika.exceptions.AMQPConnectionError:
        log.error(
            "Unable to connect to AMQP server. Notifications will not be sent")


def post_commit_publish(status, **kwargs):
    """This is a post-transaction commit hook which sends a message
    to rabbitmq (only if the transaction commits successfully).
    """
    connection = get_mq_connection()
    if not connection:
        log.warn("Can't rabbitmq connection. Won't send message")
        return
    if status:
        channel = connection.channel()
        channel.basic_publish(**kwargs)
    else:
        log.error("Transaction did not commit successfully. "
            "AMQP message will not be sent"
        )


def queue_notification(document, event):
    connection = get_mq_connection()
    if not connection:
        return
    mq_utility = component.getUtility(IMessageQueueConfig)
    domain_class = document.__class__
    unproxied = removeSecurityProxy(document)
    mapper = orm.object_mapper(unproxied)
    primary_key = mapper.primary_key_from_instance(unproxied)[0]
    notifications_utility = component.getUtility(INotificationsUtility)
    message = {
        "document_id": primary_key,
        "document_type": notifications_utility.get_type(domain_class),
        "source": event.source,
        "destination": event.destination
    }
    kwargs = dict(
        exchange=str(mq_utility.get_task_exchange()),
        routing_key=str(mq_utility.get_task_queue()),
        body=simplejson.dumps(message),
        properties=pika.BasicProperties(
            content_type="text/plain", delivery_mode=1
        )
    )
    txn = transaction.get()
    txn.addAfterCommitHook(post_commit_publish, (), kwargs)


def get_principal_ids(document, roles):
    principal_ids = set()
    document_prm = IPrincipalRoleMap(document)
    group_prms = get_group_prms(document)
    for role in roles:
        if role in ROLES_DIRECTLY_DEFINED_ON_OBJECTS:
            principals = document_prm.getPrincipalsForRole(role)
            for principal in principals:
                principal_ids.add(principal[0])
        else:
            for group_prm in group_prms:
                principals = group_prm.getPrincipalsForRole(role)
                for principal in principals:
                    principal_id = principal[0]
                    if principal_id.startswith("group"):
                        group_mbr_ids = get_group_member_ids(principal_id)
                        for group_mbr in group_mbr_ids:
                            principal_ids.add(group_mbr)
    return principal_ids


def get_group_member_ids(group_principal_name):
    session = Session()
    group = session.query(
        domain.Group).filter(
        domain.Group.principal_name == group_principal_name).one()
    if group:
        return [member.user.login for member in group.members]
    return []


def get_group_prms(document):
    prms = []
    prms.append(IPrincipalRoleMap(common.get_application()))
    parent_group = getattr(document, "group", None)
    if parent_group:
        prms.append(IPrincipalRoleMap(parent_group))
    assigned_groups = getattr(document, "group_assignment", list())
    if assigned_groups:
        for group in assigned_groups:
            prms.append(IPrincipalRoleMap(group))
    return prms


def notification_time(time_string):
    """Takes a time config string and computes the notification
    time
    """
    hours = report_tools.compute_hours(time_string)
    return datetime.datetime.now() + datetime.timedelta(hours=hours)


def get_message(document, principal_ids):
    message = bungeni.core.serialize.obj2dict(document, 0)
    if not message.get("type", None):
        try:
            message["type"] = message["document_type"]
        except KeyError:
            message["type"] = naming.polymorphic_identity(document.__class__)
    message["principal_ids"] = list(principal_ids)
    return message


def worker():
    connection = get_mq_connection()
    if not connection:
        return
    channel = connection.channel()
    mq_utility = component.getUtility(IMessageQueueConfig)

    def callback(channel, method, properties, body):
        notification_utl = component.getUtility(INotificationsUtility)
        exchange = str(mq_utility.get_message_exchange())
        message = simplejson.loads(body)
        domain_class = notification_utl.get_domain(
            message["document_type"])
        session = Session()
        if domain_class and message["document_id"]:
            document = session.query(domain_class).get(message["document_id"])
            if document:
                # first we handle the transition based notifications
                transition_roles = notification_utl.get_transition_based_roles(
                    domain_class, message["destination"]
                )
                transition_principal_ids = get_principal_ids(
                    document, transition_roles)
                if transition_principal_ids:
                    mes = get_message(document, transition_principal_ids)
                    mes["notification_type"] = "onstate"
                    dthandler = lambda obj: obj.isoformat() if isinstance(
                        obj, datetime.datetime) else obj
                    channel.basic_publish(
                        exchange=exchange,
                        body=simplejson.dumps(mes, default=dthandler),
                        properties=pika.BasicProperties(
                            content_type="text/plain",
                            delivery_mode=1
                        ),
                        routing_key="")
                # then we handle the time based notifications
                time_roles = notification_utl.get_time_based_time_and_roles(
                    domain_class, message["destination"]
                )
                for time_string, roles in time_roles.iteritems():
                    time_ntf = domain.TimeBasedNotication()
                    time_ntf.object_id = message["document_id"]
                    time_ntf.object_type = message["document_type"]
                    time_ntf.object_status = message["destination"]
                    time_ntf.time_string = time_string
                    time_ntf.notification_date_time = notification_time(
                        time_string)
                    session.add(time_ntf)
        # we commit manually here as this code is not executed in a zope
        # transaction
        session.commit()
        session.close()
        channel.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(callback, queue=str(mq_utility.get_task_queue()))
    channel.start_consuming()


def queue_time_based_notifications():
    session = Session()
    notification_utl = component.getUtility(INotificationsUtility)
    mq_utility = component.getUtility(IMessageQueueConfig)
    connection = get_mq_connection()
    if not connection:
        return
    channel = connection.channel()
    exchange = str(mq_utility.get_message_exchange())
    notifications = session.query(domain.TimeBasedNotication).filter(
        domain.TimeBasedNotication.notification_date_time <
        datetime.datetime.now()).all()
    for notification in notifications:
        domain_class = notification_utl.get_domain(
            notification.object_type)
        item = session.query(domain_class).get(notification.object_id)
        if item and item.status == notification.object_status:
            roles = notification_utl.get_time_based_roles(
                domain_class, notification.object_status,
                notification.time_string)
            principal_ids = get_principal_ids(item, roles)
            if principal_ids:
                message = get_message(item, principal_ids)
                message["notification_type"] = "afterstate"
                message["notification_time_string"] = notification.time_string
                dthandler = lambda obj: obj.isoformat() if isinstance(
                    obj, datetime.datetime) else obj
                channel.basic_publish(
                    exchange=exchange,
                    body=simplejson.dumps(message, default=dthandler),
                    properties=pika.BasicProperties(
                        content_type="text/plain",
                        delivery_mode=1
                    ),
                    routing_key="")
        session.delete(notification)
        session.commit()


def setup_task_workers():
    mq_utility = component.getUtility(IMessageQueueConfig)
    connection = get_mq_connection()
    if not connection:
        return
    channel = connection.channel()
    channel.queue_declare(queue=str(mq_utility.get_task_queue()), durable=True)
    channel.queue_bind(queue=str(mq_utility.get_task_queue()),
                       exchange=str(mq_utility.get_task_exchange()),
                       routing_key=str(mq_utility.get_task_queue()))
    for i in range(mq_utility.get_number_of_workers()):
        task_thread = Thread(target=worker)
        task_thread.daemon = True
        task_thread.start()


def setup_message_exchange():
    connection = get_mq_connection()
    if not connection:
        return
    channel = connection.channel()
    mq_utility = component.getUtility(IMessageQueueConfig)
    channel.exchange_declare(exchange=str(mq_utility.get_message_exchange()),
                             type="fanout", durable=True)


def setup_task_exchange():
    connection = get_mq_connection()
    if not connection:
        return
    channel = connection.channel()
    mq_utility = component.getUtility(IMessageQueueConfig)
    channel.exchange_declare(exchange=str(mq_utility.get_task_exchange()),
                             type="direct", durable=True)


class NotificationsUtility(object):
    implements(INotificationsUtility)
    time_based = {}
    transition_based = {}
    domain_type = {}

    def set_transition_based_notification(self, domain_class, state, roles):
        if domain_class not in self.transition_based:
            self.transition_based[domain_class] = {}
        if state not in self.transition_based[domain_class]:
            self.transition_based[domain_class][state] = []
        self.transition_based[domain_class][state].extend(roles)

    def get_transition_based_roles(self, domain_class, state):
        if domain_class in self.transition_based.keys():
            if state in self.transition_based[domain_class]:
                return self.transition_based[domain_class][state]
        return []

    def set_time_based_notification(self, domain_class, state, roles, time):
        if domain_class not in self.time_based:
            self.time_based[domain_class] = {}
        if state not in self.time_based[domain_class]:
            self.time_based[domain_class][state] = {}
        if time not in self.time_based[domain_class][state]:
            self.time_based[domain_class][state][time] = []
        self.time_based[domain_class][state][time].extend(roles)

    def get_time_based_time_and_roles(self, domain_class, state):
        """Returns a ditcionary with time_strings as keys and roles to be
        notified as roles
        """
        if domain_class in self.time_based:
            if state in self.time_based[domain_class]:
                    return self.time_based[domain_class][state]
        return {}

    def get_time_based_roles(self, domain_class, state, time):
        """Returns a list of roles to be notified
        """
        if domain_class in self.time_based:
            if state in self.time_based[domain_class]:
                if time in self.time_based[domain_class][state]:
                    return self.time_based[domain_class][state][time]
        return []

    #!+NOTIFICATIONS(miano, feb 2012) Similar to
    # bungeni.core.workspace.WorkspaceUtility
    # TODO - make more generic
    def register_item_type(self, domain_class, item_type):
        """ Stores domain_class -> item_type and vice versa in a dictionary eg.
        domain.Bill -> bill.
        """
        if item_type in self.domain_type.keys():
            raise ValueError("Multiple notification declarations"
                             "with same name - %s") % (item_type)
        if domain_class in self.domain_type.keys():
            raise ValueError("Multiple notification domain classes"
                             "with same name - %s") % (domain_class)
        self.domain_type[item_type] = domain_class
        self.domain_type[domain_class] = item_type

    def get_domain(self, key):
        """Passed a type string returns the domain class"""
        if key in self.domain_type:
            return self.domain_type[key]
        return None

    def get_type(self, key):
        """Passed a domain class returns a string"""
        if key in self.domain_type:
            return self.domain_type[key]
        return None

component.provideUtility(NotificationsUtility())


@capi.bungeni_custom_errors
def load_notification_config(file_name, domain_class):
    """Loads the notification configuration for each document
    """
    notifications_utility = component.getUtility(INotificationsUtility)
    path = capi.get_path_for("notifications")
    file_path = os.path.join(path, file_name)
    notification = capi.schema.validate_file_rng("notifications", file_path)
    item_type = file_name.split(".")[0]
    notifications_utility.register_item_type(domain_class, item_type)
    for notify in notification.iterchildren("notify"):
        roles = capi.schema.qualified_roles(notify.get("roles"))
        for role in roles:
            assert component.queryUtility(IRole, role, None), \
                "Notifications configuration error : " \
                "Invalid role - %s. file: %s, state : %s" % (
                role, file_name)
        if notify.get("onstate"):
            states = notify.get("onstate").split()
            for state in states:
                notifications_utility.set_transition_based_notification(
                        domain_class, state, roles)
        elif notify.get("afterstate"):
            states = notify.get("afterstate").split()
            time = notify.get("time")
            for state in states:
                notifications_utility.set_time_based_notification(
                        domain_class, state, roles, time)
        else:
            raise ValueError("Please specify either onstate or afterstate")
    # Register subscriber for domain class
    component.provideHandler(queue_notification,
        adapts=(domain_class, IWorkflowTransitionEvent))


def load_notifications():
    setup_message_exchange()
    setup_task_exchange()
    setup_task_workers()
    for type_key, ti in capi.iter_type_info():
        workflow = ti.workflow
        if workflow and workflow.has_feature("notification"):
            load_notification_config("%s.xml" % type_key, ti.domain_model)
    s = kronos.ThreadedScheduler()
    s.add_interval_task(queue_time_based_notifications,
        "time_based_notifications", 0, 3600, kronos.method.threaded, [], None)
    s.start()
