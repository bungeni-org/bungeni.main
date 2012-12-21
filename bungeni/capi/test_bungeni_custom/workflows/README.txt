Custom Definitions of the Workflows of Parliamentary Documents
==============================================================

This file reference information and guidelines about how to define/localize the 
workflow instances of parliamentary documents, for a given Bungeni deployment.

!+DEVELOPER_ORIENTED(mr, jun-2011) this README is to be reworked, as
currently oriented more towards the Bungeni developer than to the site 
administartor of a Bungeni deployment.

For the spec of the workflow XML format see: bungeni/schema/workflow.rnc

Guide to Workflow XML Definitions
=================================

Workflow (root element):

- workflow states may be tagged with system-provided tags and any state tag 
used in the workflow must be declared within workflow.@tags, as a 
space-separated-value of tag names.

- the complete set of system-provided tags is as follows:
    draft
    private
    public
    tobescheduled
    approved
    scheduled
    actionclerk
    actionmp
    terminal
    succeed     # terminal
    fail        # terminal
    oral        # questions
    written     # questions
    published   # groupsitting
    workspace
    agendaprivate # groupsitting - if a sitting is in a state tagged
        # "agendaprivate" its agenda should not be publicly available
    
    !+ should public/private tags be inferred via Anonymous can View or not?

- the order of workflow attributes should respect:
    title
    description
    tags
    note


Features
--------

Enables/disables a feature on the workflowed type--may define additional 
feature-specific settings (!+ as attributes or sub-elements).

For list of currently known features (for different archetypes) see:
bungeni/models/feauture.py

- @name must be for a supported feature of the workflowed type. 

- if no <feature> element present for a named feature, then that feature is not
*enabled*; if a <feature> element is present then it is by default enabled 
(unless @enabled is explicitly set to "false").

- the order of feature attributes should respect:
    name 
    enabled
    note

States
------

- the state ID should be a lowercase *adverb* (more or less) that describes 
the _condition_ an object is in, given the transition trail of the object.

- state multiple-word IDs are `_` (underscore) separated -:- in particular 
the `-` (hyphen) should *not* be used as separator as this character, 
besides being invalid as part of a python name, is reserved by 
`bungeni.core.workflow` for use as a separator character.

- a bungeni _role_ name should *never* be part of a state name or title.

- states within a same workflow should never have a same id -:- because in 
an XML document all element IDs should be unique, and Bungeni defines each 
workflow as a single XML document.

- permissions, the order of how they are specified is organized by target type
- within each permission-target-section, the order of appearance of permission 
  actions should have the following standard 4 appearing first:
    View
    Edit
    Add
    Delete
- the @roles space-separated value should include roles in a consistent order,
  with the following known ones first:
    <role id="bungeni.Clerk" title="Clerks Office" />
    <role id="bungeni.Speaker" title="Speaker Office" />
    <role id="bungeni.Owner" title="Owner" />
    <role id="bungeni.Signatory" title="Signatory" />
    <role id="bungeni.MP" title="Member of parliament" />
    <role id="bungeni.Minister" title="Minister" />
    <role id="bungeni.Authenticated" title="All authenticated users" />
    <role id="bungeni.Anonymous" title="Bungeni Visitor" />

- the order of state attributes should respect:
    id 
    title
    version=False
    permissions_from_state
    tags
    note
    permissions_from_parent=False
    obsolete=False

- AVOID contradictory/superfluous permissions assignments:
When defining permissons on states, should avoid potentially contradictory or
superfluous (e.g. always denied) assignments as the permission checking may 
give incorrect results. There is logical overlap between being Authenticated 
and being an MP, Clerk, etc, and the security model does not take into account.

For example, in the case of Attachment, denying the "zope.View" permission 
for "bungeni.Authenticated" and granting it for "bungeni.MP":

    <allow permission="zope.View" role="bungeni.MP" />
    <deny permission="zope.View" role="bungeni.Authenticated" /> 

