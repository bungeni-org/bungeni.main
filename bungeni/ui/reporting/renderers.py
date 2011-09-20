# -*- coding: utf-8 -*-
# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Report generators

See `bungeni.ui.reports.intefaces.IReportGenerator` for signature

$Id$
"""

log = __import__("logging").getLogger("bungeni.ui.reporting")

import os
import cStringIO
import zope.interface
from zope.location.interfaces import ILocation
import zope.app.form.browser.widget
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zc.table import column, table

from bungeni.alchemist.interfaces import IAlchemistContainer
from bungeni.core.translation import translate_i18n
from bungeni.ui.i18n import _
from bungeni.ui.utils import common, url
from bungeni.ui.reporting.interfaces import IContentrenderer, IReportRenderer

LISTING_CSS_CLASSES = {
    "table": "listing",
}

class RenderMixin(object):
    def __call__(self):
        return self.render()


class TextRenderer(RenderMixin):
    """Simple text renderer - Can be overriden via ZCML overrides
    """
    
    zope.interface.implements(IContentrenderer)
    
    tag = "p"
    css_class = None
    
    def __init__(self, context, context_property=None, text=None, tag=None):
        self.context = context
        self.context_property = context_property
        self.text = text
        if tag is not None:
            self.tag = tag

    def getRenderContent(self):
        if (self.text is not None) or (self.context_property is None):
            return unicode(self.text)
        if self.context_property.startswith("dc:"):
            dc_property = self.context_property.strip()[3:]
            self.css_class = dc_property
            try:
                content = getattr(IDCDescriptiveProperties(self.context),
                    dc_property
                )
                return content
            except Exception, e:
                log.error("Dublin core property  %s of object %s not found:%s",
                    dc_property, self.context, e.__str__()
                )
        else:
            self.css_class = " ".join(
                [self.css_class or '', self.context_property]
            )
            try:
                content = getattr(self.context, self.context_property)
                return content
            except AttributeError:
                log.error("Object %s has no attribute %s", self.context,
                    self.context_property
                )
        missing_text = _("report_missing_text", 
            default=u"Unable to get text for: ${property}",
            mapping = {"property": self.context_property}
        )
        return translate_i18n(missing_text)

    def render(self):
        text = self.getRenderContent()
        return zope.app.form.browser.widget.renderElement(self.tag,
            cssClass=unicode(self.css_class),
            contents = text
        )
        

class HeadingRenderer(TextRenderer):
    tag = "h2"
    css_class = "heading"

class ListingRenderer(RenderMixin):
    """Renderer for listings - Renders listings as HTML tables
    
    Provides links back to item if object provides ILocation
    """
    css_class = None
    
    zope.interface.implements(IContentrenderer)
    
    def __init__(self, context, context_property):
        self.context = context
        self.context_property = context_property

    @property
    def request(self):
        if not hasattr(self, "_computed_request"):
            self._computed_request = common.get_request()
        return self._computed_request

    @property
    def columns(self):
        item_columns = [
            column.GetterColumn(title=_(u"Item"),
                getter = lambda i,f: (
                    zope.app.form.browser.widget.renderElement("a",
                        contents = IDCDescriptiveProperties(i).title,
                        href = url.absoluteURL(self.request, i) 
                    ) if ILocation.providedBy(i) else
                    IDCDescriptiveProperties(i).title
                )
            ),
            column.GetterColumn(title=_(u"Description"),
                getter = lambda i,f:IDCDescriptiveProperties(i).description
            )
        ]
        return item_columns

    def getRenderContent(self):
        """Return an HTML table for display 
        """
        if hasattr(self.context, self.context_property):
            try:
                items = getattr(self.context, self.context_property)
            except AttributeError:
                log.error("[Reports] No property %s found on %s", 
                    self.context_property, self.context
                )
                items = []
            if IAlchemistContainer.providedBy(items):
                items = [ item for item in common.list_container_items(items) ]
            if len(items):
                formatter = table.AlternatingRowFormatter(None, self.request,
                    items, columns=self.columns
                )
                formatter.cssClasses = LISTING_CSS_CLASSES
                return formatter()
        return zope.app.form.browser.widget.renderElement("p",
            contents = _(u"No items found")
        )
    
    def render(self):
        return self.getRenderContent()
