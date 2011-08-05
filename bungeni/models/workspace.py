from ore.alchemist.container import AlchemistContainer, contained
from bungeni.models.utils import get_principal
from bungeni.core.interfaces import IWorkspaceTabsUtility
from zope import component
from bungeni.models import domain
from zope.security.proxy import removeSecurityProxy
from sqlalchemy import orm, exceptions
from zope import interface
from zope.location.interfaces import ILocation
from bungeni.models import interfaces
from bungeni.alchemist import Session, model
from bungeni.ui.utils.common import get_context_roles, get_workspace_roles
from bungeni.core.workflows.utils import get_group_context
from zope.securitypolicy.interfaces import IPrincipalRoleMap
from bungeni.models.utils import get_current_parliament
from bungeni.alchemist.security import LocalPrincipalRoleMap

def stringKey( instance ):
    unproxied = removeSecurityProxy( instance )
    mapper = orm.object_mapper( unproxied )
    primary_key = mapper.primary_key_from_instance( unproxied )
    domain_class = instance.__class__
    workspace_tabs = component.getUtility(IWorkspaceTabsUtility)
    item_type = workspace_tabs.getType(domain_class)
    return "%s-%s" % (item_type, str(primary_key[0]))

def valueKey( identity_key ):
    """Returns a tuple, (domain_class, primary_key)"""
    if not isinstance( identity_key, (str, unicode)):
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
        if marker is not None:
            interface.alsoProvides(self, marker)
        super(WorkspaceContainer, self).__init__()
    
    @property
    def _query( self ):
        principal = get_principal()
        roles = get_workspace_roles(principal)
        workspace_tabs = component.getUtility(IWorkspaceTabsUtility)
        domain_status = {}
        for role in roles:
            dom_stat = workspace_tabs.getDomainAndStatuses(role, self.__name__)
            if dom_stat:
                for key in dom_stat.keys():
                    if key in domain_status.keys():
                        domain_status[key].extend(dom_stat[key])
                    else:
                        domain_status[key] = dom_stat[key]    
        session = Session()
        results = []
        for domain_class in domain_status.keys():
            query = session.query(domain_class).filter(
                           domain_class.status.in_(domain_status[domain_class]))
            results.extend(query.all())
        results.sort(key = lambda x: x.status_date, reverse=True)
        for result in results:
            yield result
        
    def items( self ):
        for obj in self._query:
            name = stringKey( obj )
            yield (name, contained(obj, self, name))
            
    def get( self, name, default=None ):
        try:
            domain_class, primary_key = valueKey( name )
        except:
            return default
        session = Session()
        value = session.query(domain_class).get(primary_key)
        if value is None:
            return default
        # The check below is to ensure an error is raised if an object is not
        # in the tab requested eg. through an outdated url
        if value in self._query:
            value = contained( value, self, stringKey(value) )
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
        value = self.get( name )
        if value is None:
            raise KeyError( name )
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
    def __init__( self, context ):
        self.context = context
        current_parliament = get_current_parliament()
        self.object_type = current_parliament.type
        self.oid = current_parliament.group_id
