# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Workspace

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workspace")

import sys
import os
import time
from sqlalchemy import orm, Date, cast
from sqlalchemy.sql import expression
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
from bungeni.models.interfaces import IDoc
from bungeni.capi import capi
from bungeni.core.interfaces import (
    IWorkspaceTabsUtility,
    IWorkspaceContainer,
    IWorkspaceUnderConsiderationContainer,
    IWorkspaceTrackedDocumentsContainer,
    IWorkspaceGroupsContainer,
)
from bungeni.ui.utils.common import get_workspace_roles
from bungeni.utils import common, probing
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
        type_key = workspace_utility.get_type(domain_class)
        return "%s-%d" % (type_key, primary_key[0])

    @staticmethod
    def value_key(identity_key):
        """Returns a tuple, (domain_class, primary_key).
        """
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
        """Returns {type: [str]} where type is a domain model class and [str]
        is the list of workflow states.
        """
        filter_type = kw.get("filter_type", None)
        filter_status = kw.get("filter_status", None)
        domain_status = {}
        if filter_type:
            domain_class = self.workspace_config.get_domain(filter_type)
            if domain_class:
                domain_status[domain_class] = []
                for role in roles:
                    statuses = self.workspace_config.get_status(
                        role, domain_class, self.__name__)
                    if filter_status:
                        if (filter_status in statuses and
                                filter_status not in domain_status[domain_class]
                            ):
                            domain_status[domain_class].append(filter_status)
                    else:
                        domain_status[domain_class] = list(set(
                            domain_status[domain_class] + statuses))
        else:
            domain_status = self.domain_status(roles, self.__name__)
            if filter_status:
                for domain_class in domain_status.keys():
                    if filter_status in domain_status[domain_class]:
                        domain_status[domain_class] = [filter_status]
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
    
    def filter_group(self, query, domain_class, kw):
        try:
            group_id = int(kw.get("filter_group", 0) or 0) # incoming value is 
            # typically the "" empty string, resulting in exception noise below
        except (TypeError, ValueError):
            probing.log_exc(sys.exc_info(), log_handler=log.error)
            group_id = 0
        if group_id:
            if hasattr(domain_class, "group_id"):
                query = query.filter(domain_class.group_id==group_id)
            elif hasattr(domain_class, "chamber_id"):
                query = query.filter(domain_class.chamber_id==group_id)
        return query
    
    def filter_title(self, query, domain_class, kw):
        if kw.get("filter_title", None):
            column = self.title_column(domain_class)
            return query.filter(expression.func.lower(column).like(
                "%%%s%%" % kw["filter_title"].lower()))
        return query

    def order_query(self, query, domain_class, kw, reverse):
        if (kw.get("sort_on", None) and
                hasattr(domain_class, str(kw.get("sort_on")))):
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
    def chamber_id(self):
        """Vocabularies in the forms get the chamber id from the context,
        this property returns the id of the chamber the currently logged in
        user is a member of
        """
        chamber = utils.get_user_chamber(utils.get_login_user())
        return chamber.group_id

    # see alchemist.traversal.managed.One2Many
    # see alchemist.ui.content.AddFormBase -> self.context[""] = ob
    # see bungeni.core.app.AppSetup
    # In the managed containers, the constraint manager
    # in One2Many sets the foreign key of an item to the
    # primary key of the container when an item is added.
    # This does the same for the workspace containers
    # This sets the foreign key of the doc to the chamber the currently
    # logged in member is a user
    
    def is_type_workspaced(self, type_key):
        """Is this type workspaced for this !+workspace context (for user)?
        !+WORKSPACE_GROUP_CONTEXTS should be refined further to specific groups, 
        not just be WorkspaceContainer-wide (for all groups)!
        """
        ti = capi.get_type_info(type_key)
        workspace_feature = ti.workflow.get_feature("workspace")
        if workspace_feature is not None:
            group_names = workspace_feature.get_param("group_names")
            if group_names:
                user = utils.get_login_user()
                for group in utils.get_user_groups(user):
                    if group.conceptual_name in group_names:
                        return True
        return False

