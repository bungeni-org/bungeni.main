import json
import zope.interface
from zope.app.component.hooks import getSite
import zope.publisher.interfaces.browser
import zope.cachedescriptors.property
from bungeni.capi import capi
from bungeni.ui.i18n import _
from bungeni.ui.utils import url, common
from bungeni.core.translation import (translate_i18n as i18n, 
    get_request_language
)
from bungeni.ui.calendar import data

class CachedProperties(object):
    @zope.cachedescriptors.property.cachedIn("__available_docs_container__")
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
    "calendar-globals.js": "calendar_globals"
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

#columns
COLUMN_TYPE = _("scheduling_column_type", default="Type")
COLUMN_MOVER = _("scheduling_column_mover", default="Moved by")
COLUMN_STATUS = _("scheduling_column_status", default="Status")
COLUMN_STATUS_DATE = _("scheduling_column_status_date", default="Date")
COLUMN_REGISTRY_NUMBER = _("scheduling_column_registry_no", default="No.")
COLUMN_DESCRIPTION = _("scheduling_column_description", 
    default="Description")
COLUMN_MINUTE_TEXT = _("scheduling_column_minute_text", 
    default="Minute Text")

#titles
TITLE_AGENDA = _("scheduling_title_agenda", default="Agenda")
TITLE_AGENDA_MINUTES = _("scheduling_title_agenda_minutes", 
    default="Agenda Minutes and Votes")
TITLE_SCHEDULED_ITEMS = _("scheduling_title_scheduled_items", 
    default="Scheduled Items")
TITLE_AVAILABLE_ITEMS = _("scheduling_title_available_items", 
    default="Available Items")
TITLE_DISCUSSIONS = _("scheduling_title_discussions", 
    default="Agenda and Minutes")

#types
TYPE_HEADING = _("scheduling_type_heading", default="Heading")
TYPE_MINUTE = _("scheduling_type_minute", default="Minute Record")
TYPE_EDITORIAL_NOTE = _("scheduling_type_editorial_note", 
    default="Editorial Note")

#actions
REMOVE_ITEM = _("scheduling_action_remove_item", default="Remove Item")
ADD_MINUTE = _("scheduling_action_add_minute", default="Add Minute")
SAVE_AND_PREVIEW = _("scheduling_action_save_preview", 
    default="Save and preview")
SAVE_CHANGES = _("scheduling_action_save_changes", 
    default="Save Changes")
DISCARD_CHANGES = _("scheduling_action_discard_changes", 
    default="Discard Changes")

