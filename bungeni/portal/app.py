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

def sync_xml_files():
    """ Merges deliverance's rules.xml
        with proxy server configuration
        to generate actual configuration xml
    """
    deliverance_conf_path = os.path.join(os.path.dirname(__file__),
                                         '../../../../portal/deliverance-proxy.conf')
    if os.path.exists(deliverance_conf_path):

        conf_file = open(deliverance_conf_path, 'r')
        conf_data = conf_file.read()
        conf_file.close()

        rules_file_path = os.path.join(os.path.dirname(__file__),
                                       'static/themes/rules.xml')
        rules_file = open(rules_file_path, 'r')
        rules_data = rules_file.read()
        rules_file.close()

        deliverance_file_path = os.path.join(os.path.dirname(__file__),
                                       'static/themes/proxy.xml')
        deliverance_file = open(deliverance_file_path, 'w')
        result_data = rules_data.replace('<!-- deliverance-proxy -->', conf_data)
        deliverance_file.write(result_data)