class WorkspaceContainer(WorkspaceBaseContainer):
    interface.implements(IWorkspaceContainer)
    
    def _query(self, **kw):
        # !+REWORK **kw to be explicit keywords, see context.query() in ui/workspace.py
        session = Session()
        results = []
        count = 0
        reverse = True if (kw.get("sort_dir", "desc") == "desc") else False
        principal_id = common.get_request_principal().id
        
        def extend_results_for_roles(roles):
            domain_status = self.item_status_filter(kw, roles)
            OBJECT_ROLES = [ 
                role for role in roles if role in ROLES_DIRECTLY_DEFINED_ON_OBJECTS ]
            for domain_class, status in domain_status.iteritems():
                query = session.query(domain_class).filter(
                    domain_class.status.in_(status)).enable_eagerloads(False)
                query = self.filter_group(query, domain_class, kw)
                query = self.filter_title(query, domain_class, kw)
                query = self.filter_status_date(query, domain_class, kw)
                query = self.order_query(query, domain_class, kw, reverse)
                for obj in query.all():
                    if obj in results:
                        continue
                    if OBJECT_ROLES:
                        prm = IPrincipalRoleMap(obj)
                        if not prm.getSetting(obj_role, principal_id) == Allow:
                            continue
                    results.append(contained(obj, self, self.string_key(obj)))
        # get results for roles
        extend_results_for_roles(get_workspace_roles())
        for obj_role in ROLES_DIRECTLY_DEFINED_ON_OBJECTS:
            extend_results_for_roles([obj_role])
        
        # filter 
        results = [ item for item in results 
            if checkPermission(view_permission(item), item) ]
        
        # sort items
        if (kw.get("sort_on", None) and kw.get("sort_dir", None)):
            results.sort(key=lambda x: getattr(x, str(kw.get("sort_on"))),
                reverse=reverse)
        count = len(results)
        if not (kw.get("filter_title", None) or
                kw.get("filter_type", None) or
                kw.get("filter_status", None) or
                kw.get("filter_status_date", None)
            ):
            self.set_tab_count(principal_id, count)
        return (results, count)
    
    def count(self, read_from_cache=True, **kw):
        """Count of items in a container
        """
        principal = common.get_request_principal()
        if (read_from_cache and principal.id in self.tab_count_cache.keys() and
                (self.tab_count_cache[principal.id].timestamp +
                    capi.workspace_tab_count_cache_refresh_time) > time.time()
            ):
            return self.tab_count_cache[principal.id].count
        results, count = self._query(**kw)
        return count


