from zope.component import getUtility
from zope.securitypolicy.interfaces import IRole, IPrincipalRoleMap
from zope.app.security.settings import Allow

from bungeni.ui.browser import BungeniBrowserView
from bungeni.ui.i18n import _
from bungeni.ui.table import TableFormatter
from bungeni.ui import forms
from bungeni.utils.capi import capi
from bungeni.alchemist import Session
from bungeni.models import domain, utils
from bungeni.models.interfaces import ISubRoleAnnotations

class AssignmentView(BungeniBrowserView, forms.common.BaseForm):
    """View/Edit form for object AssignmentView
    """
    def get_object_type(self):
        return capi.get_type_info(self.context.__class__)

    def get_assignable_roles(self):
        ti = self.get_object_type()
        workflow = ti.workflow
        #the assigner roles that this user has
        assigner_roles = []
        #all the assigner roles that are in the workflow config
        config_assigner_roles = []
        assignable_roles = []
        config_assignable_roles = []
        prm = IPrincipalRoleMap(self.context)
        principal = utils.get_principal()
        if workflow.has_feature("assignment"):
            feature = None
            for f in workflow.features:
                if f.name == "assignment":
                    feature = f
            if feature:
                config_assigner_roles = feature.params["assigner_roles"]
                for role in config_assigner_roles:
                    if (prm.getSetting(role, principal.id) == Allow):
                        assigner_roles.append(role)
                config_assignable_roles = feature.params["assignable_roles"]
                for assigner_role in assigner_roles:
                    assigner_role_annt = ISubRoleAnnotations(
                        getUtility(IRole, role))
                    if assigner_role_annt.is_sub_role:
                        #find other sub_roles with the same parent
                        for c_assignable_role in config_assignable_roles:
                            c_assignable_role_annt = ISubRoleAnnotations(
                                c_assignable_role)
                            if (c_assignable_role_annt.parent ==
                                assigner_role_annt.parent):
                                assignable_roles.append(c_assignable_role)
                    else:
                        for c_assignable_role in config_assignable_roles:
                            if (c_assignable_role in
                                assigner_role_annt.sub_roles):
                                assignable_roles.append(c_assignable_role)
        return assignable_roles

    def get_users(self, role):
        session = Session()
        gmrs = session.query(domain.GroupMembershipRole).filter(
            domain.GroupMembershipRole.sub_role == role).all()
        return [gmr.member.user for gmr in gmrs]
