/**
 * Resusable configurations used by various Bungeni scheduling bundles
 * 
 * Defines the bungeni namespace and configuration components
**/
YAHOO.namespace("bungeni");

/**
 * Notify schedule author of unsaved changes
 */
window.onbeforeunload = function(ev){
    $.unblockUI();
    if (YAHOO.bungeni.unsavedChanges){
        return scheduler_globals.text_unsaved_changes;
    }else{
        return null;
    }
}

YAHOO.bungeni.Utils = function(){
    /**
     * @function wrapText
     * @description returns text as html wrapped in el tags
     */
    var wrapText = function(text, el){
        var _el = el || "em";
        return "<" + _el + ">" + text + "</" + _el + ">";
    }

    return {
        wrapText: wrapText
    }
}();

/**
 * Custom bungeni events fired during scheduling
 */
YAHOO.bungeni.Events = function(){
    return {
        scheduleAvailable : new YAHOO.util.CustomEvent("onAvailable")
    }
}();

/**
 * @method refresh
 * @description Custom method of added to data table to refresh data
 **/
YAHOO.widget.DataTable.prototype.refresh = function(params) {
    var dataSource = this.getDataSource();
    var data_url = null;
    if (params != undefined){
        var data_params = new Array()
        for (filter in params){
            data_params.push([filter, params[filter]].join("="));
        }
        data_url = "&" + data_params.join("&");
    }
    dataSource.sendRequest(
            data_url,
            {
                success: this.onDataReturnInitializeTable,
                failure: this.onDataReturnInitializeTable,
                scope: this
            }
    );
};


