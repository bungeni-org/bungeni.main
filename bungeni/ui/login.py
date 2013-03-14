import datetime
import hashlib
from email.mime.text import MIMEText

from zope import interface
from zope import schema
from zope.formlib import form
from zope.formlib.namedtemplate import NamedTemplate
from zope.publisher.browser import BrowserView
from zope.app.security.interfaces import IUnauthenticatedPrincipal
from zope.app.component.hooks import getSite
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.component import getUtility
from bungeni.core.interfaces import IBungeniMailer

from bungeni.models.domain import User
from bungeni.alchemist import Session
from bungeni.models.domain import PasswordRestoreLink
from bungeni.models.utils import get_login_user
from bungeni.ui import vocabulary
from bungeni.ui import widgets
from bungeni.core.i18n import _
from bungeni.models.settings import EmailSettings
from bungeni.core.app import BungeniApp
import bungeni.ui.utils as ui_utils
from bungeni.ui.descriptor.constraints import check_email
from zope.interface import invariant
from bungeni.ui.forms.common import BaseForm
from bungeni.alchemist import ui


SECRET_KEY = "bungeni"


class ILoginForm(interface.Interface):
    login = schema.TextLine(title=_("label_login_form_username",
        default=u"Username"))
    password = schema.Password(title=_("label_login_form_password", 
        default=u"Password"))
    camefrom = schema.TextLine(required=False)


class Login(form.FormBase):
    form_fields = form.Fields(ILoginForm)
    form_fields["camefrom"].custom_widget = widgets.HiddenTextWidget
    prefix = ""
    form_name = _("login_form_title", default=u"Login")
    template = NamedTemplate("alchemist.form")
    
    def __call__(self):
        if not IUnauthenticatedPrincipal.providedBy(self.request.principal):
            app = getSite()
            workspace = app["workspace"]
            self.request.response.redirect(
                        ui_utils.url.absoluteURL(workspace, self.request))
        return super(Login, self).__call__()

    @form.action(_("label_login_form_login", default=u"Login"), 
        name="login")
    def handle_login(self, action, data):
        if IUnauthenticatedPrincipal.providedBy(self.request.principal):
            self.status = _(u"Invalid account credentials")
        else:
            camefrom = ui_utils.url.absoluteURL(getSite(), self.request)
            if self.request.get('camefrom').strip():
                camefrom = self.request.get('camefrom').strip()
            self.status = _("You are now logged in")
            self.request.response.redirect( camefrom )


class Logout(BrowserView):
    def __call__( self ):
        self.request.response.expireCookie( "wc.cookiecredentials" )
        site_url = ui_utils.url.absoluteURL(getSite(), self.request)
        self.request.response.redirect( site_url )


class IRestoreLoginForm(interface.Interface):
    email = schema.TextLine(
        title=_("label_restore_login_email", default=u"Email"))        

class RestoreLogin(form.FormBase):
    form_fields = form.Fields(IRestoreLoginForm)
    prefix = ""
    form_name = _(u"Restore Login")
    
    template = NamedTemplate("alchemist.form")
    
    def __call__(self):
        if not IUnauthenticatedPrincipal.providedBy(self.request.principal):
            app = getSite()
            workspace = app["workspace"]
            self.request.response.redirect(
                        ui_utils.url.absoluteURL(workspace, self.request))
        
        return super(RestoreLogin, self).__call__()
            
    @form.action(_(u"Restore"), name="restore")
    def handle_restore(self, action, data):
        email = data.get("email", "")
        if email:
            app = BungeniApp()
            settings = EmailSettings(app)
            session = Session()
            user = session.query(User).filter(
                            User.email==email).first()
            if user:
                mailer = getUtility(IBungeniMailer)
                self.message = _(u"Your login is: ") + user.login
                
                text = ViewPageTemplateFile("templates/mail.pt")(self)
                message = MIMEText(text)
                message.set_charset("utf-8")
                message["Subject"] = _(u"Bungeni login restoration")
                message["To"] = email
                mailer.send(message)
                self.status = _(u"Your login was sent to you email.")
            else:
                self.status = _(u"Wrong email address.")


class IRestorePasswordForm(interface.Interface):
    login = schema.TextLine(
        title=_("label_restore_password_username", default=u"Username"), 
        required=False
    )
    email = schema.TextLine(
        title=_("label_restore_password_email", default=u"Email"), 
        required=False
    )
    
