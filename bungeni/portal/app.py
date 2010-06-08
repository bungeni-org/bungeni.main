import os

from paste import urlparser

here = os.path.abspath(os.path.dirname(__file__))
static = urlparser.StaticURLParser(os.path.join(here, 'static'))

def make_static_serving_app(global_conf, document_root=""):
    def app(environ, start_response):
        environ['SCRIPT_NAME'] = ''
        path_info = environ.get('PATH_INFO', '')
        environ['PATH_INFO'] = document_root + environ['PATH_INFO']
        return static(environ, start_response)
    return app
