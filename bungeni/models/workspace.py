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
from bungeni.ui.utils.common import get_context_roles
from bungeni.core.workflows.utils import get_group_context

def stringKey( instance ):
    unproxied = removeSecurityProxy( instance )
    mapper = orm.object_mapper( unproxied )
    primary_key = mapper.primary_key_from_instance( unproxied )
    domain_class = instance.__class__
    workspace_tabs = component.getUtility(IWorkspaceTabsUtility)
    item_type = workspace_tabs.getDomainOrType(domain_class)
    return "%s-%s" % (item_type, str(primary_key[0]))

def valueKey( identity_key ):
    """Returns a tuple, (domain_class, primary_key)"""
    if not isinstance( identity_key, (str, unicode)):
        raise ValueError
    properties = identity_key.split("-")
    if len(properties) != 2:
        raise ValueError
    workspace_tabs = component.getUtility(IWorkspaceTabsUtility)
    domain_class = workspace_tabs.getDomainOrType(properties[0])
    primary_key = properties[1]
    return domain_class, primary_key

class WorkspaceContainer(AlchemistContainer):
    __name__ = __parent__ = None
    interface.implements(interfaces.IWorkspaceContainer)
    
    def __init__(self, parent, tab_type, title, description, marker=None):
        self.__parent__ = parent
        self.__name__ = tab_type
        self.title = title
        self.description = description
        if marker is not None:
            interface.alsoProvides(self, marker)
        super(WorkspaceContainer, self).__init__()
    
    def get_principal_roles(self, principal):
        """Returns roles associated with groups.
        """
        session = Session()
        roles = []
        for group_id in principal.groups.keys():
            result = session.query(domain.Group).filter(
                            domain.Group.group_principal_id == group_id).first()
            if result:
                roles.extend(get_context_roles(
                                          get_group_context(result), principal))
        return roles
            
    @property
    def _query( self ):
        principal = get_principal()
        roles = self.get_principal_roles(principal)
        #Add bungeni.Owner to the roles
        roles.append("bungeni.Owner")
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
        
