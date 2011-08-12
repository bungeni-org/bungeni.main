from sqlalchemy import orm
from zope import interface
from zope import component
from zope.security.proxy import removeSecurityProxy
from zope.securitypolicy.interfaces import IPrincipalRoleMap
from zope.app.security.settings import Allow
from ore.alchemist.container import AlchemistContainer, contained
from bungeni.models import interfaces
from bungeni.alchemist import Session
from bungeni.ui.utils.common import get_workspace_roles
from bungeni.models.utils import get_principal
from bungeni.core.interfaces import IWorkspaceTabsUtility
from bungeni.models.utils import get_current_parliament
from bungeni.alchemist.security import LocalPrincipalRoleMap
#!+WORKSPACE(miano, jul 2011)
# Roles can be divided into two, roles that a principal gets by virtue
# of his membership to a group and roles that are defined on objects
# eg. bungeni.Owner and bungeni.Signatory
# When generating the query for items to be included in the workspace
# we do not know whether or not the user has any roles defined on any
# of the objects so we have to query all object states defined for this
# type of roles.
OBJECT_ROLES = ["bungeni.Owner", "bungeni.Signatory"]


def stringKey(instance):
    unproxied = removeSecurityProxy(instance)
    mapper = orm.object_mapper(unproxied)
    primary_key = mapper.primary_key_from_instance(unproxied)
    domain_class = instance.__class__
    workspace_tabs = component.getUtility(IWorkspaceTabsUtility)
    item_type = workspace_tabs.getType(domain_class)
    return "%s-%s" % (item_type, str(primary_key[0]))


def valueKey(identity_key):
    """Returns a tuple, (domain_class, primary_key)"""
    if not isinstance(identity_key, (str, unicode)):
        raise ValueError
    properties = identity_key.split("-")
    if len(properties) != 2:
        raise ValueError
    workspace_tabs = component.getUtility(IWorkspaceTabsUtility)
    domain_class = workspace_tabs.getDomain(properties[0])
    primary_key = properties[1]
    return domain_class, primary_key


class WorkspaceContainer(AlchemistContainer):
    __name__ = __parent__ = None
    interface.implements(interfaces.IWorkspaceContainer)

    def __init__(self, tab_type, title, description, marker=None):
        self.__name__ = tab_type
        self.title = title
        self.description = description
        self.workspace_config = component.getUtility(IWorkspaceTabsUtility)
        if marker is not None:
            interface.alsoProvides(self, marker)
        super(WorkspaceContainer, self).__init__()

    def domain_status(self, roles, tab):
        """Given a list of roles and tab returns a dictionary containing the
           domain classes and status of items to appear for that principal in
           that tab. Role should be a list, tab a string
        """
        dom_stat = {}
        for role in roles:
            workspace_dom_stat = self.workspace_config.getDomainAndStatuses(role,
                tab)
            if workspace_dom_stat:
                for key in workspace_dom_stat.keys():
                    if key in dom_stat.keys():
                        dom_stat[key].extend(workspace_dom_stat[key])
                    else:
                        dom_stat[key] = workspace_dom_stat[key]
        return dom_stat

    def item_status_filter(self, kw, roles):
        domain_status = {}
        if kw.get("item_type_filter", None):
            domain_class = self.workspace_config.getDomain(kw["item_type_filter"])
            if domain_class:
                domain_status[domain_class] = []
                for role in roles:
                    statuses = self.workspace_config.getStatus(role, domain_class,
                                                           self.__name__)
                    if kw.get("status_filter", None) and \
                            kw["status_filter"] in statuses:
                        domain_status[domain_class] = kw["status_filter"] 
                    elif statuses:
                        domain_status[domain_class].extend(statuses)
        else:
            domain_status = self.domain_status(roles, self.__name__)
            if kw.get("status_filter", None):
                for domain_class in domain_status.keys():
                    if kw["status_filter"] in \
                            domain_status[domain_class]:
                        domain_status[domain_class] = [kw["status_filter"]]
                    else:
                        del domain_status[domain_class]
        return domain_status
    
    def title_column(self, domain_class):
        table = orm.class_mapper(domain_class).mapped_table
        utk = dict([(table.columns[k].key, k)
                    for k in table.columns.keys()])
        # TODO : update to support other fields
        column = table.columns[utk["short_name"]]
        return column

    def _query(self, **kw):
        principal = get_principal()
        roles = get_workspace_roles(principal)
        group_roles_domain_status = self.item_status_filter(kw, roles)
        session = Session()
        results = []
        for domain_class, status in group_roles_domain_status.iteritems():
            query = session.query(domain_class).filter(domain_class.status.in_(
                    status))
            if kw.get("title_filter", None):
                column = self.title_column(domain_class)
                query = query.filter("(lower(%s) LIKE '%%%s%%')" %
                                     (column, kw["title_filter"]))
            results.extend(query.all())
        object_roles_domain_status = self.item_status_filter(kw, OBJECT_ROLES)
        for domain_class, status in object_roles_domain_status.iteritems():
            query = session.query(domain_class).filter(
                domain_class.status.in_(status))
            if kw.get("title_filter", None):
                column = self.title_column(domain_class)
                query = query.filter("(lower(%s) LIKE '%%%s%%')" %
                                     (column, kw["title_filter"]))
            for obj in query.all():
                prm = IPrincipalRoleMap(obj)
                for obj_role in OBJECT_ROLES:
                    if prm.getSetting(obj_role, principal.id) == Allow and \
                            obj not in results:
                        results.append(obj)
                        break
        for result in results:
            yield result

    def items(self):
        for obj in self._query():
            name = stringKey(obj)
            yield (name, contained(obj, self, name))

    def get(self, name, default=None):
        try:
            domain_class, primary_key = valueKey(name)
        except:
            return default
        session = Session()
        value = session.query(domain_class).get(primary_key)
        if value is None:
            return default
        # The check below is to ensure an error is raised if an object is not
        # in the tab requested eg. through an outdated url
        if value in self._query():
            value = contained(value, self, stringKey(value))
            return value
        else:
            return default

    @property
    def parliament_id(self):
        """Vocabularies in the forms get the parliament id from the context,
        this property returns the id of the current parliament because
        the workspace is meant only for adding current documents
        """
        return get_current_parliament().group_id

    def __getitem__(self, name):
        value = self.get(name)
        if value is None:
            raise KeyError(name)
        return value
    # see alchemist.traversal.managed.One2Many
    # see alchemist.ui.content.AddFormBase -> self.context[''] = ob
    # see bungeni.core.app.AppSetup
    # In the managed containers, the constraint manager
    # in One2Many sets the foreign key of an item to the
    # primary key of the container when an item is added.
    # This does the same for the workspace containers
    # The add forms in the workspace are only to add documents to the
    # current parliament.
    # This sets the foreign key of the doc to the current parliament.

    def __setitem__(self, name, item):
        session = Session()
        current_parliament = get_current_parliament()
        item.parliament_id = current_parliament.parliament_id
        session.add(item)

# (SECURITY, miano, july 2011) This factory adapts the workspaces to
# zope.securitypolicy.interface.IPrincipalRoleMap and is equivalent to the
# principalrolemap of the current parliament.
# If/when Bungeni is modified to support bicameral houses this should be
# modified so that the oid is set to the group_id of the house the current
# principal in the interaction is a member of.


class WorkspacePrincipalRoleMap(LocalPrincipalRoleMap):

    def __init__(self, context):
        self.context = context
        current_parliament = get_current_parliament()
        self.object_type = current_parliament.type
        self.oid = current_parliament.group_id
