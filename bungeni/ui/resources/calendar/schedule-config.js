/**
 * Resusable configurations used by various Bungeni scheduling bundles
 * 
 * Defines the bungeni namespace and configuration components
**/
YAHOO.namespace("bungeni");

var SGlobals = scheduler_globals;

/**
 * Notify schedule author of unsaved changes
 */
window.onbeforeunload = function(ev){
    $.unblockUI();
    if (YAHOO.bungeni.unsavedChanges){
        return SGlobals.text_unsaved_changes;
    }else{
        return null;
    }
}

YAHOO.bungeni.Utils = function(){
    /**
     * @function wrapText
     * @description returns text as html wrapped in el tags
     */
    var wrapText = function(text, el, attrs){
        var _el = el || "em";
        var _attrs = attrs || "";
        return "<" + _el + " " + _attrs + ">" + text + "</" + _el + ">";
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
    var Event = YAHOO.util.Event;
    var Y$ = YAHOO.util.Selector;

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
        WORKFLOW_STATE : "wf_state",
        WORKFLOW_ACTIONS : "wf_actions",
        ADD_TEXT_RECORD : "add_text_record",
    }
    scheduling_columns.move_columns = [
        scheduling_columns.MOVE_UP, scheduling_columns.MOVE_DOWN
    ];

    var _schemas = {
        available_items : {
            resultsList : "items",
            fields : [scheduling_columns.ID, scheduling_columns.TYPE, 
                scheduling_columns.TITLE, scheduling_columns.STATUS,
                scheduling_columns.STATUS_DATE, scheduling_columns.REGISTRY_NO, 
                scheduling_columns.MOVER, scheduling_columns.URI
            ]
        }    
    }
    
    var element_selectors = {
        "checkbox": "input[type=checkbox]"
    };

    var dialogs = function(){
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
        var blocking = {
            init: function(){
                this.dialog = new YAHOO.widget.SimpleDialog(
                    "scheduling-blocking", dialog_config.default
                );
                this.dialog.setHeader(SGlobals.saving_dialog_header);
                this.dialog.setBody("");
                this.dialog.cfg.queueProperty("width", "200px");
                this.dialog.cfg.queueProperty("close", false);
                this.dialog.cfg.queueProperty("icon",
                    YAHOO.widget.SimpleDialog.ICON_BLOCK
                );
                this.dialog.render(document.body);
            },
            show: function(message){
                if(!this.dialog){
                    this.init();
                }
                this.dialog.setBody(message);
                this.dialog.show();
                this.dialog.bringToTop();
            },
            hide: function(){
                this.dialog.hide();
            }
        }
        var notification = {
            init: function(){
                this.dialog = new YAHOO.widget.SimpleDialog(
                    "scheduling-notification", dialog_config.default
                );
                this.dialog.setHeader(SGlobals.text_warning);
                this.dialog.setBody("");
                this.dialog.cfg.queueProperty("width", "200px");
                this.dialog.cfg.queueProperty("close", false);
                this.dialog.cfg.queueProperty("icon",
                    YAHOO.widget.SimpleDialog.ICON_WARN
                );
                this.dialog.render(document.body);
            },
            show: function(message){
                if(!this.dialog){
                    this.init();
                }
                this.dialog.setBody(message);
                this.dialog.show();
                this.dialog.bringToTop();
                window.setTimeout(function(){
                        YAHOO.bungeni.config.dialogs.notification.hide();
                    }, 1000
                );
            },
            hide: function(){
                this.dialog.hide();
            }
        }
        var confirm = {
            init: function(){
                var buttons = [
                    {
                        text: SGlobals.delete_dialog_confirm,
                        handler: function(){
                            if(this._parent.confirm_callback){
                                this._parent.confirm_callback();
                                this._parent.confirm_callback = null;
                            }
                            this.hide();
                        }
                    },
                    {
                        text: SGlobals.delete_dialog_cancel,
                        handler: function(){ 
                            this._parent.confirm_callback = null;
                            this.hide(); 
                        },
                        default: true
                    },
                ];
                this.dialog = new YAHOO.widget.SimpleDialog(
                    "scheduling-confirm", dialog_config.default
                );
                this.dialog._parent = this;
                this.dialog.setHeader(SGlobals.confirm_dialog_title);
                this.dialog.setBody("");
                this.dialog.cfg.queueProperty("width", "200px");
                this.dialog.cfg.queueProperty("buttons", buttons);
                this.dialog.render(document.body);
            },
            show: function(message, confirm_callback){
                if(!this.dialog){
                    this.init();
                }
                this.confirm_callback = confirm_callback;
                this.dialog.setBody(message);
                this.dialog.show();
                this.dialog.bringToTop();
            },
            hide: function(){
                this.confirm_callback = null;
                this.dialog.hide();
            }
        }
        var textrecords = {
            init: function(){
                var buttons = [
                    {
                        text: SGlobals.text_dialog_done_action,
                        handler: function(){
                            if(YAHOO.bungeni.getScheduleTable){
                                sDt = YAHOO.bungeni.getScheduleTable();
                            }else{
                                sDt = YAHOO.bungeni.scheduling.getScheduleTable();
                            }
                            Columns = YAHOO.bungeni.config.scheduling.columns;
                            var tabs = this.tab_view;
                            var activeTab = tabs.getTab(tabs.get("activeIndex"));
                            var recordData = activeTab.getRecordValue();
                            var total_recs = sDt.getRecordSet().getLength();
                            var selected = sDt.getSelectedRows();
                            var sel_record = sDt.getRecord(selected[0]);
                            var sel_data = sel_record.getData();
                            var new_index = 0;
                            if(selected.length){
                                new_index = (sDt.getRecordIndex(sel_record)+1);
                            }
                            if(recordData.value.length){
                                if(recordData.type == SGlobals.types.MINUTE){
                                    YAHOO.bungeni.agendaconfig.minutesCache.add(
                                        sel_data[Columns.OBJECT_ID],
                                        { body_text: recordData.value[0] }
                                    );
                                    sDt.updateRow((new_index-1), sel_data);
                                }else{
                                    var new_data_entries = new Array();
                                    for(idx=0; idx<(recordData.value.length); idx++){
                                        new_data_entries.push({
                                            item_title: recordData.value[idx],
                                            item_type: recordData.type
                                        });
                                    }
                                    sDt.addRows(new_data_entries, new_index);
                                    var refresh_columns = [
                                        sDt.getColumn(Columns.MOVE_UP),
                                        sDt.getColumn(Columns.MOVE_DOWN),
                                    ]
                                    if(new_index > 0){
                                        var updated_record = sDt.getRecord(
                                            (new_index - 1)
                                        );
                                        var record_data = updated_record.getData();
                                        for (idx=0; idx<=(refresh_columns.length); idx++){
                                            sDt.updateCell(
                                                updated_record, 
                                                refresh_columns[idx],
                                                record_data
                                            );
                                        }
                                    }
                                }
                                this.hide();
                            }else{
                                this.hide();
                            }
                        }
                    },
                    {
                        text: SGlobals.text_dialog_cancel_action,
                        handler: function(){ 
                            this.hide();
                        },
                        default: true
                    },
                ];
                this.dialog = new YAHOO.widget.SimpleDialog(
                    "text-records-dialog", dialog_config.default
                );
                this.dialog._parent = this;
                this.dialog.setHeader(SGlobals.text_records_title);
                this.dialog.setBody("");
                this.dialog.cfg.queueProperty("width", "500px");
                this.dialog.cfg.queueProperty("buttons", buttons);
                this.dialog.renderEvent.subscribe(
                    YAHOO.bungeni.availableitems.handlers.renderTextRecordsTabs
                );
                this.dialog.render(document.body);
            },
            show: function(tab_id){
                this.tab_id = tab_id || null;
                if(!this.dialog){
                    this.init();
                }
                if ((this.dialog.tab_view!=undefined) && tab_id){
                    this.dialog.selectTab(tab_id);
                }
                this.dialog.show();
                this.dialog.bringToTop();
            },
            hide: function(){
                this.confirm_callback = null;
                this.dialog.hide();
            }
        }
        return {
            config: dialog_config,
            blocking: blocking,
            confirm: confirm,
            notification: notification,
            textrecords: textrecords
        }
    }();
    
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
                 if(rec_data.item_type == SGlobals.types.HEADING){
                     el.innerHTML = (
                        "<span style='text-align:center;display:block;'><strong>" + 
                        rec_data.item_title + "</strong></span>"
                    );
                 }else if(rec_data.item_type == SGlobals.types.EDITORIAL_NOTE){
                     el.innerHTML = BungeniUtils.wrapText(rec_data.item_title);
                 }else{
                     if (rec_data.item_uri){
                        el.innerHTML = (rec_data.item_title + 
                            "<em style='display:block;'><span>" +
                            SGlobals.text_moved_by + " : " + 
                            rec_data.item_mover + "</span>&nbsp;&nbsp;" +
                            "<a href='" + rec_data.item_uri + "' target='blank'>" + 
                            SGlobals.text_action_view + "</a>"
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
              * @method itemTitleMinutesFormatter
              * @method render item title and minutes where applicable
              */
              var itemTitleMinutesFormatter = function(el, record, column, data){
                  var data = record.getData();
                  var record_index = this.getRecordIndex(record);
                  if (SGlobals.discussable_types.indexOf(
                        data[Columns.TYPE]
                    )<0
                  ){
                      el.innerHTML = data[Columns.TITLE];
                  } else {
                      var cHTML = "";
                      if(el.innerHTML){
                          tElem = Y$.query("em", el)[0];
                          cHTML = BungeniUtils.wrapText(tElem.innerHTML);
                      }else{
                          cHTML = BungeniUtils.wrapText(data[Columns.TITLE]);
                      }
                      cHTML = cHTML + BungeniUtils.wrapText(
                        SGlobals.minutes_header, "span", "class='minutes-header'"
                      );
                      var mAttrs = "class='minute-record'";
                      var eAttrs = "class='minute-record-error'";
                      var obj_id = data[Columns.OBJECT_ID];
                      if (obj_id!=undefined){
                          var ds_id = obj_id;
                          var attrs = "id='"+ ds_id +"' " + mAttrs;
                          cHTML = cHTML + BungeniUtils.wrapText(
                            BungeniUtils.wrapText(SGlobals.minutes_loading,
                                "span", attrs
                            ), "div"
                          );
                          Event.onAvailable(ds_id, function(){
                            var minutesContainer = this;
                            var ds_url = ("./items/" + 
                                data[Columns.OBJECT_ID] +
                                SGlobals.discussion_items_json_url
                            );
                            var oDs = YAHOO.util.DataSource(ds_url);
                            oDs.responseType = YAHOO.util.DataSource.TYPE_JSON;
                            oDs.responseSchema = {
                                resultsList: "nodes",
                                fields: [ Columns.OBJECT_ID, Columns.BODY_TEXT ]
                            }
                            var render_minutes = function(items){
                                var nHTML = "";
                                if(items.length){
                                    for (idx=0; idx<items.length; idx++){
                                        mdata = items[idx];
                                        idAttr = "rel='rec-"+ idx +"'";
                                        edId = "minute-edit_" + record_index + "-" + idx;
                                        var editAttrs = (
                                            "class='edit-minute-control' " + 
                                            "id='" + edId + "'"
                                        );
                                        nHTML = nHTML + BungeniUtils.wrapText(
                                            (mdata[Columns.BODY_TEXT] +
                                                BungeniUtils.wrapText(
                                                    "&nbsp;",
                                                    "span", editAttrs
                                                )
                                            ), 
                                            "span", mAttrs + " " + idAttr
                                        );
                                        Event.addListener(edId, "click",
                                            YAHOO.bungeni.agendaconfig.handlers.editMinute
                                        );
                                    }
                                }else{
                                    nHTML = nHTML + BungeniUtils.wrapText(
                                        SGlobals.minutes_no_records,
                                        "span", eAttrs
                                    );
                                }
                                minutesContainer.innerHTML = nHTML;
                            }
                            callback = {
                                success: function(request, response, payload){
                                    var nHTML = "";
                                    YAHOO.bungeni.agendaconfig.minutesCache.set(
                                        ds_id, response.results
                                    );
                                    render_minutes(response.results);
                                },
                                failure: function(req, resp, payload){
                                    nHTML = oHTML + BungeniUtils.wrapText(
                                        SGlobals.minutes_loading_error,
                                        "span", eAttrs
                                    );
                                    el.innerHTML = nHTML;
                                },
                            }
                            var cached_items = YAHOO.bungeni.agendaconfig.minutesCache.get(ds_id);
                            if(cached_items){
                                render_minutes(cached_items);
                            }else{
                                oDs.sendRequest(null, callback, this);
                            }

                          });
                      }else{
                          cHTML = cHTML + BungeniUtils.wrapText(
                            BungeniUtils.wrapText(
                                SGlobals.minutes_unsaved_agenda
                            ), "span", mAttrs
                          );
                      }
                      el.innerHTML = cHTML;
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
                    SGlobals.column_discussion_text_missing
                );
                el.innerHTML = BungeniUtils.wrapText(text);
            }

            var editButtonFormatter = function(el, record, column, data){
                if (!el.innerHTML){
                    var button = new YAHOO.widget.Button({
                        label: SGlobals.column_discussion_edit_button,
                        id: el.id + "-edit-button"
                    });
                    button.appendTo(el);
                }
            }

            var deleteButtonFormatter = function(el, record, column, data){
                if (!el.innerHTML){
                    var button = new YAHOO.widget.Button({
                        label: SGlobals.column_discussion_delete_button,
                        id: el.id + "-delete-button"
                    });
                    button.appendTo(el);
                }
            }
            
            var linkFormatter = function(el, oRecord, oColumn, oData, oDataTable) {
                if(lang.isString(oData) && (oData > "")) {
                    el.innerHTML = ("<a href=\"" + oData + 
                        "\" target=\"blank\"\">" + 
                        SGlobals.text_action_view + "</a>"
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

            /**
             * @method workflowActionsFormatter
             * @description render workflow actions available for current
             * item
             */
             var workflowActionsFormatter = function(el, record, column, data){
                 var index = this.getTrIndex(record);
                 var rec_data = record.getData();
                 if (rec_data[Columns.WORKFLOW_STATE]==undefined){
                     el.innerHTML = "";
                     return;
                 }
                 var actions = rec_data[Columns.WORKFLOW_ACTIONS];
                 var state_title = rec_data[Columns.WORKFLOW_STATE];
                 if(actions.length){
                    el.innerHTML = "";
                    var wfActionButton = new YAHOO.widget.Button(
                        {
                            type: "menu",
                            label: BungeniUtils.wrapText(state_title),
                            id: "wf_action_" + index,
                            name: "wf_action_" + index,
                            menu: actions,
                            container: el,
                        }
                    );
                    wfActionButton.on("selectedMenuItemChange", function(args){
                            var menuValue = args.newValue;
                            this.set("label", BungeniUtils.wrapText(
                                args.newValue.cfg.getProperty("text")
                            ));
                        }
                    );
                    //!+HACK(add get wf value property to record)
                    if (!record.getWFStatus){
                        record.getWFStatus = function(){
                            var active = wfActionButton.getMenu().activeItem;
                            return active?active.value:null;
                        }
                    }
                 }else{
                     el.innerHTML = BungeniUtils.wrapText(state_title);
                 }
             }


            /**
             * @method addTextRecordFormatter
             * @description renders button to add text records to schedule
             */
            var addTextRecordFormatter = function(el, record, column, data){
                if (SGlobals.discussable_types.indexOf(
                        record.getData()[Columns.TYPE]
                    )<0
                ){
                    if(el.innerHTML){
                        el.innerHTML="";
                    }
                    return;
                }
                if (!el.innerHTML){
                    var menu = [
                        {
                            text: SGlobals.heading_button_text,
                            value: SGlobals.types.HEADING
                        },
                        {
                            text: SGlobals.text_button_text,
                            value: SGlobals.types.EDITORIAL_NOTE
                        },
                    ]
                    if(YAHOO.bungeni.agendaconfig.minuteEditor!=undefined){
                        menu.push(
                            {
                                text: SGlobals.minute_button_text,
                                value: SGlobals.types.MINUTE
                            }
                        );
                    }

                    var button = new YAHOO.widget.Button({
                        type: "menu",
                        label: "+",
                        id: el.id + "-add-text-record-button",
                        menu: menu
                    });
                    var clickHandler = function(type, args){
                        menuItem = args[1];
                        if (menuItem){
                            YAHOO.bungeni.config.dialogs.textrecords.show(
                                menuItem.value
                            );
                        }
                    }
                    button.getMenu().subscribe("click", clickHandler);
                    button.appendTo(el);
                }
            }

            return {
                title: itemTitleFormatter,
                title_with_minutes: itemTitleMinutesFormatter,
                type: itemTypeFormatter,
                moveUp: itemMoveUpFormatter,
                moveDown: itemMoveDownFormatter,
                counter: countFormatter,
                longText: longTextFormatter,
                editButton: editButtonFormatter,
                deleteButton: deleteButtonFormatter,
                link: linkFormatter,
                availableItemSelect: availableItemSelectFormatter,
                workflowActions: workflowActionsFormatter,
                addTextRecord: addTextRecordFormatter
            }
        }(),
        handlers: function(){
            /**
             * @method _renderRTECellEditor
             * @description initialize textarea cell editor with an RTE editor on
             * initial display, then unbind this method when the RTE is rendered for 
             * the current editor instance.
             * 
             * This also overrides the getInputValue method to get the RTE value and
             * the cell editor show event to populate the shared editor with the
             * context record value.
             **/
             var _renderRTECellEditor = function(args){
                rteCellEditor = new YAHOO.widget.Editor(args.editor.textarea,
                    { width: "400px", autoHeight: true }
                );
                rteCellEditor.render();
                args.editor.getInputValue = function(){
                    value = rteCellEditor.cleanHTML(rteCellEditor.getEditorHTML());
                    rteCellEditor.setEditorHTML("");
                    return value
                }
                args.editor.unsubscribe("showEvent", _renderRTECellEditor);
                args.editor.subscribe("showEvent", function(args){
                    rteCellEditor.setEditorHTML(args.editor.textarea.value);
                });
             }
             
            /**
             * @method _showCellEditor
             * @description displays an editor to modify text records on the schedule
             */
            var _showCellEditor = function(args){
                var column = this.getColumn(args.target);
                if (column.field != scheduling_columns.TITLE){
                    return;
                }
                var record = this.getRecord(args.target);
                if (SGlobals.editable_types.indexOf(record.getData().item_type)>=0){
                    this.onEventShowCellEditor(args);
                }
            }
             
             /**
              * @method _addTextRecord
              * @description reusable add text records handler
              */
              var _addTextRecord = function(args){
                  var column = this.getColumn(args.target);
                  if (column.field != scheduling_columns.ADD_TEXT_RECORD){
                      return;
                  }
                  YAHOO.bungeni.config.dialogs.textrecords.show();
              }
             
             /**
              * @method _moveRecord
              * @description swap datatable rows
              **/
            var _moveRecord = function(args){
                var MOVE_COLUMNS = scheduling_columns.move_columns;
                var target_column = this.getColumn(args.target);
                if (MOVE_COLUMNS.indexOf(target_column.field)<0){
                   return;
                }
                var target_record = this.getRecord(args.target);
                var target_index = this.getTrIndex(target_record);
                var record_count = this.getRecordSet().getLength();
                var swap_rows = [];
                if (target_column.field == scheduling_columns.MOVE_UP){
                    if (target_index!=0){
                        swap_rows = [target_index, (target_index - 1)]
                    }
                }else{
                    if (target_index != (record_count-1)){
                        swap_rows = [target_index, (target_index + 1)]
                    }
                }
                
                if (swap_rows.length == 2){
                    var data_0 = this.getRecord(swap_rows[0]).getData();
                    var data_1 = this.getRecord(swap_rows[1]).getData();
                    this.updateRow(swap_rows[0], data_1);
                    this.updateRow(swap_rows[1], data_0);
                    this.unselectAllRows();
                    this.selectRow(swap_rows[1]);
                }
            }
            
            /*
             * @method _attachContextMenu
             * @description context menu for each record
             **/
            var _attachContextMenu = function(args){
                var container = document.createElement("div");
                container.id = "dt-context-menu-container";
                document.body.appendChild(container);
                var menuClickHandler = function(type, args, dt){
                    var menuItem = args[1];
                    if (menuItem){
                        var target = this.contextEventTarget;
                        var row = dt.getTrEl(target);
                        var _delete_callback = function(){
                            dt.deleteRow(row);
                        }
                        if(row){
                            switch(menuItem.index){
                                case 0: 
                                YAHOO.bungeni.config.dialogs.confirm.show(
                                    SGlobals.delete_dialog_text,
                                    _delete_callback
                                )
                            }
                        } 
                    }
                }
                var contextMenu = new YAHOO.widget.ContextMenu(
                    "dt-context-menu", { trigger:this.getTbodyEl() }
                );
                contextMenu.addItem(SGlobals.remove_button_text);
                contextMenu.render(container);
                contextMenu.clickEvent.subscribe(menuClickHandler, this);
                this.unsubscribe("initEvent",
                    YAHOO.bungeni.config.scheduling.handlers.attachContextMenu
                );
            }
             
             return {
                 renderRTECellEditor: _renderRTECellEditor,
                 showCellEditor: _showCellEditor,
                 moveRecord: _moveRecord,
                 addTextRecord: _addTextRecord,
                 attachContextMenu: _attachContextMenu
             }
        }(),
    }
    return {
        schemas: _schemas,
        scheduling: scheduling_configs,
        selectors: element_selectors,
        dialogs: dialogs
    }
}();
