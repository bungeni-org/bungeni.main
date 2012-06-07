import datetime
from zope import interface
from zope import schema
from zope.i18n import translate
from zope.formlib import form
from zope.formlib.namedtemplate import NamedTemplate
from zope.app.pagetemplate import ViewPageTemplateFile

from bungeni.models.interfaces import IParliament

from bungeni.ui.i18n import _
from bungeni.ui import cookies
from bungeni.ui import vocabulary
from bungeni.ui.widgets import TextDateWidget as DateWidget


class ArchiveDatesForm(form.PageForm):

    status = None
    
    class IDateRangeSchema(interface.Interface):
        range_start_date = schema.Date(
            title=_(u"From"),
            description=_(u"Leave blank or set lower limit"),
            required=False)

        range_end_date = schema.Date(
            title=_(u"To"),
            description=_(u"Leave blank or set upper limit"),
            required=False)

        parliament = schema.Choice(
            title=_(u"Or select"),
            description=_(u"Set date range to that of a given particular parliament"),
            vocabulary=vocabulary.parliament_factory,
            required=False)

    template = NamedTemplate("alchemist.subform")
    form_fields = form.Fields(IDateRangeSchema, render_context=True)
    form_fields["range_start_date"].custom_widget = DateWidget
    form_fields["range_end_date"].custom_widget = DateWidget
    form_description = _(u"Filter the archive by date range")

    def is_in_parliament(self, context):
        parent = context
        while not IParliament.providedBy(parent):
            parent = getattr(parent, "__parent__", None)
            if parent is None:
                return False
        return True
            
    def get_start_end_restictions(self, context):
        parent = context
        while not hasattr(parent, "start_date"):
            parent = getattr(parent, "__parent__", None)
            if parent is None:
                return None, None
        return getattr(parent, "start_date", None), getattr(parent, "end_date", None)

    def setUpWidgets(self, ignore_request=False, cookie=None):
        if ignore_request is False:
            start_date, end_date = cookies.get_date_range(self.request)
        else:
            start_date = end_date = None

        context = type("context", (), {
            "range_start_date": start_date,
            "range_end_date": end_date,
            "parliament": None})

        self.adapters = {
            self.IDateRangeSchema: context,
            }
        if self.is_in_parliament(self.context):
            self.form_fields = self.form_fields.omit("parliament")
            
        self.widgets = form.setUpWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            form=self, adapters=self.adapters, ignore_request=True)
        try:
            self.widgets["parliament"]._messageNoValue = _(
                u"parliament...")
        except KeyError:
            pass
        start, end = self.get_start_end_restictions(self.context)
        self.widgets["range_start_date"].set_min_date(start)
        self.widgets["range_end_date"].set_min_date(start)
        self.widgets["range_start_date"].set_max_date(end)
        self.widgets["range_end_date"].set_max_date(end)
    
    @form.action(_(u"Filter"), name="filter")
    def handle_filter(self, action, data):
        start_date = data.get("range_start_date")
        end_date = data.get("range_end_date")
        params = {}

        if start_date and end_date:
            if start_date > end_date:
                self.status = _("Invalid Date Range")
                cookies.unset_date_range(self.request)
                return
        start, end = self.get_start_end_restictions(self.context)
        if start_date and end:
            if start_date > end:
                  self.status = (_("Start date must be before %s") %
                        end.strftime("%d %B %Y"))
                  cookies.unset_date_range(self.request)
                  return
        if end_date and start:
            if end_date < start:
                  self.status = (_("End date must be after %s") %
                        start.strftime("%d %B %Y"))
                  cookies.unset_date_range(self.request)
                  return
                                
        cookies.set_date_range(self.request, start_date, end_date)
        self.request.response.redirect(
            "?portal_status_message=%s" % translate(
                _(u"Date range set")))

    @form.action(_(u"Clear"), name="clear")
    def handle_clear(self, action, data):
        cookies.unset_date_range(self.request)
        
        self.request.response.redirect(
            "?portal_status_message=%s" % translate(
                _(u"Date range cleared")))


class ArchiveDatesViewlet(object):
    """Viewlet to allow users to choose start- and end-dates to frame
    a search into the archive.

    In effect, parameters ``start_date`` and ``end_date`` will be
    set as a cookie.
    """
    render = ViewPageTemplateFile("templates/archive-dates.pt")

    def update(self):
        self.form = ArchiveDatesForm(self.context, self.request)
        start_date, end_date = cookies.get_date_range(self.request)
        if start_date or end_date:
            self.filter_on = "dates-filtered"
        else:
            self.filter_on = ""

            