class RestorePassword(form.FormBase):
    form_fields = form.Fields(IRestorePasswordForm)
    prefix = ""
    form_name = _(u"Restore Password")
    
    template = NamedTemplate("alchemist.form")
    
    def __call__(self):
        if not IUnauthenticatedPrincipal.providedBy(self.request.principal):
            app = getSite()
            workspace = app["workspace"]
            self.request.response.redirect(
                        ui_utils.url.absoluteURL(workspace, self.request))
            
        return super(RestorePassword, self).__call__()
            
    @form.action(_(u"Restore"), name="restore")
    def handle_restore(self, action, data):
        site_url = ui_utils.url.absoluteURL(getSite(), self.request)
        login = data.get("login", "")
        email = data.get("email", "")
        user = None
            
        app = BungeniApp()
        settings = EmailSettings(app)
            
        session = Session()
        if email:
            user = session.query(User).filter(
                                User.email==email).first()
        elif login:
            user = session.query(User).filter(
                                User.login==login).first()
                                    
        if user:
            email = user.email
            link = session.query(PasswordRestoreLink).filter(
                PasswordRestoreLink.user_id==user.user_id).first()
            if link:
                if not link.expired():
                    self.status = _(u"This user's link is still active!")
                    return
            else:
                link = PasswordRestoreLink()
                
            link.hash = hashlib.sha224(user.login + 
                                        SECRET_KEY + 
                                        str(datetime.datetime.now())).hexdigest()
            link.expiration_date = datetime.datetime.now() + datetime.timedelta(1)
            link.user_id = user.user_id
            session.add(link)
                        
            mailer = getUtility(IBungeniMailer)
                
                
            self.message = _(u"Restore password link: ")\
                        + "%s/reset_password?key=%s" % (site_url, link.hash)
            self.message += u"\n\n"
            self.message += _(u"This link will expire in 24 hours.")
                
            text = ViewPageTemplateFile("templates/mail.pt")(self)
            message = MIMEText(text)
            message.set_charset("utf-8")
            message["Subject"] = _(u"Bungeni password restoration")
            message["To"] = email
            mailer.send(str(message))
            self.status = _(u"Email was sent!")
        else:
            self.status = _(u"User not found!")

        
class IResetPasswordForm(interface.Interface):
    password = schema.Password(title=_(u"Password"))
    confirm_password = schema.Password(title=_(u"Confirm Password"))
    key = schema.TextLine(required=False)

class ResetPassword(form.FormBase):
    form_fields = form.Fields(IResetPasswordForm)
    form_fields["key"].custom_widget = widgets.HiddenTextWidget
    prefix = ""
    form_name = _(u"Reset Password")
    status = ""
    template = NamedTemplate("alchemist.form")
    
    def __init__(self, *args, **kwargs):
        super(ResetPassword, self).__init__(*args, **kwargs)
        key = self.request.get("key",self.request.get("form.key",""))
        self.session = Session()
        self.link = self.session.query(PasswordRestoreLink).filter(
                                PasswordRestoreLink.hash==key).first()
    
    def __call__(self):
        if not self.link:
            self.status = _(u"Wrong key!")
        if self.link and self.link.expired():
            self.status = _(u"Key expired!")
        return super(ResetPassword, self).__call__()
    
    @form.action(_(u"Reset"), name="reset")
    def handle_reset(self, action, data):
        site_url = ui_utils.url.absoluteURL(getSite(), self.request)
        password = data.get("password", "")
        confirm_password = data.get("confirm_password", "")
        
        if password.__class__ is not object:
            if password != confirm_password:
                self.status = _(u"Password confirmation failed!")
                return
            
        if password and password == confirm_password and self.link:
            if not self.link.expired():
                user = self.link.user
                user._password = password
                self.link.expiration_date = datetime.datetime.now()
                self.status = _(u"Password successfully reset!")


class IProfileForm(interface.Interface):
    first_name = schema.TextLine(title=_(u"First name"))
    last_name = schema.TextLine(title=_(u"Last name"))
    middle_name = schema.TextLine(title=_(u"Middle name"), required=False)
    email = schema.TextLine(
        title=_("label_profile_email", default=u"Email"), 
        constraint=check_email
    )
    description = schema.Text(title=_(u"Biographical notes"), required=False)
    gender = schema.Choice(title=_("Gender"), vocabulary=vocabulary.gender)
    date_of_birth = schema.Date(title=_("Date of Birth"))
    birth_nationality = schema.Choice(
        title=_("Nationality at Birth"), 
        source=vocabulary.country_factory)
    birth_country = schema.Choice(
        title=_("Country of Birth"), 
        source=vocabulary.country_factory)
    current_nationality = schema.Choice(
        title=_("Current Nationality"), 
        source=vocabulary.country_factory)
    image = schema.Bytes(title=_("Image"))
    
    @invariant
    def checkEmail(self):
        session = Session()
        users = session.query(User).filter(User.email==self.email)
        message = _("error_profile_email_taken", "Email already taken!")
        if users.count() > 1:
            raise interface.Invalid(message,"email")
        if users.count() == 1 and users.first().user_id != get_login_user().user_id:
            raise interface.Invalid(message,"email")
        

