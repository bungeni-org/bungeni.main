from zope.securitypolicy.interfaces import IPrincipalRoleMap
from bungeni.core.workflows.utils import get_group_context


def member_role_added(member_role, event):
    if member_role.is_global:
        prm = IPrincipalRoleMap(
            get_group_context(member_role.member.group))
        prm.assignRoleToPrincipal(
            member_role.role_id,
            member_role.member.user.login)


def member_role_deleted(member_role, event):
    if member_role.is_global:
        prm = IPrincipalRoleMap(
            get_group_context(member_role.member.group))
        prm.unsetRoleForPrincipal(
            member_role.role_id,
            member_role.member.user.login)


