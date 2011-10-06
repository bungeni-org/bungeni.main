# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Loading of workflows and and set-up and registering of associated adapters.

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflows")

from zope import component
from zope.interface import classImplements
import zope.securitypolicy.interfaces
from bungeni.models import interfaces
from bungeni.core.workflow import xmlimport
from bungeni.core.workflow.interfaces import IWorkflow, IWorkflowed, \
    IStateController, IWorkflowController
from bungeni.core.workflow.states import StateController, WorkflowController, \
    get_object_state_rpm, get_object_version_state_rpm
import bungeni.core.audit
import bungeni.core.version
import bungeni.core.interfaces
from bungeni.utils.capi import capi

__all__ = ["get_workflow"]


WORKFLOW_REG = [ # !+bungeni_custom
    # (name, iface)
    ("address", interfaces.IUserAddress),
    ("address", interfaces.IGroupAddress),
    # !+AttachedFile (mr, jul-2011)
    # a) must be loaded before any other type that *may* support attachments!
    # b) MUST support versions
    ("attachedfile", interfaces.IAttachedFile),
    ("agendaitem", interfaces.IAgendaItem),
    ("bill", interfaces.IBill),
    ("committee", interfaces.ICommittee),
    ("event", interfaces.IEventItem),
    ("group", interfaces.IBungeniGroup),
    ("groupsitting", interfaces.IGroupSitting),
    ("heading", interfaces.IHeading),
    ("motion", interfaces.IMotion),
    ("parliament", interfaces.IParliament),
    ("question", interfaces.IQuestion),
    ("report", interfaces.IReport),
    ("tableddocument", interfaces.ITabledDocument),
    ("user", interfaces.IBungeniUser),
    ("signatory", interfaces.ISignatory),
]
# !+ dedicated interfaces for archetype incantations should be auto-generated, 
# from specific workflow name/attr... e.g. via:
# zope.interface.interface.InterfaceClass(iname, bases, __module__)

def get_workflow(name):
    """Get the named workflow utility.
    """
    #return component.getUtility(IWorkflow, name) !+BREAKS_DOCTESTS(mr, apr-2011)
    return get_workflow._WORKFLOWS[name]
# a mapping of workflow names workflow instances as a supplementary register 
# of instantiated workflows -- not cleared when componenet registry is cleared
get_workflow._WORKFLOWS = {} # { name: workflow.states.Workflow }


# component.provideUtility(component, provides=None, name=u''):
def provideUtilityWorkflow(utility, name):
    #component.provideUtility(utility, IWorkflow, name) !+BREAKS_DOCTESTS
    get_workflow._WORKFLOWS[name] = utility

# component.provideAdapter(factory, adapts=None, provides=None, name="")
def provideAdapterWorkflow(factory, adapts_kls):
    component.provideAdapter(factory, (adapts_kls,), IWorkflow)


def load_workflow(name, path_custom_workflows=capi.get_path_for("workflows")):
    """Setup the Workflow instance, from XML definition, for named workflow.
    """
    # load / register as utility / retrieve
    #
    #if not component.queryUtility(IWorkflow, name): !+BREAKS_DOCTESTS
    if not get_workflow._WORKFLOWS.has_key(name):
        wf = xmlimport.load(path_custom_workflows, name)
        log.debug("Loading WORKFLOW: %s %s" % (name, wf))
        # debug info
        for state_key, state in wf.states.items():
            log.debug("   STATE: %s %s" % (state_key, state))
            for p in state.permissions:
                log.debug("          %s" % (p,))
        # Workflow instances as utilities
        provideUtilityWorkflow(wf, name)
    else:
        wf = get_workflow(name)
        log.warn("Already Loaded WORKFLOW : %s %s" % (name, wf))


