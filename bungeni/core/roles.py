from zope.securitypolicy.interfaces import IPrincipalRoleMap
from bungeni.core.workflows.utils import get_group_context


def group_membership_role_added(group_membership_role, event):
    if group_membership_role.is_global:
        prm = IPrincipalRoleMap(
            get_group_context(group_membership_role.member.group))
        prm.assignRoleToPrincipal(
            group_membership_role.role_id,
            group_membership_role.member.user.login)


def group_membership_role_deleted(group_membership_role, event):
    if group_membership_role.is_global:
        prm = IPrincipalRoleMap(
            get_group_context(group_membership_role.member.group))
        prm.unsetRoleForPrincipal(
            group_membership_role.role_id,
            group_membership_role.member.user.login)
