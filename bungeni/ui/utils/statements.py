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
    %s
    ORDER BY adate DESC
    """

sql_bill_timeline = sql_item_timeline % """
     UNION
        SELECT "action" as "atype", "content_id" AS "item_id", 
        "description" AS "title", 
        "date" AS "adate" 
        FROM "public"."bill_changes" AS "bill_changes" 
        WHERE "action" = 'workflow'
        AND "content_id" = :item_id
     UNION
        SELECT 'version' AS "atype", 
            "bill_changes"."change_id" AS "item_id", 
            "bill_changes"."description" AS "title", 
            "bill_changes"."date" AS "adate" 
        FROM "public"."bill_versions" AS "bill_versions", 
            "public"."bill_changes" AS "bill_changes" 
        WHERE "bill_versions"."change_id" = "bill_changes"."change_id" 
        AND "bill_versions"."manual" = True
        AND "bill_changes"."content_id" = :item_id
    """

sql_motion_timeline = sql_item_timeline % """
     UNION
        SELECT "action" as "atype", "content_id" AS "item_id", 
        "description" AS "title", 
        "date" AS "adate" 
        FROM "public"."motion_changes" AS "motion_changes" 
        WHERE "action" = 'workflow'
        AND "content_id" = :item_id
     UNION
        SELECT 'version' AS "atype", 
            "motion_changes"."change_id" AS "item_id", 
            "motion_changes"."description" AS "title", 
            "motion_changes"."date" AS "adate" 
        FROM "public"."motion_versions" AS "motion_versions", 
            "public"."motion_changes" AS "motion_changes" 
        WHERE "motion_versions"."change_id" = "motion_changes"."change_id" 
        AND "motion_versions"."manual" = True
        AND "motion_changes"."content_id" = :item_id
    """
        
sql_question_timeline = sql_item_timeline % """
     UNION
        SELECT "action" as "atype", "content_id" AS "item_id", 
        "description" AS "title", 
        "date" AS "adate" 
        FROM "public"."question_changes" AS "question_changes" 
        WHERE "action" = 'workflow'
        AND "content_id" = :item_id
     UNION
        SELECT 'version' AS "atype", 
            "question_changes"."change_id" AS "item_id", 
            "question_changes"."description" AS "title", 
            "question_changes"."date" AS "adate" 
        FROM "public"."question_versions" AS "question_versions", 
            "public"."question_changes" AS "question_changes" 
        WHERE "question_versions"."change_id" = "question_changes"."change_id" 
        AND "question_versions"."manual" = True
        AND "question_changes"."content_id" = :item_id
    """

sql_tableddocument_timeline = sql_item_timeline % """
     UNION
        SELECT "action" as "atype", "content_id" AS "item_id", 
        "description" AS "title", 
        "date" AS "adate" 
        FROM "public"."tabled_document_changes" AS "tableddocument_changes" 
        WHERE "action" = 'workflow'
        AND "content_id" = :item_id
     UNION
        SELECT 'version' AS "atype", 
            "tableddocument_changes"."change_id" AS "item_id", 
            "tableddocument_changes"."description" AS "title", 
            "tableddocument_changes"."date" AS "adate" 
        FROM "public"."tabled_document_versions" AS "tableddocument_versions", 
            "public"."tabled_document_changes" AS "tableddocument_changes" 
        WHERE "tableddocument_versions"."change_id" = "tableddocument_changes"."change_id" 
        AND "tableddocument_versions"."manual" = True
        AND "tableddocument_changes"."content_id" = :item_id
    """
        
        
