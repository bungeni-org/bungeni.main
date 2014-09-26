# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Workflow transition-to-state actions.

Signature of all transition-to-state action callables:

    (context:Object) -> None

All transition-to-state actions are executed "on workflow trransition" i.e. 
exactly when the status is updated from the source to the destination state, 
and in exactly the order they are specified in the state.@actions xml attribute.

REMEMBER: when a transition-to-state action is executed, the context.status 
is already updated to the destination state.

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflows._actions")

from bungeni.core.workflows import utils
from bungeni.core.workflow.interfaces import IWorkflowController
from bungeni.utils.misc import describe
from bungeni import _

# version
# - create a new version of an object and return it
# - context must be version-enabled
# - recommendation: when present, version should be first action to execute
from bungeni.core.version import (
    create_version as version
)
# !+capi.template_message_version_transition
#message_template = "New version on workflow transition to: %(status)s"
#message = message_template % context.__dict__

from bungeni.core.workflows.utils import (
    
    # when a doc reaches a state that semantically implies "receive"
    set_doc_registry_number,
    
    # when a doc is admitted
    set_doc_type_number,
    
    # when a doc is withdrawn
    unschedule_doc,
    
    # when a sitting's agenda is published
    schedule_sitting_items,
)

from bungeni.core.workflows.dbutils import (
    # utility to help create parametrized "transfer to chamber" actions
    # PARAMETERS: (source_doc, target_chamber_type, target_type_key, target_state_id)
    # !+SUB_TYPE: PARAMETERS: (source_doc, target_group_conceptual_name, target_type_key, target_state_id)
    spawn_doc,
)


@describe(_(u"Activate a group"))
def activate(group):
    """Perform any actions required to activate a group.
    
    When a group is activated the group role is granted to the group principal 
    (and by virtue of membership, also to each active member of the group) 
    on target context as specified by this group's privilege_extent setting.
    """
    utils.set_group_local_role(group)

@describe(_(u"Deactivate a group"))
def deactivate(group):
    """Perform any actions required to deactivate a group.
    
    When a group is deactivated the group role is revoked to the group principal 
    (and by virtue of membership, also to each active member of the group) 
    on target context as specified by this group's privilege_extent setting.
    """
    utils.unset_group_local_role(group)


@describe(_(u"Dissolve a group"))
def dissolve(group):
    """Perform any actions required to dissolve a group - 
    typically set as an action on group workflow state "dissolved".
    
    When a group is dissolved:
    - all members of this group get the end date of 
    the group (if they do not have one yet) and there active_p status gets set
    to False.
    - any child group is ended and dissolved.
    
    """
    from bungeni.core.workflows import dbutils
    dbutils.deactivate_group_members(group)
    for ended_child_group in dbutils.end_child_groups(group):
        # !+GROUP_DISSOLVE assumes that workflow of EVERY child group type has:
        # - a state "active" AND a state "dissolved" AND
        # - a transition from first to second AND
        # - that the semantic meaning of the state "dissolved" is indeed 
        #   dissolution of the group...
        # should probably replace with a GroupType.dissolve() method that 
        # knows how to dissolve itself and/or as dissolve feature parameters
        IWorkflowController(ended_child_group
            ).fireTransition("active-dissolved", check_security=False)
    utils.unset_group_local_role(group)


# doc

''' !+ should be part of application logic
def set_role_group(doc):
    """Assign the role of the doc's group, to the group itself, onto doc.
    """
    # !+PrincipalRoleMapContextData infer role from context data
    from bungeni.models.interfaces import IDoc
    assert IDoc.providedBy(doc), "Not a Doc: %s" % (doc)
    utils.set_role(doc.group.group_role, doc.group.principal_name, doc)
'''

def propagate_parent_assigned_group_role(child_doc):
    """Propagate the role of the group that is assigned to the parent doc of 
    this child doc.
    """
    from bungeni.models.interfaces import IDoc
    assert IDoc.providedBy(child_doc), "Not a Doc: %s" % (child_doc)
    def get_parent_doc_assigned_group(child_doc):
        parent_group_assignments = child_doc.head.sa_group_assignments
        for group_assignment in parent_group_assignments:
            # !+QUALIFIED_FEATURES(mr, apr-2013) may need to "qualify" each assignment!
            # !+MULTI_ASSIGNMENTS_MULTI_MEMBERSHIPS(mr, apr-2013) for now we just
            # take the first assigned group we find, but this is obvioulsy 
            # incorrect! Need to determine: in case doc has been assigned to 
            # more than one group, within which is the current user acting
            # (keeping in mind, also that the current user may be member of more
            # than one group that the doc is assigned to!).
            #!+GROUP_ASSIGNMENT.GROUP assert isinstance(group, domain.Group), group
            return group_assignment.principal
    pag = parent_assigned_group = get_parent_doc_assigned_group(child_doc)
    assert pag is not None, child_doc
    # !+ is this constraint correct?
    assert child_doc.group is pag, \
        "!+GROUP child doc [%s] group [%s] must be the assigned group [%s] for parent doc [%s]" % (
            child_doc, child_doc.group, pag, child_doc.head)
    utils.set_role(pag.group_role, pag.principal_name, child_doc)

