log = __import__("logging").getLogger("bungeni.portal.ploned")

from chameleon.core.template import Macro
from z3c.pt.pagetemplate import ViewPageTemplateFile

import layout

class PlonedLayout(object):
    template = ViewPageTemplateFile("ploned.pt")
    
    def __init__(self, context, request):
        template = layout.bungeni
        
        def render(slots, **kwargs):
            ectx = kwargs.get('econtext', None)
            log.debug("%s.render slots=%s         kwargs=%s" % (
                                    self.__class__.__name__, slots, kwargs))
            if ectx:
                request = ectx.get('request', None)
            else:
                request = None
            if request:
                url = request.getURL()
            else:
                url = None
            if url:
                path = url.split('//')
            else:
                path = ''
            if len(path) == 2:
                spath = path[1].split('/')
            else:
                spath = ''
            if len(spath) > 0:
                section = '-' + spath[1]
            else:
                section = ''
            kwargs['attributes'] = {
                'plone.body.attributes': {
                    'class': "section-bungeni" + section,
                    }
                }

            return template.render_macro(
                "", global_scope=False, slots=slots, parameters=kwargs)
        
        log.debug(" __init__ %s %s %s" % (self, context, id(request)))
        self.macro = Macro(render)
    
    def __getitem__(self, key):
        return self.template.macros.bind(macro=self.macro)[key]
