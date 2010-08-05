import re
import os
from appy.pod.renderer import Renderer
from zope.publisher.browser import BrowserView
import time
import datetime
import tempfile
from zope.security.proxy import removeSecurityProxy
import htmlentitydefs
from xml.dom.minidom import parseString
from bungeni.ui import zcml
from interfaces import IOpenOfficeConfig
from zope.component import getUtility
from ore.alchemist import Session
from bungeni.models import domain
from zope import interface
from zope.formlib import form
from zope.formlib import namedtemplate
from zope.app.pagetemplate import ViewPageTemplateFile
from zope import schema
from bungeni.ui.widgets import SelectDateWidget
from bungeni.ui.calendar import utils
from bungeni.ui.tagged import get_states
from bungeni.ui.i18n import _
from bungeni.ui.utils import misc, url as ui_url, queries, debug
from bungeni.ui.menu import get_actions
from bungeni.ui.forms.common import set_widget_errors
from bungeni.ui import vocabulary
from bungeni.core.location import location_wrapped
from bungeni.core.interfaces import ISchedulingContext
#from bungeni.core.schedule import PlenarySchedulingContext
from bungeni.core.odf import OpenDocument
from zope.schema.vocabulary import SimpleVocabulary
from zope.app.form.browser import MultiCheckBoxWidget as _MultiCheckBoxWidget
def verticalMultiCheckBoxWidget(field, request):
    vocabulary = field.value_type.vocabulary
    widget = _MultiCheckBoxWidget(field, vocabulary, request)
    widget.cssClass = u"verticalMultiCheckBoxWidget"
    widget.orientation='vertical'
    return widget 

def horizontalMultiCheckBoxWidget(field, request):
    vocabulary = field.value_type.vocabulary
    widget = _MultiCheckBoxWidget(field, vocabulary, request)
    widget.cssClass = u"horizontalMultiCheckBoxWidget"
    widget.orientation='horizontal'
    return widget 
    
def availableItems(context):
    items = ('Bills',
                'Agenda Items',
                'Motions',
                'Questions',
                'Tabled Documents',
                )
    return SimpleVocabulary.fromValues(items)
           
def billOptions(context):
    items = ('Title',
             'Summary', 
             'Text', 
             'Owner',
             'Cosignatories',
            )
    return SimpleVocabulary.fromValues(items)

def agendaOptions(context):
    items = ('Title',
             'Text', 
             'Owner',
            )
    return SimpleVocabulary.fromValues(items)

def motionOptions(context):
    items = ('Title',
             'Number', 
             'Text', 
             'Owner',
            )
    return SimpleVocabulary.fromValues(items)

def tabledDocumentOptions(context):
    items = ('Title',
             'Number', 
             'Text', 
             'Owner',
            )
    return SimpleVocabulary.fromValues(items)

def questionOptions(context):
    items = ('Title',
             'Number', 
             'Text', 
             'Owner',
             #'Response',
             'Type',
            )
    return SimpleVocabulary.fromValues(items)



