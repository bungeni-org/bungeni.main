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

def exceptions_as(exc_kls):
    def _exceptions_as(f):
        """Decorator to intercept any error raised by function f and 
        re-raise it as a exc_kls. 
        """
        def _errorable_f(*args, **kw):
            try: 
                return f(*args, **kw)
            except Exception:
                e_type, e_inst, e_traceback = sys.exc_info()
                m = "%r in CALL to %s.%s (%s) WITH args=%r AND kw=%r" % (
                    e_inst, f.__module__, f.__name__, hex(id(f)), args, kw)
                log.debug(traceback.format_exc(e_traceback))
                raise exc_kls, m, e_traceback
        return _errorable_f
    return _exceptions_as


