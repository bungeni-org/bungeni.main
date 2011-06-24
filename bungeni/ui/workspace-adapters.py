from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.security.proxy import removeSecurityProxy
from zope import interface
from zope import component
from bungeni.models.interfaces import IBungeniContent
from bungeni.ui.interfaces import IWorkspaceAdapter
from bungeni.ui.descriptor.descriptor import localized_datetime_column
from bungeni.ui.utils import date
from bungeni.ui.utils.common import get_request
class WorkspaceAdapter(object):
    
    component.adapts(IBungeniContent)
    interface.implements(IWorkspaceAdapter)
    
    def __init__(self, context):
        self.context = removeSecurityProxy(context)
    
    @property
    def title(self):
        return IDCDescriptiveProperties(self.context).title
        
    @property
    def itemtype(self):
        return self.context.type
        
    @property
    def status(self):
        return self.context.status
        
    @property
    def status_date(self):
        value = self.context.status_date
        request = get_request()
        date_formatter = date.getLocaleFormatter(request, "dateTime", "medium")
        return date_formatter.format(value)
        
