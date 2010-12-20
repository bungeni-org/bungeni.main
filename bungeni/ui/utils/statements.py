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
            "item_schedules"."item_id" AS "item_id", 
            "item_schedules"."item_status" AS "description", 
            "group_sittings"."start_date" AS "adate",
            '' as "notes"
        FROM "public"."item_schedules" AS "item_schedules", 
            "public"."group_sittings" AS "group_sittings" 
        WHERE "item_schedules"."group_sitting_id" = "group_sittings"."group_sitting_id" 
        AND "item_schedules"."active" = True
        AND "item_schedules"."item_id" = :item_id
     UNION
        SELECT "parliamentary_items"."type" AS "atype", 
            "parliamentary_items"."parliamentary_item_id" AS "item_id", 
            "parliamentary_items"."short_name" AS "description", 
            "event_items"."event_date" AS "adate",
            '' as "notes"
        FROM "public"."event_items" AS "event_items", 
            "public"."parliamentary_items" AS "parliamentary_items" 
        WHERE "event_items"."event_item_id" = "parliamentary_items"."parliamentary_item_id"
        AND "event_items"."item_id" = :item_id
    UNION
        SELECT 'assignment start' AS "atype", 
            "group_assignments"."item_id" AS "item_id", 
            "groups"."short_name" || ' - ' || "groups"."full_name",
            "group_assignments"."start_date" AS "adate",
            '' as "notes"
        FROM "public"."group_assignments" AS "group_assignments", 
            "public"."groups" AS "groups" 
        WHERE "group_assignments"."group_id" = "groups"."group_id"
        AND "group_assignments"."item_id" = :item_id
    UNION
        SELECT 'assignment end' AS "atype", 
            "group_assignments"."item_id" AS "item_id", 
            "groups"."short_name" || ' - ' || "groups"."full_name",
            "group_assignments"."end_date" AS "adate",
            '' as "notes"
        FROM "public"."group_assignments" AS "group_assignments", 
            "public"."groups" AS "groups" 
        WHERE "group_assignments"."group_id" = "groups"."group_id"
        AND "group_assignments"."item_id" = :item_id
        AND "group_assignments"."end_date" IS NOT NULL
    
    UNION
        SELECT "action" as "atype", 
            "content_id" AS "item_id", 
            "description" AS "description", 
            "date_active" AS "adate",
            "notes" as "notes"
        FROM "public"."%(PI_TYPE)s_changes" AS "%(PI_TYPE)s_changes" 
        WHERE "action" = 'workflow'
        AND "content_id" = :item_id
     UNION
        SELECT 'version' AS "atype", 
            "%(PI_TYPE)s_changes"."change_id" AS "item_id", 
            "%(PI_TYPE)s_changes"."description" AS "description", 
            "%(PI_TYPE)s_changes"."date_active" AS "adate", 
            "notes" as "notes"
        FROM "public"."%(PI_TYPE)s_versions" AS "%(PI_TYPE)s_versions", 
            "public"."%(PI_TYPE)s_changes" AS "%(PI_TYPE)s_changes" 
        WHERE "%(PI_TYPE)s_versions"."change_id" = "%(PI_TYPE)s_changes"."change_id" 
        AND "%(PI_TYPE)s_versions"."manual" = True
        AND "%(PI_TYPE)s_changes"."content_id" = :item_id
    
    ORDER BY adate DESC
"""

sql_bill_timeline = sql_item_timeline % {"PI_TYPE": "bill"}
sql_motion_timeline = sql_item_timeline % {"PI_TYPE": "motion"}
sql_question_timeline = sql_item_timeline % {"PI_TYPE": "question"}
sql_tableddocument_timeline = sql_item_timeline % {"PI_TYPE": "tabled_document"}
# Note: event_items UNION block is not relevant for agendaitems as these 
# do not support addition of events
sql_agendaitem_timeline = sql_item_timeline % {"PI_TYPE": "agenda_item"}


