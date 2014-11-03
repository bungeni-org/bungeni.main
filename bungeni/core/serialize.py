# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Utilities to serialize objects to XML

$Id$
"""
logging = __import__("logging")
log = logging.getLogger("bungeni.core.serialize")
import os
import errno
import threading
import functools
import inspect
import math
import string
import random
import sys
import traceback
from StringIO import StringIO
from zipfile import ZipFile

from xml.etree.cElementTree import Element, ElementTree
from tempfile import NamedTemporaryFile as tmp
import simplejson

import zope.component
import zope.app.component
import zope.security
import zope.event
from zope.lifecycleevent import IObjectModifiedEvent, IObjectCreatedEvent
from bungeni.core.testing import create_participation

from sqlalchemy.orm import class_mapper, object_mapper
from sqlalchemy import sql

from bungeni.alchemist.container import stringKey, valueKey
from bungeni.alchemist import Session
from bungeni.alchemist.interfaces import IAlchemistContent
from bungeni.alchemist.utils import get_vocabulary
from bungeni.core.workflow.states import get_object_state_rpm
from bungeni.core.interfaces import (
    IMessageQueueConfig, 
    NotificationEvent, 
    IVersionCreatedEvent,
    ITranslationCreatedEvent
)
from bungeni.core.workflow.interfaces import (IWorkflow, IStateController,
    IWorkflowed, IWorkflowController, InvalidStateError
)
import bungeni.core

from bungeni.models import interfaces, domain, settings
from bungeni.feature.interfaces import (
    IFeatureVersion,
    IFeatureEvent,
    IFeatureAttachment,
)
from bungeni.models.utils import is_column_binary
from bungeni.utils import register, naming, common
from bungeni.ui.interfaces import IVocabularyTextField, ITreeVocabulary
from bungeni.capi import capi

import transaction
import pika

# local thread storage
thread_locals = threading.local()

# timer delays in setting up serialization workers
INITIAL_DELAY = 10
MAX_DELAY = 900
TIMER_DELAYS = {
    "serialize_setup": INITIAL_DELAY
}

def make_key(length=64):
    """generate random key using letters"""
    return "".join(
        [ random.choice(string.letters) for i in xrange(length) ])

def setupStorageDirectory(part_target="xml_db"):
    """ Returns path to store xml files.
    """
    store_dir = __file__
    x = ""
    while x != "src":
        store_dir, x = os.path.split(store_dir)
    store_dir = os.path.join(store_dir, "parts", part_target)
    if os.path.exists(store_dir):
        assert os.path.isdir(store_dir)
    else:
        try:
            os.mkdir(store_dir)
        except OSError:
            # assume some other code created directory
            assert(os.path.exists(store_dir))
    
    return store_dir


def get_origin_chamber(context):
    """get the chamber applicable to this object
    !+UPGRADE_NOTE(ah, 2014-10-01) this API needs to be deprecated
    and its use-case merged with bungeni.models.utils.get_chamber_for_context
    """
    chamber_id = getattr(context, "chamber_id", None)
    if not chamber_id:
        group_id = getattr(context, "group_id", None)
        if group_id:
            group = Session().query(domain.Group).get(group_id)
            # The top-most group is a legislature now, not a 
            # chamber, but we are interested only in the chamber
            # container.
            while not isinstance(group, domain.Chamber):
                group = Session().query(
                    domain.Group).get(group.parent_group_id)
            if isinstance(group, domain.Chamber):
                chamber_id = group.group_id
        if not chamber_id:
            if hasattr(context, "head_id") and context.head_id:
                return get_origin_chamber(context.head)
    return chamber_id

def generate_random_filename():
    """
    Generates a random string, which is used to uniquely suffix the 
    serialized file name. The problem with using just obj-xx.xml file names is
    that they are not unique per message. For instance, an object can go 
    through multiple transitions,and each generates a separate serialize 
    message, but the same serialized file. As the exist sync process is 
    independent of of the serialize process the message may be out of sync 
    with the file being processed
    """
    import base64
    import uuid
    return base64.urlsafe_b64encode(uuid.uuid4().bytes)

#!+REFACTORING(mb, Mar-2013) This can be made more general to work in
# other instances
class memoized(object):
    """Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    adapted from http://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
    
    Since serialize functions are run in threads, we use a thread local as 
    a cache.
    """
    def __init__(self, func):
        self.func = func
    def __call__(self, *args, **kwargs):
        # check if a thread locals cache has been set up
        if not hasattr(thread_locals, "serialize_cache"):
            return self.func(*args, **kwargs)
        key_args = (args[0], kwargs.get("root_key"))
        if not isinstance(key_args, collections.Hashable):
            # uncacheable. a list, for instance.
            # better to not cache than blow up.
            return self.func(*args, **kwargs)
        if key_args in thread_locals.serialize_cache:
            return thread_locals.serialize_cache[key_args]
        else:
            value = self.func(*args, **kwargs)
            thread_locals.serialize_cache[key_args] = value
            return value
    def __repr__(self):
        return self.func.__repr__()

    def __get__(self, obj, objtype):
        return functools.partial(self.__call__, obj)

class _PersistFiles(object):
    """save files in the serialization hierarchy"""
    _saved_files = {}
    
    def get_files(self, root_key):
        return self._saved_files.get(root_key, [])
    
    def clear_files(self, root_key):
        if self._saved_files.has_key(root_key):
            del self._saved_files[root_key]
    
    def store_file(self, context, parent, key, root_key):
        """Store file.
        Skipped if file is serialized elsewhere (other serializable context).
        This ensures attachments are not serialized multiple times in document
        hierarchies.
        """
        if not(parent and interfaces.ISerializable.providedBy(context)):
            content = getattr(context, key, None)
            if content:
                bfile = tmp(delete=False)
                bfile.write(content)
                bfile.flush()
                bfile.close()
                file_name = os.path.basename(bfile.name)
                if not self._saved_files.has_key(root_key):
                    self._saved_files[root_key] = []
                self._saved_files[root_key].append(bfile.name)
                return file_name
PersistFiles = _PersistFiles()

getter_lock = threading.RLock()
class _LockStore(object):
    """instance of this stores all locks if module is loaded"""
    locks = {}
    
    def get_lock(self, lock_name):
        with getter_lock:
            if not self.locks.has_key(lock_name):
                self.locks[lock_name] = threading.RLock()
            return self.locks.get(lock_name)
LockStore = _LockStore()

def remove_files(paths):
    """delete files generated/left over after serialization"""
    rm_files = [ path for path in paths if os.path.exists(path) ]
    map(os.remove, rm_files)

def publish_to_xml(context):
    """Generates XML for object and saves it to the file. If object contains
    attachments - XML is saved in zip archive with all attached files. 
    """
    context = zope.security.proxy.removeSecurityProxy(context)
    obj_type = IWorkflow(context).name
    #locking
    random_name_sfx = generate_random_filename()
    context_file_name = "%s-%s" % (stringKey(context), random_name_sfx)
    #lock_name = "%s-%s" %(obj_type, context_file_name)
    #!+LOCKING(AH, 25-01-2014) disabling file locking
    #! locking was reqiured when the serializer used ta constant file name
    #! for an object. Now serialized file names are unique, and non repeated
    #with LockStore.get_lock(lock_name):
    #    
    #root key (used to cache files to zip)
    root_key = make_key()
    # create a fake interaction to ensure items requiring a participation
    # are serialized 
    #!+SERIALIZATION(mb, Jan-2013) review this approach
    try:
        zope.security.management.getInteraction()
    except zope.security.interfaces.NoInteraction:
        principal = zope.security.testing.Principal("user", "manager", ())
        zope.security.management.newInteraction(create_participation(principal))
    include = []
    # data dict to be published
    data = {}
    if IFeatureVersion.providedBy(context):
        include.append("versions")
    if IFeatureEvent.providedBy(context):
        include.append("event")
    
    exclude = ["data", "event", "attachments"]
    updated_dict = obj2dict(context, 1, 
	    parent=None,
	    include=include,
	    exclude=exclude,
	    root_key=root_key
        )
    data.update(
        updated_dict
    )

    tags = IStateController(context).get_state().tags
    if tags:
        data["tags"] = tags
    permissions = get_object_state_rpm(context).permissions
    data["permissions"] = get_permissions_dict(permissions)

    # setup path to save serialized data
    path = os.path.join(setupStorageDirectory(), obj_type)
    log.info("Setting up path to write to : %s", path)
    if not os.path.exists(path):
        #
        # !+THREADSAFE(AH, 2014-09-24) making makedirs threadsafe, 
        # sometimes between checking for existence and execution 
        # of makedirs() the folder has already been created by 
        # another thread
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                log.info("Error Folder : %s already exists, ignoring exception ", path)
            else:
                raise

    # xml file path
    file_path = os.path.join(path, context_file_name) 
    # files to zip
    files = []

    if IFeatureAttachment.providedBy(context):
        attachments = getattr(context, "attachments", None)
        if attachments:
	    data["attachments"] = []
	    for attachment in attachments:
	        # serializing attachment
	        attachment_dict = obj2dict(attachment, 1,
	            parent=context,
	            exclude=["data", "event", "versions"])
	        # saving attachment to tmp
	        attached_file = tmp(delete=False)
	        attached_file.write(attachment.data)
	        attached_file.flush()
	        attached_file.close()
	        files.append(attached_file.name)
	        attachment_dict["saved_file"] = os.path.basename(
	            attached_file.name
	        )
	        data["attachments"].append(attachment_dict)

    # add explicit origin chamber for this object (used to partition data
    # in if more than one chamber exists)
    
    if obj_type == "Legislature":
        data["origin_chamber"] = None
    else:
        data["origin_chamber"] = get_origin_chamber(context)

    # add any additional files to file list
    files = files + PersistFiles.get_files(root_key)
    # zipping xml, attached files plus any binary fields
    # also remove the temporary files
    if files:
        # generate temporary xml file
        temp_xml = tmp(delete=False)
        temp_xml.write(serialize(data, name=obj_type))
        temp_xml.close()
        # write attachments/binary fields to zip
        with  ZipFile("%s.zip" % (file_path), "w") as zip_file:
	    for f in files:
	        zip_file.write(f, os.path.basename(f))
	    # write the xml
	    zip_file.write(temp_xml.name, "%s.xml" % os.path.basename(file_path))
        files.append(temp_xml.name)
    else:
        # save serialized xml to file
        with open("%s.xml" % (file_path), "w") as xml_file:
	    xml_file.write(serialize(data, name=obj_type))
	    xml_file.close()
    # publish to rabbitmq outputs queue
    connection = bungeni.core.notifications.get_mq_connection()
    if not connection:
        return
    channel = connection.channel()
    #channel.confirm_delivery()
    publish_file_path = "%s.%s" %(file_path, ("zip" if files else "xml"))
    #channel_delivery = 
    channel.basic_publish(
        exchange=SERIALIZE_OUTPUT_EXCHANGE,
        routing_key=SERIALIZE_OUTPUT_ROUTING_KEY,
        body=simplejson.dumps({"type": "file", "location": publish_file_path }),
        properties=pika.BasicProperties(content_type="text/plain",
            delivery_mode=2
        )
    )
    #if channel_delivery:
    #    log.info("Message published to exchange %s with key %s for %s" % 
    #        (SERIALIZE_OUTPUT_EXCHANGE, SERIALIZE_OUTPUT_ROUTING_KEY, publish_file_path))
    #else:
    #    log.error("Message publication failed for %r", publish_file_path)
        

    #clean up - remove any files if zip was/was not created
    if files:
        files.append("%s.%s" %(file_path, "xml"))
    else:
        files.append("%s.%s" %(file_path, "zip"))
    remove_files(files)

    # clear the cache
    PersistFiles.clear_files(root_key)


def serialize(data, name="object"):
    """ Serializes dictionary to xml.
    """
    content_elem = Element("contenttype")
    content_elem.attrib["name"] = name 
    _serialize(content_elem, data)
    tree = ElementTree(content_elem)
    f = StringIO()
    tree.write(f, "UTF-8")
    return f.getvalue()


def _serialize(parent_elem, data):
    if isinstance(data, (list, tuple)):
        _serialize_list(parent_elem, data)
    elif isinstance(data, dict):
        _serialize_dict(parent_elem, data)
    else:
        parent_elem.attrib["name"] = parent_elem.tag
        parent_elem.tag = "field"
        if not isinstance(data, unicode):
            try:
                data = unicode(data)
            except UnicodeDecodeError:
                data = "Unknown Value (Error)"
                log.error("Decode error in property: %s", parent_elem.tag)
        parent_elem.text = data


def _serialize_list(parent_elem, data_list):
    for i in data_list:
        item_elem = Element(naming.singular(parent_elem.tag))
        parent_elem.append(item_elem)
        _serialize(item_elem, i)


def _serialize_dict(parent_elem, data_dict):
    if data_dict.has_key("displayAs"):
        parent_elem.tag = "field"
        parent_elem.attrib["name"] = data_dict.get("name")
        parent_elem.attrib["displayAs"] = data_dict.get("displayAs")
        data = data_dict.get("value")
        if not isinstance(data, unicode):
            data = unicode(data)
        parent_elem.text = data
        return
    for k, v in data_dict.iteritems():
        key_elem = Element(k)
        parent_elem.append(key_elem)
        _serialize(key_elem, v)

# notifications setup for serialization
SERIALIZE_QUEUE = "bungeni_serialization_queue"
SERIALIZE_EXCHANGE = "bungeni_serialization_exchange"
SERIALIZE_ROUTING_KEY = "bungeni_serialization"
SERIALIZE_OUTPUT_QUEUE = "bungeni_serialization_output_queue"
SERIALIZE_OUTPUT_EXCHANGE = "bungeni_serialization_output_exchange"
SERIALIZE_OUTPUT_ROUTING_KEY = "bungeni_serialization_output"

SERIALIZE_FAILURE_TEMPLATE = """
There was an error while serializing a document: 

