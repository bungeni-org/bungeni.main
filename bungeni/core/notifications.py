log = __import__("logging").getLogger("bungeni.core.notifications")

import os
import pika
import simplejson
import datetime
import socket
from lxml import etree
from threading import Thread
from sqlalchemy import orm
from zope.interface import implements
from zope import component
from zope.security.proxy import removeSecurityProxy
from zope.securitypolicy.interfaces import IPrincipalRoleMap, IRole
from zope.component.zcml import handler
from bungeni.utils.capi import capi, bungeni_custom_errors
from bungeni.core.interfaces import INotificationsUtility, IMessageQueueConfig
from bungeni.core.workflow.interfaces import IWorkflowTransitionEvent
from bungeni.alchemist import Session
from bungeni.alchemist.container import contained
from bungeni.models.utils import get_current_parliament, obj2dict
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
                               username="", password="",
                               host="", port=None, virtual_host="",
                               channel_max=None, frame_max=None,
                               heartbeat=None, number_of_workers=0,
                               task_queue=""):
    context.action(discriminator=('RegisterMessageQueueConfig'),
                   callable=handler,
                   args=('registerUtility',
                         MessageQueueConfig(message_exchange, task_exchange,
                                            username, password,
                                            host, port, virtual_host,
                                            channel_max, frame_max, heartbeat,
                                            number_of_workers, task_queue),
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
        heartbeat=mq_utility.get_heartbeat()
    )
    return connection_parameters


def get_mq_connection():
    try:
        return  pika.BlockingConnection(parameters=get_mq_parameters())
    except socket.error:
        log.error("Unable to connect to AMQP server."
                  "Notifications will not be sent")
        return None

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


def queue_transition_based_notification(document, event):
    connection = get_mq_connection()
    if not connection:
        return
    mq_utility = component.getUtility(IMessageQueueConfig)
    domain_class = document.__class__
    unproxied = removeSecurityProxy(document)
    mapper = orm.object_mapper(unproxied)
    primary_key = mapper.primary_key_from_instance(unproxied)
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


def worker():
    connection = get_mq_connection()
    if not connection:
        return
    channel = connection.channel()

    def callback(channel, method, properties, body):
        notifications_utility = component.getUtility(INotificationsUtility)
        message = simplejson.loads(body)
        domain_class = notifications_utility.get_domain(
            message["document_type"])
        roles = notifications_utility.get_transition_based_roles(
            domain_class, message["destination"]
            )
        session = Session()
        document = session.query(domain_class).get(message["document_id"])
        principal_ids = set()
        if document:
            prm = IPrincipalRoleMap(contained(
                    document, get_current_parliament()))
            for role in roles:
                principals = prm.getPrincipalsForRole(role)
                for principal in principals:
                    principal_ids.add(principal[0])
        else:
            pass
        exchange = str(mq_utility.get_message_exchange())
        if principal_ids:
            # create message and send to exchange
            mes = obj2dict(document, 0)
            mes["principal_ids"] = list(principal_ids)
            dthandler = lambda obj: obj.isoformat() if isinstance(obj,
                                                    datetime.datetime) else obj
            channel.basic_publish(
                exchange=exchange,
                body=simplejson.dumps(mes, default=dthandler),
                properties=pika.BasicProperties(content_type="text/plain",
                                                delivery_mode=1
                                                ),
                routing_key="")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        session.close()

    channel.basic_qos(prefetch_count=1)
    mq_utility = component.getUtility(IMessageQueueConfig)
    channel.basic_consume(callback, queue=str(mq_utility.get_task_queue()))
    channel.start_consuming()


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
        if domain_class in self.transition_based:
            if state in self.transition_based[domain_class]:
                return self.transition_based[domain_class][state]
        return []

    def set_time_based_notification(self, domain_class, state, roles, time):
        if domain_class not in self.time_based:
            self.time_based[domain_class] = {}
        if state not in self.time_based[domain_class]:
            self.time_based[domain_class][state] = []
        if time not in self.time_based[domain_class][state]:
            self.time_based[domain_class][state][time] = []
        self.time_based[domain_class][state][time].extend(roles)

    #!+NOTIFICATIONS(miano, feb 2012) Similar bungeni.core.workspace.WorkspaceUtility
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


@bungeni_custom_errors
def load_notification_config(file_name, domain_class):
    """Loads the notification configuration for each document
    """
    notifications_utility = component.getUtility(INotificationsUtility)
    path = capi.get_path_for("notifications")
    file_path = os.path.join(path, file_name)
    item_type = file_name.split(".")[0]
    notifications_utility.register_item_type(domain_class, item_type)
    notification_xml = etree.fromstring(open(file_path).read())
    for notify in notification_xml.iterchildren("notify"):
        roles = notify.get("roles").split()
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
    component.provideHandler(queue_transition_based_notification,
        adapts=(domain_class, IWorkflowTransitionEvent))


def load_notifications():
    setup_message_exchange()
    setup_task_exchange()
    setup_task_workers()
    for type_key, ti in capi.iter_type_info():
        workflow = ti.workflow
        if workflow and workflow.has_feature("notification"):
            load_notification_config("%s.xml" % ti.workflow_key,
                                     ti.domain_model)
