
from zope import interface
from zope.security.proxy import removeSecurityProxy
from zope.i18n import translate
from zope.dublincore.interfaces import IDCDescriptiveProperties
from bungeni.ui.interfaces import IWorkspaceContentAdapter
from bungeni.ui.utils import date
from bungeni.ui.utils.common import get_request
from bungeni.ui.i18n import _
from bungeni.core.workflow.states import get_object_state
from bungeni.alchemist import utils


class WorkspaceContentAdapter(object):
    interface.implements(IWorkspaceContentAdapter)

    def __init__(self, context):
        self.context = removeSecurityProxy(context)

    @property
    def title(self):
        return IDCDescriptiveProperties(self.context).title

    @property
    def type(self):
        descriptor = utils.get_descriptor(self.context.__class__)
        item_type = descriptor.display_name if descriptor \
            else self.context.type
        request = get_request()
        return translate(item_type, context=request)

    @property
    def status(self):
        status_title = get_object_state(self.context).title
        request = get_request()
        return translate(_(status_title), context=request)

    @property
    def status_date(self):
        value = self.context.status_date
        request = get_request()
        date_formatter = date.getLocaleFormatter(request, "dateTime", "medium")
        return date_formatter.format(value)
