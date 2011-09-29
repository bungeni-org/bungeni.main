# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

""" Utilities to serialize objects to XML
"""
from StringIO import StringIO
from xml.etree.cElementTree import Element, ElementTree
from zope.security.proxy import removeSecurityProxy
from sqlalchemy.orm import RelationshipProperty, class_mapper 
import collections

from zipfile import ZipFile
from zope.securitypolicy.interfaces import IPrincipalRoleMap

import traceback
import sys
import os

custom = {
    "signatory": "signatories",
}

def setupStorageDirectory(part_target="xml_db"):
    # TODO: this is probably going to break with package restucturing
    store_dir = __file__
    x = 0
    while x < 5:
        x += 1
        store_dir = os.path.split(store_dir)[0]
    store_dir = os.path.join(store_dir, 'parts', part_target)
    if os.path.exists(store_dir):
        assert os.path.isdir(store_dir)
    else:
        os.mkdir(store_dir)
    
    return store_dir

def publish_to_xml(context, type='', include=['event','versions']):
    """ Generates XML for object and saves it to the file. If object contains
        attachments - XML is saved in zip archive with all attached files. 
    """
    try:
        context = removeSecurityProxy(context)
        data = obj2dict(context,1,parent=None,include=include,exclude=['file_data', 'image', 'logo_data','event_item'])
        if not type:
            type = context.type
            data['permissions']= []
            map = IPrincipalRoleMap(context)
            for x in list(map.getPrincipalsAndRoles()):
                data['permissions'].append({'role':x[0], 'user':x[1], 'permission':x[2].getName()})
            
        files = []
        path = os.path.join(setupStorageDirectory(), type)
        if not os.path.exists(path):
            os.makedirs(path)
        file_path = os.path.join(path,context.__name__)
        files.append(file_path+'.xml') 
        with open(file_path+'.xml','w') as file:
            file.write(serialize(data, name=type))
        try:
            if len(context.attached_files) > 0:
                for attachment in context.attached_files:
                    attachment_path = os.path.join(path, attachment.file_name)
                    files.append(attachment_path)
                    with open(os.path.join(path, attachment.file_name), 'wb') as file:
                        file.write(attachment.file_data)
                zip = ZipFile(file_path+'.zip', 'w')
                for file in files:
                    zip.write(file, os.path.split(file)[-1])
                    os.remove(file)
                zip.close()
        except AttributeError:
            pass
    except:
        traceback.print_exception(*sys.exc_info())

def singular(pname):
    """Get the english singular of (plural) name.
    """
    for sname in custom:
        if custom[sname] == pname:
            return sname
    if pname.endswith("ses"):
        return pname[:-2]
    if pname.endswith("s"):
        return pname[:-1]
    return pname

def serialize(data, name='object'):
    content_elem = Element('contenttype')
    content_elem.attrib['name'] = name 
    _serialize(content_elem, data)
    tree = ElementTree(content_elem)
    f = StringIO()
    tree.write(f, 'UTF-8')
    return f.getvalue()

def _serialize(parent_elem, data):
    if isinstance(data, (list, tuple)):
        _serialize_list(parent_elem, data)
    elif isinstance(data, dict):
        _serialize_dict(parent_elem, data)
    else:
        parent_elem.attrib['name'] = parent_elem.tag
        parent_elem.tag = 'field'
        parent_elem.text = unicode(data)

def _serialize_list(parent_elem, data_list):
    for i in data_list:
        item_elem = Element(singular(parent_elem.tag))
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
    try:
        # Get additional attributes
        for name in include:
            value = getattr(obj, name)
            if not name.endswith('s'): name += 's'
            if isinstance(value, collections.Iterable):
                res = []
                for item in value.values():
                    res.append(obj2dict(item, 0))
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
                        result[property.key].append(obj2dict(item, depth-1, parent=obj,include=[],exclude=exclude+['changes',]))
                else:
                    result[property.key] = obj2dict(value, depth-1, parent=obj,include=[],exclude=exclude+['changes',])
            else:
                if isinstance(property, RelationshipProperty):
                    continue
                result[property.key] = value
    except:
        traceback.print_exception(*sys.exc_info())
    return result