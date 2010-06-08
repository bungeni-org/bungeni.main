log = __import__("logging").getLogger("bungeni.core.vhost")

from zope.traversing.browser import AbsoluteURL
from zope.proxy import sameProxiedObjects
from zope.security.proxy import removeSecurityProxy

class ProxyAwareAbsoluteURL(AbsoluteURL):
    def __str__(self):
        target = removeSecurityProxy(self.context).__target__
        vhostroot = self.request.getVirtualHostRoot()

        if sameProxiedObjects(vhostroot, target):
            return str(AbsoluteURL(target, self.request))
        
        log.debug("ProxyAwareAbsoluteURL.__str__: %s [%s]" % (
                                                vhostroot, target))
        return super(ProxyAwareAbsoluteURL, self).__str__()

    __call__ = __str__
