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
    def cleanupText(self):
        '''This function generates an ODT document from the text of a report'''
        #This should really be at the top of this file.
        #Leaving it here for the time being so that having 
        #libtidy is not a requirement to run bungeni
        import tidy
        body_text = removeSecurityProxy(self.context.body_text)
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
        params = {}
        params['body_text'] = self.cleanupText()
        renderer = Renderer(self.odt_file, params, self.tempFileName)
        renderer.run()
        self.request.response.setHeader('Content-type', 'application/vnd.oasis.opendocument.text')
        self.request.response.setHeader('Content-disposition', 'inline;filename="'+
                                            removeSecurityProxy(self.context.report_type)+"_"+
                                            removeSecurityProxy(self.context.start_date).strftime('%Y-%m-%d')+'.odt"')
        f = open(self.tempFileName, 'rb')
        doc = f.read()
        f.close()      
        os.remove(self.tempFileName)    
        return doc  

    
class  DownloadPDF(DownloadDocument):
    #appy.Renderer expects a file name of a file that does not exist.
    #TODO Find a better way
    tempFileName = os.path.dirname(__file__) + '/tmp/%f.pdf' % ( time.time())
     
    def __call__(self): 
        params = {}
        params['body_text'] = self.cleanupText()
        openofficepath = getUtility(IOpenOfficeConfig).getPath()
        renderer = Renderer(self.odt_file, params, self.tempFileName, pythonWithUnoPath=openofficepath)
        renderer.run()
        self.request.response.setHeader('Content-type', 'application/pdf')
        self.request.response.setHeader('Content-disposition', 'inline;filename="'
                            +removeSecurityProxy(self.context.report_type)+"_"
                            +removeSecurityProxy(self.context.start_date).strftime('%Y-%m-%d')+'.pdf"')
        f = open(self.tempFileName, 'rb')
        doc = f.read()
        f.close()
        os.remove(self.tempFileName)
        return doc 
        
