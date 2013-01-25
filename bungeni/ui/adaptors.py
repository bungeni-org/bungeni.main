# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""UI Adapters

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.adapters")

# !+SPELLING(mr, jan-2012) why does name for this file use "adaptor" spelling 
# and not "adapter" like everywhere else thoughout the application?
from zope import interface
from zope.location.interfaces import ILocation
from zope.security import checkPermission
from zope.security.proxy import removeSecurityProxy
from z3c.traverser.traverser import NameTraverserPlugin
from bungeni.alchemist import Session
from bungeni.core.interfaces import IRSSValues
from bungeni.core.workflows.utils import view_permission
from bungeni.core.workflow.interfaces import IWorkflowController
from bungeni.models import domain
from bungeni.models.interfaces import (IFeatureAudit, \
    IAlchemistContainer
)
from bungeni.utils import register
from bungeni.capi import capi
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
        workflow = capi.get_type_info(self.context.domain_model).workflow
        public_wfstates = workflow.get_state_ids(tagged=["public"],
            restrict=False)
        return [ x for x in self.context.values()
            if checkPermission(view_permission(x), x) and x.status in public_wfstates ]


@register.adapter(adapts=(IFeatureAudit,), provides=IRSSValues)
class TimelineRSSValues(RSSValues):
    """Adapter for getting values to form rss feed out of object's changes.
    """
    @property
    def values(self):
        return domain.get_changes(self.context, "modify", "add")


class DebateTraverserPlugin(NameTraverserPlugin):
    traversalName = "debate"

    def _traverse(self, request, name):
        self.context = removeSecurityProxy(self.context)
        session = Session()
        context = session.merge(self.context)
        debate = session.query(domain.DebateRecord) \
            .filter(domain.DebateRecord.sitting_id
                == context.sitting_id) \
                .first()
        if not debate:
            debate = domain.DebateRecord()
            debate.sitting_id = context.sitting_id
            session.add(debate)
            wfc = IWorkflowController(debate)
            wfc.fireAutomatic()
            session.flush()
        debate.__name__ = self.traversalName
        debate.__parent__ = self.context
        interface.alsoProvides(debate, ILocation)
        return debate
