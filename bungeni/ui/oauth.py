import hashlib
import hmac
import random
import string
import urllib
import simplejson
import time
from datetime import datetime, timedelta
import sqlalchemy as sa
from sqlalchemy.orm.exc import NoResultFound
from zope.formlib import form
from zope import interface
from zope import schema
from zope.event import notify
from zope.lifecycleevent import ObjectCreatedEvent
from zope.publisher.browser import BrowserPage
from zope.app.security.interfaces import IUnauthenticatedPrincipal
from zope.app.component.hooks import getSite
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.formlib.namedtemplate import NamedTemplate
from bungeni.ui.i18n import _
from bungeni.ui import forms, widgets
from bungeni.ui.browser import BungeniBrowserView
from bungeni.capi import capi
from bungeni.models import domain
from bungeni.models.utils import get_login_user
from bungeni.alchemist import Session
from bungeni.ui.utils import url, misc


def get_key():
    """Return a randomly generated key"""
    m = hashlib.sha1()
    m.update("".join(random.sample(string.letters + string.digits, 20)))
    return m.hexdigest()


class AddOAuthApplication(forms.common.AddForm):

    @form.action(_(u"Create Application"), name="create")
    def handle_create_application(self, action, data, validator="validateAdd"):
        oauth_app = domain.OAuthApplication()
        oauth_app.identifier = data["identifier"]
        oauth_app.name = data["name"]
        oauth_app.redirection_endpoint = data["redirection_endpoint"]
        oauth_app.secret = get_key()
        session = Session()
        session.add(oauth_app)
        session.flush()
        notify(ObjectCreatedEvent(oauth_app))
        next_url = url.absoluteURL(self.__parent__, self.request)
        self.request.response.redirect(next_url)

    @form.action(_(u"Cancel"), name="cancel")
    def handle_cancel(self, action, data):
        next_url = url.absoluteURL(self.__parent__, self.request)
        self.request.response.redirect(next_url)


class OAuthException(Exception):

    def __init__(self, redirect_uri=None, state=None):
        self.redirect_uri = redirect_uri
        self.state = state

    @property
    def error(self):
        raise NotImplemented

    @property
    def error_description(self):
        raise NotImplemented


class UnauthorizedClient(OAuthException):
    @property
    def error(self):
        return "unauthorized_client"

    @property
    def error_description(self):
        return "The client is not authorized to request an authorization" \
            " code using this method."


class UnsupportedResponseType(OAuthException):
    @property
    def error(self):
        return "unsupported_response_type"

    @property
    def error_description(self):
        return "The authorization server does not support obtaining an" \
            " authorization code using this method."


class AccessDenied(OAuthException):
    @property
    def error(self):
        return "access_denied"

    @property
    def error_description(self):
        return "The resource owner or authorization server denied the" \
            " request."


class InvalidRequest(OAuthException):
    @property
    def error(self):
        return "invalid_request"

    @property
    def error_description(self):
        return "The request is missing a required parameter, includes an" \
            " invalid parameter value, includes a parameter more than" \
            " once, or is otherwise malformed."


class UnsupportedGrantType(OAuthException):
    @property
    def error(self):
        return "unsupported_grant_type"

    @property
    def error_description(self):
        return "The authorization grant type is not supported by the" \
            "authorization server."


class InvalidGrant(OAuthException):
    @property
    def error(self):
        return "invalid_grant"

    @property
    def error_description(self):
        return "The provided authorization grant (e.g. authorization " \
            "code, resource owner credentials) or refresh token is " \
            "invalid, expired, revoked, does not match the redirection " \
            "URI used in the authorization request, or was issued to " \
            "another client."


class ErrorPage(BungeniBrowserView):

    template = ViewPageTemplateFile("templates/error-page.pt")

    def __init__(self, context, request, error):
        self.error = error
        super(ErrorPage, self).__init__(context, request)

    def __call__(self):
        self.request.response.setStatus(400)
        self.error_message = self.error.error_description
        return self.template()


