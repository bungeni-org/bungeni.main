# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Workspace

$Id: $
"""
log = __import__("logging").getLogger("bungeni.core.workspace")

import os
import time
from sqlalchemy import orm, Date, cast
from sqlalchemy.sql import expression
from lxml import etree
from collections import namedtuple

from zope import interface
from zope import component
from zope.app.publication.traversers import SimpleComponentTraverser
from zope.security.proxy import removeSecurityProxy
from zope.security import checkPermission
from zope.publisher.interfaces import NotFound
from zope.securitypolicy.interfaces import IPrincipalRoleMap
from zope.app.security.settings import Allow
from zope.securitypolicy.interfaces import IRole
from bungeni.alchemist import Session
from bungeni.alchemist.security import LocalPrincipalRoleMap
from bungeni.alchemist.container import AlchemistContainer, contained
from bungeni.models import utils, domain
from bungeni.models.roles import ROLES_DIRECTLY_DEFINED_ON_OBJECTS
from bungeni.capi import capi
from bungeni.core.interfaces import (
    IWorkspaceTabsUtility,
    IWorkspaceContainer,
    IWorkspaceUnderConsiderationContainer,
    IWorkspaceTrackedDocumentsContainer,
    IWorkspaceGroupsContainer,
)
from bungeni.ui.utils.common import get_workspace_roles
from bungeni.utils import common
from bungeni.ui.container import get_date_strings, string_to_date
from bungeni.core.workflows.utils import view_permission

TabCountRecord = namedtuple("TabCountRecord", ["timestamp", "count"])


class WorkspaceBaseContainer(AlchemistContainer):
    __name__ = __parent__ = None

    def __init__(self, tab_type, title, description=None, marker=None):
        self.__name__ = tab_type
        self.title = title
        self.description = description
        self.workspace_config = component.getUtility(IWorkspaceTabsUtility)
        self.tab_count_cache = {}
        if marker is not None:
            interface.alsoProvides(self, marker)
        super(WorkspaceBaseContainer, self).__init__()

    @staticmethod
    def string_key(instance):
        unproxied = removeSecurityProxy(instance)
        mapper = orm.object_mapper(unproxied)
        primary_key = mapper.primary_key_from_instance(unproxied)
        domain_class = instance.__class__
        workspace_utility = component.getUtility(IWorkspaceTabsUtility)
        item_type = workspace_utility.get_type(domain_class)
        return "%s-%d" % (item_type, primary_key[0])

    @staticmethod
    def value_key(identity_key):
        """Returns a tuple, (domain_class, primary_key)"""
        if not isinstance(identity_key, basestring):
            raise ValueError
        properties = identity_key.split("-")
        if len(properties) != 2:
            raise ValueError
        workspace_utility = component.getUtility(IWorkspaceTabsUtility)
        domain_class = workspace_utility.get_domain(properties[0])
        primary_key = properties[1]
        return domain_class, primary_key

    def domain_status(self, roles, tab):
        """Given a list of roles and tab returns a dictionary containing the
           domain classes and status of items to appear for that principal in
           that tab. Role should be a list, tab a string
        """
        domain_status = {}
        for role in roles:
            domain_classes = self.workspace_config.get_role_domains(role, tab)
            
            if domain_classes:
                for domain_class in domain_classes:
                    status = self.workspace_config.get_status(
                        role, domain_class, tab)
                    if status:
                        if domain_class in domain_status.keys():
                            for st in status:
                                if st not in domain_status[domain_class]:
                                    domain_status[domain_class].append(st)
                        else:
                            domain_status[domain_class] = status
        return domain_status

    def item_status_filter(self, kw, roles):
        domain_status = {}
        if kw.get("filter_type", None):
            domain_class = self.workspace_config.get_domain(kw["filter_type"])
            if domain_class:
                domain_status[domain_class] = []
                for role in roles:
                    statuses = self.workspace_config.get_status(
                        role, domain_class, self.__name__)
                    if kw.get("filter_status", None):
                        if (kw["filter_status"] in statuses and
                            kw["filter_status"] not in
                            domain_status[domain_class]):
                            domain_status[domain_class].append(
                                kw["filter_status"])
                    else:
                        domain_status[domain_class] = list(set(
                                domain_status[domain_class] + statuses))
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
        # !+ update to support other fields
        column = table.columns[utk["title"]]
        return column

    def filter_title(self, query, domain_class, kw):
        if kw.get("filter_title", None):
            column = self.title_column(domain_class)
            return query.filter(expression.func.lower(column).like(
                    "%%%s%%" % kw["filter_title"].lower()))
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

    def filter_status_date(self, query, domain_class, kw):
        #filter on status_date
        attr = getattr(domain_class, "status_date")
        start_date_str, end_date_str = get_date_strings(
            kw.get("filter_status_date", ""))
        start_date = string_to_date(start_date_str)
        end_date = string_to_date(end_date_str)
        if start_date:
            query = query.filter(cast(attr, Date) >= start_date)
        if end_date:
            query = query.filter(cast(attr, Date) <= end_date)
        return query

    def _query(self, **kw):
        raise NotImplementedError("Inheriting class must implement this")

    def query(self, **kw):
        return self._query(**kw)

    def count(self, read_from_cache=True):
        raise NotImplementedError("Inheriting class must implement this")

    def items(self, **kw):
        for obj in self._query(kw):
            name = self.string_key(obj)
            yield (name, contained(obj, self, name))

    def set_tab_count(self, principal_id, count):
        self.tab_count_cache[principal_id] = TabCountRecord(time.time(), count)

    def check_item(self, domain_class, status):
        roles = get_workspace_roles() + ROLES_DIRECTLY_DEFINED_ON_OBJECTS
        for role in roles:
            statuses = self.workspace_config.get_status(
                role, domain_class, self.__name__)
            if statuses and status in statuses:
                return True
        return False

    def get(self, name, default=None):
        try:
            domain_class, primary_key = self.value_key(name)
        except ValueError:
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
        this property returns the id of the parliament the currently logged in
        user is a member of
        """
        chamber = utils.get_login_user_chamber()
        return chamber.group_id

    def __getitem__(self, name):
        value = self.get(name)
        if value is None:
            raise KeyError(name)
        return value
    # see alchemist.traversal.managed.One2Many
    # see alchemist.ui.content.AddFormBase -> self.context[""] = ob
    # see bungeni.core.app.AppSetup
    # In the managed containers, the constraint manager
    # in One2Many sets the foreign key of an item to the
    # primary key of the container when an item is added.
    # This does the same for the workspace containers
    # This sets the foreign key of the doc to the parliament the currently
    # logged in member is a user

    def __setitem__(self, name, item):
        session = Session()
        chamber = utils.get_login_user_chamber()
        item.parliament_id = chamber.parliament_id
        session.add(item)


