import datetime
from zope import component
from zope import formlib
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.app.publication.traversers import SimpleComponentTraverser
from zope.security.proxy import removeSecurityProxy
from zope.app.security.settings import Allow
from zope.securitypolicy.interfaces import IPrincipalRoleMap
from zope.publisher.interfaces import NotFound
from zc.resourcelibrary import need
from zc.table import column

from bungeni.alchemist import Session
from bungeni.models import domain
from bungeni.ui.i18n import _
from bungeni.ui import forms
from bungeni.ui.table import TableFormatter
from bungeni.core.interfaces import IDebateRecordConfig
from bungeni.core.dc import IDCDescriptiveProperties
from bungeni.ui.utils import url, date, common
from bungeni.ui.browser import BungeniBrowserView

class DebateRecordView(BungeniBrowserView):
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


class DebateRecordTakes(BungeniBrowserView, forms.common.BaseForm):
    """View to generate takes
    """
    form_fields = []
    render = ViewPageTemplateFile("templates/debate-takes.pt")

    def __init__(self, context, request):
        self.context = removeSecurityProxy(context)
        self.prm = IPrincipalRoleMap(self.context)
        super(DebateRecordTakes, self).__init__(context, request)

    def __call__(self):
        self.update()
        self.listing = self.formatted_listing()
        return self.render()

    def columns(self):
        date_formatter = date.getLocaleFormatter(common.get_request(),
            "dateTime", "medium")
        listing_columns = [
            column.GetterColumn(
                title=_("Take start time"),
                getter=lambda i,f: date_formatter.format(i.start_date)
            ),
            column.GetterColumn(
                title=_("Take end time"),
                getter=lambda i,f: date_formatter.format(i.end_date)
            ),
            column.GetterColumn(
                title=_("Take name"),
                getter=lambda i,f: i.debate_take_name
            ),
            column.GetterColumn(
                title=_("Take transcriber"),
                getter=lambda i,f: IDCDescriptiveProperties(i.user).title
            ),
        ]
        return listing_columns

    def formatted_listing(self):
        formatter = TableFormatter(self.context, self.request,
            self.context.debate_takes, columns=self.columns()
        )
        formatter.updateBatching()
        return formatter()

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
            take_name_prefix = take_name_prefix + chr(64+take_count)
        return take_name_prefix + chr(65+(b_take_count%26))

    def has_no_takes(self, action=None):
        return False if len(self.context.debate_takes) > 0 else True
    

    @formlib.form.action(label=_("Generate takes"), name="generate",
        condition=has_no_takes)
    def handle_generate_takes(self, action, data):
        transcribers = self.get_transcribers()
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
            take_count = take_count+1
            session.add(take)
        session.flush()
        next_url = url.absoluteURL(self, self.request)
        self.request.response.redirect(next_url)
