# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Signatories validation machinery for parliamentary documents

$Id$
"""

log = __import__("logging").getLogger("bungeni.models.signatories")

import zope.component
import zope.interface
import zope.event
import zope.lifecycleevent
from zope.security.proxy import removeSecurityProxy
from zope.securitypolicy.interfaces import IPrincipalRoleMap
from zope.component import getGlobalSiteManager
from zope.cachedescriptors import property as cached_property

from bungeni.alchemist import Session
from bungeni.models import interfaces, domain, utils as model_utils
from bungeni.utils import register
from bungeni.utils.capi import capi
from bungeni.core.workflow.interfaces import IWorkflowController, IWorkflowTransitionEvent

CONFIGURABLE_PARAMS = ("max_signatories", "min_signatories", "submitted_states",
    "draft_states", "expire_states", "open_states"
)
OWNER_ROLE = "bungeni.Owner"
SIGNATORY_ROLE = "bungeni.Signatory"
SIGNATORIES_REJECT_STATES = [u"rejected", u"withdrawn"]
SIGNATORY_CONSENTED_STATES = [u"consented"]
SIGNATORY_CONSENTED_STATE = u"consented"

# !+IFEATURE_SIGNATORY this is logically a class method (signatories may be 
# allowed or not at the class level, not per instance) not an instance method
# (that is monkey-patched downstream onto the class).
# Besides, there was already a more homegenoeous (as well as simpler and more 
# direct and more efficient) way to do this, namely by checking the signatory 
# feature settings on the workflow for this model class.
def _allow_signatures(context):
    """Callable on class to check if document is open for signatures.
    
    Used in bungeni/ui/menu.zcml to filter out 'sign document action'
    """
    manager = interfaces.ISignatoryManager(context)
    return manager.autoSign()

@register.handler(adapts=(interfaces.IFeatureSignatory, IWorkflowTransitionEvent))
def doc_workflow(ob, event):
    wfc = IWorkflowController(ob, None)
    if wfc:
        manager = interfaces.ISignatoryManager(ob)
        manager.workflowActions()

@register.handler(adapts=(interfaces.ISignatory, 
    zope.lifecycleevent.interfaces.IObjectCreatedEvent))
def signatory_created(ob, event):
    manager = interfaces.ISignatoryManager(ob.head)
    if manager.documentSubmitted() or manager.autoSign():
        IPrincipalRoleMap(ob).assignRoleToPrincipal(OWNER_ROLE, 
            ob.owner.login
        )
        IPrincipalRoleMap(ob.head).assignRoleToPrincipal(SIGNATORY_ROLE,
            ob.owner.login
        )


def make_owner_signatory(context):
    """Make document owner a default signatory when document is submitted to
    signatories for consent.
    """
    signatories = context.signatories
    if context.owner_id not in [sgn.user_id for sgn in signatories._query]:
        session = Session()
        signatory = signatories._class()
        signatory.user_id = context.owner_id
        signatory.head_id = context.doc_id
        session.add(signatory)
        session.flush()
        zope.event.notify(zope.lifecycleevent.ObjectCreatedEvent(signatory))

def sign_document(context, user_id):
    """Sign context for this user if they have not already signed
    """
    signatories = removeSecurityProxy(context.signatories)
    signatory = None
    for sgn in signatories.values():
        if sgn.user_id == user_id:
            signatory = removeSecurityProxy(sgn)
            break

    if not signatory:
        session = Session()
        signatory = domain.Signatory()
        signatory.user_id = user_id
        signatory.head_id = context.doc_id
        session.add(signatory)
        session.flush()
        zope.event.notify(zope.lifecycleevent.ObjectCreatedEvent(signatory))
    else:
        wfc = IWorkflowController(signatory)
        if not wfc.state_controller.get_status() == SIGNATORY_CONSENTED_STATE:
            wfc.state_controller.set_status(SIGNATORY_CONSENTED_STATE)
    return signatory
        


class SignatoryValidator(object):
    zope.interface.implements(interfaces.ISignatoryManager)
    
    max_signatories = 0
    min_signatories = 0
    submitted_states = ("submitted_signatories",)
    draft_states = ("draft", "redraft",)
    expire_states = ("submitted",)
    open_states = ()
    
    def __init__(self, context):
        self.context = context
        self.object_type = context.type
        self.wf_status = IWorkflowController(
            context).state_controller.get_status()

    @cached_property.cachedIn("__signatories__")
    def signatories(self):
        #!+VERSIONS(mb, aug-2011) automatic transitions firing for versions?
        # as at r8488 - check whether the context actually has signatories
        #!+SECURITY(mb, aug-2011) remove proxy to allow access to 
        # signature status. View permission only checked on attribute access
        # from container `values` listing
        if hasattr(self.context, "signatories"):
            return [ sgn for sgn in 
                removeSecurityProxy(self.context.signatories).values()
            ]
        else:
            log.warning("The object  %s has no signatories. Returning"
                " empty list of signatories.", 
                self.context.__str__()
            )
            return []

    @property
    def signatories_count(self):
        return len(list(self.signatories))

    @property
    def consented_signatories(self):
        return self.consentedSignatories()
   
   
    def is_signatory(self, user_id=None):
        user_id = user_id or model_utils.get_db_user_id()
        if user_id:
            return user_id in [ sgn.user_id for sgn in self.signatories ] 
        return False
    
    #!+PLEASE_USE_STANDARD_NAMING_CONVENTIONS(mr, apr-2012)
    
    def requireSignatures(self):
        return self.min_signatories > 0

    def validateSignatories(self):
        return self.signatories_count > 0

    def consentedSignatories(self):
        return len(filter(lambda cs:cs.status in SIGNATORY_CONSENTED_STATES, 
            self.signatories
        ))
    
    def validateConsentedSignatories(self):
        return (
            (self.consented_signatories >= self.min_signatories) and
            ((not self.max_signatories) or 
                (self.consented_signatories <= self.max_signatories)
            )
        )

    def allowSignature(self):
        return (not self.max_signatories or 
            (self.consented_signatories < self.max_signatories)
        ) and (self.documentSubmitted() or self.autoSign)

    def autoSign(self):
        return self.wf_status in self.open_states

    def canSign(self):
        """Check if the current user can sign a document"""
        is_owner = ((
            model_utils.get_prm_owner_principal_id(self.context) ==
                model_utils.get_principal_id()) or 
            model_utils.get_db_user() == self.context.owner
        )
        return (self.autoSign() and not is_owner and not self.is_signatory())

    def signDocument(self, user_id):
        return sign_document(self.context, user_id)

    def expireSignatures(self):
        return self.wf_status in self.expire_states

    def documentSubmitted(self):
        return self.wf_status in self.submitted_states

    def documentInDraft(self):
        """Check that a document is being redrafted
        """
        return self.wf_status == self.draft_states

    def updateSignatories(self):
        for signatory in self.signatories:
            wfc = IWorkflowController(signatory)
            wfc.fireAutomatic()

    def setupRoles(self):
        if self.documentSubmitted():
            make_owner_signatory(self.context)
            for signatory in self.signatories:
                login_id = signatory.owner.login
                IPrincipalRoleMap(self.context).assignRoleToPrincipal(
                    SIGNATORY_ROLE, login_id
                )
                IPrincipalRoleMap(signatory).assignRoleToPrincipal(
                    OWNER_ROLE, login_id
                )
        elif self.documentInDraft():
            for signatory in self.signatories:
                IPrincipalRoleMap(self.context).unsetRoleForPrincipal(
                    SIGNATORY_ROLE, signatory.owner.login
                )
        elif self.expireSignatures():
            for signatory in self.signatories:
                wfc = IWorkflowController(signatory)
                if wfc.state_controller.get_status() in SIGNATORIES_REJECT_STATES:
                    IPrincipalRoleMap(self.context).unsetRoleForPrincipal(
                        SIGNATORY_ROLE, signatory.owner.login
                    )
                
    def workflowActions(self):
        """Perform any workflow related actions on signatories and/or parent
        """
        self.setupRoles()
        self.updateSignatories()
        
def createManagerFactory(domain_class, **params):
    manager_name = "%sSignatoryManager" % domain_class.__name__ #!+naming
    if manager_name in globals().keys():
        log.errror("Signatory manager named %s already exists", manager_name)
        return
    #!+TIMING
    #!+TYPE_INFO(mb, Jun-2012) type_info may still not be setup as workflows 
    # are still loading
    ti = capi.get_type_info(domain_class)
    domain_iface = ti.interface
    if domain_iface is None:
        log.error("No model interface for class %s", domain_class)
        log.error("Not creating Signatory Manager for class %s", domain_class)
        return
    
    globals()[manager_name] = type(manager_name, (SignatoryValidator,), {})
    manager = globals()[manager_name]
    for config_name, config_value in params.iteritems():
        assert config_name in CONFIGURABLE_PARAMS, ("Check your signatory "
            "feature configuration for %s. Only these parameters may be "
            "configured %s" % (domain_class.__name__, CONFIGURABLE_PARAMS))
        config_type = type(getattr(manager, config_name))
        if config_type in (tuple, list):
            config_value = map(str.strip, config_value.split())
        setattr(manager, config_name, config_type(config_value))
    assert set.intersection(
            set(manager.submitted_states), 
            set(manager.draft_states), 
            set(manager.expire_states)
        )==set(), "draft, submitted and expired states must be distinct lists"
    
    gsm = getGlobalSiteManager()
    gsm.registerAdapter(manager, (domain_iface,), interfaces.ISignatoryManager)
    # !+IFEATURE_SIGNATORY(mr, oct-2012) this should be included in signatory 
    # feature setup and handling
    domain_class.allow_signatures = _allow_signatures

