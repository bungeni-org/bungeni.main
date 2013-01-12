# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Workflow support for GraphViz Dot Language

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.workflow.dot")

from cStringIO import StringIO
from bungeni.core.workflow import interfaces


def dot(workflow):
    """Return the "GraphViz Dot Language" representation of the workflow.
    """
    states = [None]
    visited = set()
    num_transitions = 0
    out = [
        "digraph g {",
        "None [shape=doublecircle]"
    ]
    while states:
        state = states.pop()
        for transition in workflow.get_transitions_from(state):
            num_transitions += 1
            dest = transition.destination
            if dest not in visited:
                states.append(dest)
                visited.add(dest)
            out.append('t%d [shape=none, label="%s"]' % (
                num_transitions, transition.title))
            out.append('"%s" -> t%d -> "%s"' % (state, num_transitions, dest))
    out.append("}")
    return "\n".join(out)


def toDot(workflow):
    """Fancier export of workflow as dot:
    transition colors
     - automatic triggers in green
     - system triggers in yellow if no conditions
     - system triggers in blue if conditional
     - manual triggers in red
    state colors
     - end states in red
    """
    io = StringIO()
    states = set()
    end_states = set()
    print >> io, "digraph workflow {"
    for state, transitions in workflow._transitions_by_source.items():
        states.add(state)
        for t in transitions:
            option = []
            states.add(t.destination)
            if t.destination not in workflow._transitions_by_source:
                end_states.add(t.destination)
            if t.trigger is interfaces.AUTOMATIC:
                option.append("color=green")
            elif t.trigger is interfaces.SYSTEM:
                if not t.condition is None:
                    option.append("color=yellow")
                else:
                    option.append("color=blue")
            elif not t.condition is None:
                option.append("color=red")
            print >> io, ' %s -> %s [label="%s", %s];' % (
                t.source, t.destination, t.id, ", ".join(option))
    for state in states:
        if state in end_states:
            print >> io, " %s [color=red];" % state
        else:
            print >> io, " %s [shape=box];" % state
    print >> io, "}"
    return io.getvalue()

