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
    domain = workflow.get('domain')

    for s in workflow.iterchildren('state'):
        permissions = []
        for g in s.iterchildren('grant'):
            permissions.append(
                (GRANT, g.get('permission'), g.get('role')))
        for d in s.iterchildren('deny'):
            permissions.append(
                (DENY, d.get('permission'), d.get('role')))
        state_id = s.get('id')
        states.append(
            State(state_id,
                  Message(s.get('title', domain)),
                  permissions))

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
