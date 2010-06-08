import re
import webob

from urlparse import urlparse, urlunparse
from urllib import urlencode
try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

from paste.httpexceptions import HTTPFound
from paste.request import parse_dict_querystring
from paste.request import parse_formvars

from zope.interface import implements
from repoze.who.plugins.form import FormPluginBase
from repoze.who.interfaces import IIdentifier
from repoze.who.interfaces import IChallenger
from repoze.who.interfaces import IChallengeDecider
from cStringIO import StringIO

def matcher(string):
    return re.compile(string).search

class FormAuthPlugin(FormPluginBase):
    """This plugin supports an application-based login procedure."""
    
    implements(IChallenger, IIdentifier, IChallengeDecider)

    username = "login", "__ac_name"
    password = "password", "__ac_password"
    
    def __init__(self, login_handler_path, logout_handler_path,
                 forgetter_name=None, post_logout_url=None,
                 rememberer_name=None):
        self.login_handler_match = matcher(login_handler_path)
        self.logout_handler_match = matcher(logout_handler_path)
        self.post_logout_url = post_logout_url
        self.forgetter_name = forgetter_name
        self.rememberer_name = rememberer_name
        
    def __call__(self, environ, status, headers):
        """The challenger decider will match the logout handler and
        forget credentials if matched.

        Only on a '401 Unauthorized' will we invoke the challenger.
        """

        if status.startswith('401 '):
            return True
        
        if self.logout_handler_match(environ['PATH_INFO']):
            headers.extend(
                environ['repoze.who.plugins'][self.forgetter_name].forget(
                    environ, None))

        return False

    def identify(self, environ):
        path_info = environ['PATH_INFO']
        query = parse_dict_querystring(environ)

        # we've been asked to perform a login
        if self.login_handler_match(path_info):
            body = environ['wsgi.input'].read()
            stream = environ['wsgi.input'] = StringIO(body)
            form = parse_formvars(environ)
            form.update(query)
            stream.seek(0)

            # extract username and password
            for key in self.username:
                if key in form:
                    login = form[key]; break
            else:
                return None

            for key in self.password:
                if key in form:
                    password = form[key]; break
            else:
                return None

            return {
                'login': login,
                'password': password,
                }

    def challenge(self, environ, status, app_headers, forget_headers):
        """Override the parent's challenge to avoid challenging the
        user on logout, introduce a post-logout page and/or pass the
        login counter to the login form.
        """

        # if the current path matches the logout handler path, log out
        # the user without challenging.
        if self.logout_handler_match(environ['PATH_INFO']):
            came_from = environ.get('came_from')
            if self.post_logout_url:
                # redirect to a predefined "post logout" URL.
                destination = self._get_full_path(
                    self.post_logout_url, environ)
                
                if came_from:
                    destination = self._insert_qs_variable(
                                  destination, 'came_from', came_from)

                return HTTPFound(destination, headers=forget_headers)

            return HTTPFound(webob.Request(environ).url, headers=forget_headers)
    
    def _get_full_path(self, path, environ):
        """
        Return the full path to ``path`` by prepending the SCRIPT_PATH.
        
        If ``path`` is a URL, do nothing.
        
        """
        if path.startswith('/'):
            path = environ.get('SCRIPT_PATH', '') + path
        return path
    
    def _insert_qs_variable(self, url, var_name, var_value):
        """
        Insert the variable ``var_name`` with value ``var_value`` in the query
        string of ``url`` and return the new URL.
        
        """
        url_parts = list(urlparse(url))
        query_parts = parse_qs(url_parts[4])
        query_parts[var_name] = var_value
        url_parts[4] = urlencode(query_parts, doseq=True)
        return urlunparse(url_parts)