a) for "bungeni.Authenticated" this is superfluous as it is denied in all 
states in same workflow
b) adding it explicitly and with the **contrary** setting alongside another 
**authenticated** role as for "bungeni.MP" gives incorrect results!
c) plus, to keep in mind, when a workflow state is loaded from XML, all 
denies are executed **after** all grants.


DEBUGGING NOTE: to easily see the the evaluated result of all permission 
assigments for each workflow state definition (that uses permissions_from_state) 
set the logging level to DEBUG.

!+ <state ... manual_date="true">
    transition to a "politicocratic" destination states need to allow 
    freedom to manually set the transition date_active, but transition 
    to a "bureaucratic" destination states should not.



Transitions
-----------

- the transition title should be a lowercase *verb*.

- for convenience, the source allows to specify multiple state ids, that are 
specified as a "space separated string"; however, it is not possible to mix
other state ids along with the special-case "initial" state of a workflow (that 
by convention is the empty string). 

- irrespective of how sources are grouped into <transition> elements, there may 
be only *one* path from any given *source* to any given *destination* state. 

- a bungeni _role_ name should *never* be part of a transition title.

- each individual workflow transition (*except* for _initial_ category of 
transitions) have an automatically generated *dedicated* permission, that 
is named as follows: `bungeni.{object}.wf.{transition}`
The _initial_ class of transitions is an exception to this rule because 
such transitions have an _automatic_ trigger resulting from the act of 
creating the object, that presumably is already access-controlled with a 
`bungeni.{object}.Add` type permission. Because of this, all _initial_ 
transitions must have *no permission specified*.

- grouping_unique_sources used to semantically connect multiple transitions 
and constrain that accumulative sources are unique.

- the order of attributes should respect:
    title
    source
    destination
    grouping_unique_sources=None # any grouping id
    condition=None
    trigger=MANUAL
    roles=Clerk
    #permission=CheckerPublic !+ bungeni.{module}.wf.{transition_id}
    order=0
    require_confirmation=False
    note=None



Guide: Manage permissions for "sub-items"
-----------------------------------------

A "head" doc may enable a feature that implies management of sub-items 
e.g. attachment, address, event. In this cases, the reponsibility for management
of permissions for each such sub-item is shared between 
(a) the workflow of the parent item and (b) the workflow of the sub-item.

General guidelines for how this works are below:

- In either workflow, the permissions relating to the sub-item type (the 
standard 4 CRUD permissions as well as any others) should NOT be global grants.

- The parent doc workflow (supporting the feature and requiring the sub-type) 
decides who can do what and when with the sub-item, by granting permissions
related to the sub-item explicity in all workflow states.

- The sub-item workflow explicitly manages for itself any non-Add permissions 
in its own workflow (for all states not bound to parent via the 
permissions_from_parent="true" declaration).

- The sub-item workflow may still make use of workflow state option 
permissions_from_parent="true" on any state in its own workflow.

- !+ The "primary" View permission on the sub-item should ALWAYS use the 
generic "zope.View" (that is redefined upstream to "bungeni.TYPE.View".
!+redefinePermission "zope.View" to "bungeni.View", and then redefinePermission
of "bungeni.View" to "bungeni.TYPE.View"?


Workflow "draft" state for sub-items

The workflow for a sub-item type, e.g. for attachment, address, event, 
SHOULD default newly created items into a DRAFT state that SHOULD NOT
be bound with permissions_from_parent="true".

As a convenience for when the parent document is also in draft, the worklfow 
transition conditions "context_parent_is_draft" and "context_parent_is_not_draft" 
may be used to auto-transit directly a newly created sub-item to a state 
bound to parent with permissions_from_parent="true" e.g. "attached". The rule 
of thumb to respect here is that when parent is NOT in draft, any newly created
sub-item SHOULD be created in draft.

A related issue with transiting a sub-item away from a state bound to parent 
with permissions_from_parent="true" is that such items SHOULD NOT be adjusted 
once the parent document has become public. The workflow conditions 
"context_parent_is_public" and "context_parent_is_not_public" are provided to
be able to control availability of such transitions.