class Profile(BaseForm):
    form_fields = form.Fields(IProfileForm)
    
    form_fields["gender"].custom_widget=widgets.CustomRadioWidget
    form_fields["date_of_birth"].custom_widget=widgets.DateWidget
    form_fields["description"].custom_widget=widgets.RichTextEditor
    form_fields["image"].custom_widget=widgets.ImageInputWidget
    
    prefix = ""
    form_name = _(u"Profile")
    
    # !+ only used here [ bungeni.ui.login.Login ] ?
    template = NamedTemplate("alchemist.form")
    
    def __init__(self, *args, **kwargs):
        super(Profile, self).__init__(*args, **kwargs)
        self.user = get_login_user()
        self.context = self.user
            
    def __call__(self):
        if IUnauthenticatedPrincipal.providedBy(self.request.principal):
            self.request.response.redirect(
                        ui_utils.url.absoluteURL(
                        getSite(), self.request)+"/login"
                        )
        return super(Profile, self).__call__()
    
    def setUpWidgets(self, ignore_request=False):
        super(Profile, self).setUpWidgets(ignore_request=ignore_request)
        for widget in self.widgets:
            name = widget.name
            if self.request.get(name,None) is None:
                self.widgets[name].setRenderedValue(
                                    getattr(self.user, name, None))
            else:
                self.widgets[name].setRenderedValue(
                                    self.request.get(name,None))
                if name == "gender":
                    self.widgets[name].setRenderedValue(
                                        self.request.get(name)[0])
        
    def _do_save(self, data):
        email = data.get("email","")
        first_name = data.get("first_name","")
        last_name = data.get("last_name","") 
        middle_name = data.get("middle_name","")
        description = data.get("description","")
        gender = data.get("gender","")
        image = data.get("image","")
        date_of_birth = data.get("date_of_birth","")
        birth_nationality = data.get("birth_nationality","")
        birth_country = data.get("birth_country","")
        current_nationality = data.get("current_nationality","")
                        
        if email:
            self.user.email = email
            
        if first_name:
            self.user.first_name = first_name
            
        if last_name:
            self.user.last_name = last_name
        
        if middle_name:
            self.user.middle_name = middle_name
        
        if description:
            self.user.description = description
        
        if gender:
            self.user.gender = gender
            
        if date_of_birth:
            self.user.date_of_birth = date_of_birth
            
        if image:
            self.user.image = image
            
        if birth_nationality:
            self.user.birth_nationality = birth_nationality
        
        if birth_country:
            self.user.birth_country = birth_country
        
        if current_nationality:
            self.user.current_nationality = current_nationality
                
        self.status = _("Profile data updated")
        
    @form.action(_(u"Save Profile"), name="save",
                 condition=form.haveInputWidgets)
    def handle_edit_save(self, action, data):
        self._do_save(data)

    @form.action(_(u"Save profile and view"), name="save_and_view",
                 condition=form.haveInputWidgets)
    def handle_edit_save_and_view(self, action, data):
        self._do_save(data)
        if not self._next_url:
            self._next_url = ui_utils.url.absoluteURL(self.context, self.request) + \
                "?portal_status_message= Saved"
        self.request.response.redirect(self._next_url)

    @form.action(_(u"Cancel"), name="cancel",
                 validator=ui.null_validator)
    def handle_edit_cancel(self, action, data):
        if not self._next_url:
            self._next_url = ui_utils.url.absoluteURL(self.context, self.request)
        self.request.response.redirect(self._next_url)
        

class IChangePasswordForm(interface.Interface):
    old_password = schema.Password(title=_(u"Old password"), required=True)
    pswd = schema.Password(title=_(u"New password"), required=True)
    confirm_password = schema.Password(title=_(u"Confirm new password"),
                                       required=True)
    
    @invariant
    def checkOldPassword(self):
        if not get_login_user().checkPassword(self.old_password):
            raise interface.Invalid(_("Old password incorrect"), "old_password")
    

class ChangePasswordForm(BaseForm):
    form_fields = form.Fields(IChangePasswordForm)
    
    prefix = ""
    form_name = _("change_password_form_title", 
        default=u"Change password")
    
    # !+ only used here [ bungeni.ui.login.Login ] ?
    template = NamedTemplate("alchemist.form")
    
    def __init__(self, *args, **kwargs):
        super(ChangePasswordForm, self).__init__(*args, **kwargs)
        self.session = Session()
        self.user = get_login_user()
            
    def __call__(self):
        if IUnauthenticatedPrincipal.providedBy(self.request.principal):
            self.request.response.redirect(
                        ui_utils.url.absoluteURL(
                        getSite(), self.request)+"/login"
                        )
        return super(ChangePasswordForm, self).__call__()
    
    @form.action(_("label_change_password", default=u"Change password"), 
        name="change_password")
    def save_password(self, action, data):
        password = data.get("pswd","")
        confirm_password= data.get("confirm_password","")
        
        if password:
            if password != confirm_password:
                self.status = _("Password confirmation failed")
                return
            self.user._password = password
        
        self.status = _("Password changed")
