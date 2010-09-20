import zope.component
import zope.securitypolicy.interfaces

from ore.workflow.interfaces import IWorkflow, IWorkflowInfo
from bungeni.models import domain

import ore.workflow.workflow
import bungeni.core.version
import bungeni.models.interfaces
import bungeni.core.workflows.adapters
import bungeni.core.workflows.events
import alchemist.security.permission
import alchemist.security.role

def verify_workflow(wf):
    states = wf.workflow.states
    sources = set((states.get(wf.context.status),))
    destinations = set(wf.workflow.states.values())

    while sources and destinations:
        source = sources.pop()

        if source is not None:
            source = source.id
    
        for transition in wf.getTransitions(source):
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
    wf = IWorkflow(item)
    info = IWorkflowInfo(item)
    state = info.state().getState()
    return tuple(transition.transition_id 
               for transition in wf.getTransitions(state))

def list_permissions(item):
    wf = IWorkflow(item)
    info = IWorkflowInfo(item)
    state = info.state().getState()
    return tuple(transition.permission 
                for transition in wf.getTransitions(state))

def setup_adapters():
    
    # generic workflow adapters
    
    # this is an attempt (that does not give the desired result) to get
    #   bungeni.core.workflows.states.StateWorkflowInfo 
    # to be used as the factory provider for
    #   ore.workflow.interfaces.IWorkflowInfo
    
    zope.component.provideAdapter(
        adapts=[bungeni.alchemist.interfaces.IAlchemistContent], 
        provides=ore.workflow.interfaces.IWorkflowInfo,
        factory=bungeni.core.workflows.states.StateWorkflowInfo)
    
    zope.component.provideAdapter(
        adapts=[bungeni.alchemist.interfaces.IAlchemistContent], 
        provides=ore.workflow.interfaces.IWorkflowState,
        factory=bungeni.core.workflows.states.WorkflowState) 
    
    # content workflow
    
    zope.component.provideAdapter(
        bungeni.core.workflows.states.WorkflowState,
        (bungeni.models.interfaces.IBungeniContent,))

    zope.component.provideAdapter(
        bungeni.core.workflows.adapters.QuestionWorkflowAdapter,
        (domain.Question,))

    zope.component.provideAdapter(
        bungeni.core.workflows.states.StateWorkflowInfo,
        (domain.Question,))

    zope.component.provideAdapter(
        bungeni.core.workflows.adapters.BillWorkflowAdapter,
        (domain.Bill,))

    zope.component.provideAdapter(
        bungeni.core.workflows.states.StateWorkflowInfo,
        (domain.Bill,))

    zope.component.provideAdapter(
        bungeni.core.workflows.adapters.MotionWorkflowAdapter,
        (domain.Motion,))

    zope.component.provideAdapter(
        bungeni.core.workflows.states.StateWorkflowInfo,
        (domain.Motion,))

    zope.component.provideHandler(
        bungeni.core.workflows.events.workflowTransitionEventDispatcher)

    zope.component.provideAdapter(
        bungeni.core.version.ContextVersioned,
        (bungeni.core.interfaces.IVersionable,),
        bungeni.core.interfaces.IVersioned)

    zope.component.provideAdapter(
        bungeni.core.workflows.adapters.GroupSittingWorkflowAdapter,
        (domain.GroupSitting,))

    zope.component.provideAdapter(
        bungeni.core.workflows.states.StateWorkflowInfo,
        (domain.GroupSitting,))
        
    zope.component.provideAdapter(
        bungeni.core.workflows.adapters.AddressWorkflowAdapter,
        (domain.UserAddress,))

    zope.component.provideAdapter(
        bungeni.core.workflows.states.StateWorkflowInfo,
        (domain.UserAddress,))
        
    zope.component.provideAdapter(
        bungeni.core.workflows.adapters.TabledDocumentWorkflowAdapter,
        (domain.TabledDocument,))

    zope.component.provideAdapter(
        bungeni.core.workflows.states.StateWorkflowInfo,
        (domain.TabledDocument,))
    
    zope.component.provideAdapter(
        bungeni.core.workflows.adapters.AgendaItemWorkflowAdapter,
        (domain.AgendaItem,))

    zope.component.provideAdapter(
        bungeni.core.workflows.states.StateWorkflowInfo,
        (domain.AgendaItem,))


def setup_security_adapters():
    gsm = zope.component.getGlobalSiteManager()

    gsm.registerAdapter(
        alchemist.security.role.GlobalPrincipalRoleMap,
         (bungeni.models.interfaces.IBungeniApplication, ),
         zope.securitypolicy.interfaces.IPrincipalRoleMap)

    gsm.registerAdapter(
        alchemist.security.permission.GlobalRolePermissionMap,
         (bungeni.models.interfaces.IBungeniApplication, ),
         zope.securitypolicy.interfaces.IRolePermissionMap)
      
      
    gsm.registerAdapter(
        alchemist.security.role.LocalPrincipalRoleMap,
         (bungeni.models.interfaces.IBungeniContent, ),
         zope.securitypolicy.interfaces.IPrincipalRoleMap)
        
    gsm.registerAdapter(
        alchemist.security.permission.LocalRolePermissionMap,
         (bungeni.models.interfaces.IBungeniContent, ),
         zope.securitypolicy.interfaces.IRolePermissionMap) 

