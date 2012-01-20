# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""UI Adapters

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.adapters")

# !+SPELLING(mr, jan-2012) why does name for this file use "adaptor" spelling 
# and not "adapter" like everywhere else thoughout the application?

from zope.security.proxy import removeSecurityProxy
from bungeni.alchemist import model
from bungeni.core import interfaces
from bungeni.models import domain
from bungeni.models.interfaces import IBungeniParliamentaryContent
from bungeni.utils import register


''' !+UNUSED(mr, jan-2012) but time wasted on it anyway.
from zope import component
class BillAnnotationAdaptor(object):
    """Annotation Adaptor for Bills."""
    
    def __init__(self, context):
        self.context = context
    
    def getBodyText(self):
        """Returns the annotatable text"""
        return self.context.body_text
    
    def getTitle(self):
        """Returns the annotatable title"""
        return self.context.short_name
    
    def isAnnotatable(self):
        """Return True."""
        return True
    
    def getAnnotatedUrl(self, request=None):
        """Returns the annotated url.
        """
        view = component.getMultiAdapter((self.context, request), name=u"absolute_url")
        return view()
'''

# !+IS-THIS-NEEDED?(mr, jan-2012)
#@register.adapter(provides=interfaces.IRSSValues)
class RSSValues(object):
    """Adapter for getting values to form rss feed.
    """
    def __init__(self, context):
        self.context = context
        self.domain_model = removeSecurityProxy(self.context).domain_model
        self.domain_interface = model.queryModelInterface(self.domain_model)
        self.domain_annotation = model.queryModelDescriptor(
            self.domain_interface)
    
    @property
    def values(self):
        public_wfstates = getattr(self.domain_annotation,
                                  "public_wfstates",
                                  None)
        trusted = removeSecurityProxy(self.context)
        if public_wfstates:
            return filter(lambda x: x.status in public_wfstates, trusted.values())
        return trusted.values()


@register.adapter(adapts=(IBungeniParliamentaryContent,),
    provides=interfaces.IRSSValues)
class TimelineRSSValues(RSSValues):
    """Adapter for getting values to form rss feed out of object's changes.
    """
    def __init__(self, context):
        self.context = context
    
    @property
    def values(self):
        return domain.get_changes(self.context, "modify", "add")

