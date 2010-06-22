# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt
'''Query-related utilities for the UI

usage: 
from bungeni.ui.utils import statements

$Id$
'''

# timeline for a bill
# select all relevant events:
# sittings for which this bill was scheduled,
# manually created events,
# workflow changes, 
# manually created versions.

sql_item_timeline = """
     SELECT 'schedule' AS "atype",
            "items_schedule"."item_id" AS "item_id", 
            "items_schedule"."item_status" AS "title", 
            "group_sittings"."start_date" AS "adate" 
        FROM "public"."items_schedule" AS "items_schedule", 
            "public"."group_sittings" AS "group_sittings" 
        WHERE "items_schedule"."sitting_id" = "group_sittings"."sitting_id" 
        AND "items_schedule"."active" = True
        AND "items_schedule"."item_id" = :item_id
     UNION
        SELECT "parliamentary_items"."type" AS "atype", 
            "parliamentary_items"."parliamentary_item_id" AS "item_id", 
            "parliamentary_items"."short_name" AS "title", 
            "event_items"."event_date" AS "adate"
        FROM "public"."event_items" AS "event_items", 
            "public"."parliamentary_items" AS "parliamentary_items" 
        WHERE "event_items"."event_item_id" = "parliamentary_items"."parliamentary_item_id"
        AND "event_items"."item_id" = :item_id
    UNION
        SELECT 'assignment start' AS "atype", 
            "group_assignments"."item_id" AS "item_id", 
            "groups"."short_name" || ' - ' || "groups"."full_name",
            "group_assignments"."start_date" AS "adate"
        FROM "public"."group_assignments" AS "group_assignments", 
            "public"."groups" AS "groups" 
        WHERE "group_assignments"."group_id" = "groups"."group_id"
        AND "group_assignments"."item_id" = :item_id
    UNION
        SELECT 'assignment end' AS "atype", 
            "group_assignments"."item_id" AS "item_id", 
            "groups"."short_name" || ' - ' || "groups"."full_name",
            "group_assignments"."end_date" AS "adate"
        FROM "public"."group_assignments" AS "group_assignments", 
            "public"."groups" AS "groups" 
        WHERE "group_assignments"."group_id" = "groups"."group_id"
        AND "group_assignments"."item_id" = :item_id
        AND "group_assignments"."end_date" IS NOT NULL
    
    UNION
        SELECT "action" as "atype", "content_id" AS "item_id", 
        "description" AS "title", 
        "date" AS "adate" 
        FROM "public"."%(PI_TYPE)s_changes" AS "%(PI_TYPE)s_changes" 
        WHERE "action" = 'workflow'
        AND "content_id" = :item_id
     UNION
        SELECT 'version' AS "atype", 
            "%(PI_TYPE)s_changes"."change_id" AS "item_id", 
            "%(PI_TYPE)s_changes"."description" AS "title", 
            "%(PI_TYPE)s_changes"."date" AS "adate" 
        FROM "public"."%(PI_TYPE)s_versions" AS "%(PI_TYPE)s_versions", 
            "public"."%(PI_TYPE)s_changes" AS "%(PI_TYPE)s_changes" 
        WHERE "%(PI_TYPE)s_versions"."change_id" = "%(PI_TYPE)s_changes"."change_id" 
        AND "%(PI_TYPE)s_versions"."manual" = True
        AND "%(PI_TYPE)s_changes"."content_id" = :item_id
    
    ORDER BY adate DESC
"""
# !+ add inclusion of event_items to the timeline data?

#

sql_bill_timeline = sql_item_timeline % {"PI_TYPE": "bill"}
sql_motion_timeline = sql_item_timeline % {"PI_TYPE": "motion"}
sql_question_timeline = sql_item_timeline % {"PI_TYPE": "question"}
sql_tableddocument_timeline = sql_item_timeline % {"PI_TYPE": "tabled_document"}
sql_agendaitem_timeline = sql_item_timeline % {"PI_TYPE": "agenda_item"}

#

