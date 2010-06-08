import pytz
from zope import interface, component
from zope.interface.common.idatetime import ITZInfo
from zope.publisher.interfaces.browser import IBrowserRequest

@interface.implementer(ITZInfo)
@component.adapter(IBrowserRequest)
def tzinfo(request):
     return pytz.timezone('Africa/Nairobi') # or whatever timezone you wish
