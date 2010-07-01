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
    "tableddocument": workflows.tableddocument.states,
}

from states import ACTIVE_TAGS, TAG_MAPPINGS

# Utilities

def get_states(pi_type, tagged=[], negate=False):
    """Get the list of matching states.
    tagged: list of tags to match against.
    negate: 
        when False (default), get list of all states tagged by ANY tag in tagged; 
        when True, get list of all states NOT tagged by ANY tag in tagged.
    """
    tag_mapping = TAG_MAPPINGS[pi_type]
    states = STATES_MAPPING[pi_type]
    matched = []
    _tagged = [ t for t in tagged if t in ACTIVE_TAGS ]
    assert _tagged==tagged
    for state_id, state_tags in tag_mapping.items():
        if not negate:
            for t in tagged:
                if t in state_tags:
                    matched.append(states[state_id].id)
                    break
        else:
            matched.append(states[state_id].id)
            for t in tagged:
                if t in state_tags:
                    matched.remove(states[state_id].id)
                    break                
    return matched

def get_keyed_states(pi_type, keys=[]):
    states = STATES_MAPPING[pi_type]
    return [ states[key].id for key in keys ]
    
#