def apply_customization_workflow(name):
    """Apply customizations, features as per configuration from a workflow. 
    Must (currently) be run after db setup.
    """
    # support to infer/get the domain class from the workflow name
    def camel(name):
        """Convert an underscore-separated word to CamelCase.
        """
        return "".join([ s.capitalize() for s in name.split("_") ])
    from bungeni.models import domain, schema, orm
    def get_domain_kls(workflow_name):
        """Infer a workflow's target domain kls from the workflow file name, 
        following underscore naming to camel case convention; names that do 
        not follow the convention are custom handled, as per mapping below.
        """
        # !+ should state it explicitly as a param?
        # !+ problem with multiple types sharing same workflow e.g. 
        #    UserAddress, GroupAddress
        kls_name = camel(
            get_domain_kls.non_conventional.get(workflow_name, workflow_name))
        return getattr(domain, kls_name)
    # !+RENAME_TO_CONVENTION
    get_domain_kls.non_conventional = {
        "address": "address", # !+ use common base cls for User & Group addresses
        "agendaitem": "agenda_item",
        "attachedfile": "attached_file",
        "event": "event_item",
        "groupsitting": "group_sitting",
        "tableddocument": "tabled_document",
    }
    # get the domain class
    kls = get_domain_kls(name)
    
    # We "mark" the domain class with IWorkflowed, to be able to 
    # register/lookup adapters generically on this single interface.
    classImplements(kls, IWorkflowed)
    
    # dynamic features from workflow
    wf = get_workflow(name)
    def _apply_customization_workflow(kls):
        # decorate/modify domain/schema/mapping as needed
        kls = domain.configurable_domain(kls, wf)
        schema.configurable_schema(kls)
        orm.configurable_mappings(kls)
        # !+ ok to call set_auditor(kls) more than once?
        # !+ following should be part of the domain.auditable(kls) logic
        if wf.has_feature("audit"):
            # create/set module-level dedicated auditor singleton for auditable kls
            bungeni.core.audit.set_auditor(kls)
    
    if kls.__dynamic_features__:
        _apply_customization_workflow(kls)


def load_workflows():
    # workflow instances (+ adapter *factories*)
    for name, iface in WORKFLOW_REG:
        load_workflow(name)
        # !+ address: UserAddress, GroupAddress
        apply_customization_workflow(name)


def register_workflow_adapters():
    """Register general and specific worklfow-related adapters.
    
    Note: as the registry is cleared when placelessetup.tearDown() is called,
    this needs to be called independently on each doctest.
    """
    # General adapters on generic IWorkflowed (once for all workflows).
    
    # IRolePermissionMap adapter for IWorkflowed objects
    component.provideAdapter(get_object_state_rpm, 
        (IWorkflowed,),
        zope.securitypolicy.interfaces.IRolePermissionMap)
    # IRolePermissionMap adapter for a version of an IWorkflowed object
    component.provideAdapter(get_object_version_state_rpm, 
        (interfaces.IVersion,),
        zope.securitypolicy.interfaces.IRolePermissionMap)
    
    # !+IPrincipalRoleMap(mr, aug-2011) also migrate principal_role_map from 
    # db to be dynamic and based on workflow definitions. Would need to infer
    # the Roles of a user with respect to the context e.g.owner, or signatory
    # and then check against the permissions required by the current object's
    # state. 
    
    # IStateController
    component.provideAdapter(
        StateController, (IWorkflowed,), IStateController)
    # IWorkflowController
    component.provideAdapter(
        WorkflowController, (IWorkflowed,), IWorkflowController)
    # IVersioned
    component.provideAdapter(bungeni.core.version.ContextVersioned,
        (interfaces.IVersionable,),
        bungeni.core.interfaces.IVersioned)
    
    # Specific adapters, a specific iface per workflow.
    
    for name, iface in WORKFLOW_REG:
        wf = get_workflow(name)
        # Workflows are also the factory of own AdaptedWorkflows
        provideAdapterWorkflow(wf, iface)


def _setup_all():
    """Do all workflow related setup.
    """
    load_workflows()
    # !+zcml_check_regenerate(mr, sep-2011) should be only done *once* and 
    # when *all* workflows are loaded i.e. only first time (on module import).
    # check/regenerate zcml directives for workflows
    xmlimport.zcml_check_regenerate()
    # cleared by each call to zope.app.testing.placelesssetup.tearDown()
    register_workflow_adapters()
    # import events module, registering handlers
    import bungeni.core.workflows.events

# do it, when this module is imported. 
_setup_all()

#