class WorkspaceContainer(WorkspaceBaseContainer):
    interface.implements(IWorkspaceContainer)

    def _query(self, **kw):
        principal = common.get_request_principal()
        roles = get_workspace_roles()
        group_roles_domain_status = self.item_status_filter(kw, roles)
        session = Session()
        results = []
        count = 0
        reverse = True if (kw.get("sort_dir", "desc") == "desc") else False
        for domain_class, status in group_roles_domain_status.iteritems():
            query = session.query(domain_class).filter(
                domain_class.status.in_(status)).enable_eagerloads(False)
            #filter on title
            query = self.filter_title(query, domain_class, kw)
            #filter on status_date
            query = self.filter_status_date(query, domain_class, kw)
            # Order results
            query = self.order_query(query, domain_class, kw, reverse)
            results.extend(query.all())
        for obj_role in ROLES_DIRECTLY_DEFINED_ON_OBJECTS:
            object_roles_domain_status = self.item_status_filter(
                kw, [obj_role])
            for domain_class, status in object_roles_domain_status.iteritems():
                query = session.query(domain_class).filter(
                    domain_class.status.in_(status)).enable_eagerloads(False)
                #filter on title
                query = self.filter_title(query, domain_class, kw)
                #filter on status_date
                query = self.filter_status_date(query, domain_class, kw)
                # Order results
                query = self.order_query(query, domain_class, kw, reverse)
                for obj in query.all():
                    if obj in results:
                        continue
                    prm = IPrincipalRoleMap(obj)
                    if (prm.getSetting(obj_role, principal.id) == Allow):
                        results.append(
                            contained(obj, self, self.string_key(obj)))
        results = [item for item in results if checkPermission(
            view_permission(item), contained(item, self, self.string_key(item)))]
        # Sort items
        if (kw.get("sort_on", None) and kw.get("sort_dir", None)):
            results.sort(key=lambda x: getattr(x, str(kw.get("sort_on"))),
                reverse=reverse)
        count = len(results)
        if not (kw.get("filter_title", None) or
                kw.get("filter_type", None) or
                kw.get("filter_status", None) or
                kw.get("filter_status_date", None)
            ):
            self.set_tab_count(principal.id, count)
        return (results, count)

    def count(self, read_from_cache=True):
        """Count of items in a container
        """
        principal = common.get_request_principal()
        if (read_from_cache and principal.id in self.tab_count_cache.keys() and
                (self.tab_count_cache[principal.id].timestamp +
                    capi.workspace_tab_count_cache_refresh_time) > time.time()
            ):
            return self.tab_count_cache[principal.id].count
        results, count = self._query()
        return count

