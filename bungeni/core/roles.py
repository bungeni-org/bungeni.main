from zope.securitypolicy.interfaces import IPrincipalRoleMap
from bungeni.core.workflows.utils import get_group_context


def group_member_role_added(group_member_role, event):
    if group_member_role.is_global:
        prm = IPrincipalRoleMap(
            get_group_context(group_member_role.member.group))
        prm.assignRoleToPrincipal(
            group_member_role.role_id,
            group_member_role.member.user.login)


def group_member_role_deleted(group_member_role, event):
    if group_member_role.is_global:
        prm = IPrincipalRoleMap(
            get_group_context(group_member_role.member.group))
        prm.unsetRoleForPrincipal(
            group_member_role.role_id,
            group_member_role.member.user.login)


