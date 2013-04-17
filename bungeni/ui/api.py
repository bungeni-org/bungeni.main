import simplejson
from datetime import datetime, date, time
from zope import component
from zope.publisher.browser import BrowserPage
from zope.publisher.interfaces import NotFound
from zope.security.proxy import removeSecurityProxy
from zope.app.publication.traversers import SimpleComponentTraverser
from bungeni.core.serialize import obj2dict
from bungeni.ui.browser import BungeniBrowserView
from bungeni.ui.utils import url, misc
from bungeni.models.utils import get_login_user

dthandler = lambda obj: obj.isoformat() if type(obj) in \
    (date, time, datetime) else obj

class APIDefaultView(BungeniBrowserView):
    def __call__(self):
        return "Bungeni API"


class APISectionView(BrowserPage):
    def __call__(self):
        data = []
        for key in self.context.keys():
            item = {}
            item["id"] = key
            item["title"] = self.context[key].title
            item["url"] = url.absoluteURL(
                self.context[key], self.request)
            data.append(item)
        misc.set_json_headers(self.request)
        return simplejson.dumps(data)


class APIObjectView(BrowserPage):
    def __call__(self):
        data = obj2dict(self.context, 0)
        misc.set_json_headers(self.request)
        return simplejson.dumps(data, default=dthandler)


class APIUserView(BrowserPage):
    def __call__(self):
        data = obj2dict(self.context, 0, exclude=["salt", "_password",
            "password", "active_p", "principal_id", "user_id", "type"])
        misc.set_json_headers(self.request)
        return simplejson.dumps(data, default=dthandler)


class APIUserContainerTraverser(SimpleComponentTraverser):
    """Traverser for workspace containers"""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        if name == "current":
            return get_login_user()
        trusted = removeSecurityProxy(self.context)
        view = component.queryMultiAdapter((trusted, request), name=name)
        if view:
            return view
        ob = trusted.get(name)
        if ob:
            return ob
        raise NotFound(self.context, name)
