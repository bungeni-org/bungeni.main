# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt
"""Workflow States tagging mechanism and processing, 
to manage logical collections of Workflow States.

$Id: app.py 6682 2010-06-03 14:32:56Z mario.ruggier $
"""
log = __import__("logging").getLogger("bungeni.ui.tagged")

from bungeni.core import workflows
STATES_MAPPING = {
    "bill": workflows.bill.states,
    "question": workflows.question.states,
    "tableddocument": workflows.tableddocument.states,
}

from states import ACTIVE_TAGS, TAG_MAPPINGS

# Utilities

EMPTY_SET = set()

def get_states(pi_type, tagged=[], not_tagged=[], keys=[], conjunction="OR"):
    """Get the list of matching states.
    
    tagged: matches all states tagged with ANY tag in in this list
    not_tagged: matches all states tagged with NONE of these tags
    keys: matches all states explictly named by keye here 
    conjunction: 
        "OR": matches any state that is matched by ANY criteria above
        "AND": matches any state that is matched by ALL criteria above
    """
    tag_mapping = TAG_MAPPINGS[pi_type]
    # validate input parameters
    if tagged:
        assert tagged==[ t for t in tagged if t in ACTIVE_TAGS ]
    if not_tagged:
        assert not_tagged==[ t for t in not_tagged if t in ACTIVE_TAGS ]
    if keys:
        assert keys==[ k for k in keys if k in tag_mapping ]
    assert conjunction in ("OR", "AND"), "Not supported."
    # process
    states = STATES_MAPPING[pi_type]
    _tagged = _not_tagged = _keys = EMPTY_SET
    if tagged:
        _tagged = set()
        for state_id, state_tags in tag_mapping.items():
            for t in tagged:
                if t in state_tags:
                    _tagged.add(states[state_id].id)
                    break
    if not_tagged:
        _not_tagged = set()
        for state_id, state_tags in tag_mapping.items():
            _not_tagged.add(states[state_id].id)
            for t in not_tagged:
                if t in state_tags:
                    _not_tagged.remove(states[state_id].id)
                    break
    if keys:
        _keys = set([ states[key].id for key in keys ])
    # combine
    if conjunction=="OR":
        return list(_tagged.union(_not_tagged).union(_keys))
    elif conjunction=="AND":
        return list(_tagged.intersection(_not_tagged).intersection(_keys))

