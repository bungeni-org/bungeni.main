# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni user auth views

$Id$
"""

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
from bungeni.core.language import I18N_COOKIE_NAME

from bungeni.alchemist import Session
from bungeni.models.domain import User
from bungeni.models.domain import PasswordRestoreLink
from bungeni.models.utils import get_login_user

from bungeni.ui import widgets
import bungeni.ui.utils as ui_utils
from bungeni.ui.forms.common import BaseForm, EditForm
from bungeni.core.workspace import CURRENT_INBOX_COOKIE_NAME
from bungeni import _


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
            if data.get("camefrom", None) and data.get("camefrom").strip():
                camefrom = data["camefrom"].strip()
            else:
                camefrom = ui_utils.url.absoluteURL(getSite(), self.request)
            self.status = _("You are now logged in")
            self.request.response.redirect(camefrom)

    def update(self):
        self.form_fields["camefrom"].field.default = self.request.get(
            "camefrom")
        super(Login, self).update()


class Logout(BrowserView):
    def __call__( self ):
        self.request.response.expireCookie("wc.cookiecredentials")
        self.request.response.expireCookie(I18N_COOKIE_NAME)
        self.request.response.expireCookie(CURRENT_INBOX_COOKIE_NAME)
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


class Profile(EditForm):
    form_name = _(u"Profile")

class IChangePasswordForm(interface.Interface):
    old_password = schema.Password(title=_(u"Old password"), required=True)
    pswd = schema.Password(title=_(u"New password"), required=True)
    confirm_password = schema.Password(title=_(u"Confirm new password"),
                                       required=True)
    
    @interface.invariant
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
