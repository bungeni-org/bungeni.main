from zope.securitypolicy.interfaces import IPrincipalRoleMap
from bungeni.core.workflows.utils import get_group_context


def member_title_added(title, event):
    if title.title_type.role_id:
        prm = IPrincipalRoleMap(get_group_context(title.title_type.group))
        prm.assignRoleToPrincipal(title.title_type.role_id,
                                  title.member.user.login)


def member_title_deleted(title, event):
    if title.title_type.role_id:
        prm = IPrincipalRoleMap(get_group_context(title.title_type.group))
        prm.unsetRoleForPrincipal(title.title_type.role_id,
                                  title.member.user.login)