class WorkspacePrincipalRoleMap(LocalPrincipalRoleMap):
    
    def __init__(self, context):
        self.context = context
        chamber = utils.get_login_user_chamber()
        if chamber:
            self.object_type = chamber.type
            self.oid = chamber.group_id
        else:
            self.object_type = None
            self.oid = None

class WorkspaceContainerTraverser(SimpleComponentTraverser):
    """Traverser for workspace containers"""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        """First checks if the name refers to a view of this container,
        then checks if the name refers to an item in this container,
        else raises a NotFound.
        """
        workspace = removeSecurityProxy(self.context)
        view = component.queryMultiAdapter((workspace, request), name=name)
        if view:
            return view
        ob = workspace.get(name)
        if ob:
            return ob
        log.error("Workspace - Object does not exist - %s", name)
        raise NotFound(workspace, name)


class WorkspaceTabsUtility(object):
    """This is utility stores the workflow configuration.
    """
    interface.implements(IWorkspaceTabsUtility)

    workspaces = {}
    domain_type = {}

    def set_content(self, role, tab, domain_class, status):
        """ Sets the workspace info
        """
        if role not in self.workspaces:
            self.workspaces[role] = {}
        if tab not in self.workspaces[role]:
            self.workspaces[role][tab] = {}
        if domain_class not in self.workspaces[role][tab]:
            self.workspaces[role][tab][domain_class] = []
        if status not in self.workspaces[role][tab][domain_class]:
            self.workspaces[role][tab][domain_class].append(status)

    def register_item_type(self, domain_class, item_type):
        """ Stores domain_class -> item_type and vice versa in a dictionary eg.
        domain.Bill -> bill. Used by the Workspace Container to set the
        contained object names and to retrieve the contained objects given
        a name.
        """
        if item_type in self.domain_type.keys():
            raise ValueError(
                "Multiple workspace declarations with same name - %s") % (
                    item_type)
        if domain_class in self.domain_type.keys():
            raise ValueError(
                "Multiple workspace domain classes with same name - %s") % (
                    domain_class)
        self.domain_type[item_type] = domain_class
        self.domain_type[domain_class] = item_type
    
    def get_role_domains(self, role, tab):
        """Returns a list of domain classes that a role will see for a
        certain tab.
        """
        if role in self.workspaces.keys():
            if tab in self.workspaces[role].keys():
                return list(self.workspaces[role][tab].keys())
        return []

    def get_domain(self, key):
        """Passed a type string returns the domain class."""
        if key in self.domain_type:
            return self.domain_type[key]
        return None

    def get_type(self, key):
        """Passed a domain class returns a string."""
        if key in self.domain_type:
            return self.domain_type[key]
        return None

    def get_tab(self, role, domain_class, status):
        """Returns the tab an object should be in, given its domain class,
        status and role.
        """
        if role in self.workspaces:
            for tab in self.workspaces[role]:
                if (domain_class in self.workspaces[role][tab] and
                        status in self.workspaces[role][tab][domain_class]
                    ):
                    return tab
        return None

    def get_status(self, role, domain_class, tab):
        """Returns all applicable statuses given the role,
        domain_class and tab.
        """
        if role in self.workspaces:
            if tab in self.workspaces[role]:
                if domain_class in self.workspaces[role][tab]:
                    return self.workspaces[role][tab][domain_class]
        return []