class OAuthAuthorizeForm(form.FormBase):
    class IOAuthAuthorizeForm(interface.Interface):
        client_id = schema.TextLine(required=False)
        state = schema.TextLine(required=False)
        time = schema.TextLine(required=False)
        nonce = schema.TextLine(required=False)

    form_fields = form.Fields(IOAuthAuthorizeForm)
    form_fields["client_id"].custom_widget = widgets.HiddenTextWidget
    form_fields["state"].custom_widget = widgets.HiddenTextWidget
    form_fields["nonce"].custom_widget = widgets.HiddenTextWidget
    form_fields["time"].custom_widget = widgets.HiddenTextWidget
    template = NamedTemplate("alchemist.form")
    form_name = _("authorise_oauth_application",
        default=u"Authorise OAuth Application")

    def __init__(self, context, request, parameters={}):
        self.parameters = parameters
        if self.parameters:
            self.parameters["time"] = time.time()
            self.parameters["nonce"] = self.generate_nonce(
                self.parameters["client_id"], self.parameters["time"])
        self.action_url = "/oauth/authorize-form"
        super(OAuthAuthorizeForm, self).__init__(context, request)

    def __call__(self):
        authorization_token = self.check_authorization()
        if authorization_token:
            redirect_uri = self.get_redirect_uri(
                authorization_token, self.request.form.get("state", None))

            self.request.response.redirect(redirect_uri, trusted=True)
        else:
            return super(OAuthAuthorizeForm, self).__call__()

    def get_authorization_token(self, authorization):
        authorization_token = domain.OAuthAuthorizationToken()
        authorization_token.authorization = authorization
        authorization_token.authorization_code = get_key()
        authorization_token.expiry = datetime.now() + timedelta(
            seconds=capi.oauth_authorization_token_expiry_time)
        authorization_token.refresh_token = get_key()
        return authorization_token

    def check_authorization(self):
        session = Session()
        client_id = self.request.form.get("client_id", None)
        user = get_login_user()
        if client_id:
            try:
                authorization = session.query(domain.OAuthAuthorization
                    ).join(domain.OAuthApplication
                    ).filter(sa.and_(
                        domain.OAuthApplication.identifier == client_id,
                        domain.OAuthAuthorization.user_id == user.user_id)
                    ).one()
                authorization_token = self.get_authorization_token(
                    authorization)
                session.add(authorization_token)
                return authorization_token
            except NoResultFound:
                return None
        return None

    def setUpWidgets(self, ignore_request=False):
        self.widgets = form.setUpWidgets(
            self.form_fields, "", self.context, self.request,
            data=self.parameters if self.parameters else self.request.form,
            ignore_request=ignore_request
        )

    def generate_nonce(self, client_id, auth_time):
        data = "{0}:{1}:{2}".format(
            client_id, get_login_user().user_id, auth_time)
        return hmac.new(capi.oauth_hmac_key, data, hashlib.sha1).hexdigest()

    def verify_data(self, action, data):
        errors = []
        for key, value in self.request.form.iteritems():
            data[key] = value
        t_delta = timedelta(seconds=capi.oauth_authorization_token_expiry_time)
        auth_time = datetime.fromtimestamp(float(data["time"]))
        max_time = auth_time + t_delta
        if (datetime.now() > max_time):
            errors.append(InvalidGrant)
        nonce = self.generate_nonce(data["client_id"], data["time"])
        if data["nonce"] != nonce:
            errors.append(InvalidGrant)
        return errors

    def handle_failure(self, action, data, errors):
        return ErrorPage(self.context, self.request, errors[0])()

    def get_redirect_uri(self, authorization_token, state=None):
        redirect_uri = "{0}?code={1}".format(
            authorization_token.authorization.application.redirection_endpoint,
            authorization_token.authorization_code)
        if state:
            redirect_uri = "{0}&state={1}".format(redirect_uri, state)
        return redirect_uri

    @form.action(_(u"Authorize application"), name="authorize",
        validator=verify_data, failure=handle_failure)
    def handle_authorize_app(self, action, data):
        session = Session()
        authorization = domain.OAuthAuthorization()
        authorization.user_id = get_login_user().user_id
        app = session.query(domain.OAuthApplication
            ).filter(domain.OAuthApplication.identifier ==
                data["client_id"]
            ).one()
        authorization.application_id = app.application_id
        authorization.active = True
        session.add(authorization)
        authorization_token = self.get_authorization_token(authorization)
        session.add(authorization_token)
        session.flush()
        redirect_uri = self.get_redirect_uri(authorization_token,
            data["state"])
        self.request.response.redirect(redirect_uri, trusted=True)

    @form.action(_(u"Cancel"), name="cancel")
    def handle_cancel(self, action, data):
        session = Session()
        app = session.query(domain.OAuthApplication
            ).filter(domain.OAuthApplication.application_identifier
                     == data["client_id"]
            ).one()
        error = UnauthorizedClient(app.redirection_endpoint, data["state"])
        redirect_error(self.context, self.request, error)


def redirect_error(context, request, error):
    if error.redirect_uri:
        next_url = "{0}?error={1}&error_description={2}".format(
            error.redirect_uri, error.error, error.error_description)
        if error.state:
            next_url = "{0}&state={1}".format(next_url, error.state)
        return request.response.redirect(next_url, trusted=True)
    else:
        return ErrorPage(context, request, error)()


def bad_request(context, request, error):
    request.response.setStatus(400)
    data = {"error": error.error, "error_description": error.error_description}
    misc.set_json_headers(request)
    return simplejson.dumps(data)


