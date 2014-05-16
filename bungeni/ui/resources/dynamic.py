# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Python code for JavaScript resources.

$Id$
"""
import json
import zope.interface
from zope.app.component.hooks import getSite
import zope.publisher.interfaces.browser
from zope.dublincore.interfaces import IDCDescriptiveProperties
from bungeni.ui.utils import url
from bungeni.utils import common, misc
from bungeni.models import utils as model_utils
from bungeni.core.language import get_default_language
from bungeni.core.workspace import CURRENT_INBOX_COOKIE_NAME
from bungeni.ui.calendar import data
from bungeni.capi import capi
from bungeni import _, translate


class CachedProperties(object):
    
    @misc.cached_property
    def items_container(self):
        """The URL to a container listing documents available for scheduling
        """
        site =  getSite()
        container = site["workspace"]["scheduling"]["documents"]
        request = common.get_request()
        app_url = request.getApplicationURL()
        return url.absoluteURL(container, request).replace(app_url, "")

cached_props = CachedProperties()

RESOURCE_MAPPING = {
    "scheduler-globals.js": "scheduler_globals",
    "calendar-globals.js": "calendar_globals",
    "workspace-globals.js": "workspace_globals"
}

RESOURCE_HEADERS = {}

## some global strings to i18n ##
YES = _("scheduling_message_yes", default=u"Yes")
NO = _("scheduling_message_no", default=u"No")
OKAY = _("scheduling_message_okay", default=u"Okay")
DONE = _("scheduling_message_done", default=u"Done")
NOTICE = _("scheduling_message_notice", default=u"Notice")
WORKING = _("scheduling_message_working", default=u"Working")
CANCEL = _("scheduling_message_cancel", default=u"Cancel")
VIEW = _("scheduling_message_view", default=u"View")
EDIT = _("scheduling_message_edit", default=u"Edit")
DELETE = _("scheduling_message_delete", default=u"Delete")
WARNING = _("scheduling_message_warning", default=u"Warning")
MINUTES = _("scheduling_text_minutes", default=u"Minutes")
START_DATE = _("scheduling_filters_start_date", default=u"Start Date")
END_DATE = _("scheduling_filters_end_date", default=u"End Date")

# columns
COLUMN_TYPE = _("scheduling_column_type", default="Type")
COLUMN_MOVER = _("scheduling_column_mover", default="Moved by")
COLUMN_STATUS = _("scheduling_column_status", default="Status")
COLUMN_STATUS_DATE = _("scheduling_column_status_date", default="Date")
COLUMN_REGISTRY_NUMBER = _("scheduling_column_registry_no", default="No.")
COLUMN_DESCRIPTION = _("scheduling_column_description", 
    default="Description")
COLUMN_MINUTE_TEXT = _("scheduling_column_minute_text", 
    default="Minute Text")

# titles
TITLE_AGENDA = _("scheduling_title_agenda", default="Agenda")
TITLE_AGENDA_MINUTES = _("scheduling_title_agenda_minutes", 
    default="Agenda Minutes and Votes")
TITLE_SCHEDULED_ITEMS = _("scheduling_title_scheduled_items", 
    default="Scheduled Items")
TITLE_AVAILABLE_ITEMS = _("scheduling_title_available_items", 
    default="Available Items")
TITLE_DISCUSSIONS = _("scheduling_title_discussions", 
    default="Agenda and Minutes")

# types
TYPE_HEADING = _("scheduling_type_heading", default="Heading")
TYPE_MINUTE = _("scheduling_type_minute", default="Minute Record")
TYPE_EDITORIAL_NOTE = _("scheduling_type_editorial_note", 
    default="Editorial Note")

# actions
REMOVE_ITEM = _("scheduling_action_remove_item", default="Remove Item")
ADD_MINUTE = _("scheduling_action_add_minute", default="Add Minute")
SAVE_AND_PREVIEW = _("scheduling_action_save_preview", 
    default="Save and preview")
SAVE_CHANGES = _("scheduling_action_save_changes", 
    default="Save Changes")
DISCARD_CHANGES = _("scheduling_action_discard_changes", 
    default="Discard Changes")


def get_globals(group_name, target_language=None):
    kwargs = {"target_language": target_language or capi.default_language}
    type_names = {
        "heading": translate(_(u"heading"), **kwargs),
        "editorial_note": translate(TYPE_EDITORIAL_NOTE, **kwargs),
        "minute": translate(_(u"minute record"), **kwargs),
    }
    type_names.update([
        (name, translate(info.get("display_name"), **kwargs))
        for (name, info) in data.get_schedulable_types(True).iteritems()
    ])
    globals_map = {
        "SCHEDULER_GLOBALS" : {
            "items_container_uri": cached_props.items_container,
            "schedulable_types": [ 
                dict(name=name, title=translate(info.get("title"), **kwargs)) 
                for (name, info) in 
                sorted(data.get_schedulable_types().iteritems())
             ],
            "discussable_types": [k for k in data.get_schedulable_types(True)],
            "editable_types": ["editorial_note", "heading", "minute"],
            "types": {
                "HEADING": "heading",
                "EDITORIAL_NOTE": "editorial_note",
                "MINUTE": "minute",
            },
            "type_names": type_names,
            "current_schedule_title": translate(TITLE_AGENDA, **kwargs),
            "agenda_minutes_title": translate(TITLE_AGENDA_MINUTES, **kwargs),
            "current_schedule_items": translate(TITLE_SCHEDULED_ITEMS, **kwargs),
            "available_items_title": translate(TITLE_AVAILABLE_ITEMS, **kwargs),
            "schedule_discussions_title": translate(TITLE_DISCUSSIONS, **kwargs),
            "scheduled_item_context_menu_header": translate(_(u"Modify Item"), 
                **kwargs
            ),
            "json_listing_url" : "./items/jsonlisting-schedule?include_text_records=y",
            "json_listing_url_meta" : "./items/jsonlisting-schedule?add_wf=y&include_text_records=y",
            "save_schedule_url": "./items/save-schedule",
            "discussions_save_url": "discussions/save-discussions",
            "discussion_items_json_url" : "discussions/jsonlisting-raw",
            "schedulable_items_json_url" : "./schedulable-items-json",
            "column_title": translate(COLUMN_DESCRIPTION, **kwargs),
            "column_discussion_text": translate(COLUMN_MINUTE_TEXT, **kwargs),
            "column_discussion_text_missing": translate(_(u"NO TEXT RECORD FOUND"), **kwargs),
            "column_discussion_edit_button": translate(EDIT, **kwargs),
            "column_discussions_edit_button": translate(MINUTES, **kwargs),
            "column_discussion_delete_button": translate(DELETE, **kwargs),
            "column_available_headings_title": translate(_(u"Select existing heading"), **kwargs),
            "column_type": translate(COLUMN_TYPE, **kwargs),
            "column_mover": translate(COLUMN_MOVER, **kwargs),
            "column_status": translate(COLUMN_STATUS, **kwargs),
            "column_status_date": translate(COLUMN_STATUS_DATE, **kwargs),
            "column_registry_number": translate(COLUMN_REGISTRY_NUMBER, **kwargs),
            "empty_agenda_message": translate(_(u"the agenda is empty. add items "
                "from below from from the available documents to the right"),
                **kwargs),
            "text_button_text": translate(TYPE_EDITORIAL_NOTE, **kwargs),
            "text_records_title": translate(_(u"add text records"), **kwargs),
            "heading_button_text": translate(TYPE_HEADING, **kwargs),
            "minute_button_text": translate(TYPE_MINUTE, **kwargs),
            "new_heading_text": translate(_(u"custom heading"), **kwargs),
            "text_action_view": translate(VIEW, **kwargs),
            "text_moved_by": translate(COLUMN_MOVER, **kwargs),
            "remove_button_text": translate(REMOVE_ITEM, **kwargs),
            "save_button_text": translate(SAVE_CHANGES, **kwargs),
            "save_and_preview_button_text": translate(SAVE_AND_PREVIEW, **kwargs),
            "discard_button_text": translate(DISCARD_CHANGES, **kwargs),
            "add_discussion_button_text": translate(ADD_MINUTE, **kwargs),
            "save_discussion_button_text": translate(ADD_MINUTE, **kwargs),
            "initial_editor_text": translate(_(u"change this text"), **kwargs),
            "delete_dialog_header": translate(_(u"Remove item from schedule")),
            "delete_dialog_text": translate(
                _(u"Are you sure you want to remove this item from schedule ?"),
                **kwargs),
            "delete_dialog_confirm": translate(YES, **kwargs),
            "delete_dialog_cancel": translate(NO, **kwargs),
            "save_dialog_header": translate(NOTICE, **kwargs),
            "save_dialog_empty_message": translate(
                _(u"No items have been scheduled. Add something then save."), 
                **kwargs),
            "save_dialog_confirm": translate(OKAY, **kwargs),
            "saving_dialog_header": translate(WORKING, **kwargs),
            "saving_schedule_text": translate(_(u"saving changes to schedule..."), **kwargs),
            "saving_discussions_text": translate(_(u"saving changes to minutes..."), **kwargs),
            "saving_dialog_refreshing": translate(_(u"reloading schedule..."), **kwargs),
            "saving_dialog_exception": translate(
                _(u"there was an error while saving the schedule"), **kwargs),
            "filters_no_filters_header": translate(_(u"no filters selected"), **kwargs),
            "filters_no_filters_message": translate(
                _(u"you did not choose any filters." "select some filters then hit apply"), 
                **kwargs),
            "filters_start_date_label": translate(START_DATE, **kwargs),
            "filters_end_date_label": translate(END_DATE, **kwargs),
            "filters_clear_label": translate(_(u"clear filters"), **kwargs),
            "filter_config": data.get_filter_config(),
            "filter_apply_label": translate(_(u"apply filters"), **kwargs),
            "message_no_add_rights": translate(_(u"this schedule is read only"), **kwargs),
            "text_warning": translate(WARNING, **kwargs),
            "text_items_dialog_header": translate(_(u"add text to schedule"), **kwargs),
            "text_dialog_confirm_action": translate(OKAY, **kwargs),
            "text_dialog_done_action": translate(DONE, **kwargs),
            "text_dialog_cancel_action": translate(CANCEL, **kwargs),
            "text_unsaved_changes": translate(_(u"Schedule has unsaved changes"), **kwargs),
            "text_unsaved_discussions": translate(_(u"Do you want to delete unsaved minute?"), **kwargs),
            "confirm_dialog_title": translate(_(u"Confirmation Required"), **kwargs),
            "confirm_message_delete_discussion": translate(
                _(u"Really remove this minute record?"), **kwargs),
            "message_item_not_saved": translate(_(u"You need to save the schedule before "
                    "adding minutes for it to this item."), **kwargs),
            "minutes_header": translate(MINUTES, **kwargs),
            "minutes_unsaved_agenda": translate(_(u"*Unsaved item. No minute records."), **kwargs),
            "minutes_no_records": translate(_(u"No minute records"), **kwargs),
            "add_minutes_record": translate(_(u"add minutes record"), **kwargs),
            "minutes_edit": translate(_(u"Edit"), **kwargs),
            "minutes_loading": translate(_(u"Loading minutes..."), **kwargs),
            "minutes_loading_error": translate(_(u"unable to load minutes..."), **kwargs),
            "preview_msg_header": translate(_(u"agenda preview"), **kwargs),
            "preview_msg_generating": translate(_(u"generating agenda preview..."), **kwargs),
            "preview_msg_error": translate(_(u"ERROR: Could to generate preview"), **kwargs),
        },
        "CALENDAR_GLOBALS": {
            "unsaved_event": translate(_(u"This event is unsaved. " 
                "Edit to make any corrections and then save it"), **kwargs),
            "errors_scheduler": translate(_(u"Please make corrections. "
                "The highlighted fields are required."), **kwargs),
            "error_collission": translate(_(u"This timeslot already has another " 
                    u"event.\n Do you want still want to add it?"), **kwargs
            ),
            "message_okay": translate(OKAY, **kwargs),
        },
    }
    return globals_map.get(group_name, {})

class DynamicDirectoryFactory(object):
    """Allows generation of static resources whose content is contextual.
    
    For example, we want some system parameters to be available to certain
    registered JavaScript resources
    """
    
    zope.interface.implements(
        zope.publisher.interfaces.browser.IBrowserPublisher
    )

    def __init__(self, source, checker, name):
        self.name = name
        self.__Security_checker__ = checker
        self.language = None
    
    def __call__(self, name):
        return self
    
    def __getitem__(self, name):
        return lambda:"/@@/%s/%s" % (self.name, name)
    
    def publishTraverse(self, request, name):
        request.response.setHeader("Content-type", 
            RESOURCE_HEADERS.get(name, "text/javascript")
        )
        self.request = request
        self.language = get_default_language()
        return getattr(self, RESOURCE_MAPPING.get(name))
    
    def scheduler_globals(self):
        return """var scheduler_globals = %s;""" % json.dumps(
            get_globals("SCHEDULER_GLOBALS", target_language=self.language)
        )
    
    def calendar_globals(self):
        return """var calendar_globals = %s;""" % json.dumps(
            get_globals("CALENDAR_GLOBALS", target_language=self.language)
        )

    def workspace_globals(self):
        user = model_utils.get_login_user()
        groups = [ g for g in model_utils.get_user_groups(user) ]
        groups.sort(key=lambda g:g.group_id)
        group_data = {
            "groups": [ dict(group_id=str(g.group_id),
                name=IDCDescriptiveProperties(g).short_title)
                for g in groups ],
            "all_documents_tab": translate('all documents',
                target_language=self.language),
            "current_inbox": self.request.getCookies().get(
                CURRENT_INBOX_COOKIE_NAME, "")
        }
        return """var workspace_globals = %s;""" % json.dumps(group_data)


