# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Javascript viewlets used in dhtmlxscheduler interface

$Id$
"""

log = __import__("logging").getLogger("bungeni.ui")

from zope.viewlet.viewlet import JavaScriptViewlet
from zope.traversing import api
from zope.location.interfaces import LocationError

class JSViewlet(JavaScriptViewlet("")):
    """We override the render method here to handle a case where
    we cant find a resource, gracefully.
    """
    def render(self, *args, **kw):
        if self._path:
            return super(JSViewlet, self).render(*args, **kw)
        log.warn("JavaScript viewlet %s has no path",
            self.__class__
        )
        return ""

class DhtmlxSchedulerMainLanguage(JSViewlet):
    """Loads the locale strings for the dhtmlxscheduler UI
    """

    language = None
    default_path = "dhtmlxscheduler/sources/locale/locale.js"
    
    def __init__(self, *args, **kwargs):
        super(DhtmlxSchedulerMainLanguage, self).__init__(*args, **kwargs)
        if self.request.get("I18N_LANGUAGE"):
            self.language = self.request.get("I18N_LANGUAGE")
        self._path = self.setPath()

    def getPath(self):
        path = self.default_path
        if self.language:
            path = "dhtmlxscheduler/sources/locale/locale_%s.js" % (
                self.language)
        return path

    def setPath(self):
        test_path = self.getPath()
        if test_path:
            try:
                api.traverse(self.context, 
                    '++resource++' + test_path, request=self.request)
            except LocationError:
                log.exception("Translation for requested language does "
                    "not exist")
                test_path = None
        return test_path or self.default_path
    
            
class DhtmlxSchedulerRecurringLanguage(DhtmlxSchedulerMainLanguage):
    """Loads the locale strings for the dhtmlxscheduler recurring
    events UI
    """
    default_path = None
    
    def getPath(self):
        test_path = None
        if self.language:
            test_path = ("dhtmlxscheduler/sources/locale/recurring/"
                "locale_recurring_%s.js") % self.language
        return test_path
