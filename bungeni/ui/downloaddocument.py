# encoding: utf-8
# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt
from __future__ import with_statement
"""Views for download of documents in formats - PDF/ODT

$Id$
"""

log = __import__("logging").getLogger("bungeni.ui")


import os
import time
import re
import htmlentitydefs
import random
import base64
import mimetypes
from tidylib import tidy_fragment
from lxml import etree

from zope.security.proxy import removeSecurityProxy
from zope.component import getUtility
#from zope.lifecycleevent import ObjectCreatedEvent
#from zope.event import notify
from zope.component.interfaces import ComponentLookupError
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.publisher.browser import BrowserView
from zope.app.component.hooks import getSite

from interfaces import IOpenOfficeConfig
from bungeni.alchemist import Session
from bungeni.models import domain, interfaces
from appy.pod.renderer import Renderer


from bungeni.capi import capi
from bungeni.ui.i18n import _
from bungeni.ui.utils import url, misc
from bungeni.ui.reporting import generators
from bungeni.ui import vocabulary

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

def cleanupText(text):
    """This method cleans up the text of the report using libtidy"""
    #tidylib options
    options = dict(output_xhtml=1,
                    add_xml_decl=1,
                    indent=1,
                    tidy_mark=0,
                    char_encoding="utf8",
                    quote_nbsp=0)
    #remove html entities from the text
    ubody_text = unescape(text)
    #clean up xhtml using tidy
    aftertidy, errors = tidy_fragment(ubody_text.encode("utf8"), options, keep_doc=False)
    #tidylib returns a <tidy.lib._Document object>
    return str(aftertidy)

class DocumentGenerationError(Exception):
    """Raised when document generation fails"""