def get_globals(group_name, **kwargs):
    language = kwargs.get("language", "en")
    type_names = {
        "heading":i18n(_(u"heading"), language),
        "editorial_note":i18n(TYPE_EDITORIAL_NOTE, language),
        "minute":i18n(_(u"minute record"), language),
    }
    type_names.update([
        (name, i18n(info.get("display_name"), language))
        for (name, info) in data.get_schedulable_types(True).iteritems()
    ])
    globals_map = {
        "SCHEDULER_GLOBALS" : {
            "items_container_uri": cached_props.items_container,
            "schedulable_types": [ 
                dict(name=name, title=i18n(info.get("title"), language)) 
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
            "current_schedule_title": i18n(TITLE_AGENDA, language),
            "agenda_minutes_title": i18n(TITLE_AGENDA_MINUTES, language),
            "current_schedule_items": i18n(TITLE_SCHEDULED_ITEMS, language),
            "available_items_title": i18n(TITLE_AVAILABLE_ITEMS, language),
            "schedule_discussions_title": i18n(TITLE_DISCUSSIONS, language),
            "scheduled_item_context_menu_header": i18n(_(u"Modify Item"), 
                language
            ),
            "json_listing_url" : "./items/jsonlisting-schedule",
            "json_listing_url_meta" : "./items/jsonlisting-schedule?add_wf=y",
            "save_schedule_url": "./items/save-schedule",
            "discussions_save_url": "discussions/save-discussions",
            "discussion_items_json_url" : "discussions/jsonlisting-raw",
            "schedulable_items_json_url" : "./schedulable-items-json",
            "column_title": i18n(COLUMN_DESCRIPTION, language),
            "column_discussion_text": i18n(COLUMN_MINUTE_TEXT, language),
            "column_discussion_text_missing": i18n(
                _(u"NO TEXT RECORD FOUND"), language),
            "column_discussion_edit_button": i18n(EDIT, language),
            "column_discussions_edit_button": i18n(MINUTES, language),
            "column_discussion_delete_button": i18n(DELETE, language),
            "column_available_headings_title": i18n(
                _(u"Select existing heading"), 
                language
            ),
            "column_type": i18n(COLUMN_TYPE, language),
            "column_mover": i18n(COLUMN_MOVER, language),
            "column_status": i18n(COLUMN_STATUS, language),
            "column_status_date": i18n(COLUMN_STATUS_DATE, language),
            "column_registry_number": i18n(COLUMN_REGISTRY_NUMBER, language),
            "empty_agenda_message": i18n(_(u"the agenda is empty. "
                "add items from below from from the available documents to the"
                " right"
            ),
                language
            ),
            "text_button_text": i18n(TYPE_EDITORIAL_NOTE, language),
            "text_records_title": i18n(_(u"add text records"), language),
            "heading_button_text": i18n(TYPE_HEADING, language),
            "minute_button_text": i18n(TYPE_MINUTE, language),
            "new_heading_text": i18n(_(u"custom heading"), language),
            "text_action_view": i18n(VIEW, language),
            "text_moved_by": i18n(COLUMN_MOVER, language),
            "remove_button_text": i18n(REMOVE_ITEM, language),
            "save_button_text": i18n(SAVE_CHANGES, language),
            "save_and_preview_button_text": i18n(SAVE_AND_PREVIEW, language),
            "discard_button_text": i18n(DISCARD_CHANGES, language),
            "add_discussion_button_text": i18n(ADD_MINUTE, language),
            "save_discussion_button_text": i18n(ADD_MINUTE, language),
            "initial_editor_text": i18n(
                _(u"change this text"), language
            ),
            "delete_dialog_header": i18n(_(u"Remove item from schedule")),
            "delete_dialog_text": i18n(
                _(u"Are you sure you want to remove this item from schedule ?"),
                language
            ),
            "delete_dialog_confirm": i18n(YES, language),
            "delete_dialog_cancel": i18n(NO, language),
            "save_dialog_header": i18n(NOTICE, language),
            "save_dialog_empty_message": i18n(
                _(u"No items have been scheduled. Add something then save."), 
                language
            ),
            "save_dialog_confirm": i18n(OKAY, language),
            "saving_dialog_header": i18n(WORKING, language),
            "saving_schedule_text": i18n(_(u"saving changes to schedule..."), 
                language
            ),
            "saving_discussions_text": i18n(
                _(u"saving changes to minutes..."), 
                language
            ),
            "saving_dialog_refreshing": i18n(
                _(u"reloading schedule..."), language
            ),
            "saving_dialog_exception": i18n(
                _(u"there was an error while saving the schedule"), language
            ),
            "filters_no_filters_header": i18n(_(u"no filters selected"), 
                language
            ),
            "filters_no_filters_message": i18n(
                _(u"you did not choose any filters." "select some filters then"
                    " hit apply"
                ), 
                language
            ),
            "filters_start_date_label": i18n(START_DATE, language),
            "filters_end_date_label": i18n(END_DATE, language),
            "filters_clear_label": i18n(_(u"clear filters"), language),
            "filter_config": data.get_filter_config(),
            "filter_apply_label": i18n(_(u"apply filters"), language),
            "message_no_add_rights": i18n(_(u"this schedule is read only"), 
                language
            ),
            "text_warning": i18n(WARNING, language),
            "text_items_dialog_header": i18n(_(u"add text to schedule"),
                language
            ),
            "text_dialog_confirm_action": i18n(OKAY, language),
            "text_dialog_done_action": i18n(DONE, language),
            "text_dialog_cancel_action": i18n(CANCEL, language),
            "text_unsaved_changes": i18n(_(u"Schedule has unsaved changes"),
                language
            ),
            "text_unsaved_discussions": i18n(
                _(u"Do you want to delete unsaved minute?"), language
            ),
            "confirm_dialog_title": i18n(_(u"Confirmation Required"), language),
            "confirm_message_delete_discussion": i18n(
                _(u"Really remove this minute record?"), language
            ),
            "message_item_not_saved": i18n(
                _(u"You need to save the schedule before adding minutes for it." 
                    u"to this item."
                ),
                language
            ),
            "minutes_header": i18n(MINUTES, language),
            "minutes_unsaved_agenda": i18n(_(u"*Unsaved item. No minute records."),
                language
            ),
            "minutes_no_records": i18n(_(u"No minute records"),
                language
            ),
            "add_minutes_record": i18n(_(u"add minutes record"),
                language
            ),
            "minutes_edit": i18n(_(u"Edit"), language),
            "minutes_loading": i18n(_(u"Loading minutes..."),
                language
            ),
            "minutes_loading_error": i18n(_(u"unable to load minutes..."),
                language
            ),
            "preview_msg_header": i18n(_(u"agenda preview"), language),
            "preview_msg_generating": i18n(_(u"generating agenda preview..."), 
                language
            ),
            "preview_msg_error": i18n(_(u"ERROR: Could to generate preview"), 
                language
            ),
        },
        "CALENDAR_GLOBALS" : {
            "unsaved_event": i18n(_(u"This event is unsaved. " 
                "Edit to make any corrections and then save it"), language
            ),
            "errors_scheduler": i18n(_(u"Please make corrections. "
                "The highlighted fields are required."), language),
            "error_collission": i18n(_(u"This timeslot already has another " 
                    u"event.\n Do you want still want to add it?"
                ), language
            ),
            "message_okay": i18n(OKAY, language),
        }
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
        self.request_language = capi.default_language
    
    def __call__(self, name):
        return self
    
    def __getitem__(self, name):
        return lambda:"/@@/%s/%s" % (self.name, name)
    
    def publishTraverse(self, request, name):
        request.response.setHeader("Content-type", 
            RESOURCE_HEADERS.get(name, "text/javascript")
        )
        self.request_language = get_request_language()
        return getattr(self, RESOURCE_MAPPING.get(name))
    
    def scheduler_globals(self):
        return """var scheduler_globals = %s;""" % json.dumps(
            get_globals("SCHEDULER_GLOBALS", language=self.request_language)
        )

    def calendar_globals(self):
        return """var calendar_globals = %s;""" % json.dumps(
            get_globals("CALENDAR_GLOBALS", language=self.request_language)
        )

