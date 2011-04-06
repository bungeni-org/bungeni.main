
import zope.component
import zope.securitypolicy.interfaces
import bungeni.alchemist.security
import bungeni.models.interfaces


def verify_workflow(awf):
    states = awf.workflow.states
    sources = set((states.get(awf.context.status),))
    destinations = set(states.values())
    while sources and destinations:
        source = sources.pop()
        if source is not None:
            source = source.id
        for transition in awf.get_transitions_from(source):
            destination = states[transition.destination]
            if destination not in destinations:
                continue
            assert destination is not source
            sources.add(destination)
            destinations.remove(destination)
    if destinations:
        raise ValueError("Some destinations could not be reached: %s." % (
                ", ".join([d.title for d in destinations])))


def setup_security_adapters():
    gsm = zope.component.getGlobalSiteManager()
    
    gsm.registerAdapter(
        bungeni.alchemist.security.GlobalPrincipalRoleMap,
         (bungeni.models.interfaces.IBungeniApplication,),
         zope.securitypolicy.interfaces.IPrincipalRoleMap)
    
    gsm.registerAdapter(
        bungeni.alchemist.security.GlobalRolePermissionMap,
         (bungeni.models.interfaces.IBungeniApplication,),
         zope.securitypolicy.interfaces.IRolePermissionMap)
    
    gsm.registerAdapter(
        bungeni.alchemist.security.LocalPrincipalRoleMap,
         (bungeni.models.interfaces.IBungeniContent,),
         zope.securitypolicy.interfaces.IPrincipalRoleMap)
    
    gsm.registerAdapter(
        bungeni.alchemist.security.LocalRolePermissionMap,
         (bungeni.models.interfaces.IBungeniContent,),
         zope.securitypolicy.interfaces.IRolePermissionMap) 