class DownloadDocument(BrowserView):
    """Abstact base class for ODT and PDF views"""
    #path to the odt template. Must be set by sub-class
    oo_template_file = None
    #Error page in case of failure to generate document
    error_template = ViewPageTemplateFile("templates/report-error.pt")
    #Custom Template selection UI
    #Source document
    document = None
    #document type to be produced
    document_type = None
    site_url = ""
    error_messages = []

    def __init__(self, context, request):
        self.document = removeSecurityProxy(context)
        self.site_url = url.absoluteURL(getSite(), request)
        super(DownloadDocument, self).__init__(context, request)

    def setHeader(self, document_type):
        """Set Content-type and Content-disposition header
        """        
        self.request.response.setHeader("Content-type",
            mimetypes.guess_type(self.file_name)[0] or "application/octet-stream"
        )
        self.request.response.setHeader("Content-disposition", 
            'attachment;filename="%s"' % self.file_name
        )
    def bodyText(self):
        """Returns body text of document. Must be implemented by subclass"""

    @property
    def file_name(self):
        fname = misc.slugify(self.document.title)
        if interfaces.IReport.providedBy(self.document):
            fname = misc.slugify(
                u'-'.join((self.document.title, 
                    self.document.status_date.isoformat(), 
                ))
            )
        return u"%s.%s" % (fname, self.document_type)

    def generateDocumentText(self):
        """Generate document using template from templates stored in
        
        src/bungeni_custom/reporting/templates/documents
        Each template has a config parameter with the document type for
        which it may be used.
        """
        def default_template(templates):
            default_templates = filter(lambda term: "default" in term.doctypes,
                templates
            )
            if default_templates:
                return default_templates[0].value
            return  None
        template_vocabulary = vocabulary.document_xhtml_template_factory()
        doc_templates = [ term.value for term in template_vocabulary if 
            self.document.type in term.doctypes
        ]
        log.debug("Looking for templates to generate [%s] report. Found : %s",
            self.document.type, doc_templates
        )
        if doc_templates:
            doc_template = doc_templates[0]
        else:
            doc_template = default_template(template_vocabulary)
        if doc_template is None:
            self.error_messages.append(
                _(u"No template for document of type: ${dtype}. Contact admin.",
                    mapping={ "dtype": self.document.type }
                )
            )
            raise DocumentGenerationError(
                "No template found to generate this document"
            )
        generator = generators.ReportGeneratorXHTML(doc_template, 
            self.document
        )
        return generator.generateReport()

    def generateDoc(self):
        """Generates ODT/PDF doc"""
        tempFileName = os.path.dirname(__file__) + "/tmp/%f-%f.%s" % (
                            time.time(),random.random(),self.document_type)
        if (interfaces.IReport.providedBy(self.document) or 
            interfaces.ISittingReport.providedBy(self.document)):
            document_text = self.bodyText()
        else:
            document_text = self.generateDocumentText()
        params = dict(body_text = cleanupText(document_text))
        openofficepath = getUtility(IOpenOfficeConfig).getPath()
        ooport = getUtility(IOpenOfficeConfig).getPort()
        renderer = Renderer(self.oo_template_file, params, tempFileName,
                                               pythonWithUnoPath=openofficepath,
                                               ooPort=ooport)
        from globalSemaphore import globalOpenOfficeSemaphore
        try:
            # appy.pod only connects with openoffice when converting to
            # PDF. We need to restrict number of connections to the
            # max connections option set in openoffice.zcml
            if self.document_type == "pdf":
                with globalOpenOfficeSemaphore:
                    renderer.run()
            else:
                renderer.run()
        except:
            log.exception("An error occured during ODT/PDF generation")
            try:
                return self.error_template()
            # This should only happen in unit tests because the site config
            # has not been read in
            except ComponentLookupError:
                return u"An error occured during ODT/PDF generation."
        f = open(tempFileName, "rb")
        doc = f.read()
        f.close()
        os.remove(tempFileName)    
        self.setHeader(self.document_type)
        return doc
        
    def documentData(self, cached=False):
        """Either generate ODT/PDF doc or retrieve from attached files of the
        content item. Cached should only be True for content items that
        are immutable eg. reports."""
        #TODO : Either generate a hash of a mutable content item and store it 
        # with the odt/pdf doc or track changes to a doc
        # Add caching by state. items in terminal states do not change
        if cached:
            d = [ f.title for f in self.document.attachments ]
            if self.document_type not in d:
                att = domain.Attachment()
                att.title = self.document_type
                att.data = self.generateDoc()
                att.language = self.document.language
                att.type = "system" # !+ATTACHED_FILE_TYPE_SYSTEM
                self.document.attachments.append(att)
                session = Session()
                session.add(self.document)
                session.flush()
                #!+ REPORTS(miano, apr-2011) Anonymous users may prompt 
                #the storage of a report if it hasn't been stored before.
                #Actions that are executed when an objectcreatedevent
                #is triggered may require a principal in the 
                #request eg. auditing. Report attachments are not displayed in 
                #listings or any other place so not triggering the event 
                #shouldn't do any harm.
                #notify(ObjectCreatedEvent(att))
            for f in self.document.attachments:
                if f.title == self.document_type: 
                    self.setHeader(self.document_type)
                    return f.data.__str__()
            #If file is not found
            try:
                return self.error_template()
            except ComponentLookupError:
                return u"An error occured during ODT/PDF generation."
        else:
            try:
                return self.generateDoc()
            except DocumentGenerationError:
                return self.error_template()

    def setupTemplate(self):
        """Check if a template was provided in the request as url/form 
        parameter.
        """
        template_encoded = self.request.form.get("template", "")
        if template_encoded != "":
            template_file_name = base64.decodestring(template_encoded)
            template_path = capi.get_path_for("reporting", "templates", 
                template_file_name
            )
            if os.path.exists(template_path):
                self.oo_template_file = template_path

    def __call__(self):
        self.setupTemplate();
        return self.documentData(cached=False)
        
        

#The classes below generate ODT and PDF documents of bungeni content items
#TODO:This implementation displays a default set of the content item's attributes
#once the localisation API is complete it should get info on which attributes
#to display from there.
class BungeniContentODT(DownloadDocument):
    oo_template_file = os.path.dirname(__file__) + "/templates/bungenicontent.odt"  
    template = ViewPageTemplateFile("templates/bungeni-content.pt")
    document_type = "odt"
    
    def bodyText(self):
        if not hasattr(self.document,"group"):
            session = Session()
            self.document.group = session.query(domain.Group).get(self.document.parliament_id)
        return self.template()
    
            
class BungeniContentPDF(DownloadDocument):
    oo_template_file = os.path.dirname(__file__) + "/templates/bungenicontent.odt"  
    template = ViewPageTemplateFile("templates/bungeni-content.pt")
    document_type = "pdf"
    
    def bodyText(self):
        if not hasattr(self.document,"group"):
            session = Session()
            self.document.group = session.query(domain.Group).get(self.document.parliament_id)
        return self.template()
    