# register a WorkspaceTabsUtility instance
component.provideUtility(WorkspaceTabsUtility())


def load_workspaces():
    for type_key, ti in capi.iter_type_info():
        if ti.workflow and ti.workflow.has_feature("workspace"):
            load_workspace("%s.xml" % type_key, ti.domain_model, ti.workflow)

@capi.bungeni_custom_errors
def load_workspace(file_name, domain_class, workflow):
    """Loads the workspace configuration for each documemnt.
    """
    workspace_utility = component.getUtility(IWorkspaceTabsUtility)
    path = capi.get_path_for("workspace")
    file_path = os.path.join(path, file_name)
    workspace = capi.schema.validate_file_rng("workspace", file_path)
    item_type = file_name.split(".")[0]
    workspace_utility.register_item_type(domain_class, item_type)
    for state in workspace.iterchildren(tag="state"):
        # Raises invalid state error if there is no such state defined in the
        # workflow
        workflow.get_state(state.get("id"))
        for tab in state.iterchildren(tag="tab"):
            assert tab.get("id") in capi.workspace_tabs, \
                "Workspace configuration error : " \
                "Invalid tab - %s. file: %s, state : %s" % (
                    tab.get("id"), file_name, state.get("id"))
            if tab.get("roles"):
                roles = capi.schema.qualified_roles(tab.get("roles"))
                for role in roles:
                    assert component.queryUtility(IRole, role, None), \
                        "Workspace configuration error : " \
                        "Invalid role - %s. file: %s, state : %s" % (
                            role, file_name, state.get("id"))
                    workspace_utility.set_content(role,
                        tab.get("id"), domain_class, state.get("id"))


class WorkspaceUnderConsiderationContainer(WorkspaceBaseContainer):

    interface.implements(IWorkspaceUnderConsiderationContainer)

    def __init__(self, name, title, description=None, marker=None):
        self.__name__ = name
        self.title = title
        self.description = description
        self.workspace_config = component.getUtility(IWorkspaceTabsUtility)
        if marker is not None:
            interface.alsoProvides(self, marker)
        AlchemistContainer.__init__(self)

    def domain_status(self):
        domain_status_map = {}
        workspace_roles = set(get_workspace_roles())
        for type_key, ti in capi.iter_type_info():
            workflow = ti.workflow
            if (workflow and workflow.has_feature("workspace") and
                (not workspace_roles.isdisjoint(set(workflow.roles_used)))):
                states = workflow.get_state_ids(
                    tagged=["public"], not_tagged=["terminal"],
                    conjunction="AND")
                domain_status_map[ti.domain_model] = states
        return domain_status_map

    def item_status_filter(self, kw):
        domain_status_map = self.domain_status()
        filter_domain_status = {}
        if kw.get("filter_type", None):
            domain_class = self.workspace_config.get_domain(kw["filter_type"])
            if domain_class in domain_status_map.keys():
                if kw.get("filter_status", None):
                    if kw["filter_status"] in domain_status_map[domain_class]:
                        filter_domain_status[domain_class] = [kw["filter_status"]]
                else:
                    filter_domain_status[domain_class] = domain_status_map[domain_class]
        else:
            if kw.get("filter_status", None):
                for domain_class in domain_status_map.keys():
                    if kw["filter_status"] in domain_status_map[domain_class]:
                        filter_domain_status[domain_class] = [kw["filter_status"]]
            else:
                filter_domain_status = domain_status_map
        return filter_domain_status

    def _query(self, **kw):
        session = Session()
        domain_status = self.item_status_filter(kw)
        reverse = True if (kw.get("sort_dir", "desc") == "desc") else False
        results = []
        for domain_class, status in domain_status.iteritems():
            query = session.query(domain_class).filter(
                domain_class.status.in_(status)).enable_eagerloads(False)
            query = self.filter_title(query, domain_class, kw)
            #filter on status_date
            query = self.filter_status_date(query, domain_class, kw)
            query = self.order_query(query, domain_class, kw, reverse)
            results.extend(query.all())
        count = len(results)
        if (kw.get("sort_on", None) and kw.get("sort_dir", None)):
            results.sort(key=lambda x: getattr(x, str(kw.get("sort_on"))),
                         reverse=reverse)
        return (results, count)

    def check_item(self, domain_class, status):
        domain_status_map = self.domain_status()
        if (domain_class in domain_status_map.keys() and
            status in domain_status_map[domain_class]):
            return True
        else:
            return False


