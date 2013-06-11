import simplejson
from datetime import datetime, date, time, timedelta
from sqlalchemy.sql.expression import and_
from zope import component
from zope import formlib
from zope.publisher.browser import BrowserPage
from zope.publisher.interfaces import NotFound
from zope.security.proxy import removeSecurityProxy
from zope.app.publication.traversers import SimpleComponentTraverser
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.formlib.namedtemplate import NamedTemplate
from bungeni.alchemist import container, Session
from bungeni.core.serialize import obj2dict
from bungeni.ui.workspace import WorkspaceAddForm
from bungeni.ui.forms.common import AddForm, EditForm
from bungeni.ui.browser import BungeniBrowserView
from bungeni.ui.utils import url, misc
from bungeni.ui.container import ContainerJSONListingRaw
from bungeni.models.utils import get_login_user
from bungeni.models import domain


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
            data.append(item)
        misc.set_json_headers(self.request)
        return simplejson.dumps(data)


class APIObjectView(BrowserPage):
    def __call__(self):
        data = obj2dict(self.context, 1, exclude=["data", "versions", "audits", "changes", "permissions"])
        misc.set_json_headers(self.request)
        return simplejson.dumps(data, default=dthandler)


class APIDebateRecordView(BrowserPage):
    def __call__(self):
        data = obj2dict(self.context, 0)
        data["start_date"] = self.context.sitting.start_date
        data["end_date"] = self.context.sitting.end_date
        data["title"] = IDCDescriptiveProperties(self.context).title
        data["url"] = url.absoluteURL(self.context, self.request)
        data["media"] = [obj2dict(m, 0) for m in self.context.debate_media]
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


class APITakeListing(ContainerJSONListingRaw):

    def query_add_filters(self, query):
        login = self.request.get("filter_transcriber_login", None)
        if login:
            query = query.join(domain.User).filter(domain.User.login == login)
        return query

    def get_batch(self, start, limit):
        """Get the data instances for this batch.
        """
        media_url = ""
        trusted = removeSecurityProxy(self.context)
        for media in trusted.__parent__.debate_media:
            if media.media_type == "transcription":
                media_url = media.media_path
                break
        batch = super(APITakeListing, self).get_batch(start, limit)
        for item in batch:
            if media_url == "":
                item.media_url = ""
            else:
                start_time = item.start_date - \
                    item.debate_record.sitting.start_date
                end_time = item.end_date - \
                    item.debate_record.sitting.start_date
                item.media_url = "{0}?t=npt:{1}/{2}".format(media_url,
                    str(start_time), str(end_time))
        return batch

    def _json_values(self, nodes):
        """Return nodes as JSON"""
        values = []
        for node in nodes:
            d = {}
            for field in self.fields:
                fn = field.__name__
                d[fn] = getattr(node, fn, None)
                v = d[fn]
                if type(v) in (date, time, datetime):
                    d[fn] = v.isoformat()
            d["object_id"] = url.set_url_context(container.stringKey(node))
            d["media_url"] = node.media_url
            values.append(d)
        return values


class APIDebateRecordItemsView(BungeniBrowserView):

    def __call__(self):
        sitting = self.context.sitting
        start_time = sitting.start_date + timedelta(
            seconds=int(self.request.get("start_time", 0)))
        if self.request.get("end_time", 0):
            end_time = sitting.start_date + timedelta(
                seconds=int(self.request.get("end_time", 0)))
        else:
            end_time = sitting.end_date
        session = Session()
        speeches = session.query(domain.DebateSpeech).filter(
            and_(
                domain.DebateSpeech.start_date >= start_time,
                domain.DebateSpeech.end_date <= end_time)).all()
        docs = session.query(domain.DebateDoc).filter(
            and_(
                domain.DebateDoc.start_date >= start_time,
                domain.DebateDoc.end_date <= end_time)).all()
        data = []
        for item in speeches + docs:
            data.append(obj2dict(item, 0))
        misc.set_json_headers(self.request)
        return simplejson.dumps({"nodes": data}, default=dthandler)


class APIEditForm(EditForm):
    """API Edit form that doesn't have bungeni skin
    """
    template = NamedTemplate("alchemist.subform")

    def __call__(self):
        self.prefix = ""
        # if data has been submitted
        if (self.request.form.keys()):
            self.request.form["actions.edit"] = "edit"
        call = super(APIEditForm, self).__call__()
        return call

    @formlib.form.action("edit", name="edit",
        condition=formlib.form.haveInputWidgets)
    def handle_edit(self, action, data):
        """Saves the document and goes back to edit page"""
        self._do_save(data)

class APIAddForm(AddForm):
    """ Generic add form
    """
    
    template = NamedTemplate("alchemist.subform")

    def __call__(self):
        self.prefix = ""
        # if data has been submitted
        if (self.request.form.keys()):
            self.request.form["actions.add"] = "add"
        call = super(APIAddForm, self).__call__()
        return call

    @formlib.form.action("add", name="add",
        condition=formlib.form.haveInputWidgets)
    def handle_add(self, action, data):
        ob = self.createAndAdd(data)
        if not self._next_url:
            self._next_url = url.absoluteURL(ob, self.request)


class APIWorkspaceAddForm(APIAddForm, WorkspaceAddForm):
    """Add form for docs that have workspace Feature
    """
