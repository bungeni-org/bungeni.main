from zope.component.zcml import handler
from interfaces import IOpenOfficeConfig
from zope.interface import implements


class OpenOfficeConfig(object):

    implements(IOpenOfficeConfig)
    path = ""
    port = None
    maxConnections = None
    
    def __init__(self, path, port, maxConnections):
        self.path = path
        self.port = port
        self.maxConnections = maxConnections
        
    def getPath(self):
        return self.path
    
    def getPort(self):
        return self.port
    
    def getMaxConnections(self):
        return self.maxConnections
        
def registerOpenOfficeConfig(context, path, port, maxConnections):

   context.action(discriminator=('RegisterOpenOfficeConfig', path, port, 
                                                                maxConnections),
                   callable=handler,
                   args = ('registerUtility', 
                            OpenOfficeConfig(path, port, maxConnections), 
                            IOpenOfficeConfig)
                   )