class ReportView(form.PageForm):
    result_template = ViewPageTemplateFile('templates/reports.pt')
    class IReportForm(interface.Interface):
        item_types = schema.List(title=u'Items to include',
                   required=False,
                   value_type=schema.Choice(
                    vocabulary="Available Items"),
                   )
        bill_options = schema.List( title=u'Bill options',
                       required=False,
                       value_type=schema.Choice(
                       vocabulary='Bill Options'),
                         )
        agenda_options = schema.List( title=u'Agenda options',
                                        required=False,
                                        value_type=schema.Choice(
                                        vocabulary='Agenda Options'),)
        motion_options = schema.List( title=u'Motion options',
                                        required=False,
                                        value_type=schema.Choice(
                                        vocabulary='Motion Options'),)
        question_options = schema.List( title=u'Question options',
                                          required=False,
                                          value_type=schema.Choice(
                                          vocabulary='Question Options'),)
        tabled_document_options = schema.List( title=u'Tabled Document options',
                                          required=False,
                                          value_type=schema.Choice(
                                          vocabulary='Tabled Document Options'),)
        note = schema.TextLine( title = u'Note',
                                required=False,
                                description=u'Optional note regarding this report'
                        )
                        
    template = namedtemplate.NamedTemplate('alchemist.form')
    form_fields = form.Fields(IReportForm)
    form_fields['item_types'].custom_widget = horizontalMultiCheckBoxWidget
    form_fields['bill_options'].custom_widget = verticalMultiCheckBoxWidget
    form_fields['agenda_options'].custom_widget = verticalMultiCheckBoxWidget
    form_fields['motion_options'].custom_widget = verticalMultiCheckBoxWidget
    form_fields['question_options'].custom_widget = verticalMultiCheckBoxWidget
    form_fields['tabled_document_options'].custom_widget = verticalMultiCheckBoxWidget
    
    class contexta:
        item_types = 'Bills'
        bill_options = 'Title'
        agenda_options = 'Title'
        question_options = 'Title'
        motion_options = 'Title'
        tabled_document_options = 'Title'
        note = None
    
    def setUpWidgets(self, ignore_request=False):
        self.adapters = {
            self.IReportForm: self.contexta
            }
        self.widgets = form.setUpEditWidgets(
            self.form_fields, self.prefix, self.context, self.request,
                    adapters=self.adapters, ignore_request=ignore_request)
    def update(self):
        self.status = self.request.get('portal_status_message', '')
        super(ReportView, self).update()
        set_widget_errors(self.widgets, self.errors)

    def validate(self, action, data):
        errors = super(ReportView, self).validate(action, data)
        self.time_span = TIME_SPAN.daily
        if 'doc_type' in data:
            if data['doc_type'] == "Order of the day":
                self.time_span = TIME_SPAN.daily
            elif data['doc_type'] == "Proceedings of the day":
                self.time_span = TIME_SPAN.daily
            elif data['doc_type'] == "Weekly Business":
                self.time_span = TIME_SPAN.weekly
            elif data['doc_type'] == "Questions of the week":
                self.time_span = TIME_SPAN.weekly
       
        if 'date' in data:
            start_date = data['date']
        else:
            start_date = self.date
        end_date = self.get_end_date(start_date, time_span)

        parliament = queries.get_parliament_by_date_range(self, start_date, end_date)
        session = queries.get_session_by_date_range(self, start_date, end_date)

        if parliament is None:
            errors.append(interface.Invalid(
                _(u"A parliament must be active in the period"),
                "date"))

        return errors

    @form.action(_(u"Preview"))
    def handle_preview(self, action, data):
        self.process_form(data)
        self.save_link = ui_url.absoluteURL(self.context, self.request)+"/save_report"
        self.body_text = self.result_template()
        return self.main_result_template()
        
    def get_end_date(self, start_date, time_span):
        if time_span is TIME_SPAN.daily:
            return start_date + timedelta(days=1)
        elif time_span is TIME_SPAN.weekly:
            return start_date + timedelta(weeks=1)
        
        raise RuntimeError("Unknown time span: %s" % time_span)
        
    def get_sittings_items(self, start, end):
            """ return the sittings with scheduled items for 
                the given daterange"""
            session = Session()
            query = session.query(domain.GroupSitting).filter(
                sql.and_(
                    domain.GroupSitting.start_date.between(start,end),
                    domain.GroupSitting.group_id == self.context.group_id)
                    ).order_by(domain.GroupSitting.start_date
                    ).options(
                        eagerload('sitting_type'),
                        eagerload('item_schedule'), 
                        eagerload('item_schedule.item'),
                        eagerload('item_schedule.discussion'),
                        eagerload('item_schedule.category'))
            items = query.all()
        #items.sort(key=operator.attrgetter('start_date'))
            for item in items:
                if self.display_minutes:
                    item.item_schedule.sort(key=operator.attrgetter('real_order'))
                else:
                    item.item_schedule.sort(key=operator.attrgetter('planned_order'))
                    item.sitting_type.sitting_type = item.sitting_type.sitting_type.capitalize() 
                    #s = queries.get_session_by_date_range(self, item.start_date, item.end_date)
                
            return items    
    def process_form(self, data):
        if 'date' in data:
            self.start_date = data['date']
        else:
            self.start_date = self.date
        time_span = TIME_SPAN.daily 
        
        self.end_date = self.get_end_date(self.start_date, time_span)
        if 'date' in data:
            self.sitting_items = self.get_sittings_items(self.start_date, self.end_date)
            self.single="False"
        else:
            session = Session()
            self.sitting_items = []
            st = self.context.sitting_id
            sitting = session.query(domain.GroupSitting).get(st)
            self.sitting_items.append(sitting)
            self.single="True"
            
        self.option_data = data
        if "draft" in data:
            sitting_items = []
            for sitting in self.sitting_items:
                if data["draft"]=="No":
                    if sitting.status in get_states("groupsitting", 
                                                tagged=["published"]):
                        sitting_items.append(sitting)
                elif data["draft"]=="Yes":
                    if sitting.status in get_states("groupsitting", 
                                                tagged=["draft", "published"]):
                        sitting_items.append(sitting)
            self.sitting_items = sitting_items
        
        if self.display_minutes:
            self.link = ui_url.absoluteURL(self.context, self.request)+'/votes-and-proceedings'
        else :
            self.link = ui_url.absoluteURL(self.context, self.request)+'/agenda'
        
        try:
            self.group = self.context.get_group()
        except:
            session = Session()
            self.group = session.query(domain.Group).get(self.context.group_id)
            
        if IGroupSitting.providedBy(self.context):
            self.back_link = ui_url.absoluteURL(self.context, self.request)  + '/schedule'
        elif ISchedulingContext.providedBy(self.context):
            self.back_link = ui_url.absoluteURL(self.context, self.request)
                         
