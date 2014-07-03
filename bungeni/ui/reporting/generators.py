# -*- coding: utf-8 -*-
# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Report generators

See `bungeni.ui.reporting.intefaces.IReportGenerator` for signature

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.reporting")

import os
from copy import deepcopy
import zope.interface
from lxml import etree
from lxml import html
from tidylib import tidy_fragment
from datetime import datetime

from bungeni.alchemist.interfaces import IAlchemistContainer

from bungeni.core.dc import IDCDescriptiveProperties
from bungeni.core.language import get_default_language

from bungeni.ui.utils import common, url, report_tools
from bungeni.ui.reporting.interfaces import IReportGenerator, ReportException
from bungeni.ui.calendar.data import ExpandedSitting
from bungeni import _, translate


BUNGENI_REPORTS_NS = "http://bungeni.org/reports"


def value_repr(val):
    #!+REPORTING(mb, Nov-2012) Representation should reuse descriptor
    # field rendering utilities
    if type(val) == datetime:
        return val.isoformat()
    return val.__str__()

def get_element_value(context, name, default=None):
    if name.startswith("dc:"):
        dc_context = (
            context.sitting if type(context) == ExpandedSitting else context)
        dc_adapter = IDCDescriptiveProperties(dc_context, None)
        if dc_adapter is None:
            log.error("No dublin core adapter found for object %s", context)
            return default
        else:
            try:
                return getattr(dc_adapter, name[3:])
            except AttributeError:
                log.error("Dublin core adapter %s for %s has no attribute %s",
                    dc_adapter, context, name)
                return default
    else:
        try:
            return getattr(context, name)
        except AttributeError:
            log.error("Context %s has no such attribute %s. Check report template",
                context, name)
            return default

def get_config(doctree, name, default=None):
    """Get configuration value from report template"""
    element = doctree.find("{%s}config/%s" % (BUNGENI_REPORTS_NS, name))
    if element is not None:
        return element.text
    return default

def get_attr(element, name, namespace=BUNGENI_REPORTS_NS, default=None):
    """Returns attribute of element from tree"""
    if namespace=="":
        return element.get(name, default)
    return element.get("{%s}%s"  % (namespace, name), default)

def clean_element(element):
    """Clean out bungeni report namespace tags from document"""
    for key in element.keys():
        if BUNGENI_REPORTS_NS in key:
            del element.attrib[key]

def empty_element(element):
    """Remove an element's children from document tree."""
    map(lambda child:element.remove(child), element.getchildren())

def drop_element(element):
    """Remove an element from the document tree"""
    element.getparent().remove(element)

def add_empty_listing_node(listing_node):
    """add an empty node to template output
    """
    no_items_tag = "p"
    no_items_node = etree.Element(no_items_tag)
    no_items_node.text = translate(_(u"No items found"))

    # add to previous element of listing node - then drop it
    prev_element = listing_node.getprevious()
    add_after = None
    if prev_element:
        drop_element(listing_node)
        add_after = prev_element
    else:
        if listing_node.tag in ["tr", "tbody"]:
            parent_table = None
            for prn in listing_node.iterancestors("table"):
                parent_table = prn
                break
            if parent_table is not None:
                # assumption: there's a title element
                add_after = parent_table.getprevious()
                drop_element(parent_table)
    if add_after is not None:
        add_after.addnext(no_items_node)

class _BaseGenerator(object):
    """Base generator class. Child classes implement actual functionality.
    """
    zope.interface.implements(IReportGenerator)
    
    context = None
    configuration = None
    coverage = 168
    title = _(u"Report")
    language = None
    
    def __init__(self, report_template_file, context=None):
        self.report_template_file = report_template_file
        self.context = context
        self.load_configuration()
    
    def load_configuration(self):
        raise NotImplementedError("""Must be implemented by child classes""")
    
    def generate_report(self):
        raise NotImplementedError("""Must be implemented by child classes""")
    
    def publish_report(renderer):
        raise NotImplementedError("""Must be implemented by child classes""")
    
    def persist_report(self):
        raise NotImplementedError("""Must be implemented by child classes""")