class WorkspaceTrackedDocumentsContainer(WorkspaceUnderConsiderationContainer):

    interface.implements(IWorkspaceTrackedDocumentsContainer)

    def _query(self, **kw):
        session = Session()
        user = utils.get_login_user()
        reverse = True if (kw.get("sort_dir", "desc") == "desc") else False
        results = []
        domain_status = self.item_status_filter(kw)
        for domain_class, status in domain_status.iteritems():
            query = session.query(domain_class
                ).filter(domain_class.status.in_(status)
                ).enable_eagerloads(False
                ).join(domain.UserSubscription
                ).filter(domain.UserSubscription.user_id == user.user_id)
            query = self.filter_title(query, domain_class, kw)
            #filter on status_date
            query = self.filter_status_date(query, domain_class, kw)
            query = self.order_query(query, domain_class, kw, reverse)
            results.extend(query.all())
        count = len(results)
        if (kw.get("sort_on", None) and kw.get("sort_dir", None)):
            results.sort(key=lambda x: getattr(x, str(kw.get("sort_on"))),
                         reverse=reverse)
        return (results, count)

class WorkspaceGroupsContainer(WorkspaceBaseContainer):

    interface.implements(IWorkspaceGroupsContainer)

    def __init__(self, name, title, description, marker=None):
        self.__name__ = name
        self.title = title
        self.description = description
        self.workspace_config = component.getUtility(IWorkspaceTabsUtility)
        if marker is not None:
            interface.alsoProvides(self, marker)
        AlchemistContainer.__init__(self)

    @staticmethod
    def string_key(instance):
        unproxied = removeSecurityProxy(instance)
        principal_name = unproxied.principal_name
        url_id = str(principal_name).replace(".", "-")
        return url_id

    @staticmethod
    def value_key(identity_key):
        if not isinstance(identity_key, basestring):
            raise ValueError
        properties = identity_key.split("-")
        if len(properties) != 3:
            raise ValueError
        principal_name = identity_key.replace("-", ".")
        return domain.Group, principal_name

    def title_column(self, domain_class):
        table = orm.class_mapper(domain_class).mapped_table
        utk = dict([(table.columns[k].key, k) for k in table.columns.keys()])
        # TODO : update to support other fields
        column = table.columns[utk["full_name"]]
        return column
    
    def get(self, name, default=None):
        try:
            domain_class, principal_name = self.value_key(name)
        except ValueError:
            return default
        session = Session()
        try:
            value = session.query(domain_class).filter(
                domain_class.principal_name == principal_name).one()
        except orm.exc.NoResultFound:
            return default
        return contained(value, self, name)
    
    def filter_type(self, query, domain_class, kw):
        if kw.get("filter_type", None):
            query = query.filter(domain_class.type == kw.get("filter_type"))
        return query

    def _query(self, **kw):
        results = []
        session = Session()
        user = utils.get_login_user()
        #status = self.item_status_filter(kw)
        reverse = True if (kw.get("sort_dir", "desc") == "desc") else False
        query = session.query(domain.Group).join(
            domain.GroupMembership).filter(
            expression.and_(
                    domain.GroupMembership.user_id == user.user_id,
                    domain.GroupMembership.active_p == True,
                    #domain.Group.status.in_(status)
                    ))
        query = self.filter_title(query, domain.Group, kw)
        query = self.filter_type(query, domain.Group, kw)
        query = self.filter_status_date(query, domain.Group, kw)
        query = self.order_query(query, domain.Group, kw, reverse)
        results = query.all()
        count = query.count()
        return (results, count)


class WorkspaceSchedulableContainer(WorkspaceUnderConsiderationContainer):
    """Contains public documents for all types implemeting schedule feature
    """
    
    def domain_status(self):
        domain_status_map = {}
        for type_key, ti in capi.iter_type_info():
            workflow = ti.workflow
            if workflow and workflow.has_feature("schedule"):
                states = workflow.get_state_ids(tagged=["public"])
                domain_status_map[ti.domain_model] = states
        return domain_status_map

