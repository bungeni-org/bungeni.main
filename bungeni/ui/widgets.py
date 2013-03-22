# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""UI Widgets

$Id$
$URL$
"""
log = __import__("logging").getLogger("bungeni.ui.widgets")

import datetime
import pytz
import itertools
import os
from zope import interface
from zope.datetime import parseDatetimetz
from zope.datetime import DateTimeError
from zope.security.proxy import removeSecurityProxy
from zope.formlib.interfaces import ConversionError, InputErrors
from zope.formlib.widget import CustomWidgetFactory
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.interface.common import idatetime
import zope.security.proxy
import zope.traversing
from zope.formlib.widgets import (TextAreaWidget, FileWidget, RadioWidget,
    DropdownWidget)
from zope.formlib.itemswidgets import (ItemsEditWidgetBase, ItemDisplayWidget)
from zope.formlib import form
from zope.formlib.namedtemplate import NamedTemplate
from zope.i18n import translate
from zope import schema
from zc.resourcelibrary import need

from sqlalchemy.orm.exc import NoResultFound

from bungeni.ui.i18n import _
from bungeni.ui.utils import url, debug, date, misc
from bungeni.utils import common
from bungeni.ui.interfaces import IGenenerateVocabularyDefault, \
    IAdminSectionLayer
from bungeni.models.utils import get_login_user, get_user, get_member_of_parliament
from bungeni.core.language import get_default_language


_path = os.path.split(os.path.abspath(__file__))[0]

class IDiffDisplayWidget(zope.formlib.interfaces.IDisplayWidget):
    """ Marker interface for diff text widgets
    """
    pass

class TextWidget(zope.formlib.widgets.TextWidget):
    displayWidth = 60

''' !+UNUSED (was prev used by Doc.title)
class LongTextWidget(TextWidget):
    displayWidth = 90
'''

class ComputedTitleWidget(zope.formlib.widgets.DisplayWidget):
    """Computes a title and renders it if title field is empty
    """
    displayWidth = 90
    def __call__(self):
        if self._renderedValueSet():
            value = self._data
        else:
            value = self.context.default
        if (value == self.context.missing_value) or (len(value)==0):
            context = self.__parent__.context
            body = getattr(context, "body", None)
            if (body != None) and (body != self.context.missing_value):
                return misc.text_snippet(body, self.displayWidth)
            return _(u"Unknown")
        return super(ComputedTitleWidget, self).__call__()

class HiddenTextWidget(zope.formlib.widgets.TextWidget):
    def __call__(self):
        return self.hidden()


class MultiDateTextAreaWidget(TextAreaWidget):
    def _toFieldValue(self, value):
        dates = []
        for token in itertools.chain(*[
            line.split("\n") for line in value.split(",")]):
            token = token.strip()
            if not token:
                continue
            try:
                date = parseDatetimetz(token)
                dates.append(date.date())
            except (DateTimeError, ValueError, IndexError), v:
                raise ConversionError(
                    _("Invalid date: $value",
                      mapping={"value": token}), v)

        return dates

    def _toFormValue(self, value):
        if value:
            return u"\n".join(date.strftime("%F") for date in value)
        return u""

def CustomRadioWidget(field, request):
    """ to replace the default combo box widget for a schema.choice field"""
    vocabulary = field.vocabulary
    return RadioWidget(field, vocabulary, request)

class DefaultFileInputWidget(FileWidget):
    '''
    This is the default FileInputWidget implementation, 
    other FileInputWidget types extend this
    '''

    _missing = u""

    @property
    def update_action_name(self):
        return self.name + ".up_action"

    @property
    def upload_name(self):
        return self.name.replace(".", "_") + "_file"

    def empty_field(self):
        return self._data is None

    def _getFieldInput(self, name):
        return self.request.form.get(name, self._missing)

    def _getFormInput(self):
        """extract the input value from the submitted form """
        return (self._getFieldInput(self.update_action_name),
                self._getFieldInput(self.upload_name))


    def _toFieldValue(self, (update_action, upload)):
        """convert the input value to an value suitable for the field.
        Check the update_action if we should leave the data alone,
        delete or replace it.
        """
        if update_action == u"update":
            if upload is None or upload == "":
                if self._data is None:
                    return self.context.missing_value
                else:
                    raise ConversionError(
                        _("Form upload is not a file object"))
            try:
                seek = upload.seek
                read = upload.read
            except AttributeError, e:
                raise ConversionError(
                    _("Form upload is not a file object"), e)
            else:
                seek(0)
                data = read()
                if data or getattr(upload, "filename", ""):
                    return data
                else:
                    return self.context.missing_value
        elif update_action == u"delete":
            return None
        elif update_action == u"add":
            if upload is None or upload == "":
                return None
            else:
                try:
                    seek = upload.seek
                    read = upload.read
                except AttributeError, e:
                    raise ConversionError(
                        _("Form upload is not a file object"), e)
                else:
                    seek(0)
                    data = read()
                    if data or getattr(upload, "filename", ""):
                        return data
                    else:
                        return self.context.missing_value
        else:
            raise NotImplementedError
            return


    def hasInput(self):
        """
        determins if the widget widget has changed
        """

        if self.update_action_name in self.request.form:
            action = self.request.form.get(
                self.update_action_name, self._missing)
            if action == u"keep":
                return False
            elif action == u"delete":
                return True
            else:
                return self.upload_name  in self.request.form


class ImageInputWidget(DefaultFileInputWidget):
    '''
    render a inputwidget that displays the current
    image and lets you choose to delete, replace or just
    leave the current image as is.
    '''
    __call__ = ViewPageTemplateFile("templates/image-widget.pt")

    @property
    def imageURL(self):
        return "./file-image/%s" % self.context.__name__


class FileInputWidget(DefaultFileInputWidget):
    '''
    Upload file attachments
    Replace file attachments
    '''
    fileURL = "./download"

    def _toFieldValue(self, (update_action, upload)):
        value = super(FileInputWidget, self
            )._toFieldValue((update_action, upload))
        if value is None:
            return self.context.missing_value
        self.request.form["form.mimetype"] = upload.headers.getheader(
            "Content-Type")
        self.request.form["form.name"] = upload.filename
        return value


class NoInputWidget(TextWidget):
    def __call__(self):
        return u""


class FileAddWidget(FileInputWidget):
    __call__ = ViewPageTemplateFile("templates/add-file-widget.pt")

class FileEditWidget(FileInputWidget):
    __call__ = ViewPageTemplateFile("templates/edit-file-widget.pt")

class FileDisplayWidget(zope.formlib.widgets.DisplayWidget):
    def __call__(self):
        return u'<a href="%s/download"> %s </a>' \
            % (url.absoluteURL(self.__parent__.context, self.request),
                translate(_("download"), context=self.request),
            )

class ImageDisplayWidget(zope.formlib.widgets.DisplayWidget):
    def __call__(self):
        #from bungeni.ui.utils.url import absoluteURL
        #url = absoluteURL(self.__parent__.context, self.request)
        #return '<img src="' + url + '/file-image/%s" />' % self.context.__name__
        return '<img src="./file-image/%s" />' % self.context.__name__

class HTMLDisplay(zope.formlib.widgets.UnicodeDisplayWidget):

    def __call__(self):
        if self._renderedValueSet():
            value = self._data
        else:
            value = self.context.default
        if value == self.context.missing_value:
            return ""
        return unicode(value)

class RichTextEditor(TextAreaWidget):
    def __call__(self):
        self.cssClass = "tinymce"
        # require tiny-mce
        need("tiny-mce")
        need("tiny-mce-config")
        # render default input widget for text
        input_widget = super(RichTextEditor, self).__call__()
        return input_widget
        
''' !+UNUSED(mr, apr-2012)
class OneTimeEditWidget(TextAreaWidget):
    """
    a text area that is meant to be used once in between edit.
    when you open an edit form it displays the last entry that
    was made and an empty texarea input that will get stored.

    """
    __call__ = ViewPageTemplateFile("templates/one-time-textinput-widget.pt")
'''

'''
class SupplementaryQuestionDisplay(zope.formlib.widget.DisplayWidget):
    """
    If a question has a parent i.e it is a supplementary question
    this displays the subject of the parent, else it states that this is an
    initial question
    """
    def __call__(self):
        if self._data is not None:
            #session = Session()
            #parent = session.query(domain.Question).get(self._data)
            context = removeSecurityProxy (self.context.context)
            parent = context.getParentQuestion()
            return _(u"Supplementary Question to: <br/> %s") % parent
        else:
            return _(u"Initial Question")
'''

class SelectDateWidget(zope.formlib.widget.SimpleInputWidget):
    """A more user freindly date input.
    """
    __call__ = ViewPageTemplateFile("templates/select-date-widget.pt")

    _missing = u""
    minYear = None
    maxYear = None

    minYearDelta = 100
    maxYearDelta = 5

    js_file = open(_path + "/templates/yui-calwidget.js", "r")
    js_template = js_file.read()
    js_file.close()

    def __init__(self, *args):
        super(SelectDateWidget, self).__init__(*args)
        need("yui-calendar")
        need("yui-container")
        need("yui-element")
        need("yui-button")
        self.minDate = datetime.date.today() - datetime.timedelta(
            self.minYearDelta * 365)
        self.maxDate = datetime.date.today() + datetime.timedelta(
            self.maxYearDelta * 365)

    @property
    def time_zone(self):
        """Returns something like:
            tzinfo=<DstTzInfo 'Africa/Nairobi' LMT+2:27:00 STD>
        """
        try:
            time_zone = idatetime.ITZInfo(self.request)
        except TypeError:
            time_zone = pytz.UTC
        return time_zone

    @property
    def field_name(self):
        return self.name.replace(".", "__")

    def set_min_date(self, date):
        if date:
            if type(date) == datetime.date:
                self.minDate = date
            elif type(date) == datetime.datetime:
                self.minDate = date.date()
            else:
                self.minDate = (datetime.date.today() - 
                            datetime.timedelta(self.minYearDelta * 365))
        else:
            self.minDate = (datetime.date.today() - 
                    datetime.timedelta(self.minYearDelta * 365))
    def set_max_date(self, date):
        if date:
            if type(date) == datetime.date:
                self.maxDate = date
            elif type(date) == datetime.datetime:
                self.maxDate = date.date()
            else:
                self.maxDate = (datetime.date.today() + 
                        datetime.timedelta(self.maxYearDelta * 365))
        else:
            self.maxDate = (datetime.date.today() + 
                    datetime.timedelta(self.maxYearDelta * 365))

    def jstr(self, alist):
        return u'["' + u'", "'.join(alist) + u'"]'

    def get_js(self):
        pagedate = datetime.date.today()
        if self.maxDate < pagedate:
            pagedate = self.maxDate
        if ((type(self._data) == datetime.date) or
            (type(self._data) == datetime.datetime)
        ):
            pagedate = self._data
        calendar = self.request.locale.dates.calendars["gregorian"]
        month = _(u"Choose Month")
        year = _(u"Enter Year")
        submit = _("OK")
        cancel = _(u"Cancel")
        invalidYear = _(u"Please enter a valid year")
        months_short = self.jstr(calendar.getMonthAbbreviations())
        months_long = self.jstr(calendar.getMonthNames())
        w_day_1char = self.jstr(
            [dn[:1] for dn in calendar.getDayAbbreviations()])
        w_day_short = self.jstr(
            [dn[:2] for dn in calendar.getDayAbbreviations()])
        w_day_medium = self.jstr(calendar.getDayAbbreviations())
        w_day_long = self.jstr(calendar.getDayNames())
        return self.js_template % {
            "name": self.field_name,
            "sel_day": self._day_name,
            "sel_month": self._month_name,
            "sel_year": self._year_name,
            "txt_date": self.date_name,
            "mindate": self.minDate.strftime("%m/%d/%Y"),
            "maxdate": self.maxDate.strftime("%m/%d/%Y"),
            "pagedate": pagedate.strftime("%m/%Y"),
            "months_short": months_short,
            "months_long": months_long,
            "w_day_1char": w_day_1char,
            "w_day_short": w_day_short,
            "w_day_medium": w_day_medium,
            "w_day_long": w_day_long,
            "month": translate(
                str(month), domain="bungeni", context=self.request),
            "year": translate(
                str(year), domain="bungeni", context=self.request),
            "submit": translate(
                str(submit), domain="bungeni", context=self.request),
            "cancel": translate(
                str(cancel), domain="bungeni", context=self.request),
            "invalidYear": translate(
                str(invalidYear), domain="bungeni", context=self.request)
        }

    def _days(self):
        dl = []
        for i in range(1, 32):
            dl.append("%02d" % (i))
        return dl

    def _months(self):
        """ return a dict of month values and names"""
        calendar = self.request.locale.dates.calendars["gregorian"]
        i = 0
        months = []
        for month in  calendar.getMonthNames():
            i = i + 1
            months.append({"num": "%02d" % i, "name": month})
        return months

    @property
    def _years(self):
        minYear = self.minYear
        if self.minDate:
            minYear = self.minDate.year
        if minYear is None:
            minYear = datetime.date.today().year - int(self.minYearDelta)
        maxYear = self.maxYear
        if self.maxDate:
            maxYear = self.maxDate.year
        if maxYear is None:
            maxYear = datetime.date.today().year + int(self.maxYearDelta)
        return range(maxYear, minYear - 1, -1)

    @property
    def _day_name(self):
        return self.name.replace(".", "__") + "__day"

    @property
    def _month_name(self):
        return self.name.replace(".", "__") + "__month"

    @property
    def _year_name(self):
        return self.name.replace(".", "__") + "__year"

    @property
    def date_name(self):
        return self.name.replace(".", "__") + "__date"

    def hasInput(self):
        """Widgets need to determine whether the request contains an input
        value for them """
        return (self._day_name in self.request.form and
                self._month_name in self.request.form and
                self._year_name in self.request.form)

    def _hasPartialInput(self):
        return (self._day_name in self.request.form or
               self._month_name in self.request.form or
               self._year_name in self.request.form)



    def _getFormInput(self):
        """extract the input value from the submitted form """
        return (self._getFieldInput(self._day_name),
                self._getFieldInput(self._month_name),
                self._getFieldInput(self._year_name))


    def _getFieldInput(self, name):
        return self.request.form.get(name, self._missing)

    def _toFieldValue(self, (day, month, year)):
        """convert the input value to an value suitable for the field."""
        if day == self._missing or month == self._missing or year == self._missing:
            if self.required:
                return self.context.missing_value
            else:
                if day + month + year == self._missing:
                    return None
                else:
                    return self.context.missing_value
        else:
            try:
                time_zone = self.time_zone
                return datetime.date(
                    year=int(year), month=int(month), day=int(day)
                ) #tzinfo=time_zone)
            except ValueError, e:
                raise ConversionError(_(u"Incorrect string data for date"), e)

    def _toFormValue(self, value):
        """convert a field value to a string that can be inserted into the form"""
        if (value == self.context.missing_value) and self.required:
            d = datetime.date.today()
            return (d.day, d.month, d.year)
        else:
            try:
                return (value.day, value.month, value.year)
            except:
                return("0", "0", "0")

    def _getFormValue(self):
        """Returns a field value to a string that can be inserted into the form.
        The difference to _toFormValue is that it takes into account when a form
        has already been submitted but needs to be re-rendered (input error).
        """
        if not self._renderedValueSet():
            if self._hasPartialInput():
                error = self._error
                try:
                    try:
                        value = self.getInputValue()
                    except InputErrors:
                        return self._getFormInput()
                finally:
                    self._error = error
            else:
                if self.required:
                    value = self._getDefault()
                else:
                    value = None
        else:
            value = self._data
        return self._toFormValue(value)

class TextDateWidget(SelectDateWidget):
    """Simple date widget input in a text field.
    """
    __call__ = ViewPageTemplateFile("templates/text-date-widget.pt")

    def hasInput(self):
        """Widgets need to determine whether the request contains an input
        value for them """
        return (self.date_name in self.request.form)

    def _getFormInput(self):
        """extract the input value from the submitted form """
        return (self._getFieldInput(self.date_name))

    def _getFieldInput(self, name):
        return self.request.form.get(name, self._missing)

    def _toFieldValue(self, date):
        """convert the input value to an value suitable for the field."""
        if (date == self.context.missing_value) and self.required:
            return self.context.missing_value
        else:
            try:
                return  datetime.datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError, e:
                if date == "":
                    return
                raise ConversionError(_(u"Incorrect string data for date"), e)

    def _toFormValue(self, value):
        """Convert a field value to a string that can be inserted into the form.
        """
        if (value == self.context.missing_value) and self.required:
            d = datetime.date.today()
            return  datetime.datetime.strftime(d, "%Y-%m-%d")
        else:
            try:
                return datetime.datetime.strftime(value, "%Y-%m-%d")
            except:
                return("")

    def _getFormValue(self):
        """Returns a field value to a string that can be inserted into the form.
        The difference to _toFormValue is that it takes into account when a form
        has already been submitted but needs to be re-rendered (input error).
        """
        if not self._renderedValueSet():
            if self.hasInput():
                error = self._error
                try:
                    try:
                        value = self.getInputValue()
                    except InputErrors:
                        return self._getFormInput()
                finally:
                    self._error = error
            else:
                if self.required:
                    value = self._getDefault()
                else:
                    value = None
        else:
            value = self._data
        return self._toFormValue(value)
    
    @property
    def date_name(self):
        return self.name

DateWidget = TextDateWidget


class TextDateTimeWidget(TextDateWidget):
    
    __call__ = ViewPageTemplateFile("templates/text-datetime-widget.pt")
    
    @property
    def time_name(self):
        return self.name.replace(".", "__") + "__time"

    def hasInput(self):
        return ((self.date_name in self.request.form and
                self.time_name in self.request.form) or 
                (self.name in self.request.form)
        )

    def _hasPartialInput(self):
        return (self.date_name in self.request.form or
                self.time_name in self.request.form)
    
    def _getFormInput(self):
        """extract the input value from the submitted form """
        if not self.time_name in self.request.form:
            return self._getFieldInput(self.name).split(" ")
        return (self._getFieldInput(self.date_name),
                self._getFieldInput(self.time_name))
    
    def _toFormValue(self, value):
        """Convert a field value to a string that can be inserted into the form.
        """
        if (value == self.context.missing_value) and self.required:
            value = datetime.datetime.now()
        try:
            return (datetime.datetime.strftime(value, "%Y-%m-%d"),
                datetime.datetime.strftime(value, "%H:%M"))
        except:
            #log.error("TextDateTimeWidget._toFormValue(%s) FAILED" % (value))
            #debug.log_exc(sys.exc_info(), log_handler=log.error)
            return("", "12:00")
    
    def _toFieldValue(self, (date, time)):
        if (date == self._missing or time == self._missing):
            if self.required:
                return self.context.missing_value
            else:
                if date + time == self._missing:
                    return None
                else:
                    return self.context.missing_value
        else:
            try:
                d = datetime.datetime.strptime(date, "%Y-%m-%d")
                t = datetime.datetime.strptime(time, "%H:%M")
                return datetime.datetime(year=d.year, month=d.month,
                    day=d.day, hour=t.hour, minute=t.minute,)
            except ValueError, e:
                raise ConversionError(
                    _("Incorrect string data for date and time"), e)

DateTimeWidget = TextDateTimeWidget


class SelectDateTimeWidget(SelectDateWidget):

    __call__ = ViewPageTemplateFile("templates/select-datetime-widget.pt")

    @property
    def _hour_name(self):
        return self.name.replace(".", "__") + "__hour"

    @property
    def _minute_name(self):
        return self.name.replace(".", "__") + "__minute"



    def hasInput(self):
        return (super(SelectDateTimeWidget, self).hasInput() and
                    self._hour_name in self.request.form and
                    self._minute_name in self.request.form)
    def _hasPartialInput(self):
        return (super(SelectDateTimeWidget, self)._hasPartialInput() or
            self._hour_name in self.request.form or
            self._minute_name in self.request.form)

    def _getFormInput(self):
        return (super(SelectDateTimeWidget, self)._getFormInput() + 
                    (self._getFieldInput(self._hour_name),
                    self._getFieldInput(self._minute_name)))

    def _hours(self):
        hl = []
        for i in range(0, 24):
            hl.append("%02d" % (i))
        return hl

    def _minutes(self):
        ml = []
        for i in range(0, 60, 5):
            ml.append("%02d" % (i))
        return ml

    def _toFormValue(self, value):
        if value == self.context.missing_value and self.required:
            d = datetime.datetime.now()
            return (d.day, d.month, d.year, d.hour, d.minute)
        else:
            try:
                return (value.day, value.month, value.year,
                    value.hour, value.minute)
            except:
                return ("0", "0", "0", "0", "0")

    def _toFieldValue(self, (day, month, year, hour, minute)):
        if (day == self._missing or
            month == self._missing or
            year == self._missing or
            hour == self._missing or
            minute == self._missing
        ):
            if self.required:
                return self.context.missing_value
            else:
                if day + month + year + hour + minute == self._missing:
                    return None
                else:
                    return self.context.missing_value
        else:
            try:
                time_zone = self.time_zone
                return datetime.datetime(year=int(year), month=int(month),
                    day=int(day), hour=int(hour), minute=int(minute),)
            except ValueError, e:
                raise ConversionError(
                    _(u"Incorrect string data for date and time"), e)

'''
class AutocompleteWidget(SingleDataHelper, ItemsWidgetBase):
    """Render a single selection autocomplete widget using YUI Autocomplete.
    """
    __call__ = ViewPageTemplateFile("templates/auto-complete-widget.pt")

    def __init__(self, field, request):
        vocabulary = field.vocabulary
        super(AutocompleteWidget, self).__init__(field, vocabulary, request)
        # !+AUTOCOMPLETE(mr, oct-2010) super class ItemsWidgetBase requires
        # the additional vocabulary parameter, but passing it the one defined
        # by the field does not work

        #need("yui-autocomplete")
        # !+AUTOCOMPLETE(mr, oct-2010) get the hardwired absolute ref to the
        # public (across network) YUI js resource files out of the template,
        # and configured to pick up the file from the deployment instance.

    def value(self):
        return self._getFormValue()
'''

''' !+UNUSED - for a "view listing" Field that does not (otherwise need to) 
define an appropriate property e.g. ChangeDescriptor:user_id.
from bungeni.core.dc import IDCDescriptiveProperties
class UserDisplayWidget(zope.formlib.widget.DisplayWidget):
    def __call__(self):
        return IDCDescriptiveProperties(self.user).title
'''

def _render_link_to_mp_or_user(user_id, context, request):
    """Render the linked name of a Member of Parliament (or the User)
    to the MP's (or the User's) "home" view.
    
    For use by forms in "view" mode.
    """
    try:
        mp = get_member_of_parliament(user_id)
        return mp.user.combined_name
        #!+BUSINESS(mb, feb-2013) is deprecated - how to render
        # bicameral installation
        #return zope.formlib.widget.renderElement("a",
        #    contents=mp.user.combined_name,
        #    href="/workspace/members/obj-%s/" % (mp.membership_id))
    except NoResultFound:
        # not a member of parliament 
        #
        # Note that self.context is the field.property instance, while 
        # self.context.context is the actual model instance with a "user" 
        # relation/attribute -- BUT the user instance here may not 
        # necessarily be the "right" user instance e.g. for case of 
        # UserDelegation, the user we would want would be the one given by 
        # the "delegation" attribute. So, we can only retrieve by user_id...
        user = get_user(user_id)
        if IAdminSectionLayer.providedBy(request):
            # for now, only if admin, we link into the admin view...
            return zope.formlib.widget.renderElement("a",
                contents=user.combined_name,
                href="/admin/content/users/obj-%s/" % (user_id))
        else:
            # !+user_directory_listing_view(mr, aug-2012) link to a canonical
            # directory listing page for the user (when that is available).
            # Just the display text (no directory page to link to as yet).
            return user.combined_name


class UserURLDisplayWidget(zope.formlib.widget.DisplayWidget):
    """Display the linked name of a Member of Parliament, using as URL the
    MP's "home" view.

    For use by forms in "view" mode.
    """
    
    def __call__(self):
        # this (user_id) attribute's value IS self._data
        user_id = self._data
        return _render_link_to_mp_or_user(user_id, self.context, self.request)


class widget(object):
    """Traverce adapter for getting widget by name from form views
    """
    interface.implements(zope.traversing.interfaces.ITraversable)
    
    def __init__(self, context, request):
        self.context = zope.security.proxy.removeSecurityProxy(context)
        self.request = request

    def traverse(self, name, remaining):
        form = self.context
        form.update()

        if hasattr(form, 'widgets'):
            widget = form.widgets.get(name)

            if widget:
                return widget

        raise zope.traversing.namespace.LocationError(form, name)


class AutoCompleteAjax(object):

    """Remote Data Sourcse ajax view for autocomplete widget
    """

    def __call__(self, *args, **kw):
        context = zope.security.proxy.removeSecurityProxy(self.context)
        query = self.request.get("q")
        return """{"ResultSet": %s}""" % context.filter(query, True)


template = """
    %(html)s
    %(javascript)s
    """


OPT_PREFIX = 'yui_'
LEN_OPT_PREFIX = len(OPT_PREFIX)


class IAutoCompleteWidget(interface.Interface):
    """Markup interface for autocomplete widget
    """

class _AutoCompleteWidget(ItemsEditWidgetBase):
    """Zope3 Implementation of YUI autocomplete widget.
    Can be used with common ChoiceProperty. remote_data - parameter to choose
    type of datasourse, if False (by default, when local) else True when remote
    Can be configured by setting widget attributes with prefix %s.
    List of attributes you can find in
    http://developer.yahoo.com/yui/autocomplete""" % OPT_PREFIX

    interface.implements(IAutoCompleteWidget)

    remote_data = False

    @property
    def options(self):
        _options = {
            "autoHighlight": True,
            "forceSelection": True,
            "allowBrowserAutocomplete": False

        }

        for k in dir(self):
            if k.startswith(OPT_PREFIX):
                _options[k[LEN_OPT_PREFIX:]] = getattr(self, k)

        items = []

        for k, v in _options.items():
            if isinstance(v, bool):
                v = str(v).lower()
            elif isinstance(v, basestring):
                try:
                    v = int(v)
                except ValueError:
                    v = "\"%s\"" % v

            items.append("oAC.%s = %s;" % (k, v))

        return "\n".join(items)


    @property
    def dataSource(self):
        return self.filter()

    def filter(self, query=None, ajax=False):
        s = """{name: "%(name)s", id: "%(id)s" }""" if not ajax else \
            """{"name": "%(name)s", "id": "%(id)s" }"""

        def check_item(item):
            s = [self.textForValue(item).lower(), ]
            s += s[0].split(" ")
            return any(map(lambda x: x.startswith(query.lower()), s))

        items = filter(check_item, list(self.vocabulary)) if query else \
            list(self.vocabulary)
        items = map(lambda x: s % {'id': x.token, 'name': self.textForValue(x)},
            items)

        return "[%s]" % ",\n".join(items)

    @property
    def oDS(self):
        if self.remote_data:
            url = "%s/++widget++%s/filter" % \
                (str(self.request.URL), self.name.split('.')[-1])
            return """
                var oDS = new YAHOO.util.XHRDataSource("%s");
                oDS.responseType = YAHOO.util.XHRDataSource.TYPE_JSON;
                oDS.scriptQueryParam = "q";
                oDS.responseSchema = {
                  resultsList : "ResultSet",
                  fields : ["name", "id"]
                };
            """ % url
        kw = {"dsname": self.name.replace('.', '_'),
              "data": self.dataSource,
              }
        return """
            var %(dsname)s_data = %(data)s;
            var %(dsname)s_filter = function(sQuery) {
                var query = unescape(sQuery).toLowerCase(),
                    item,
                    items,
                    i=0,
                    j=0,
                    ll,
                    l=%(dsname)s_data.length,
                    matches = [];

                for(; i<l; i++) {
                    item = %(dsname)s_data[i];
                    items = item.name.split(" ");
                    items[items.length] = item.name;
                    ll = items.length;
                    for(j=0; j<items.length; j++) {
                        if (items[j].toLowerCase().indexOf(query) == 0) {
                            matches[matches.length] = item;
                            break;
                        }
                    }
                }

                return matches;
            };

            var oDS = new YAHOO.util.FunctionDataSource(%(dsname)s_filter);
            oDS.responseSchema = {fields : ["name", "id"]};
        """ % kw

    @property
    def javascript(self):
        kw = {"id": self.name,
              "dsname": self.name.replace('.', '_'),
              "oDS": self.oDS,
              "data": self.dataSource,
              "options": self.options,
              "help_text": translate(
                _(u"start typing to chose $fname...",
                    mapping = dict(fname=self.context.title)
                 ),
                 context=self.request
              )
        }

        return """
            <script type="text/javascript">
                YAHOO.namespace('oa.autocomplete');
                YAHOO.oa.autocomplete.%(dsname)s_func = new function() {

                    %(oDS)s

                    var helpText = "%(help_text)s";
                    var oAC = new YAHOO.widget.AutoComplete("%(id)s",
                        "%(id)s.container", oDS);
                    %(options)s
                    oAC.resultTypeList = false;
                    var myHiddenField = YAHOO.util.Dom.get("%(id)s.hidden");
                    var myHandler = function(sType, aArgs) {
                        var myAC = aArgs[0];
                        var elLI = aArgs[1];
                        var oData = aArgs[2];
                        myHiddenField.value = oData.id;
                    };
                    var helpTextHandler = function(event, args){
                        input = args[0].getInputEl();
                        if(event == "textboxBlur"){
                            if(!input.value){
                                input.value = helpText;
                            }
                        }else if(event == "textboxFocus"){
                            if(input.value==helpText){
                                input.value = "";
                            }
                        }
                    }
                    oAC.itemSelectEvent.subscribe(myHandler);
                    oAC.textboxBlurEvent.subscribe(helpTextHandler);
                    oAC.textboxFocusEvent.subscribe(helpTextHandler);
                    oAC.getInputEl().value = helpText;
                    return {
                        oDS: oDS,
                        oAC: oAC
                    };
                }();
            </script>
            """ % kw

    #!+AUTOCOMPLETE_WIDGET(ah, oct-2011) verify valid input by checking if the
    # input data is not None. The default hasInput() returns true even if the 
    # input value is none
    def hasInput(self):
        return self._data is not None

    @property
    def html(self):
        kw = {"id": self.name}
        if self._data is not None and self._data is not self._data_marker:
            term = self.vocabulary.getTerm(self._data)
            kw["value"] = term.token
            kw["text"] = self.textForValue(term)
        elif (self.hasInput() and self.hasValidInput() and
            self.getInputValue() is not None
        ):
            token = self._data
            if self._data is self._data_marker:
                token = self.getInputValue()
            term = self.vocabulary.getTerm(token)
            kw["value"] = term .token
            kw["text"] = self.textForValue(term)
        else:
            kw["text"] = kw["value"] = ""

        return """
            <div id="%(id)s.autocomplete" class="yui-skin-sam">
              <input id="%(id)s" type="text" value="%(text)s">
              <div id="%(id)s.container"></div>
              <input id="%(id)s.hidden" name="%(id)s" value="%(value)s"
                  type="hidden">
            </div>
            """ % kw

    @property
    def style(self):
        return """
        <style type="text/css">
          .yui-skin-sam .yui-ac-input { position:static;width:20em; vertical-align:middle;}
          .yui-skin-sam .yui-ac-container { width:20em;left:0px;}
        </style>
        """

    def setCurrentData(self):
        """Set current value if available
        """
        #!+FORMS(mb, Feb-2012) Investigate why this widget does not have _data
        # set similar to other widgets - perhaps related to`CustomWidgetFactory`
        record_data = getattr(removeSecurityProxy(self.__parent__.context),
            self.__parent__.getName(), self._data_marker
        )
        if record_data != self._data_marker:
            self._data = record_data

    def __call__(self):
        self.setCurrentData()
        need("yui-get")
        need("yui-connection")
        need("yui-animation")
        need("yui-json")
        need("yui-datasource")
        need("yui-autocomplete")

        contents = []
        contents.append(self.style)
        contents.append(template % {"html": self.html,
            "javascript": self.javascript})

        return "\n".join(contents)


