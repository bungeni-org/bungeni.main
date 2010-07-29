from zope.component.zcml import handler
from interfaces import IOpenOfficeConfig
from zope.interface import implements


class OpenOfficeConfig(object):

    implements(IOpenOfficeConfig)
    
    path = ""
    
    def __init__(self, path):
        self.path = path
        
    def getPath(self):
        return self.path
        
def registerOpenOfficePath(context, path):

   context.action(discriminator=('RegisterOpenOfficePath', path),
                   callable=handler,
                   args = ('registerUtility', 
                            OpenOfficeConfig(path), 
                            IOpenOfficeConfig)
                   )
