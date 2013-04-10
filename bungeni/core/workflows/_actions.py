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
from bungeni.utils.misc import describe
from bungeni.ui.i18n import _

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


@describe(_(u"Activate a group"))
def activate(group):
    """Perform any actions required to activate a group.
    """
    utils.set_group_local_role(group)

@describe(_(u"Deactivate a group"))
def deactivate(group):
    """Perform any actions required to deactivate a group.
    """
    utils.unset_group_local_role(group)


@describe(_(u"Dissolve a group"))
def dissolve(group):
    """Perform any actions required to dissolve a group.
    
    When a group is dissolved all members of this group get the end date of 
    the group (if they do not have one yet) and there active_p status gets set
    to False.
    """
    from bungeni.core.workflows import dbutils
    dbutils.deactivateGroupMembers(group)
    groups = dbutils.endChildGroups(group)
    utils.dissolveChildGroups(groups, group)
    utils.unset_group_local_role(group)


# doc
@describe(_(u"Assign the group role to the doc"))
def assign_role_group(doc):
    """Assign the role of the doc's group, to the group itself, onto doc.
    """
    # !+PrincipalRoleMapContextData infer role from context data
    from bungeni.models.interfaces import IDoc
    assert IDoc.providedBy(doc), "Not a Doc: %s" % (doc)
    if doc.group is not None:
        utils.assign_role(doc.group.group_role, doc.group.principal_name, doc)

def propagate_parent_assigned_group_role(child_doc):
    """Propagate the role of the group that is assigned to the parent doc of 
    this child doc.
    """
    from bungeni.models.interfaces import IDoc
    assert IDoc.providedBy(child_doc), "Not a Doc: %s" % (child_doc)
    assert child_doc.group is None, "!+GROUP_ID must be unset! %s" % (child_doc)
    def get_parent_doc_assigned_group(child_doc):
        parent_group_assignments = child_doc.head.group_assignment
        for ag in parent_group_assignments:
            # !+QUALIFIED_FEATURES(mr, apr-2013) may need to "qualify" each assignment!
            # !+MULTI_ASSIGNMENTS_MULTI_MEMBERSHIPS(mr, apr-2013) for now we just
            # take the first assigned group we find, but this is obvioulsy 
            # incorrect! Need to determine: in case doc has been assigned to 
            # more than one group, within which is the current user acting
            # (keeping in mind, also that the current user may be member of more
            # than one group that the doc is assigned to!).
            return ag.group
    pag = parent_assigned_group = get_parent_doc_assigned_group(child_doc)
    assert pag is not None, child_doc
    utils.assign_role(pag.group_role, pag.principal_name, child_doc)

