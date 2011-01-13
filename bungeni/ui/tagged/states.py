# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt
"""Taggings of Workflow States

$Id$
"""

# Declaration of active tags (it is an error to specify an undeclared tag)

ACTIVE_TAGS = [
    "private", 
    "public",
    "tobescheduled",
    "approved",
    "scheduled",
    "actionclerk",
    "actionmp",
    "terminal",
    "succeed", # terminal
    "fail", # terminal
    "oral", # oral questions
    "written", # written questions
    "draft", # groupsitting
    "published", # groupsitting
    "workspace",
    "agendaprivate", # groupsitting - if a sitting is in a state tagged 
                     # "agendaprivate" its agenda should not be 
                     # publicly available
] 

# Tags for Workflow States, per Parliamentary Item

TAG_MAPPINGS = {}

# !+ fgrep -ir "_wf_state" --include="*.p?" .

TAG_MAPPINGS["agendaitem"] = {
    "working_draft": ["private",],
    "draft": ["private",],
    "submitted": ["actionclerk",],
    "received": ["actionclerk",],
    "complete": [],
    "admissible": ["public", "approved",],
    "inadmissible": ["terminal", "fail",],
    "clarify_clerk": ["actionclerk",],
    "clarify_mp": ["actionmp",],
    "schedule_pending": ["public", "tobescheduled",],
    "scheduled": ["public", "scheduled",],
    "debate_adjourned": ["public", "approved",],
    "deferred": ["public", "approved",],
    "elapsed": ["public", "terminal", "fail",],
    "debated": ["public", "terminal", "succeed",],
    "dropped": ["public","terminal", "fail",],
    "withdrawn": ["terminal", "fail",],
    "withdrawn_public": ["public", "terminal", "fail",],
}
TAG_MAPPINGS["bill"] = {
    "working_draft": ["private",],
    "gazetted": [],
    "first_reading_pending": ["tobescheduled",],
    "first_reading": ["scheduled",],
    "first_reading_adjourned": ["approved",],
    "first_committee": [],
    "first_report_reading_pending": ["tobescheduled",],
    "first_report_reading": ["scheduled",],
    "first_report_reading_adjourned": ["approved",],
    "second_reading_pending": ["tobescheduled",],
    "second_reading": ["scheduled",],
    "second_reading_adjourned": ["approved",],
    "whole_house_pending": ["tobescheduled",],
    "whole_house": ["scheduled",],
    "whole_house_adjourned": ["approved",],
    "second_committee": [],
    "third_reading_pending": ["tobescheduled",],
    "third_reading": ["scheduled",],
    "third_reading_adjourned": ["approved",],
    "withdrawn_public": ["terminal", "fail",],
    "approved": ["terminal", "succeed", "approved",],
    "rejected": ["terminal", "fail",],
}
TAG_MAPPINGS["motion"] = {
    "working_draft": ["private",],
    "draft": ["private",],
    "submitted": ["actionclerk",],
    "received": ["actionclerk",],
    "complete": [],
    "admissible": ["public", "approved",],
    "inadmissible": ["terminal", "fail",],
    "clarify_mp": ["actionmp",],
    "clarify_clerk": ["actionclerk",],
    "schedule_pending": ["public", "tobescheduled",],
    "scheduled": [  "public", "scheduled",],
    "deferred": ["public", "approved",],
    "dropped": ["public","terminal", "fail",],
    "adopted": ["public", "terminal", "succeed",],
    "adopted_amendments": ["public", "terminal", "succeed",],
    "rejected": ["public", "terminal", "fail",],
    "elapsed": ["public", "terminal", "fail",],
    "debate_adjourned": ["public", "approved",],
    "withdrawn": ["terminal", "fail",],
    "withdrawn_public": ["public", "terminal", "fail",],
}
TAG_MAPPINGS["question"] = {
    "working_draft": ["private",],
    "draft": ["private",],
    "submitted": ["actionclerk",],
    "received": ["actionclerk",],
    "complete": [],
    "admissible": ["public", "approved", "oral", "written",],
    "inadmissible": ["terminal", "fail",],
    "clarify_mp": ["actionmp",],
    "clarify_clerk": ["actionclerk",],
    "schedule_pending": ["public", "tobescheduled", "oral",],
    "scheduled": ["public", "scheduled", "oral",],
    "debate_adjourned": ["public", "approved",],
    "response_pending": ["public", "written",],
    "response_submitted": ["public", "actionclerk",],
    "response_complete": ["public", "terminal", "succeed",],
    "deferred": ["public", "approved",],
    "elapsed": ["public", "terminal", "fail",],
    "debated": ["public", "terminal", "succeed",],
    "dropped": ["public","terminal", "fail",],
    "withdrawn": ["terminal", "fail",],
    "withdrawn_public": ["public", "terminal", "fail",],
}
TAG_MAPPINGS["tableddocument"] = {
    "working_draft": ["private",],
    "draft": ["private",],
    "submitted": ["actionclerk",],
    "received": ["actionclerk",],
    "complete": [],
    "admissible": ["public", "approved",],
    "schedule_pending": ["public", "tobescheduled",],
    "inadmissible": ["terminal", "fail",],
    "clarify_clerk": ["actionclerk",],
    "clarify_mp": ["actionmp",],
    "scheduled": ["public", "scheduled"],
    "adjourned": ["public", "approved",],
    "tabled": ["public", "terminal", "succeed",],
    "withdrawn": ["terminal", "fail",],
}
TAG_MAPPINGS["groupsitting"] = {
    "sitting":["public", "draft", "agendaprivate"],                            
    "draft_agenda": ["public", "draft","workspace", "agendaprivate"],
    "published_agenda": ["public", "published","workspace", ],
    "draft_minutes": ["public", "draft","workspace"],
    "published_minutes": ["public", "published"],
}
