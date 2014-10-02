# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Probing/inspect/debug/logging utilities

Frequent usage is within an interactive pdb (hence why name for this module has
been changed from "debug").

recommended usage:
from bungeni.utils import probing

$Id$
"""
log = __import__("logging").getLogger("bungeni.utils.probing")

import sys
import inspect
import math
from zope import interface


# introspection - interfaces

def interfaces(obj):
    """Dump out list of interfaces implemented/provided by obj and its cls.
    """
    return "\n".join(["",
        interfaces_implementedBy(obj.__class__),
        interfaces_implementedBy(obj), # type(obj) may itself be <type 'type'>
        interfaces_providedBy(obj),
        interfaces_directlyProvidedBy(obj),
        interfaces_iro(obj)
    ])
def interfaces_implementedBy(cls):
    """Dump out list of interfaces implementedBy cls.
    """
    try: 
        return """  interfaces implementedBy %s:
    %s""" % (cls, 
            "\n    ".join([
                    "%s %s" % (i, id(i)) 
                    for i in interface.implementedBy(cls) ] or 
                ["</>"] ))
    except TypeError:
        # raise TypeError("implementedBy called for non-factory", cls)
        import sys
        return """  interfaces implementedBy %s: ***ERROR*** %s""" % (
            cls, sys.exc_info())

def interfaces_providedBy(obj):
    """Dump out list of interfaces providedBy obj.
    """
    return """  interfaces providedBy %s:
    %s""" % (repr(obj), 
        "\n    ".join([
                "%s %s" % (i, id(i)) for i in interface.providedBy(obj) ] or 
            ["</>"] ))
def interfaces_directlyProvidedBy(obj):
    """Dump out list of interfaces directlyProvidedBy obj.
    """
    return """  interfaces directlyProvidedBy %s:
    %s""" % (repr(obj), 
        "\n    ".join([
                "%s %s" % (i, id(i)) 
                for i in interface.directlyProvidedBy(obj) ] or 
            ["</>"] ))
def interfaces_iro(obj):
    if isinstance(obj, type):
        # we have a class... iro is calculated on instances, try get one:
        try: 
            obj = obj()
        except:
            import sys
            return """  interfaces iro %s: ***ERROR*** %s""" % (
                obj, sys.exc_info())
    try:
        iro = obj.__provides__.__iro__
    except:
        import sys
        return """  interfaces iro %s: ***ERROR*** %s""" % (
            obj, sys.exc_info())
    return """  interfaces iro %s:
    %s""" % (repr(obj),
        "\n    ".join([ "%s %s" % (i, id(i)) for i in iro ] or ["</>"] ))


# introspection - dependency, heirarchy

def location_stack(obj):
    """Dump out __parent__ stack for an object.
    """
    ps = []
    def _ps(ob):
        if ob is not None:
            _ps(ob.__parent__)
            ps.append("%s [[%s]]" % (ob, getattr(ob, "context", "</>")))
        else:
            ps.append("None")
    _ps(obj)
    return """  parent [[context]] stack for %s:
    %s""" % (obj, "\n    ".join(ps))

def class_inheritance(obj, indent=4):
    """Dump out a simple text representation of possibly complex diamond-shaped 
    class hierarchy for an obj (instance or type), displaying ancestors
    cascading upwards in mro order and inheritance via indentation. 
    """
    # !+inspect.getclasstree( [type] ) possible alternative approach
    s = ["", "MRO x INHERITANCE (* denotes duplicate base) for: %s" % (obj)]
    if not isinstance(obj, (type, interface.interface.InterfaceClass)):
        obj = type(obj)
    classes_mro = []
    bases_depth = {obj: 0}
    duplicate_bases = set()
    for i, x in enumerate(inspect.getmro(obj)):
        assert x not in classes_mro
        classes_mro.append(x)
        for b in x.__bases__:
            if b in bases_depth:
                duplicate_bases.add(b)
            bases_depth[b] = i + 2
    flattened_depth = sorted([ i for i in set(bases_depth.values()) ])
    flattened_depth.reverse()
    from bungeni.utils import naming
    def bname(base):
        if base in duplicate_bases:
            return "*%s*" % (naming.qualname(base))
        return naming.qualname(base)
    for x in reversed(classes_mro):
        depth = flattened_depth.index(bases_depth[x])
        ds = " " * indent * depth
        xbases = ", ".join([ bname(b) for b in x.__bases__ ])
        s.append("%s%s (%s)" % (ds, bname(x), xbases))
    return "\n".join(s)


# introspection - python runtime

def callers_module():
    module_name = inspect.currentframe().f_back.f_globals["__name__"]
    return sys.modules[module_name]

def get_caller_module_name(depth=1):
    """Get the global __name__ value at the given caller depth, by default
    the immediate caller's module.
    
    Calling with depth=0 is equivalent to __name__ (current module name).
    Calling with a depth greater than call stack will throw ValueError.
    """ 
    return sys._getframe(depth).f_globals["__name__"]


# logging - exception

import traceback
def log_exc_info(exc_info, log_handler=log.error):
    """Traceback log an exception.
    exc_info: the 3-tuple as returned by sys.get_exc_info()
        the client is required to call sys.get_exc_info() itself
    log_handler: to allow logging via the caller's logger, 
        but defaults to log.error
    """
    cls, exc, tb = exc_info
    log_handler("""\n%s""" % (traceback.format_exc(tb)))

def log_exc(exc_info, log_handler=log.error):
    """Short log of an exception.
    exc_info: the 3-tuple as returned by sys.get_exc_info()
        the client is required to call sys.get_exc_info() itself
    log_handler: to allow logging via the caller's logger, 
        but defaults to log.error
        
    Sample usage:
        import sys
        try: ...
        except (AnError, AnotherError, ... ):
            debug.log_exc(sys.exc_info(), log_handler=log.info)
    """
    cls, exc, tb = exc_info
    log_handler(""" [%s] %s""" % (cls.__name__, exc))

def log_io(f):
    """Debugging decorator utility, print out all input parameters and the 
    return value of the decorated.
    """
    name = f.__name__
    def _f(*args, **kw):
        ret = f(*args, **kw)
        print " ** %s: %s, %s -->> %s" % (name, args, kw, ret)
        return ret
    return _f


# logging - info/debug formatting

def saccadic_padding(s, jump=16, starting=32):
    """Return whitespace to pad string s to a minimum width {starting}, or if 
    width s is wider that that, to increment padding in jumps of {jump} until 
    exceeding width s.
    """
    swidth = len(s)
    indent = jump * int(math.ceil(swidth/float(jump)))
    if indent < starting:
        indent = starting
    return " " * (indent - swidth)

import difflib
def unified_diff(old_str, new_str, old_name="OLD", new_name="NEW"):
    """Return a unified diff of two strings.
    """
    return "".join(difflib.unified_diff(
                old_str.splitlines(1), 
                new_str.splitlines(1), 
                fromfile=old_name, 
                tofile=new_name))



''' !+
# events

from zope import component
#from ore.wsgiapp.interfaces import WSGIApplicationCreatedEvent
#@component.adapter(WSGIApplicationCreatedEvent)
#def subscribe_log_all_events(event):
#    log_event(event)
#    zope.event.subscribers.append(log_event)

import zope.event
def subscribe_log_all_events():
    """Subscribe log_event handler, to log all events.
    """
    zope.event.subscribers.append(log_event)

def log_event(event):
    """Handler to log an event.
    """
    log.debug(" [log_event] %s", event)
'''

