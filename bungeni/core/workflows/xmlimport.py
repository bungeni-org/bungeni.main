"""
Support for xml defined workflows, and security manipulations by state.
"""

from lxml import etree
from zope.dottedname.resolve import resolve
from zope.i18nmessageid import Message

from bungeni.core.workflows.states import GRANT
from bungeni.core.workflows.states import DENY
from bungeni.core.workflows.states import State
from bungeni.core.workflows.states import StateTransition
from bungeni.core.workflows.states import StateWorkflow

from ore.workflow import interfaces

ASSIGNMENTS = (GRANT, DENY)

trigger_value_map = {
    'manual': interfaces.MANUAL,
    'automatic': interfaces.AUTOMATIC,
    'system': interfaces.SYSTEM}


def load(file_path):
    doc = etree.fromstring(open(file_path).read())
    return _load(doc)


def _load(workflow):
    transitions = []
    states = []
    domain = workflow.get("domain")
    
    def get_like_state(state_id):
        if state_id is None:
            return
        for state in states:
            if state.id == state_id:
                return state
        assert False, 'Invalid value: like_state="%s"' % (state_id)
        
    def remove_redefined_permission(like_permissions, permission, role):
        for p in [(GRANT, permission, role), (DENY, permission, role)]:
            if p in like_permissions:
                like_permissions.remove(p)
    
    for s in workflow.iterchildren("state"):
        state_id = s.get("id")
        assert state_id, "Workflow State must define @id"
        permissions = [] # tuple(bool:int, permission:str, role:str) 
        # state.@like_state : to reduce repetition and enhance maintainibility
        # of workflow XML files, a state may specify a @like_state attribute to 
        # inherit all permissions defined by the specified like_state; further
        # permissions specific to this state may be added, but as these may 
        # also override inherited permissions we streamline those out so that 
        # downstream execution (a permission should be granted or denied only 
        # once per transition to a state).
        like_permissions = []
        like_state = get_like_state(s.get("like_state"))
        if like_state:
            like_permissions.extend(like_state.permissions)
        # (within same state) a deny is *always* executed after a *grant*
        for i, assign in enumerate(["grant", "deny"]):
            for p in s.iterchildren(assign):
                permission, role = p.get("permission"), p.get("role")
                remove_redefined_permission(like_permissions, permission, role)
                permissions.append((ASSIGNMENTS[i], permission, role))
        # splice any remaining like_permissions at beginning of permissions
        if like_state:
            permissions[0:0] = like_permissions
        states.append(
            State(state_id, Message(s.get("title", domain)), permissions) 
        )

    for t in workflow.iterchildren('transition'):

        for key in ('source', 'destination', 'id', 'title'):
            if t.get(key) is None:
                raise SyntaxError("%s not in %s"%(key, etree.tostring(t)))

        # XXX: There must be a better way to do this:
        source = t.get('source')
        while '  ' in source:
            source = source.replace('  ', ' ')
        sources = [s or None for s in source.split(' ')]

        for source in sources:
            if len(sources) > 1:
                tid = "%s-%s" % (t.get('id'), source)
            else:
                tid = t.get('id')
            args = (tid, Message(t.get('title'), domain),
                    source, t.get('destination'))
            kw = {}

            # optionals
            for i in ('trigger', 'order', 'permission'):
                val = t.get(i)
                if not val:
                    continue
                kw[i] = val

            require_confirmation = getattr(t, 'require_confirmation', '')
            if require_confirmation.lower() == 'true':
                kw['require_confirmation'] = True

            if 'trigger' in kw:
                k = kw['trigger']
                v = trigger_value_map[k]
                kw['trigger'] = v

            # optional python resolvables
            for i in('condition', 'action', 'event'):
                val = t.get(i)
                if not val:
                    continue
                # raises importerror/nameerror
                val = resolve(val, 'bungeni.core.workflows')
                kw[i] = val
            transitions.append(StateTransition(*args, **kw))

    return StateWorkflow(transitions, states)
