from zope import component

from ore.wsgiapp import startup
from interfaces import ISettings

def application_factory(global_conf, **kwargs):
    component.provideUtility(global_conf, ISettings)
    return startup.application_factory(global_conf, **kwargs)

