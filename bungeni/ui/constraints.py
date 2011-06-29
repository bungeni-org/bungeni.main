# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Field constraints

$Id$
"""
import re
import zope.schema
from bungeni.ui.i18n import _

EMAIL_RE = ("([0-9a-zA-Z_&.+-]+!)*[0-9a-zA-Z_&.+-]+@"
    "(([0-9a-zA-Z]([0-9a-zA-Z-]*[0-9a-z-A-Z])?\.)"
    "+[a-zA-Z]{2,6}|([0-9]{1,3}\.){3}[0-9]{1,3})$"
)
LOGIN_RE = "^([a-zA-Z]){1}[a-zA-Z0-9_.]+$"

class FailedRegexMatch(zope.schema.ValidationError):
    """"Regex error initialized with a message displayed to user"""
    e_message = None

    def __init__(self, e_message=_(u"Invalid value"), *args, **kwargs):
        self.e_message = e_message
        super(FailedRegexMatch, self).__init__(*args, **kwargs)
    
    def doc(self):
        return self.e_message

class RegexChecker:
    """Regex constraint factory"""
    def __init__(self, regex, e_message):
        assert type(regex) in [str, unicode]
        self.regex = regex
        self.e_message = e_message
    
    def __call__(self, value):
        if type(value) in [str, unicode]:
            if re.match(self.regex, value) is None:
                raise FailedRegexMatch(self.e_message)
                return False
        return True

check_email = RegexChecker(EMAIL_RE, _(u"This is not a valid email address"))
check_login = RegexChecker(LOGIN_RE, _(u"Invalid login name"))