# We instantiate an AutoCompleteWidget class customized as we need it
AutoCompleteWidget = CustomWidgetFactory(_AutoCompleteWidget, remote_data=True)

def AutoCompleteWidgetOrSingleChoice(*args, **kws):
    """A "wrapper" widget, for "edit" mode, that decides dynamically whether to
    use the AutoCompleteWidget (if multiple options available) or a DropDown
    (that therefore will have upto only a single option!).
    
    Using an auto complete widget (or equivalent variation of) may be needed 
    some cases, but inapropriate in others e.g. using auto-complete for:
    - when an MP/User must be selected from entire list of MP/Users (that 
      will be in the hundreds) e.g. when Clerk is creating a document, or 
      admin adding a member to a group.
    - (not ideal, but could be OK) when a delegated must select the
      delegator on behalf of whom he is creating a document (s/he may have 
      been delegated multiple times even if the common case would likley be 
      only once).
    But, for the very common case of when an MP (or a delegated-only-once user) 
    is creating an own (delegator's) document, a autocomplete makes no sense 
    at all--in fact in that case, this only-one-value-possible field should 
    be set automatically... 

    !+ enhance the only-1-option case to simply set the value and just 
    display it as if in "view" mode.
    """
    field_property = args[0] # should always be zope.schema.Choice
    if len(field_property.vocabulary) > 1:
        return AutoCompleteWidget(*args, **kws)
    else:
        return UserDropDownWidget(*args, **kws)


