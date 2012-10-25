import json
import zope.interface
from zope.app.component.hooks import getSite
import zope.publisher.interfaces.browser
import zope.cachedescriptors.property
from bungeni.utils.capi import capi
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
        return url.absoluteURL(container, common.get_request())
cached_props = CachedProperties()

RESOURCE_MAPPING = {
    "scheduler-globals.js": "scheduler_globals",
    "calendar-globals.js": "calendar_globals"
}

RESOURCE_HEADERS = {}

## some global strings to i18n ##
YES = _(u"Yes")
NO = _(u"No")
OKAY = _(u"Okay")
DONE = _(u"Done")
NOTICE = _(u"Notice")
WORKING = _(u"Working")
CANCEL = _(u"Cancel")
VIEW = _(u"View")
EDIT = _(u"Edit")
DELETE = _(u"Delete")
WARNING = _(u"Warning")



def get_globals(group_name, **kwargs):
    language = kwargs.get("language", "en")
    type_names = {
        "heading":i18n(_(u"heading"), language),
        "editorial_note":i18n(_(u"editorial note"), language),
        "minute":i18n(_(u"minute record"), language),
    }
    type_names.update([
        (name, i18n(info.get("display_name"), language))
        for (name, info) in data.get_schedulable_types().iteritems()
    ])
    globals_map = {
        "SCHEDULER_GLOBALS" : {
            "items_container_uri": cached_props.items_container,
            "schedulable_types": [ 
                dict(name=name, title=i18n(info.get("title"), language)) 
                for (name, info) in 
                sorted(data.get_schedulable_types().iteritems())
             ],
            "discussable_types": [k for k in data.get_schedulable_types()],
            "editable_types": ["editorial_note", "minute"],
            "types": {
                "HEADING": "heading",
                "EDITORIAL_NOTE": "editorial_note",
                "MINUTE": "minute",
            },
            "type_names": type_names,
            "current_schedule_title": i18n(_(u"Agenda"), language),
            "current_schedule_items": i18n(_(u"Scheduled Items"), language),
            "available_items_title": i18n(_(u"Available Items"), language),
            "schedule_discussions_title": i18n(_(u"Agenda and minutes"), language),
            "scheduled_item_context_menu_header": i18n(_(u"Modify Item"), 
                language
            ),
            "json_listing_url" : "./items/jsonlisting-raw",
            "json_listing_url_meta" : "./items/jsonlisting-schedule",
            "save_schedule_url": "./items/save-schedule",
            "discussions_save_url": "discussions/save-discussions",
            "discussion_items_json_url" : "discussions/jsonlisting-raw",
            "schedulable_items_json_url" : "./schedulable-items-json",
            "column_title": i18n(_(u"Description"), language),
            "column_discussion_text": i18n(_(u"minute text"), language),
            "column_discussion_text_missing": i18n(_(u"NO TEXT RECORD FOUND"), 
                language
            ),
            "column_discussion_edit_button": i18n(EDIT, language),
            "column_discussions_edit_button": i18n(_(u"Minutes"), language),
            "column_discussion_delete_button": i18n(DELETE, language),
            "column_available_headings_title": i18n(
                _(u"Select existing heading"), 
                language
            ),
            "column_type": i18n(_(u"Type"), language),
            "column_mover": i18n(_(u"Moved by"), language),
            "column_status": i18n(_(u"Status"), language),
            "column_status_date": i18n(_(u"Date"), language),
            "column_registry_number": i18n(_(u"No."), language),
            "column_mover": i18n(_(u"Mover"), language),
            "empty_agenda_message": i18n(_(u"the agenda is empty. "
                "add items from below from from the available documents to the"
                " right"
            ),
                language
            ),
            "text_button_text": i18n(_(u"editorial note"), language),
            "text_records_title": i18n(_(u"add text records"), language),
            "heading_button_text": i18n(_(u"heading"), language),
            "minute_button_text": i18n(_(u"minute record"), language),
            "new_heading_text": i18n(_(u"custom heading"), language),
            "text_action_view": i18n(VIEW, language),
            "text_moved_by": i18n(_(u"Moved By"), language),
            "remove_button_text": i18n(_(u"remove item"), language),
            "save_button_text": i18n(_(u"save changes"), language),
            "save_and_preview_button_text": i18n(_(u"save and preview"), language),
            "discard_button_text": i18n(_(u"discard changes"), language),
            "add_discussion_button_text": i18n(_(u"add minute"), language),
            "save_discussion_button_text": i18n(_(u"add minute"), language),
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
            "filters_start_date_label": i18n(_(u"start date"), language),
            "filters_end_date_label": i18n(_(u"end date"), language),
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
            "minutes_header": i18n(_(u"Minutes:"), language),
            "minutes_unsaved_agenda": i18n(_(u"*Unsaved item. No minute records."),
                language
            ),
            "minutes_no_records": i18n(_(u"No minute records"),
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
            "errors_title": i18n(_(u"Make Corrections"), language),
            "venue_required": i18n(_(u"Venue : Select a venue"), language),
            "language_required": i18n(_(u"Language : Select a language"), 
                language
            ),
            "error_collission": i18n(_(u"This timeslot already has another " 
                    u"event.\n Do you want to continue?"
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