YAHOO.bungeni.config = function(){
    var lang = YAHOO.lang;

    var scheduling_columns = {
        SELECT_ROW : "item_select_row",
        ID : "item_id",
        OBJECT_ID : "object_id",
        TYPE : "item_type",
        TITLE : "item_title",
        MOVE_UP : "item_move_up",
        MOVE_DOWN : "item_move_down",
        MOVER : "item_mover",
        URI : "item_uri",
        REGISTRY_NO : "registry_number",
        STATUS : "status",
        STATUS_DATE : "status_date",
        NUMBER : "number",
        BODY_TEXT : "body_text",
        DISCUSSION_EDIT : "edit_discussion",
        DISCUSSION_DELETE : "delete_discussion",
    }
    var dialog_config = function(){
        var default_config = {
            width: "auto",
            fixedcenter: true,
            modal: true,
            visible: false,
            draggable: false,
            underlay: "none",
        }
        return {
            default: default_config
        }
    }();
    var element_selectors = {
        "checkbox": "input[type=checkbox]"
    };
    var scheduling_configs = {
        columns : scheduling_columns,
        formatters : function(){
             var BungeniUtils = YAHOO.bungeni.Utils;
             var Columns = scheduling_columns;
             
            /**
             * @method itemTypeFormatter
             * @description render item type in reduced form
             */
             var itemTypeFormatter = function(el, record, column, data){
                 el.innerHTML = ("<span style='font-size:10px;'>" + 
                    record.getData()[Columns.TYPE] + 
                    "</span>"
                );
             }


            /**
             * @method itemTitleFormatter
             * @description renders title, emphasized text for titles and italicized
             * text for text records
             */
             var itemTitleFormatter = function(el, record, column, data){
                 rec_data = record.getData();
                 if(rec_data.item_type == scheduler_globals.types.HEADING){
                     el.innerHTML = (
                        "<span style='text-align:center;display:block;'><strong>" + 
                        rec_data.item_title + "</strong></span>"
                    );
                 }else if(rec_data.item_type == scheduler_globals.types.TEXT){
                     el.innerHTML = BungeniUtils.wrapText(rec_data.item_title);
                 }else{
                     if (rec_data.item_uri){
                        el.innerHTML = (rec_data.item_title + 
                            "<em style='display:block;'><span>" +
                            scheduler_globals.text_moved_by + " : " + 
                            rec_data.item_mover + "</span>&nbsp;&nbsp;" +
                            "<a href='" + rec_data.item_uri + "' target='blank'>" + 
                            scheduler_globals.text_action_view + "</a>"
                        );
                    }else{
                        el.innerHTML = (rec_data.item_title + 
                            "<em><span style='display:block;'>Moved by: " 
                            + rec_data.item_mover + "</span></em>"
                        );
                    }
                 }
             }
             
            /**
             * @method itemMoveFormatter
             * @description renders controls to move scheduled items up/down the
             * schedule depending on direction
             */
            var itemMoveFormatter = function(el, record, column, data, dir, table){
                var move_markup = "";
                var index = table.getTrIndex(record) + 1;
                var last_row = table.getRecordSet().getLength();
                var dir_char = (dir=="up")?"&uarr;":"&darr;"

                if (!(((index == 1) && (dir=="up")) || 
                    ((index == last_row) && (dir=="down"))
                )){
                    move_markup = "<span id='up'>" + dir_char + "</span>";
                }
                el.innerHTML = move_markup;
            }
            var itemMoveUpFormatter = function(el, record, column, data){
                itemMoveFormatter(el, record, column, data, "up", this);
            }
            var itemMoveDownFormatter = function(el, record, column, data){
                itemMoveFormatter(el, record, column, data, "down", this);
            }
            
            var countFormatter = function(el, record, column, data){
                el.innerHTML = this.getTrIndex(record)+1;
            }
            
            var longTextFormatter = function(el, record, column, data){
                var text = (record.getData()[column.key] || 
                    scheduler_globals.column_discussion_text_missing
                );
                el.innerHTML = BungeniUtils.wrapText(text);
            }

            var editButtonFormatter = function(el, record, column, data){
                if (!el.innerHTML){
                    var button = new YAHOO.widget.Button({
                        label: scheduler_globals.column_discussion_edit_button,
                        id: el.id + "-edit-button"
                    });
                    button.appendTo(el);
                }
            }

            var editDiscussionsFormatter = function(el, record, column, data){
                if (scheduler_globals.discussable_types.indexOf(
                    record.getData()[Columns.TYPE])>=0
                ){
                    if (!el.innerHTML){
                        var button = new YAHOO.widget.Button({
                            label: scheduler_globals.column_discussions_edit_button,
                            id: el.id + "-edit-button"
                        });
                        button.appendTo(el);
                    }
                }
            }

            var deleteButtonFormatter = function(el, record, column, data){
                if (!el.innerHTML){
                    var button = new YAHOO.widget.Button({
                        label: scheduler_globals.column_discussion_delete_button,
                        id: el.id + "-delete-button"
                    });
                    button.appendTo(el);
                }
            }
            
            var linkFormatter = function(el, oRecord, oColumn, oData, oDataTable) {
                if(lang.isString(oData) && (oData > "")) {
                    el.innerHTML = ("<a href=\"" + oData + 
                        "\" target=\"blank\"\">" + 
                        scheduler_globals.text_action_view + "</a>"
                    );
                }
                else {
                    el.innerHTML = lang.isValue(oData) ? oData : "";
                }
            }
            
            /**
             * @method availableItemSelectorFormatter
             * @description renders checkboxes to select items to add to a 
             * schedule
             */
            var availableItemSelectFormatter = function(el, record, column, data){
                index = this.getTrIndex(record) + 1;
                record_key = ((record.getData().item_id + ":" + 
                    record.getData().item_type).toString()
                );
                checked = "";
                if (YAHOO.bungeni.scheduled_item_keys != undefined){
                    if(YAHOO.bungeni.scheduled_item_keys.indexOf(record_key)>=0){
                        checked = "checked='checked'";
                    }
                }
                el.innerHTML = ("<input type='checkbox' name='rec-sel-" + 
                    index +"' " + checked + "/>"
                );
                
            }


            return {
                title: itemTitleFormatter,
                type: itemTypeFormatter,
                moveUp: itemMoveUpFormatter,
                moveDown: itemMoveDownFormatter,
                counter: countFormatter,
                longText: longTextFormatter,
                editButton: editButtonFormatter,
                deleteButton: deleteButtonFormatter,
                link: linkFormatter,
                availableItemSelect: availableItemSelectFormatter,
                editDiscussions: editDiscussionsFormatter
            }
        }()
    }
    return {
        scheduling: scheduling_configs,
        dialogs: dialog_config,
        selectors: element_selectors
    }
}();