Object:
%(obj)s

Original AMQP message: 
%(message)s

Error:
%(error)s

- Bungeni
"""

def notify_serialization_failure(template, **kw):
    log.debug("notify_serialization_failure / %s / %s", template, kw)
    # !+DISABLING to see if the observed delays when running with only the db 
    # are actually caused by this
    return
    email_settings = settings.EmailSettings(common.get_application())
    recipients = [ email_settings.default_sender ]    
    if template:
        body_text = template % kw
    else:
        body_text = kw.get("body")
    msg_event = NotificationEvent({
        "recipients": recipients,
        "body": body_text, 
        "subject": kw.get("subject", "Serialization Failure")
    })
    zope.event.notify(msg_event)


def serialization_notifications_callback(channel, method, properties, body):
    """Publish an object to XML on receiving AMQP message
    """
    # set up thread local cache
    thread_locals.serialize_cache = {}
    obj_data = simplejson.loads(body)
    obj_type = obj_data.get("obj_type")
    domain_model = getattr(domain, obj_type, None)
    if domain_model:
        obj_key = valueKey(obj_data.get("obj_key"))
        session = Session()
        obj = session.query(domain_model).get(obj_key)
        if obj:
            try:
                publish_to_xml(obj)
            except Exception, e:
                ex_type, ex, tb = sys.exc_info()
                log.warn("Error while publish_to_xml : %r", traceback.format_tb(tb))
                log.warn("Error info type: %s, obj_key: %s, obj: %s", obj_type, obj_key, obj)
                # requeue, usually fails becuase of an object introspection timeout
                # so we simply retry
                channel.basic_reject(delivery_tag=method.delivery_tag,
                    requeue=True
                )
                notify_serialization_failure(SERIALIZE_FAILURE_TEMPLATE,
                    obj=obj, message=obj_data, error=e)
            else:
                # no exceptions so acknowledge the message
                channel.basic_ack(delivery_tag=method.delivery_tag)
        else:
            log.error("Could not query object of type %s with key %s. "
                "Check database records - Rejecting message.",
                domain_model, obj_key
            )
            # reject the message
            channel.basic_reject(delivery_tag=method.delivery_tag,
                requeue=False
            )
        session.close()
    else:
        log.error("Failed to get class in bungeni.models.domain named %s",
            obj_type
        )
    # clear thread local cache
    del thread_locals.serialize_cache

def serialization_worker():
    connection = bungeni.core.notifications.get_mq_connection()
    if not connection:
        return
    channel = connection.channel()
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(serialization_notifications_callback, 
        queue=SERIALIZE_QUEUE)
    channel.start_consuming()


class SerializeThread(threading.Thread):
    """This thread will respawn after n seconds if it crashes
    """
    is_running = True
    daemon = True
    def run(self):
        while self.is_running:
            try:
                super(SerializeThread, self).run()
            except Exception, e:
                log.error("Exception in thread %s: %s", self.name, e)
                delay = TIMER_DELAYS[self.name]
                if delay > MAX_DELAY:
                    num_attempts = int(math.log((delay/10), 2));
                    log.error("Giving up re-spawning serialization " 
                        "worker after %d seconds (%d attempts).", 
                        delay, num_attempts
                    )
                    notify_serialization_failure(None,
                        subject="Notice - Bungeni Serialization Workers",
                        body="Unable to restart serialization worker. "
                            "Please check the Bungeni logs.")
                else:
                    log.info("Attempting to respawn serialization "
                        "consumer in %d seconds", delay
                    )
                    next_delay = delay * 2
                    timer = threading.Timer(delay, init_thread, [], 
                        {"delay": next_delay })
                    timer.daemon = True
                    timer.start()
                self.is_running = False
                del TIMER_DELAYS[self.name]

def init_thread(*args, **kw):
    log.info("Initializing serialization consumer thread...")
    delay = kw.get("delay", INITIAL_DELAY)
    task_thread = SerializeThread(target=serialization_worker)
    task_thread.start()
    TIMER_DELAYS[task_thread.name] = delay
    return task_thread
    

def batch_serialize(type_key="*", start_date=None, end_date=None):
    """Serialize all objects of `type_key` or all types if with a
    wildcard(*) as the type key.
    Item set may be filtered by status date (start_date and/or end date)
    range.
    """
    # keep count of serialized objects for feedback
    serialized_count = 0
    # list of domain classes to be serialized
    domain_models = []
    if type_key == "*":
        types_vocab = get_vocabulary("serializable_type")
        # we add the legislature and the chamber first
        for term in types_vocab(None):
            if term.value in ("legislature", "chamber"):
                info = capi.get_type_info(term.value)
                domain_models.append(info.domain_model)
        # we add the rest now
        for term in types_vocab(None):
            if term.value == "*": 
                continue
            if term.value not in ("legislature", "chamber"):
                info = capi.get_type_info(term.value)
                domain_models.append(info.domain_model)
    else:
        info = capi.get_type_info(type_key)
        if info.workflow:
            domain_models.append(info.domain_model)
    session = Session()
    for domain_model in domain_models:
        query = session.query(domain_model)
        if IWorkflowed.implementedBy(domain_model) and (start_date or end_date):
            column = domain_model.status_date
            if start_date and end_date:
                expression = sql.between(column, start_date, end_date)
            elif start_date:
                expression = (column>=start_date)
            elif end_date:
                expression = (column<=end_date)
            query = query.filter(expression)
        objects = query.all()
        # !+FILTER(ah, 2014-09-19) adding a filter here - sometimes there is a mismatch
        # between the count shown on the screen i.e. X items sent for serialization and 
        # and only X-n items appear in the queue - there seem to be empty objects returned
        # sometimes, so eliminating those
        objects = filter(None, objects)
        map(queue_object_serialization, objects)
        log.error(" COUNTING_TYPES_SERIALIZED -- %s COUNT -- %s", domain_model, len(objects))
        serialized_count += len(objects)
    return serialized_count

def get_serializable_parent(obj):
    """Get serializable parent object
    """
    if hasattr(obj, "head") and interfaces.IDoc.providedBy(obj.head):
        serializable_head = get_serializable_parent(obj.head)
        if serializable_head:
            queue_object_serialization(serializable_head)
    serializable_obj = None
    if not interfaces.ISerializable.providedBy(obj):
        parent = obj
        while not interfaces.ISerializable.providedBy(parent):
            parent = (parent.__parent__ 
                if hasattr(parent, "__parent__") else None)
            if not parent:
                break
        if parent:
            serializable_obj = parent
    else:
        serializable_obj = obj
    return serializable_obj

@register.handler(adapts=(IVersionCreatedEvent,))
def serialization_version_event_handler(event):
    """Queues workflowed objects when a version is created.
    """
    # we only want to serialize manually created versions
    if event.object.procedure == "m":
        serializable_obj = get_serializable_parent(event.object.head)
        if serializable_obj:
            queue_object_serialization(serializable_obj)

@register.handler(adapts=(interfaces.ISerializable, IObjectCreatedEvent))
@register.handler(adapts=(interfaces.ISerializable, IObjectModifiedEvent))
@register.handler(adapts=(interfaces.ISerializable, ITranslationCreatedEvent))
def serialization_event_handler(obj, event):
    """queues workflowed objects when created or modified"""
    queue_object_serialization(obj)

@register.handler(adapts=(IAlchemistContent, IObjectCreatedEvent))
@register.handler(adapts=(IAlchemistContent, IObjectModifiedEvent))
def serialization_event_handler_parent(obj, event):
    """queues serialization of serializable parent (if any)"""
    serializable_obj = get_serializable_parent(obj)
    if serializable_obj is not None:
        queue_object_serialization(serializable_obj)

def queue_object_serialization(obj):
    """Send a message to the serialization queue for non-draft documents
    """
    connection = bungeni.core.notifications.get_mq_connection()
    
    if not connection:
        log.error("Could not get rabbitmq connection. Will not send "
            "AMQP message for this change."
        )
        log.error("Serialization failure for item %r", obj)
        ## If there is no connection MQ dont publish at all !!! !+MQ(ah, 2014-09-19)
        """
        log.warn("Publishing XML directly - this will slow things down")
        try:
            publish_to_xml(obj)
        except Exception, e:
            notify_serialization_failure(SERIALIZE_FAILURE_TEMPLATE,
                obj=obj, message="", error=e)
            notify_serialization_failure(None, 
                body="Failed to find running RabbitMQ",
                subject="Notice - RabbitMQ")
        notify_serialization_failure(None, 
            body="Failed to find running RabbitMQ",
            subject="Notice - RabbitMQ")
        return
        """
    wf_state = None
    try:
        wfc = IWorkflowController(obj)
        wf_state = wfc.state_controller.get_state()
    except InvalidStateError:
        # this is probably a draft document - skip queueing
        log.warn("Could not get workflow state for object %s. "
            "State: %s ; this could be a document in draft state", 
            obj, wf_state)
        return
    unproxied = zope.security.proxy.removeSecurityProxy(obj)
    mapper = object_mapper(unproxied)
    primary_key = mapper.primary_key_from_instance(unproxied)
    # !+CAPI(mb, Aug-2012) capi lookup in as at r9707 fails for some keys
    # e.g. get_type_info(instance).workflow_key resolves while 
    # get_type_info(same_workflow_key) raises KeyError
    message = {
        "obj_key": primary_key,
        "obj_type": unproxied.__class__.__name__
    }
    kwargs = dict(
        exchange=SERIALIZE_EXCHANGE,
        routing_key=SERIALIZE_ROUTING_KEY,
        body=simplejson.dumps(message),
        properties=pika.BasicProperties(
            content_type="text/plain",
            delivery_mode=2
        )
    )
    txn = transaction.get()
    log.error("AACH key: %s , type : %s", primary_key, unproxied.__class__)
    txn.addAfterCommitHook(bungeni.core.notifications.post_commit_publish, (), kwargs)
 
    
def serialization_notifications():
    """Set up bungeni serialization worker as a daemon.
    """
    mq_utility = zope.component.getUtility(IMessageQueueConfig)
    connection = bungeni.core.notifications.get_mq_connection()
    if not connection:
        # delay
        delay = TIMER_DELAYS["serialize_setup"]
        if delay > MAX_DELAY:
            log.error("Could not set up amqp workers - No rabbitmq " 
            "connection found after %d seconds.", delay)
        else:
            log.info("Attempting to setup serialization AMQP consumers "
                "in %d seconds", delay
            )
            timer = threading.Timer(TIMER_DELAYS["serialize_setup"],
                serialization_notifications
            )
            timer.daemon = True
            timer.start()
            TIMER_DELAYS["serialize_setup"] *= 2
        return
    channel = connection.channel()
    # create exchange
    channel.exchange_declare(exchange=SERIALIZE_EXCHANGE,
        type="fanout", durable=True)
    channel.queue_declare(queue=SERIALIZE_QUEUE, 
        durable=True,
    )
    channel.queue_bind(queue=SERIALIZE_QUEUE,
        exchange=SERIALIZE_EXCHANGE,
        routing_key=SERIALIZE_ROUTING_KEY)
    # xml outputs channel and queue
    channel.exchange_declare(exchange=SERIALIZE_OUTPUT_EXCHANGE,
        type="direct", passive=False)
    channel.queue_declare(queue=SERIALIZE_OUTPUT_QUEUE, 
        durable=True, exclusive=False, auto_delete=False)
    channel.queue_bind(queue=SERIALIZE_OUTPUT_QUEUE,
        exchange=SERIALIZE_OUTPUT_EXCHANGE,
        routing_key=SERIALIZE_OUTPUT_ROUTING_KEY)
    worker_threads = []
    for i in range(mq_utility.get_number_of_workers()):
        a_thread = init_thread()
        worker_threads.append(a_thread)
    return worker_threads

# serialization utilities

import collections
import zope.component
import zope.schema as schema
from zope.dublincore.interfaces import IDCDescriptiveProperties
from sqlalchemy.orm import RelationshipProperty, ColumnProperty
from bungeni.alchemist import utils
from bungeni.alchemist.interfaces import IAlchemistContainer
from bungeni import translate


def get_permissions_dict(permissions):
    results= []
    for x in permissions:
        # !+XML pls read the styleguide
        results.append({"role": x[2], 
            "permission": x[1], 
            "setting": x[0] and "Allow" or "Deny"})
    return results


INNER_EXCLUDES = ["changes", "image", "change",  "logo_data", "saved_file"]
@memoized
def obj2dict(obj, depth, parent=None, include=[], exclude=[], lang=None, root_key=None):
    """ Returns dictionary representation of a domain object.
    """
    if lang is None:
        lang = getattr(obj, "language", capi.default_language)
    result = {}
    obj = zope.security.proxy.removeSecurityProxy(obj)
    descriptor = None
    if IAlchemistContent.providedBy(obj):
        try:
            descriptor = utils.get_descriptor(obj)
        except KeyError:
            log.error("Could not get descriptor for IAlchemistContent %r", obj)
        
        if parent is not None and IWorkflowed.providedBy(obj):
            permissions = get_object_state_rpm(obj).permissions
            result["permissions"] = get_permissions_dict(permissions)
            result["tags"] = IStateController(obj).get_state().tags
        
    # Get additional attributes
    for name in include:
        value = getattr(obj, name, None)
        if value is None:
            continue
        if not name.endswith("s"):
            name += "s"
        if isinstance(value, collections.Iterable):
            res = []
            # !+ allowance for non-container-api-conformant alchemist containers
            if IAlchemistContainer.providedBy(value):
                value = value.values()
            for item in value:
                i = obj2dict(item, 0, lang=lang, root_key=root_key)
                res.append(i)
            result[name] = res
        else:
            result[name] = value
    
    # Get mapped attributes
    seen_keys = []
    mapper = class_mapper(obj.__class__)
    for mproperty in mapper.iterate_properties:
        if mproperty.key.startswith("_vp"):
            #skip vertical props
            continue
        if mproperty.key in exclude:
            continue
        seen_keys.append(mproperty.key)
        value = getattr(obj, mproperty.key)
        if value == parent:
            continue
        if value is None:
            continue
        
        if isinstance(mproperty, RelationshipProperty) and depth > 0:
            if isinstance(value, collections.Iterable):
                result[mproperty.key] = []
                for item in value:
                    # !+DEPTH(ah, 2014-09-19) depth was set to 1 here, this causes 
                    # a very deep branching for upper level groups like legislature and chamber
                    # and legislature times out occasionally. Doesnt seem neccessary to go depth=1
                    # for child objects, because they get serialized independently anyway, changing
                    # depth to depth-1 so all dependent objects are iterated 1 level lower than the 
                    # parent.
                    # UPDATE(ah, 2014-11-03) Item Schedule is an exceptional case of an object 
                    # whose context is within a parent container but is not visible outside of the sitting
                    # it is not a type defined in types.xml and does not have its own 
                    # wokflow so we need to handle that in a unique way
                    # we don't decrement the depth and instead process it as is 
                    active_depth = depth
                    if item.__class__.__name__ == "ItemSchedule":
                        active_depth = depth
                    else:
                        active_depth = depth-1
                    result[mproperty.key].append(
                         obj2dict(
                            item,
                            active_depth, 
                            parent=obj,
                            include=["owner", "item_schedule", "item_schedule_discussion"],
                            exclude=exclude + INNER_EXCLUDES,
                            lang=lang,
                            root_key=root_key
                         )
                    )
            else:
                result[mproperty.key] = obj2dict(value, depth-1, 
                    parent=obj,
                    include=["owner"],
                    exclude=exclude + INNER_EXCLUDES,
                    lang=lang,
                    root_key=root_key
                )
        else:
            if isinstance(mproperty, RelationshipProperty):
                continue
            elif isinstance(mproperty, ColumnProperty):
                columns = mproperty.columns
                if len(columns) == 1:
                    if is_column_binary(columns[0]):
                        fname = PersistFiles.store_file(obj, parent, 
                            columns[0].key, root_key)
                        if fname:
                            result[columns[0].key] = dict(saved_file=fname)
                        continue
            if descriptor:
                columns = mproperty.columns
                is_foreign = False
                if len(columns) == 1:
                    if len(columns[0].foreign_keys):
                        is_foreign = True
                if (not is_foreign) and (mproperty.key in descriptor.keys()):
                    field = descriptor.get(mproperty.key)
                    if (field and field.property and
                            (schema.interfaces.IChoice.providedBy(field.property) or
                                IVocabularyTextField.providedBy(field.property))
                        ):
                        factory = field.property.vocabulary or field.property.source
                        if factory is None:
                            vocab_name = getattr(field.property, "vocabularyName", None)
                            factory = get_vocabulary(vocab_name)
                        # !+VOCABULARIES(mb, aug-2012)some vocabularies
                        # expect an interaction to generate values
                        # todo - update these vocabularies to work 
                        # with no request e.g. in notification threads
                        display_name = None
                        try:
                            vocabulary = factory(obj)                             
                            # handle vdex hierarchical terms
                            if ITreeVocabulary.providedBy(factory):
                                values = value.splitlines()
                                term_values = []
                                for val in values:
                                    term_values.append(dict(
                                            name=mproperty.key,
                                            value=val,
                                            displayAs=factory.getTermCaption(
                                                factory.getTermById(val), lang=lang)))
                                result[mproperty.key] = term_values
                                continue
                            term = vocabulary.getTerm(value)
                            if lang:
                                if hasattr(factory, "getTermCaption"):
                                    display_name = factory.getTermCaption(
                                            factory.getTermById(value), lang=lang)
                                else:
                                    display_name = translate(
                                        term.title or term.value,
                                        target_language=lang,
                                        domain="bungeni")
                            else:
                                display_name = term.title or term.value
                        except zope.security.interfaces.NoInteraction:
                            log.error("This vocabulary %s expects an interaction "
                                "to generate terms.", factory)
                            # try to use dc adapter lookup
                            try:
                                _prop = mapper.get_property_by_column(
                                    mproperty.columns[0])
                                _prop_value = getattr(obj, _prop.key)
                                dc = IDCDescriptiveProperties(_prop_value, None)
                                if dc:
                                    display_name = IDCDescriptiveProperties(
                                            _prop_value).title
                            except KeyError:
                                log.warn("No display text found for %s on " 
                                    "object %s. Unmapped in orm.",
                                    property.key, obj)
                        except Exception, e:
                            log.error("Could not instantiate vocabulary %s. "
                                "Exception: %s", factory, e)
                        finally:
                            # fallback we cannot look up vocabularies/dc
                            if display_name is None:
                                if not isinstance(value, unicode):
                                    display_name = unicode(value)
                        if display_name is not None:
                            result[mproperty.key] = dict(
                                name=mproperty.key,
                                value=value,
                                displayAs=display_name)
                            continue
            result[mproperty.key] = value
    
    extended_props = []
    seen_keys.extend(INNER_EXCLUDES)
    for prop_name, prop_type in obj.__class__.extended_properties:
        try:
            if prop_type == domain.vp.Binary:
                fname=PersistFiles.store_file(obj, parent, prop_name, root_key)
                if fname:
                    result[prop_name] = dict(saved_file=fname)
            else:
                result[prop_name] = getattr(obj, prop_name)
            extended_props.append(prop_name)
        except zope.security.interfaces.NoInteraction:
            log.error("Extended property %s requires an interaction.",
                prop_name)

    
    # any additional attributes - this allows us to capture any derived attributes
    seen_keys.extend(include + exclude + extended_props)
    if IAlchemistContent.providedBy(obj):
        try:
            domain_schema = utils.get_derived_table_schema(type(obj))
            known_names = [ k for k, d in 
                domain_schema.namesAndDescriptions(all=True) ]
            extra_properties = set(known_names).difference(set(seen_keys))
            seen_keys.extend(extra_properties)
            for prop_name in extra_properties:
                try:
                    result[prop_name] = getattr(obj, prop_name)
                except zope.security.interfaces.NoInteraction:
                    log.error("Attribute %s requires an interaction.", prop_name)
        except KeyError:
            log.warn("Could not find table schema for %s", obj)
    
    # any other properties defined on class
    props = inspect.getmembers(type(obj), 
        predicate=lambda mm:isinstance(mm, property))
    extra_props = set([p for p, v in props]).difference(seen_keys)
    for prop in extra_props:
        if prop.startswith("_"):
            continue
        # play it safe if lookup fails and log exception
        try:
            val = getattr(obj, prop)
            if isinstance(val, (basestring, int)):
                result[prop] = getattr(obj, prop)
        except Exception, e:
            log.debug("Could not fetch property %s on object %s: %s",
                prop, obj, e)
    return result

