# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""UI Adapters

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.adapters")

# !+SPELLING(mr, jan-2012) why does name for this file use "adaptor" spelling 
# and not "adapter" like everywhere else thoughout the application?
from zope.security import checkPermission
from bungeni.core.interfaces import IRSSValues
from bungeni.core.workflows.adapters import get_workflow
from bungeni.models import domain
from bungeni.models.interfaces import (IFeatureAudit, \
    IAlchemistContainer
)
from bungeni.utils import register

#import bungeni.ui.versions # !+REGISTER


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


@register.adapter(adapts=(IAlchemistContainer,), provides=IRSSValues)
class RSSValues(object):
    """Adapter for getting values to form rss feed.
    """
    def __init__(self, context):
        self.context = context
    
    @property
    def values(self):
        workflow = get_workflow(self.context.domain_model.__name__.lower())
        public_wfstates = workflow.get_state_ids(tagged=["public"],
            restrict=False)
        return [ x for x in self.context.values()
            if checkPermission("zope.View", x)
                 and x.status in public_wfstates ]


@register.adapter(adapts=(IFeatureAudit,), provides=IRSSValues)
class TimelineRSSValues(RSSValues):
    """Adapter for getting values to form rss feed out of object's changes.
    """
    @property
    def values(self):
        return domain.get_changes(self.context, "modify", "add")