class VocabularyDefaultDropDownWidget(DropdownWidget):

    interface.implements(IGenenerateVocabularyDefault)

    def __init__(self, field, request):
        super(VocabularyDefaultDropDownWidget, self).__init__(
            field, field.vocabulary, request)

    def getDefaultVocabularyValue(self):
        raise NotImplemented
        
        user = get_login_user()
        try:
            self.context.vocabulary.getTerm(user.user_id)
        except LookupError:
            return None
        return user.user_id

class UserDropDownWidget(VocabularyDefaultDropDownWidget):

    def getDefaultVocabularyValue(self):
        user = get_login_user()
        try:
            self.context.vocabulary.getTerm(user.user_id)
        except LookupError:
            return None
        return user.user_id

class LanguageLookupWidget(VocabularyDefaultDropDownWidget):

    def getDefaultVocabularyValue(self):
        return get_default_language()


class TreeVocabularyWidget(DropdownWidget):
    """
    This widget renders a tree widget based on terms in an xml
    vocabulary - Each vocabulary utility must implement a json
    generation function see vocabulary.py and interfaces.py
    It can be used with standard Choice fields to render a tree
    vocab
    """
    def __init__(self, field, request):
        super(TreeVocabularyWidget, self).__init__(field,
            field.vocabulary, request)


    def __call__(self):
        need("dynatree")
        contents = []
        contents.append(template % {"html": self.html,
            "javascript": self.javascript()})
        return "\n".join(contents)


    def _toFieldValue(self, value):
        if value:
            return "\n".join(value.rstrip("|").split("|"))
        else:
            return None

    def dataSource(self):
        selected = []
        if self.has_input:
            selected = self.getInputValue().split("\n")
        elif self.has_data:
            selected = self._data.split("\n")
        return self.context.vocabulary.generateJSON(selected=selected)

    @property
    def has_input(self):
        return (self.hasInput() and self.hasValidInput()
            and self.getInputValue() is not None
        )

    @property
    def has_data(self):
        return self._data is not None and self._data is not self._data_marker

    @property
    def treeId(self):
        normalized_name = self.name .replace(".", "_")
        return "%s_tree" % normalized_name
    
    @property
    def html(self):
        kw = {"id": self.name,
              "tree_id": self.treeId
              }

        if self.has_data:
            kw["value"] = "|".join(self._data.split("\n"))
        elif self.has_input:
            kw["value"] = "|".join(self.getInputValue().split("\n"))
        else:
            kw["value"] = ""

        return """
            <div id="dynatree">
              <div id="%(tree_id)s"></div>
              <input id="%(id)s" name="%(id)s" value="%(value)s"
                  type="hidden">
            </div>
            """ % kw
        
    def javascript(self):
        kw = {"id": self.name,
              "data": self.dataSource(),
              "tree_id": self.treeId
             }
        return """
            <script type="text/javascript">
                %(tree_id)s = %(data)s;
             </script>
        """ % kw 


