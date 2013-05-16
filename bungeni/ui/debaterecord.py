import datetime
import simplejson
from zope import component
from zope import formlib
from zope import interface
from zope import schema
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.app.publication.traversers import SimpleComponentTraverser
from zope.security.proxy import removeSecurityProxy
from zope.app.security.settings import Allow
from zope.securitypolicy.interfaces import IPrincipalRoleMap
from zope.publisher.interfaces import NotFound
from zc.resourcelibrary import need
from zope.formlib.namedtemplate import NamedTemplate

from bungeni.alchemist import Session
from bungeni.models import domain
from bungeni.models.interfaces import IDebateTakeContainer
from bungeni.ui.i18n import _
from bungeni.ui import forms
from bungeni.core.interfaces import IDebateRecordConfig
from bungeni.ui.utils import url, common
from bungeni.ui.browser import BungeniBrowserView


class DebateRecordView(BungeniBrowserView):
    template = ViewPageTemplateFile("templates/debate-record.pt")
    transcription_video = None

    def __call__(self):
        self.context = removeSecurityProxy(self.context)
        self.transcription_video = self.get_transcription_video()
        self.speeches = self.get_speeches()
        return self.render()

    def render(self):
        need("debate-css")
        return self.template()

    def get_transcription_video(self):
        for media in self.context.debate_media:
            if media.media_type == "transcription":
                return media.media_path
        return None

    def get_speeches(self):
        speeches = []
        for speech in self.context.debate_speeches:
            speech.image_data = "data:;base64," + \
                speech.user.image.encode("base64")
            speeches.append(speech)
        return speeches


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
        raise NotFound(debate, name)


class GenerateTakesViewlet(object):
    available = True
    render = ViewPageTemplateFile("templates/debate-takes.pt")

    def __init__(self, context, request, view, manager):
        self.context = context
        self.request = request
        trusted = removeSecurityProxy(self.context)
        if len(trusted.__parent__.debate_takes) > 0:
            self.available = False

    def update(self):
        self.form = GenerateDebateRecordTakes(self.context, self.request)


class GenerateDebateRecordTakes(BungeniBrowserView, forms.common.BaseForm):
    """View to generate takes
    """
    form_fields = []
    template = NamedTemplate("alchemist.subform")

    def __init__(self, context, request):
        if IDebateTakeContainer.providedBy(context):
            self.context = removeSecurityProxy(context).__parent__
        else:
            self.context = removeSecurityProxy(context)
        self.prm = IPrincipalRoleMap(self.context)
        self.request = request
        #super(GenerateDebateRecordTakes, self).__init__(context, request)

    def get_take_duration(self):
        return component.getUtility(IDebateRecordConfig).get_take_duration()

    def get_transcriber_role(self):
        return component.getUtility(IDebateRecordConfig).get_transcriber_role()

    def get_transcribers(self):
        transcribers = []
        transcriber_role = self.get_transcriber_role()
        users = common.get_users(transcriber_role)
        for user in users:
            if self.user_is_assigned(user.login, transcriber_role):
                transcribers.append(user)
        return transcribers

    def user_is_assigned(self, user_login, role_id):
        if self.prm.getSetting(role_id, user_login) == Allow:
            return True
        return False

    def get_take_name(self, take_count):
        take_name_prefix = ""
        b_take_count = take_count
        while (take_count / 26):
            take_count = take_count / 26
            take_name_prefix = take_name_prefix + chr(64 + take_count)
        return take_name_prefix + chr(65 + (b_take_count % 26))

    def has_no_takes(self, action=None):
        return False if len(self.context.debate_takes) > 0 else True

    @formlib.form.action(label=_("Generate takes"), name="generate",
        condition=has_no_takes)
    def handle_generate_takes(self, action, data):
        transcribers = self.get_transcribers()
        next_url = url.absoluteURL(self.context, self.request)
        if not transcribers:
            return self.request.response.redirect(next_url + "/takes")
        sitting = self.context.sitting
        take_time_delta = datetime.timedelta(seconds=self.get_take_duration())
        current_end_time = sitting.start_date
        current_start_time = sitting.start_date
        take_count = 0
        session = Session()
        while current_end_time < sitting.end_date:
            take = domain.DebateTake()
            take.debate_record_id = self.context.debate_record_id
            take.start_date = current_start_time
            if ((current_end_time + take_time_delta) > sitting.end_date):
                current_end_time = sitting.end_date
            else:
                current_end_time = current_end_time + take_time_delta
                current_start_time = current_end_time + datetime.timedelta(
                    seconds=1)
            take.end_date = current_end_time
            take.transcriber_id = transcribers[
                take_count % len(transcribers)].user_id
            take.debate_take_name = self.get_take_name(take_count)
            take_count = take_count + 1
            session.add(take)
        session.flush()
        return self.request.response.redirect(next_url + "/takes")


class AddSpeeches(forms.common.BaseForm):
    template = NamedTemplate("alchemist.form")

    class IAddSpeechesForm(interface.Interface):
        data = schema.Text(required=True)
    form_fields = formlib.form.Fields(IAddSpeechesForm)

    @formlib.form.action("add", name="add")
    def handle_add(self, action, data):
        json_data = simplejson.loads(data["data"])
        session = Session()
        sitting = self.context.sitting
        for item in json_data:
            debate_speech = None
            if item.get("speech_id", None):
                debate_speech = session.query(domain.DebateSpeech
                    ).get(item["speech_id"])
            if not debate_speech:
                debate_speech = domain.DebateSpeech()
                debate_speech.debate_record_id = self.context.debate_record_id
            debate_speech.person_id = item["user_id"]
            debate_speech.text = item["speech"]
            debate_speech.language = "en"
            debate_speech.start_date = sitting.start_date + \
                datetime.timedelta(seconds=item["start_time"])
            debate_speech.end_date = sitting.start_date + \
                datetime.timedelta(seconds=item["end_time"])
            session.add(debate_speech)