class GroupSittingContextAgendaReportView(ReportView):
    display_minutes = False
                        
class GroupSittingContextMinutesReportView(ReportView):
    display_minutes = True
        
class SchedulingContextReportView(ReportView):
    class ISchedulingContextReportForm(ReportView.IReportForm):
        doc_type = schema.Choice(
                    title = _(u"Document Type"),
                    description = _(u"Type of document to be produced"),
                    values= ['Order of the day',
                             'Weekly Business',
                             'Questions of the week'],
                    required=True
                    )
        date = schema.Date(
            title=_(u"Date"),
            description=_(u"Choose a starting date for this report"),
            required=True)
    class contexta(ReportView.contexta):
            date = None
            doc_type = 'Order of the day'        
    form_fields = form.Fields(ISchedulingContextReportForm)        
    def setUpWidgets(self, ignore_request=False):
        self.adapters = {
                self.ISchedulingContextReportForm: self.contexta
            }
        self.widgets = form.setUpEditWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            adapters=self.adapters, ignore_request=ignore_request)
        
class SchedulingContextAgendaReportView(ReportView):
    display_minutes = False

class SchedulingContextMinutesReportView(ReportView):
    display_minutes = True


def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)

class DownloadDocument(BrowserView):
    
    #path to the odt template
    odt_file = os.path.dirname(__file__) + '/calendar/agenda.odt'
    def __init__(self, context, request):
        self.report = removeSecurityProxy(context)
        super(DownloadDocument, self).__init__(context, request)
        
    def cleanupText(self):
        '''This function generates an ODT document from the text of a report'''
        #This should really be at the top of this file.
        #Leaving it here for the time being so that having 
        #libtidy is not a requirement to run bungeni
        import tidy
        body_text = self.report.body_text
        #utidylib options
        options = dict(output_xhtml=1, 
                    add_xml_decl=1, 
                    indent=1, 
                    tidy_mark=0,
                    char_encoding='utf8',
                    quote_nbsp=0)
        #remove html entities from the text
        ubody_text = unescape(body_text)
        #clean up xhtml using tidy
        aftertidy = tidy.parseString(ubody_text.encode('utf8'), **options)
        #tidy returns a <tidy.lib._Document object>
        dom = parseString(str(aftertidy))
        nodeList = dom.getElementsByTagName("body")
        text = ""
        for childNode in nodeList[0].childNodes:
            text += childNode.toxml()
        dom.unlink()
        return text

class DownloadODT(DownloadDocument): 
    #appy.Renderer expects a file name of a file that does not exist.
    #TODO Find a better way
    tempFileName = os.path.dirname(__file__) + '/tmp/%f.odt' % ( time.time())  
    def __call__(self):
        self.request.response.setHeader('Content-type', 
                                        'application/vnd.oasis.opendocument.text')
        self.request.response.setHeader('Content-disposition', 
                                        'inline;filename="'+
                                        removeSecurityProxy(self.report.report_type)+"_"+
                                        removeSecurityProxy(self.report.start_date).strftime('%Y-%m-%d')+'.odt"')
        if self.report.odt_report is None:
            params = {}
            params['body_text'] = self.cleanupText()
            renderer = Renderer(self.odt_file, params, self.tempFileName)
            renderer.run()
            f = open(self.tempFileName, 'rb')
            doc = f.read()
            f.close()      
            os.remove(self.tempFileName)    
            session = Session()
            r = session.query(domain.Report).get(self.report.report_id)
            r.odt_report = doc
            session.commit()
            return doc  
        else:
            #import pdb; pdb.set_trace()
            return ""+self.report.odt_report.__str__()

    
class  DownloadPDF(DownloadDocument):
    #appy.Renderer expects a file name of a file that does not exist.
    #TODO Find a better way
    tempFileName = os.path.dirname(__file__) + '/tmp/%f.pdf' % ( time.time())
     
    def __call__(self): 
        self.request.response.setHeader('Content-type', 'application/pdf')
        self.request.response.setHeader('Content-disposition', 'inline;filename="'
                            +removeSecurityProxy(self.report.report_type)+"_"
                            +removeSecurityProxy(self.report.start_date).strftime('%Y-%m-%d')+'.pdf"')
        if self.report.pdf_report is None:
            params = {}
            params['body_text'] = self.cleanupText()
            openofficepath = getUtility(IOpenOfficeConfig).getPath()
            renderer = Renderer(self.odt_file, params, self.tempFileName, pythonWithUnoPath=openofficepath)
            renderer.run()
            f = open(self.tempFileName, 'rb')
            doc = f.read()
            f.close()
            os.remove(self.tempFileName)
            session = Session()
            r = session.query(domain.Report).get(self.report.report_id)
            r.pdf_report = doc
            session.commit()
            return doc 
        else:
            return self.report.pdf_report.__str__()
        
