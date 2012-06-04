from sqlalchemy import orm
from sqlalchemy.sql import expression
from zope import interface
from zope import component
from zope.security.proxy import removeSecurityProxy
from zope.securitypolicy.interfaces import IPrincipalRoleMap
from zope.app.security.settings import Allow
from bungeni.alchemist.container import AlchemistContainer, contained
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
    item_type = workspace_tabs.get_type(domain_class)
    return "%s-%s" % (item_type, str(primary_key[0]))


def valueKey(identity_key):
    """Returns a tuple, (domain_class, primary_key)"""
    if not isinstance(identity_key, (str, unicode)):
        raise ValueError
    properties = identity_key.split("-")
    if len(properties) != 2:
        raise ValueError
    workspace_tabs = component.getUtility(IWorkspaceTabsUtility)
    domain_class = workspace_tabs.get_domain(properties[0])
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
        domain_status = {}
        for role in roles:
            domains = self.workspace_config.get_role_domains(role, tab)
            if domains:
                for domain in domains:
                    status = self.workspace_config.get_status(
                        role, domain, tab
                        )
                    if status:
                        if domain in domain_status.keys():
                            domain_status[domain].extend(status)
                        else:
                            domain_status[domain] = status
        return domain_status

    def item_status_filter(self, kw, roles):
        domain_status = {}
        if kw.get("filter_type", None):
            domain_class = self.workspace_config.get_domain(kw["filter_type"])
            if domain_class:
                domain_status[domain_class] = []
                for role in roles:
                    statuses = self.workspace_config.get_status(
                        role, domain_class, self.__name__
                        )
                    if kw.get("filter_status", None):
                        if kw["filter_status"] in statuses:
                            domain_status[domain_class].append(
                                kw["filter_status"])
                    else:
                        domain_status[domain_class].extend(statuses)
        else:
            domain_status = self.domain_status(roles, self.__name__)
            if kw.get("filter_status", None):
                for domain_class in domain_status.keys():
                    if kw["filter_status"] in domain_status[domain_class]:
                        domain_status[domain_class] = [kw["filter_status"]]
                    else:
                        del domain_status[domain_class]
        # Remove domain classes not filtered by any status
        # Filtering to an empty dict of status is inefficient in
        # Sqlalchemy and it raises a warning, this prevents that.
        for domain_class in domain_status.keys():
            if not domain_status[domain_class]:
                del domain_status[domain_class]
        return domain_status

    def title_column(self, domain_class):
        table = orm.class_mapper(domain_class).mapped_table
        utk = dict([(table.columns[k].key, k) for k in table.columns.keys()])
        # TODO : update to support other fields
        column = table.columns[utk["short_title"]]
        return column

    def filter_query(self, query, domain_class, kw):
        if kw.get("filter_short_title", None):
            column = self.title_column(domain_class)
            return query.filter("""(lower(%s) LIKE '%%%s%%')""" %
                        (column, kw["filter_short_title"].lower()))
        return query

    def order_query(self, query, domain_class, kw, reverse):
        if (kw.get("sort_on", None) and
            hasattr(domain_class, str(kw.get("sort_on")))
            ):
            if reverse:
                return query.order_by(expression.desc(
                    getattr(domain_class, str(kw.get("sort_on"))))) 
            else:
                return query.order_by(expression.asc(
                    getattr(domain_class, str(kw.get("sort_on")))))
        return query

    def _query(self, **kw):
        principal = get_principal()
        roles = get_workspace_roles()
        group_roles_domain_status = self.item_status_filter(kw, roles)
        session = Session()
        results = []
        count = 0
        first_page = not kw.get("start", 0)
        reverse = True if (kw.get("sort_dir", "desc") == "desc") else False
        for domain_class, status in group_roles_domain_status.iteritems():
            query = session.query(domain_class).filter(
                domain_class.status.in_(status)).enable_eagerloads(False)
            #filter on title
            query = self.filter_query(query, domain_class, kw)
            # Order results
            query = self.order_query(query, domain_class, kw, reverse)
            # The first page of the results is loaded the most number of times
            # The limit on the query below optimises for when no filter has
            # been applied by limiting the number of results returned.
            if first_page:
                count = count + query.count()
                query = query.limit(kw.get("limit", 25))
            results.extend(query.all())
        object_roles_domain_status = self.item_status_filter(kw, OBJECT_ROLES)
        for domain_class, status in object_roles_domain_status.iteritems():
            object_roles_results = []
            query = session.query(domain_class).filter(
                domain_class.status.in_(status)).enable_eagerloads(False)
            #filter on title
            query = self.filter_query(query, domain_class, kw)
            # Order results
            query = self.order_query(query, domain_class, kw, reverse)
            for obj in query.all():
                prm = IPrincipalRoleMap(obj)
                for obj_role in OBJECT_ROLES:
                    if (prm.getSetting(obj_role, principal.id) == Allow and
                            obj not in results):
                        object_roles_results.append(obj)
                        break
            if first_page:
                count = count + len(object_roles_results)
            results.extend(object_roles_results)
        # Sort items
        if (kw.get("sort_on", None) and kw.get("sort_dir", None)):
            results.sort(key=lambda x: getattr(x, str(kw.get("sort_on"))),
                         reverse=reverse)
        if not first_page:
            count = len(results)
        return (results, count)

    def query(self, **kw):
        return self._query(**kw)

    def items(self, **kw):
        for obj in self._query(kw):
            name = stringKey(obj)
            yield (name, contained(obj, self, name))

    def count(self):
        """Approximate count of items in a container
        """
        kw = {}
        principal = get_principal()
        roles = get_workspace_roles()
        group_roles_domain_status = self.item_status_filter(kw, roles)
        session = Session()
        count = 0
        for domain_class, status in group_roles_domain_status.iteritems():
            query = session.query(domain_class).filter(
                domain_class.status.in_(status)).enable_eagerloads(False)
            count = count + query.count()
        object_roles_domain_status = self.item_status_filter(kw, OBJECT_ROLES)
        for domain_class, status in object_roles_domain_status.iteritems():
            object_roles_results = []
            query = session.query(domain_class).filter(
                domain_class.status.in_(status)).enable_eagerloads(False)
            for obj in query.all():
                prm = IPrincipalRoleMap(obj)
                for obj_role in OBJECT_ROLES:
                    if (prm.getSetting(obj_role, principal.id) == Allow):
                        object_roles_results.append(obj)
                        break
            count = count + len(object_roles_results)
        return count

    def check_item(self, domain_class, status):
        roles = get_workspace_roles() + OBJECT_ROLES
        for role in roles:
            statuses = self.workspace_config.get_status(
                role, domain_class, self.__name__
                )
            if statuses and status in statuses:
                return True
        return False

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
        if self.check_item(domain_class, value.status):
            value = contained(value, self, name)
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
        if current_parliament:
            self.object_type = current_parliament.type
            self.oid = current_parliament.group_id
        else:
            self.object_type = None
            self.oid = None