class OAuthAuthorization(BrowserPage):

    def process_parameters(self):
        session = Session()
        parameters = {}

        parameters["state"] = self.request.form.get("state", None)

        if self.request.form.get("client_id", None):
            try:
                application = session.query(domain.OAuthApplication
                    ).filter(domain.OAuthApplication.identifier ==
                        self.request.form.get("client_id")
                    ).one()
                parameters["client_id"] = application.identifier
                parameters["redirect_uri"] = application.redirection_endpoint
            except NoResultFound:
                raise UnauthorizedClient(parameters["state"])
        else:
            raise InvalidRequest(parameters["state"])

        if self.request.form.get("client_secret", None):
            if self.request.form.get("client_secret") != application.secret:
                raise UnauthorizedClient(parameters["state"])
        else:
            raise InvalidRequest(parameters["state"])

        if self.request.form.get("response_type", None):
            if self.request.form.get("response_type") != "code":
                raise UnsupportedResponseType(
                    parameters["redirect_uri"], parameters["state"])
            else:
                parameters["response_type"] = "code"
        else:
            raise InvalidRequest(
                parameters["redirect_uri"], parameters["state"])
        return parameters

    def __call__(self):
        try:
            parameters = self.process_parameters()
        except UnauthorizedClient as e:
            return ErrorPage(self.context, self.request, e)()
        except OAuthException as e:
            return redirect_error(self.context, self.request, e)

        if not IUnauthenticatedPrincipal.providedBy(self.request.principal):
            # authorize form
            return OAuthAuthorizeForm(self.context, self.request, parameters)()
        else:
            # redirect to login form, which will then redirect back to this
            # page
            site_url = url.absoluteURL(getSite(), self.request)
            redirect_url = "{0}?{1}".format(self.request.getURL(),
                urllib.urlencode(self.request.form))
            self.request.response.redirect("{0}/login?camefrom={1}".format(
                site_url, urllib.quote(redirect_url)))


class OAuthAccessToken(BrowserPage):
    authorization = None

    def process_parameters(self):
        parameters = {}
        session = Session()

        if self.request.form.get("grant_type", None):
            if self.request.form.get("grant_type") == "authorization_code":
                parameters["grant_type"] = "authorization_code"
            elif self.request.form.get("grant_type") == "refresh_token":
                parameters["grant_type"] = "refresh_token"
            else:
                raise UnsupportedGrantType()
        else:
            raise InvalidRequest()

        if parameters["grant_type"] == "authorization_code":
            if self.request.form.get("client_id", None):
                try:
                    application = session.query(domain.OAuthApplication
                        ).filter(domain.OAuthApplication.identifier ==
                            self.request.form.get("client_id")
                        ).one()
                    parameters["client_id"] = application.identifier
                except NoResultFound:
                    raise UnauthorizedClient()
            else:
                raise UnauthorizedClient()

            if self.request.form.get("code", None):
                try:
                    authorization_token = session.query(domain.OAuthAuthorizationToken
                        ).join(domain.OAuthAuthorization
                        ).filter(sa.and_(
                            domain.OAuthAuthorization.application_id ==
                            application.application_id,
                            domain.OAuthAuthorizationToken.authorization_code ==
                            self.request.form.get("code"))
                        ).one()
                    parameters["authorization_token"] = authorization_token
                except NoResultFound:
                    raise InvalidGrant()
            else:
                raise InvalidRequest()

            if parameters["authorization_token"].expiry < datetime.now():
                raise InvalidGrant()

            if parameters["authorization_token"].authorization.active is False:
                raise UnauthorizedClient()

        elif parameters["grant_type"] == "refresh_token":
            if self.request.form.get("refresh_token", None):
                try:
                    authorization_token = session.query(domain.OAuthAuthorizationToken
                        ).filter(domain.OAuthAuthorizationToken.refresh_token ==
                            self.request.form.get("refresh_token")
                        ).one()
                    parameters["authorization_token"] = authorization_token
                    parameters["refresh_token"] = authorization_token.refresh_token
                except NoResultFound:
                    raise UnauthorizedClient()
        else:
            raise InvalidRequest()
        return parameters

    def __call__(self):
        session = Session()
        try:
            parameters = self.process_parameters()
        except OAuthException as e:
            return bad_request(self.context, self.request, e)
        authorization_token = parameters["authorization_token"]
        if parameters["grant_type"] == "authorization_code":
            authorization_token.expiry = datetime.now()
        access_token = domain.OAuthAccessToken()
        access_token.access_token = get_key()
        access_token.authorization_token = authorization_token
        t_delta = timedelta(seconds=capi.oauth_access_token_expiry_time)
        access_token.expiry = datetime.now() + t_delta
        session.add(access_token)
        session.flush()
        data = {
            "access_token": access_token.access_token,
            "token_type": "bearer",
            "expires_in": capi.oauth_access_token_expiry_time,
            "refresh_token": access_token.authorization_token.refresh_token
        }
        misc.set_json_headers(self.request)
        return simplejson.dumps(data)
