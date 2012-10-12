# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Error Handling Utilities

Usage:
from bungeni.utils import error
    @error.NAME...

$Id$
"""
log = __import__("logging").getLogger("bungeni.utils")

__all__ = ["exceptions_as"]

import sys
import traceback

def exceptions_as(exc_kls, include_name=True):
    def _exceptions_as(f):
        """Decorator to intercept any error raised by function f and 
        re-raise it as a exc_kls. 
        """
        def _errorable_f(*args, **kw):
            try: 
                return f(*args, **kw)
            except Exception, e:
                log.error("%s [exceptions_as(%s)]\n%s" % (
                    f, 
                    exc_kls.__name__,
                    traceback.format_exc(sys.exc_info()[2])))
                if include_name:
                    raise exc_kls("%s: %s [in %s.%s]" % (
                            e.__class__.__name__, e, f.__module__, f.__name__))
                else:
                    raise exc_kls("%s" % (e))
        return _errorable_f
    return _exceptions_as


