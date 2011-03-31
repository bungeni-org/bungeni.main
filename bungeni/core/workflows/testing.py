import zope.component
import zope.securitypolicy.interfaces

from bungeni.core.workflow import interfaces
from bungeni.models import domain

import bungeni.core.version
import bungeni.models.interfaces
from bungeni.core.workflows import adapters
import bungeni.core.workflows.events
import bungeni.alchemist.security

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
        raise ValueError(
            "Some destinations could not be reached: %s." % ", ".join(
                [d.title for d in destinations]))

def list_transitions(item):
    wf = interfaces.IWorkflow(item)
    info = interfaces.IWorkflowController(item)
    state = info.state().getState()
    return tuple(transition.transition_id 
               for transition in wf.get_transitions_from(state))

def list_permissions(item):
    wf = interfaces.IWorkflow(item)
    info = interfaces.IWorkflowController(item)
    state = info.state().getState()
    return tuple(transition.permission 
                for transition in wf.get_transitions_from(state))

def provideAdapterWorkflowController(adapts_kls):
    zope.component.provideAdapter(
        bungeni.core.workflow.states.WorkflowController,
        (adapts_kls,),
        bungeni.core.workflow.interfaces.IWorkflowController)
def provideAdapterWorkflow(factory, adapts_kls):
    zope.component.provideAdapter(factory, (adapts_kls,),
        bungeni.core.workflow.interfaces.IWorkflow)

def setup_adapters():
    
    # generic workflow adapters
    
    # this is an attempt (that does not give the desired result) to get
    #   bungeni.core.workflow.states.WorkflowController 
    # to be used as the factory provider for
    #   interfaces.IWorkflowController
    
    zope.component.provideAdapter(
        factory=bungeni.core.workflow.states.WorkflowController,
        adapts=[bungeni.alchemist.interfaces.IAlchemistContent], 
        provides=interfaces.IWorkflowController
    )
    zope.component.provideAdapter(
        factory=bungeni.core.workflow.states.StateController,
        adapts=[bungeni.alchemist.interfaces.IAlchemistContent], 
        provides=bungeni.core.workflow.interfaces.IStateController
    )
    
    # content workflow
    # provideAdapter(factory, adapts=None, provides=None, name='')
    
    zope.component.provideAdapter(
        bungeni.core.workflow.states.StateController,
        (bungeni.models.interfaces.IBungeniContent,))
        
    provideAdapterWorkflow(adapters.QuestionWorkflowAdapter, domain.Question)
    provideAdapterWorkflowController(domain.Question)
    
    provideAdapterWorkflow(adapters.BillWorkflowAdapter, domain.Bill)
    provideAdapterWorkflowController(domain.Bill)
    
    provideAdapterWorkflow(adapters.MotionWorkflowAdapter, domain.Motion)
    provideAdapterWorkflowController(domain.Motion)
    
    zope.component.provideAdapter(
        bungeni.core.version.ContextVersioned,
        (bungeni.core.interfaces.IVersionable,),
        bungeni.core.interfaces.IVersioned)

    provideAdapterWorkflow(adapters.GroupSittingWorkflowAdapter, domain.GroupSitting)
    provideAdapterWorkflowController(domain.GroupSitting)
    
    provideAdapterWorkflow(adapters.UserAddressWorkflowAdapter, domain.UserAddress)
    provideAdapterWorkflow(adapters.GroupAddressWorkflowAdapter, domain.GroupAddress)
    provideAdapterWorkflowController(domain.UserAddress)
    
    provideAdapterWorkflow(adapters.TabledDocumentWorkflowAdapter, domain.TabledDocument)
    provideAdapterWorkflowController(domain.TabledDocument)

    provideAdapterWorkflow(adapters.AgendaItemWorkflowAdapter, domain.AgendaItem)
    provideAdapterWorkflowController(domain.AgendaItem)


def setup_security_adapters():
    gsm = zope.component.getGlobalSiteManager()
    
    gsm.registerAdapter(
        bungeni.alchemist.security.GlobalPrincipalRoleMap,
         (bungeni.models.interfaces.IBungeniApplication, ),
         zope.securitypolicy.interfaces.IPrincipalRoleMap)
    
    gsm.registerAdapter(
        bungeni.alchemist.security.GlobalRolePermissionMap,
         (bungeni.models.interfaces.IBungeniApplication, ),
         zope.securitypolicy.interfaces.IRolePermissionMap)
    
    gsm.registerAdapter(
        bungeni.alchemist.security.LocalPrincipalRoleMap,
         (bungeni.models.interfaces.IBungeniContent, ),
         zope.securitypolicy.interfaces.IPrincipalRoleMap)
    
    gsm.registerAdapter(
        bungeni.alchemist.security.LocalRolePermissionMap,
         (bungeni.models.interfaces.IBungeniContent, ),
         zope.securitypolicy.interfaces.IRolePermissionMap) 

