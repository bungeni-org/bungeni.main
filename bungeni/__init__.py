


import zope.interface
from zope.security.interfaces import ISecurityPolicy
import zope.securitypolicy.zopepolicy


class BungeniSecurityPolicy(zope.securitypolicy.zopepolicy.ZopeSecurityPolicy):
    zope.interface.classProvides(ISecurityPolicy)
    
    def checkPermission(self, permission, object):
        #print "BSP", permission, object
        return super(BungeniSecurityPolicy, self
            ).checkPermission(permission, object)

