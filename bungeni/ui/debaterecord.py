from zope import component
from zope.publisher.browser import BrowserView
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.app.publication.traversers import SimpleComponentTraverser
from zope.security.proxy import removeSecurityProxy
from zc.resourcelibrary import need


class DebateRecordView(BrowserView):
    template = ViewPageTemplateFile("templates/debate-record.pt")
    transcription_video = None

    def __call__(self):
        self.context = removeSecurityProxy(self.context)
        self.transcription_video = self.get_transctiption_video()
        return self.render()

    def render(self):
        need("debate-css")
        return self.template()

    def get_transctiption_video(self):
        for media in self.context.debate_media:
            if media.media_type == "transcription":
                return media.media_path
        return None

class DebateRecordTraverser(SimpleComponentTraverser):
    """Traverser for debate record objects"""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        """First checks if the name refers to a view defined on this object,
        then checks if the name refers to an attribute,
        else raises a NotFound.
        """
        debate = removeSecurityProxy(self.context)
        view = component.queryMultiAdapter((debate, request), name=name)
        if view:
            return view
        if hasattr(debate, name):
            return getattr(debate, name)
        raise NotFound(workspace, name)
