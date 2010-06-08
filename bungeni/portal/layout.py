log = __import__("logging").getLogger("bungeni.portal.layout")

import os

try:
    log.debug("TRY USING: plone.maintemplate.Layout as Layout...")
    from plone.maintemplate import Layout
    log.debug("  ...SUCCCEEDED: %s" % Layout )
except ImportError:
    from chameleon.html.template import DynamicHTMLFile as Layout
    log.debug("  ...FAILED, falling back to use: "
            "chameleon.html.template.DynamicHTMLFile as Layout")
    
from zope import interface
from zope import component
from zope.app.component.hooks import getSite
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.app.publisher.browser.directoryresource import DirectoryResourceFactory

from bungeni import portal


bungeni = Layout(
    os.path.join(
        portal.__path__[0], 'static', 'html', 'bungeni.html'))
log.debug("%s" % bungeni)

mtimes = {}

def get_url(context, request, path):
    """Return a URL for a given file-system resource ``path``; if a
    base host is not provided explicitly, it will be set to the
    request URL path."""

    path = os.path.abspath(path)
    gsm = component.getSiteManager()
    site = getSite()
    
    base = component.queryMultiAdapter(
        (site, request), IAbsoluteURL, name="resource")
    if base is None: 
        site_url = str(component.getMultiAdapter(
            (site, request), IAbsoluteURL))
    else:
        site_url = str(base)

    for name, resource in gsm.adapters.lookupAll(
        (interface.providedBy(request),), interface.Interface):

        if not isinstance(resource, DirectoryResourceFactory):
            continue
        
        resource = resource(request)
        try:
            directory = resource.context.path
        except AttributeError:
            continue
            
        if path.startswith(directory):
            relative_path = path[len(directory)+1:]
            return "/".join(
                (site_url.rstrip('/'), '++resource++%s' % name, relative_path))

def get_url_dev(context, request, path):
    path = os.path.abspath(path)
    mtime = os.path.getmtime(path)

    if mtime != mtimes.get(path):
        mtimes[path] = mtime
        invalidate = request.environment.get("X-Squeeze-Invalidate")
        if invalidate is not None:
            invalidate()

    return get_url(context, request, path)