class WorkspacePrincipalRoleMap(LocalPrincipalRoleMap):
    
    def __init__(self, context):
        self.context = context
        chamber = utils.get_user_chamber(utils.get_login_user())
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
    domain_types_by_key = {}
    domain_types_by_type = {}

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

    def register_domain_type(self, domain_class, type_key):
        """ Stores domain_class -> type_key and vice versa in a dictionary eg.
        domain.Bill -> bill. Used by the Workspace Container to set the
        contained object names and to retrieve the contained objects given
        a name.
        """
        if type_key in self.domain_types_by_key:
            raise ValueError(
                "Multiple workspace declarations with same name - %s") % (
                    type_key)
        if domain_class in self.domain_types_by_type:
            raise ValueError(
                "Multiple workspace domain classes with same name - %s") % (
                    domain_class)
        self.domain_types_by_key[type_key] = domain_class
        self.domain_types_by_type[domain_class] = type_key
    
    def get_role_domains(self, role, tab):
        """Returns a list of domain classes that a role will see for a
        certain tab.
        """
        if role in self.workspaces.keys():
            if tab in self.workspaces[role].keys():
                return list(self.workspaces[role][tab].keys())
        return []

    def get_domain(self, key):
        """Passed a type string returns the domain class or None.
        """
        return self.domain_types_by_key.get(key, None)

    def get_type(self, domain_class):
        """Passed a domain class returns the type_key or None.
        """
        return self.domain_types_by_type.get(domain_class, None)

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
    """Loads the workspace configuration for each document.
    """
    # !+LEGISLATURE_SETUP on first run on an emtpy database, no groups exists 
    # and so all these tests will fail -- as a partial workaround, only execute
    # these tests if one Legislature instance is in existence...
    if Session().query(domain.Legislature).all():
        # !+GROUP_NAMES_VALIDATION
        from bungeni.models.utils import get_group_conceptual_active
        for conceptual_name in workflow.get_feature("workspace").get_param("group_names"):
            try:
                get_group_conceptual_active(conceptual_name)
            except orm.exc.NoResultFound:
                raise Exception("Workflow %r feature %r parameter %r contains "
                    "invalid value %r -- no active group with such a conceptual_name "
                    "found in the database." % (
                        workflow.name, "workspace", "group_names", conceptual_name))
        # !+/GROUP_NAMES_VALIDATION
    workspace_utility = component.getUtility(IWorkspaceTabsUtility)
    path = capi.get_path_for("workspace")
    file_path = os.path.join(path, file_name)
    workspace = capi.schema.validate_file_rng("workspace", file_path)
    type_key = file_name.split(".")[0]
    workspace_utility.register_domain_type(domain_class, type_key)
    # to bookkeep that every workflow state is workspace-declared
    workflow_state_ids = set(workflow._states_by_id.keys())
    for state in workspace.iterchildren(tag="state"):
        state_id = state.get("id")
        workflow.get_state(state_id) # InvalidStateError if no such state
        assert state_id in workflow_state_ids, \
            "configuration file workspace/%s - duplicate declaration found for state: %r" % (
                file_name, state_id)
        workflow_state_ids.remove(state_id)
        for tab in state.iterchildren(tag="tab"):
            tab_name = tab.get("id") # !+
            assert tab_name in capi.workspace_tabs, \
                "configuration file workspace/%s - invalid tab: %r [state: %r]" % (
                    file_name, tab_name, state_id)
            tab_roles = tab.get("roles")
            if tab_roles:
                roles = capi.schema.qualified_roles(tab_roles.split())
                for role in roles:
                    assert component.queryUtility(IRole, role, None), \
                        "configuration file workspace/%s - invalid role: %r [state: %r]" % (
                            file_name, role, state_id)
                    workspace_utility.set_content(
                        role, tab_name, domain_class, state_id)
    assert not workflow_state_ids, \
        "configuration file workspace/%s - no declaration found for states: %s" % (
            file_name, list(workflow_state_ids))


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
        """Returns {type: [str]} where type is a domain model class and [str]
        is the list of workflow states.
        """
        filter_type = kw.get("filter_type", None)
        filter_status = kw.get("filter_status", None)
        domain_status_map = self.domain_status()
        filter_domain_status = {}
        if filter_type:
            domain_class = self.workspace_config.get_domain(filter_type)
            if domain_class in domain_status_map.keys():
                if filter_status:
                    if filter_status in domain_status_map[domain_class]:
                        filter_domain_status[domain_class] = [filter_status]
                else:
                    filter_domain_status[domain_class] = domain_status_map[domain_class]
        elif filter_status:
            for domain_class in domain_status_map.keys():
                if filter_status in domain_status_map[domain_class]:
                    filter_domain_status[domain_class] = [filter_status]
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
            query = self.filter_group(query, domain_class, kw)
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
                status in domain_status_map[domain_class]
            ):
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
            if IDoc.implementedBy(domain_class):
                query = session.query(domain_class
                    ).filter(domain_class.status.in_(status)
                    ).enable_eagerloads(False
                    ).join(domain.UserSubscription
                    ).filter(domain.UserSubscription.principal_id == user.user_id)
                query = self.filter_group(query, domain_class, kw)
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
        url_id = "-".join(str(principal_name).split(".g", 1))
        return url_id
    
    @staticmethod
    def value_key(url_id):
        # !+ if url_id is actual principal_name (e.g. "assembly_office_clerk.g9"
        # instead of "assembly_office_clerk-9") this would still work...
        if not isinstance(url_id, basestring):
            raise ValueError
        #properties = url_id.split("-")
        #if len(properties) != 3:
        #    raise ValueError
        principal_name = ".g".join(url_id.split("-", 1))
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
        query = Session().query(domain_class
                    ).filter(domain_class.principal_name == principal_name)
        try:
            value = query.one()
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
            domain.GroupMember).filter(
            expression.and_(
                    domain.GroupMember.user_id == user.user_id,
                    domain.GroupMember.active_p == True,
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


