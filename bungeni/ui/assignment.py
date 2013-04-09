# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""UI for Group and User assignment feature

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.assignment")


from zope.component import getUtility
from zope.security import checkPermission
from zope.securitypolicy.interfaces import IRole, IPrincipalRoleMap
from zope.app.security.settings import Allow
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy
from zc.table import column
from zope import formlib

from bungeni.core.dc import IDCDescriptiveProperties
from bungeni.ui.i18n import _
from bungeni.ui.table import TableFormatter
from bungeni.ui import forms
from bungeni.ui.utils import url, common
from bungeni.capi import capi
from bungeni.models.interfaces import ISubRoleAnnotations
from bungeni import utils


class UserAssignmentView(forms.common.BaseForm):
    """View for user assignments. Allows users with adequate permissions
    to edit the assignments
    """
    form_fields = []
    render = ViewPageTemplateFile("templates/assignment.pt")

    def __init__(self, context, request):
        self._assignable_roles = []
        self.principal = utils.common.get_request_principal()
        self.context_roles = common.get_context_roles(
            context, self.principal)
        self.context = removeSecurityProxy(context)
        self.prm = IPrincipalRoleMap(self.context)
        super(UserAssignmentView, self).__init__(context, request)

    def __call__(self):
        self.update()
        return self.render()

    def get_object_type_info(self):
        return capi.get_type_info(self.context.__class__)

    def get_config_roles(self, role_type):
        ti = self.get_object_type_info()
        workflow = ti.workflow
        if workflow.has_feature("user_assignment"):
            feature = None
            for f in workflow.features:
                if f.name == "user_assignment":
                    feature = f
        if feature:
            if role_type == "assigner":
                return capi.schema.qualified_roles(feature.params["assigner_roles"])
            elif role_type == "assignable":
                return capi.schema.qualified_roles(feature.params["assignable_roles"])
        return []

    def assignable_roles(self):
        """Returns a list of role ids that this user can assign to
        """
        if self._assignable_roles:
            return self._assignable_roles
        # the assigner roles that this user has
        assigner_roles = []
        # all the assigner roles that are in the workflow config
        config_assigner_roles = self.get_config_roles("assigner")
        for c_a_role in config_assigner_roles:
            role = getUtility(IRole, c_a_role)
            if role.id in self.context_roles:
                assigner_roles.append(role.id)
        # the assignable roles that this user can assign to
        assignable_roles = []
        # all the assignable roles that are in the workflow config
        config_assignable_roles = self.get_config_roles("assignable")
        # Only assign to roles that have the same parent or are children
        # of assigner roles that this user has
        for assigner_role in assigner_roles:
            assigner_role_annt = ISubRoleAnnotations(
                getUtility(IRole, assigner_role))
            if assigner_role_annt.is_sub_role:
                for c_assignable_role in config_assignable_roles:
                    c_assignable_role_annt = ISubRoleAnnotations(
                        getUtility(IRole, c_assignable_role))
                    if (c_assignable_role_annt.parent ==
                        assigner_role_annt.parent):
                        assignable_roles.append(c_assignable_role)
            else:
                for c_assignable_role in config_assignable_roles:
                    if (c_assignable_role in assigner_role_annt.sub_roles):
                        assignable_roles.append(c_assignable_role)
        self._assignable_roles = assignable_roles
        return self._assignable_roles

    def can_edit(self, action=None):
        return checkPermission("bungeni.user_assignment.Edit", self.context)

    @property
    def columns(self):
        return [
            column.GetterColumn(
                title=_("user name"),
                getter=lambda i, f: i.get("title")
            ),
            column.GetterColumn(
                title=_("assigned"),
                getter=lambda i, f: i,
                cell_formatter=lambda g, i, f: \
                    '<input type="checkbox" name="%s" %s %s/>' % (
                        i["name"],
                        i["is_assigned"] and ' checked="checked"' or "",
                        not i["editable"] and ' disabled="disabled"' or "")
                )
            ]

    @property
    def checkbox_prefix(self):
        return "assignment_users"

    def make_id(self, role_id, user_login_id):
        return ".".join(
            (self.checkbox_prefix, role_id, user_login_id))

    def user_is_assigned(self, user_login, role_id):
        if self.prm.getSetting(role_id, user_login) == Allow:
            return True
        return False

    def role_listing(self, role_id, editable):
        listing = []
        users = common.get_users(role_id)
        if not users:
            return _("No users available for this role.")
        for user in users:
            data = {}
            data["title"] = IDCDescriptiveProperties(user).title
            data["name"] = self.make_id(user.login, role_id)
            data["is_assigned"] = self.user_is_assigned(user.login, role_id)
            data["editable"] = editable
            listing.append(data)
        formatter = TableFormatter(
            self.context, self.request, listing, prefix="assignment",
            columns=self.columns)
        formatter.updateBatching()
        return formatter()

    def update(self):
        self.tables = []
        assignable_roles = self.assignable_roles()
        for role_id in assignable_roles:
            if role_id in assignable_roles:
                editable = True
            else:
                editable = False
            self.tables.append(
                {"title": getUtility(IRole, role_id).title,
                 "table": self.role_listing(role_id, editable)})
        forms.common.BaseForm.update(self)

    def get_selected(self):
        selected = [
            (k[len(self.checkbox_prefix) + 1:].split(".")[0].decode("base64"),
            k[len(self.checkbox_prefix) + 1:].split(".")[1].decode("base64"))
            for k in self.request.form.keys()
            if k.startswith(self.checkbox_prefix) and self.request.form.get(k)
        ]
        return selected

    def process_assignment(self):
        for role_id in self.assignable_roles():
            for user in common.get_users(role_id):
                key = self.make_id(user.login, role_id)
                if key in self.request.form.keys():
                    self.prm.assignRoleToPrincipal(role_id, user.login)
                else:
                    self.prm.unsetRoleForPrincipal(role_id, user.login)

    @formlib.form.action(label=_("Save"), name="save", condition=can_edit)
    def handle_save(self, action, data):
        self.process_assignment()
        next_url = url.absoluteURL(self.context, self.request)
        self.request.response.redirect(next_url)

    @formlib.form.action(label=_("Cancel"), name="", condition=can_edit)
    def handle_cancel(self, action, data):
        next_url = url.absoluteURL(self.context, self.request)
        self.request.response.redirect(next_url)

