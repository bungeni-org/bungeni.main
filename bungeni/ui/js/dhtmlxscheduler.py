log = __import__("logging").getLogger("bungeni.ui")
from zope.viewlet.viewlet import JavaScriptViewlet
from zope.traversing import api
from zope.location.interfaces import LocationError

JSViewlet = JavaScriptViewlet("")

class DhtmlxSchedulerMainLanguage(JSViewlet):
    language = None    
    
    def __init__(self, *args, **kwargs):
        super(DhtmlxSchedulerMainLanguage, self).__init__(*args, **kwargs)
        if self.request.get("I18N_LANGUAGE"):
            self.language = self.request.get("I18N_LANGUAGE")
        self._path = self.setPath()
    
    def setPath(self):
        if self.language:
            path = "dhtmlxscheduler/sources/locale_%s.js" % self.language
            try:
                resource = api.traverse(self.context, '++resource++' + path,
                                request=self.request)
            except LocationError:
                log.exception("Translation for requested language does not exist")
                path = "dhtmlxscheduler/sources/locale.js"
        else:
            path = "dhtmlxscheduler/sources/locale.js"
        return path
    
            
class DhtmlxSchedulerRecurringLanguage(DhtmlxSchedulerMainLanguage):
    def setPath(self):
        if self.language:
            if self.request.get("I18N_LANGUAGE"):
                self.language = self.request.get("I18N_LANGUAGE")
            path = "dhtmlxscheduler/sources/locale_recurring_%s.js" % \
                                                                   self.language   
            try:
                resource = api.traverse(self.context, '++resource++' + path,
                                request=self.request)
            except LocationError:
                log.exception("Translation for requested language does not exist")
                path = "dhtmlxscheduler/sources/locale_recurring.js"
        else:
            path = "dhtmlxscheduler/sources/locale_recurring.js"
        return path
