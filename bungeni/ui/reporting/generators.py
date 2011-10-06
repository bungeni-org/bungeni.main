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

from bungeni.alchemist.interfaces import IAlchemistContainer

from bungeni.core.dc import IDCDescriptiveProperties
from bungeni.core.language import get_default_language
from bungeni.core.translation import translate_i18n

from bungeni.ui.i18n import _
from bungeni.ui.utils import common, url, report_tools
from bungeni.ui.reporting.interfaces import IReportGenerator, ReportException

BUNGENI_REPORTS_NS="http://bungeni.org/reports"

def get_element_value(context, name, default=None):
    if name.startswith("dc:"):
        dc_adapter = IDCDescriptiveProperties(context, None)
        if dc_adapter is None:
            log.error("No dublin core adapter found for object %s", context)
            return default
        else:
            try:
                return getattr(dc_adapter, name[3:])
            except AttributeError:
                log.error("Dublin core adapter %s for %s has no attribute %s",
                    dc_adapter, context, name
                )
                return default
    try:
        return getattr(context, name)
    except AttributeError:
        log.error("Context %s has no such attribute %s. Check report template",
            context, name
        )
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
    REMOVE_ATTRIBUTES = ["type", "source", "url"]
    for key in REMOVE_ATTRIBUTES:
        _key = "{%s}%s" % (BUNGENI_REPORTS_NS, key)
        if _key in element.keys():
            del element.attrib[_key]

def empty_element(element):
    """Remove an element's children from document tree."""
    map(lambda child:element.remove(child), element.getchildren())

def drop_element(element):
    """Remove an element from the document tree"""
    element.getparent().remove(element)
    

class _BaseGenerator(object):
    """Base generator class. Child classes implement actual functionality"""

    zope.interface.implements(IReportGenerator)

    context = None
    configuration = None
    coverage = 168
    title = _(u"Report")
    language = None
    
    def __init__(self, report_template_file, context=None):
        self.report_template_file = report_template_file
        self.context = context
        self.loadConfiguration()
    
    def loadConfiguration(self):
        raise NotImplementedError("""Must be implemented by child classes""")
    
    def generateReport(self):
        raise NotImplementedError("""Must be implemented by child classes""")
    
    def publishReport(renderer):
        raise NotImplementedError("""Must be implemented by child classes""")

    def persistReport(self):
        raise NotImplementedError("""Must be implemented by child classes""")


class ReportGeneratorXHTML(_BaseGenerator):
    """Generates xHTML for a report of sittings and persists in a 
       `bungeni.models.Report`.
    """
    
    def loadConfiguration(self):
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
        
    def generateReport(self):
        """Generate report content based on report template and context
        """
        def generate_tree(root, context):
            for element in root.getiterator():
                typ = get_attr(element, "type")
                src = get_attr(element, "source")
                if typ:
                    if typ=="text":
                        clean_element(element)
                        element.text = get_element_value(context, src)
                    elif typ=="link":
                        clean_element(element)
                        url_source = get_attr(element, "url")
                        if url_source:
                            link_url = get_element_value(context, url_source)
                        else:
                            link_url = url.absoluteURL(context, 
                                common.get_request()
                            )
                        element.attrib["href"] = link_url
                        if src:
                            element.text = get_element_value(context, src)
                    elif typ=="html":
                        clean_element(element)
                        _html = u"<div>%s</div>" % get_element_value(context, 
                            src
                        )
                        new_html = element.insert(0, etree.fromstring(_html))
                    elif typ=="listing":
                        listing = get_element_value(context, src, default=[])
                        
                        if IAlchemistContainer.providedBy(listing):
                            _listing = common.list_container_items(listing)
                            listing = [ item for item in _listing ]
                        
                        log.debug("[LISTING] %s @@ %s", src, listing)
                        listing_count = len(listing)
                        new_children = [
                            deepcopy(element.getchildren()) 
                            for x in range(listing_count) 
                        ]
                        empty_element(element)
                        clean_element(element)
                        
                        if listing_count == 0:
                            parent = element.getparent()
                            no_items_element = etree.SubElement(element, "p")
                            no_items_element.text = translate_i18n(
                                _(u"No items found")
                            )
                        else:
                            for (index, item) in enumerate(listing):
                                for child in new_children[index]:
                                    generate_tree(child, item)
                            for children in new_children:
                                for descendant in children:
                                    element.append(descendant)
                        break
            return etree.tostring(root)
        generate_tree(self.report_template, self.context)
        return etree.tostring(self.report_template)

    def publishReport(self):
        pass
    
    def persistReport(self):
        pass
