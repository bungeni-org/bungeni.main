import simplejson
from datetime import datetime
from zope.publisher.browser import BrowserPage
from bungeni.core.serialize import obj2dict
from bungeni.ui.browser import BungeniBrowserView
from bungeni.ui.utils import url, misc


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
        dthandler = lambda obj: obj.isoformat() if isinstance(
            obj, datetime) else obj
        data = obj2dict(self.context, 0)
        misc.set_json_headers(self.request)
        return simplejson.dumps(data, default=dthandler)
