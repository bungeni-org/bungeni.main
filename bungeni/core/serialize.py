# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

""" Utilities to serialize objects to XML

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.serialize")

from zope.security.proxy import removeSecurityProxy
from zope.lifecycleevent import IObjectModifiedEvent, IObjectCreatedEvent
from sqlalchemy.orm import RelationshipProperty, ColumnProperty, class_mapper
from sqlalchemy.types import Binary

from bungeni.alchemist.container import stringKey
from bungeni.alchemist.interfaces import IAlchemistContainer
from bungeni.core.workflow.states import (get_object_state_rpm, 
    get_head_object_state_rpm
)
from bungeni.core.workflow.interfaces import (IWorkflow, IStateController,
    IWorkflowed, IWorkflowController, InvalidStateError
)
from bungeni.models import interfaces
from bungeni.utils import register, naming

import os
import collections
from StringIO import StringIO
from zipfile import ZipFile
from xml.etree.cElementTree import Element, ElementTree
from tempfile import NamedTemporaryFile as tmp


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
        os.mkdir(store_dir)
    
    return store_dir


def get_permissions_dict(permissions):
    results= []
    for x in permissions:
        # !+XML pls read the styleguide
        results.append({"role": x[2], 
            "permission": x[1], 
            "setting": x[0] and "Allow" or "Deny"})
    return results

@register.handler(adapts=(IWorkflowed, IObjectCreatedEvent))
@register.handler(adapts=(IWorkflowed, IObjectModifiedEvent))
def publish_handler(ob, event):
    try:
        wf_state = IWorkflowController(ob).state_controller.get_state()
        if wf_state and wf_state.publish:
            publish_to_xml(ob)
    except InvalidStateError:
        log.error("Unable to get workflow state for object %s.", ob)
    

def publish_to_xml(context):
    """Generates XML for object and saves it to the file. If object contains
    attachments - XML is saved in zip archive with all attached files. 
    """
    include = []
    # list of files to zip
    files = []
    # data dict to be published
    data = {}
    
    context = removeSecurityProxy(context)
    
    if interfaces.IFeatureVersion.providedBy(context):
        include.append("versions")
    if interfaces.IFeatureAudit.providedBy(context):
        include.append("event")
    
    exclude = ["data", "event", "attachments", "changes"]
    
    # include binary fields and include them in the zip of files for this object
    for column in class_mapper(context.__class__).columns:
        if column.type.__class__ == Binary:
            exclude.append(column.key)
            content = getattr(context, column.key, None)
            if content:
                with tmp(delete=False) as f:
                    f.write(content)
                    files.append(f.name)
                    data[column.key] = dict(saved_file=os.path.basename(f.name))
    
    data.update(
        obj2dict(context, 1, 
            parent=None,
            include=include,
            exclude=exclude
        )
    )
    
    # !+please do not use python builtin names as variable names
    type = IWorkflow(context).name
    
    # !+IWorkflow(context).get_state(context.status).tags
    tags = IStateController(context).get_state().tags
    if tags:
        data["tags"] = tags
    
    permissions = get_object_state_rpm(context).permissions
    data["permissions"] = get_permissions_dict(permissions)
    
    data["changes"] = []
    for change in getattr(context, "changes", []):
        change_dict = obj2dict(change, 0, parent=context)
        change_permissions = get_head_object_state_rpm(change).permissions
        change_dict["permissions"] = get_permissions_dict(change_permissions)
        data["changes"].append(change_dict)
    
    # setup path to save serialized data 
    path = os.path.join(setupStorageDirectory(), type)
    if not os.path.exists(path):
        os.makedirs(path)
    
    # xml file path
    file_path = os.path.join(path, stringKey(context)) 
    
    if interfaces.IFeatureAttachment.providedBy(context):
        attachments = getattr(context, "attachments", None)
        if attachments:
            # add xml file to list of files to zip
            files.append("%s.xml" % (file_path))
            data["attachments"] = []
            for attachment in attachments:
                # serializing attachment
                attachment_dict = obj2dict(attachment, 1,
                    parent=context,
                    exclude=["data", "event", "versions"])
                permissions = get_object_state_rpm(attachment).permissions
                attachment_dict["permissions"] = \
                    get_permissions_dict(permissions)
                # saving attachment to tmp
                with tmp(delete=False) as f:
                    f.write(attachment.data)
                    files.append(f.name)
                    attachment_dict["saved_file"] = os.path.basename(f.name)
                data["attachments"].append(attachment_dict)
    
    # saving xml file
    with open("%s.xml" % (file_path), "w") as file:
        file.write(serialize(data, name=type))
    
    # zipping xml, attached files plus any binary fields
    # also remove the temporary files
    if files:
        zip = ZipFile("%s.zip" % (file_path), "w")
        for f in files:
            zip.write(f, os.path.basename(f))
            os.remove(f)
        zip.close()


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
        parent_elem.text = unicode(data)


def _serialize_list(parent_elem, data_list):
    for i in data_list:
        item_elem = Element(naming.singular(parent_elem.tag))
        parent_elem.append(item_elem)
        _serialize(item_elem, i)


def _serialize_dict(parent_elem, data_dict):
    for k, v in data_dict.iteritems():
        key_elem = Element(k)
        parent_elem.append(key_elem)
        _serialize(key_elem, v)


def obj2dict(obj, depth, parent=None, include=[], exclude=[]):
    """ Returns dictionary representation of an object.
    """
    result = {}
    obj = removeSecurityProxy(obj)
    
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
                i = obj2dict(item, 0)
                if name == "versions":
                    permissions = get_head_object_state_rpm(item).permissions
                    i["permissions"] = get_permissions_dict(permissions)
                res.append(i)
            result[name] = res
        else:
            result[name] = value
    
    # Get mapped attributes
    for property in class_mapper(obj.__class__).iterate_properties:
        if property.key in exclude:
            continue
        value = getattr(obj, property.key)
        if value == parent:
            continue
        if value is None:
            continue
        
        if isinstance(property, RelationshipProperty) and depth > 0:
            if isinstance(value, collections.Iterable):
                result[property.key] = []
                for item in value:
                    result[property.key].append(obj2dict(item, depth-1, 
                            parent=obj,
                            include=[],
                            exclude=exclude + ["changes"]
                    ))
            else:
                result[property.key] = obj2dict(value, depth-1, 
                    parent=obj,
                    include=[],
                    exclude=exclude + ["changes"]
                )
        else:
            if isinstance(property, RelationshipProperty):
                continue
            elif isinstance(property, ColumnProperty):
                columns = property.columns
                if len(columns)==1:
                    if columns[0].type.__class__ == Binary:
                        continue
            result[property.key] = value
    return result