class ReportGeneratorXHTML(_BaseGenerator):
    """Generates xHTML for a report of sittings and persists in a 
       `bungeni.models.Report`.
    """
    
    def load_configuration(self):
        """Process report template for configuration
        """
        if os.path.exists(self.report_template_file):
            template_file = open(self.report_template_file)
            file_string = template_file.read()
            self.report_template = etree.fromstring(file_string)
            template_file.close()
            
            self.title = get_config(self.report_template, "title", self.title)
            self.language = get_config(self.report_template, "language",
                get_default_language()
            )
            coverage_text = get_config(self.report_template, "length")
            if coverage_text is not None:
                self.coverage = report_tools.compute_hours(coverage_text)
            drop_element(
                self.report_template.find("{%s}config" % BUNGENI_REPORTS_NS)
            )
        else:
            raise ReportException(
                _(u"report-template-missing",
                    default=u"Report template file does not exist at ${path}",
                    mapping={"path": self.report_template_file}
                )
            )
    
    def generate_report(self, request):
        """Generate report content based on report template and context.
        """
        def process_single_node(node, context, typ, src):
            clean_element(node)
            if typ == "text":
                node.text = value_repr(get_element_value(context, src))
            elif typ == "html":
                raw_value = get_element_value(context, src, "")
                if raw_value:
                    html_element = html.fragments_fromstring("<div>%s</div>" % 
                        tidy_fragment(raw_value)[0]
                    )[0]
                    for (key, value) in node.attrib.iteritems():
                        html_element.attrib[key] = value
                    node.addnext(html_element)
                    node.insert(0, html_element)
            elif type == "link":
                url_src = get_attr(node, "url")
                if url_src:
                    link_url = get_element_value(context, url_src)
                else:
                    link_url = url.absoluteURL(context, request)
                node.attrib["href"] = link_url
                if src:
                    node.text = get_element_value(context, src)
        
        def check_exists(context, prop):
            return bool(get_element_value(context, prop))
        
        def process_document_tree(root, context):
            """Iterate and optionally update children of provided root node.
            
            Rendering is based on type of node. Further calls to this function
            happen when a node with children exists - and so on.
            
            Only nodes with the bungeni namespace tags "br:type" are modified
            with content from the provided context.
            """
            cond = get_attr(root, "condition")
            if cond and not check_exists(context, cond):
                return None
            iter_children = root.getchildren() or [root]
            if not (root in iter_children):
                root_typ = get_attr(root, "type")
                if root_typ:
                    process_single_node(root, context, root_typ, 
                        get_attr(root, "source")
                    )
            for child in iter_children:
                typ = get_attr(child, "type")
                src = get_attr(child, "source")
                cond = get_attr(child, "condition")
                if cond and not check_exists(context, cond):
                    drop_element(child)
                    continue
                children = child.getchildren()
                if len(children) == 0:
                    if typ:
                        process_single_node(child, context, typ, src)
                else:
                    if not typ:
                        process_document_tree(child, context)
                    elif typ == "listing":
                        clean_element(child)
                        children = child.getchildren()
                        listing = get_element_value(context, src, default=[])
                        if IAlchemistContainer.providedBy(listing):
                            listing = [ item for item in 
                                common.list_container_items(listing) 
                            ]
                        len_listing = len(listing)
                        if not len_listing:
                            add_empty_listing_node(child)
                        else:
                            expanded_children = [ deepcopy(children) 
                                for x in range(len_listing)
                            ]
                            empty_element(child)
                            for i, item in enumerate(listing):
                                for inner_element in expanded_children[i]:
                                    iroot = process_document_tree(inner_element, 
                                        item
                                    )
                                    if iroot is not None:
                                        child.append(iroot)
                    elif typ == "block" and src:
                        block_context = get_element_value(context, src, 
                            default=None)
                        process_document_tree(child, block_context)
                    else:
                        process_document_tree(child, context)
            clean_element(root)
            return root
        process_document_tree(self.report_template, self.context)
        return etree.tostring(self.report_template)

    def publish_report(self):
        pass
    
    def persist_report(self):
        pass