# !+RENAME TreeTermsDisplayWidget?
class TermsDisplayWidget(zope.formlib.widget.UnicodeDisplayWidget):
    
    hint = _(u"selected subject terms") # !+ should be init param?
    
    @property
    def has_value(self):
        return (self._data is not None and
            self._data is not self._data_marker
        )

    def __call__(self):
        if not self.has_value:
            return "<span>%s</span>" %(_(u"no subjects"))
        
        lang = get_default_language()
        term_texts = [
            self.context.vocabulary.getTermCaptionById(data_value, lang)
            for data_value in self._data.split("\n")
        ]
        return  "<ul>%s</ul>" % (
            "".join([ "<li>%s</li>" % (t) for t in term_texts ]))


class YesNoDisplayWidgetBase(ItemDisplayWidget):

    def __call__(self):
        value = self._getFormValue()
        term = self.vocabulary.getTerm(value)
        return self.textForValue(term)

def YesNoDisplayWidget(*attrs, **kw):
    return CustomWidgetFactory(YesNoDisplayWidgetBase, *attrs, **kw)

def text_input_search_widget(table_id, field_id):
    """Default search widget displays a text input field.
    """
    script = open("%s/templates/text-input-search-widget.js" % (_path)).read()
    return "", script % {"table_id": table_id, "field_id": field_id}


