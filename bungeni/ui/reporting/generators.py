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
import cStringIO
import zope.interface
from lxml import etree

from bungeni.core.language import get_default_language

from bungeni.ui.i18n import _
from bungeni.ui.utils import report_tools
from bungeni.ui.reporting.interfaces import IReportGenerator, ReportException
from bungeni.ui.reporting.renderers import TextRenderer, HeadingRenderer, ListingRenderer

CONTAINER_TAGS = ["heading", "body", "listing"]
TEXT_TAGS = ["text"]

RENDERERS = {
    "heading": HeadingRenderer,
    "text": TextRenderer,
    "listing": ListingRenderer 
}

def get_renderer(tag):
    return RENDERERS.get(tag, TextRenderer)

class _BaseGenerator(object):
    """Base generator class. Child classes implement actuall functionality"""

    zope.interface.implements(IReportGenerator)

    context = None
    configuration = None
    coverage = 168
    title = _(u"Report")
    language = None
    
    def __init__(self, config_file, context=None):
        self.configuration_file = config_file
        self.context = context
        self.loadConfiguration()
    
    def loadConfiguration(self):
        raise NotImplementedError("""Must be implemented by child classes""")
    
    def getContext(self):
        raise NotImplementedError("""Must be implemented by child classes""")
    
    def loadStyle(self, target):
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
        """Process XML configuration
        """
        if os.path.exists(self.configuration_file):
            _file = open(self.configuration_file)
            doctree = etree.fromstring(_file.read())
            self.configuration = doctree
            _file.close()
            _title = doctree.find("title")
            self.title = self.title if (_title is None) else _title.text
            self.language = doctree.get("language", get_default_language())
            _period = doctree.find("length")
            self.coverage = report_tools.compute_hours(_period.text)
        else:
            raise ReportException(
                _(u"configuration_file_missing",
                    default=u"Configuration file does not exist at ${path}",
                    mapping={"path": self.configuration}
                )
            )
    
    def getContext(self, **kwargs):
        """Get the sittings covered by period"""
        pass
    
    def loadStyle(self, target):
        """Load style element from report configuration"""
        style = self.configuration.find("styles/style[@for='%s']" % target)
        return style

    def generateReport(self):
        """Generate report content based on XML configuration
        """
        out = cStringIO.StringIO()
        def render_element(element, context, level=1):
            if element.tag in CONTAINER_TAGS:
                text = element.get("title", None)
                if text:
                    renderer_class = get_renderer("heading")
                    text_renderer = renderer_class(context)
                    text_renderer.tag = "h%d" % level
                    text_renderer.text = text
                    out.write(text_renderer())
                children = element.getchildren()
                if len(children)==0:
                    style = self.loadStyle(element.get("source"))
                    if style is None:
                        renderer_class = get_renderer(element.tag)
                        list_renderer = renderer_class(context, 
                            element.get("source")
                        )
                        out.write(list_renderer())
                    else:
                        for item in getattr(context, element.get("source")):
                            for child in style:
                                render_element(child, item, level=level+1)
                else:
                    source = element.get("source", None)
                    if source is not None:
                        context = getattr(context, source)
                        for item in context:
                            for child in children:
                                render_element(child, item, level=level+1)
                    else:
                        for child in children:
                            render_element(child, context, level=level+1)
            elif element.tag in TEXT_TAGS:
                tag_type = element.get("type", element.tag)
                renderer_class = get_renderer(tag_type)
                if renderer_class == HeadingRenderer:
                    renderer_class.tag = "h%d" % level
                renderer = renderer_class(context, element.get("source"), 
                    text=element.text
                )
                out.write(renderer())

        content = self.configuration.find("content")
        for element in content:
            log.error("Rendering Element %s", element.tag)
            render_element(element, self.context, level=2)

        out.reset()
        self._generated_content = out.read()
        out.reset()
        return out.read()

    def publishReport(self):
        pass
    
    def persistReport(self):
        pass