class DateFilterWidget(form.PageForm):

    macro_template = NamedTemplate("alchemist.form")
    template = ViewPageTemplateFile("templates/date-input-search.pt")

    def __init__(self, context, request, table_id, field_id):
        self.prefix = "form_%s_%s" % (table_id, field_id)
        super(DateFilterWidget, self).__init__(context, request)

    class IDateRangeSchema(interface.Interface):
        range_start_date = schema.Date(
            title=_(u"From"),
            description=_(u"Leave blank or set lower limit"),
            required=False)

        range_end_date = schema.Date(
            title=_(u"To"),
            description=_(u"Leave blank or set upper limit"),
            required=False)

    macro_template = NamedTemplate("alchemist.form")
    template = ViewPageTemplateFile("templates/date-input-search.pt")
    form_fields = form.Fields(IDateRangeSchema, render_context=True)
    form_fields["range_start_date"].custom_widget = DateWidget
    form_fields["range_end_date"].custom_widget = DateWidget
    
    def setUpWidgets(self, ignore_request=False, cookie=None):
        class context:
            range_start_date = None
            range_end_date = None
        self.adapters = {
            self.IDateRangeSchema: context,
            }
        self.widgets = form.setUpWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            form=self, adapters=self.adapters, ignore_request=True)

    @form.action(_(u"Ok"), name="ok")
    def handle_ok(self, action, data):
        #Handled by Javascript
        pass

    @form.action(_(u"Clear"), name="clear")
    def handle_clear(self, action, data):
        #Handled by Javascript
        pass


def date_input_search_widget(table_id, field_id):
    import bungeni.ui.utils.common
    form = DateFilterWidget(common.get_application(), 
        bungeni.ui.utils.common.get_request(), 
        table_id, field_id)
    html = '<div id="date_input_search_widget_%(table_id)s_%(field_id)s" style="display: none;">%(html)s</div>' \
           % {"table_id": table_id,
              "field_id": field_id,
              "html": form.render()}
    script = open("%s/templates/date-input-search-widget.js" % (_path)).read()
    return html, script % {"table_id": table_id, "field_id": field_id}
