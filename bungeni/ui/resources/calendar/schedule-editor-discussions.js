/**
 * This module renders UI components that hadle editing of minutes.
**/
var MODE_ADD = "MODE_ADD";
var MODE_EDIT = "MODE_EDIT";

YAHOO.bungeni.scheduling = function(){
    var Event = YAHOO.util.Event;
    var YJSON = YAHOO.lang.JSON;
    var YCM = YAHOO.util.Connect;
    var BungeniUtils = YAHOO.bungeni.Utils;
    var Columns = YAHOO.bungeni.config.scheduling.columns;
    var DialogConfig = YAHOO.bungeni.config.dialogs;
    var Formatters = YAHOO.bungeni.config.scheduling.formatters;
    var MOVE_COLUMNS = [Columns.MOVE_UP, Columns.MOVE_DOWN];
    YAHOO.bungeni.unsavedChanges = false;
    YAHOO.bungeni.unsavedDiscussions = false;
    
    var dialogs = function(){
        var blocking = {
            init: function(){
                this.dialog = new YAHOO.widget.SimpleDialog(
                    "scheduling-blocking", DialogConfig.default
                );
                this.dialog.setHeader(scheduler_globals.saving_dialog_header);
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
                    "scheduling-notification", DialogConfig.default
                );
                this.dialog.setHeader(scheduler_globals.text_warning);
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
                        YAHOO.bungeni.scheduling.dialogs.notification.hide();
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
                        text: scheduler_globals.delete_dialog_confirm,
                        handler: function(){ 
                            this._parent.confirm_callback();
                            this._parent.confirm_callback = null;
                            this.hide();
                        }
                    },
                    {
                        text: scheduler_globals.delete_dialog_cancel,
                        handler: function(){ 
                            this._parent.confirm_callback = null;
                            this.hide(); 
                        },
                        default: true
                    },
                ];
                this.dialog = new YAHOO.widget.SimpleDialog(
                    "scheduling-confirm", DialogConfig.default
                );
                this.dialog._parent = this;
                this.dialog.setHeader(scheduler_globals.confirm_dialog_title);
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
        return {
            blocking: blocking,
            confirm: confirm,
            notification: notification
        }
    }();
    
    var discussionEditor = function(){
        init = function(){
           this.dialog = new YAHOO.widget.SimpleDialog("discussion-editor",
                DialogConfig.default
            );
            this.dialog._parent = this
            var dialogButtons = [
                {
                    text: scheduler_globals.save_discussion_button_text,
                    handler: function(){
                        var text = this._parent.getText();
                        var mode = this._parent.mode;
                        var cDt = this._parent.dataTable;
                        if (text){
                            if (mode == MODE_ADD){
                                var new_record = {};
                                new_record[Columns.BODY_TEXT] = text;
                                cDt.addRow(new_record);
                            }else{
                                var index = cDt.getSelectedRows()[0];
                                if(index){
                                    var record = cDt.getRecord(index);
                                    var data = record.getData();
                                    data[Columns.BODY_TEXT] = text;
                                    cDt.updateRow(index, data);
                                }
                            }
                            this.hide();
                        }
                    }
                },
                {
                    text: scheduler_globals.text_dialog_cancel_action,
                    handler: function(){ this.hide(); }
                },
            ]
            this.dialog.cfg.queueProperty("width", "500px");
            this.dialog.cfg.queueProperty("height", "400px");
            this.dialog.cfg.queueProperty("buttons", dialogButtons);
            this.dialog.setBody("<div><textarea name='discussiontext' id='discussiontext'></textarea></div>");
            this.dialog.setHeader(scheduler_globals.schedule_discussions_title);
            this.dialog.render(document.body);
            Event.onAvailable("discussiontext", function(e){
                var editor = new YAHOO.widget.Editor("discussiontext",
                    { width:"100%", height:"150px" ,autoHeight: false }
                );
                editor.render();
                YAHOO.bungeni.scheduling.discussionEditor.getText = function(){
                    return editor.cleanHTML(editor.getEditorHTML())
                }
                YAHOO.bungeni.scheduling.discussionEditor.setText = function(text){
                    editor.setEditorHTML(text);
                }
            });
        }
        render = function(dataTable, mode){
            this.dataTable = dataTable;
            this.mode = mode || MODE_ADD;
            this.mode
            if (!this.dialog){
                this.init();
            }
            this.dialog.show();
        }
        var RequestObject = {
            handleSuccess: function(o){
                YAHOO.bungeni.scheduling.getScheduleTable().refresh();
                YAHOO.bungeni.scheduling.dialogs.blocking.hide();
                YAHOO.bungeni.unsavedChanges = false;
            },
            handleFailure: function(o){
                YAHOO.bungeni.scheduling.dialogs.blocking.hide();
                YAHOO.bungeni.scheduling.dialogs.notification.show(
                    scheduler_globals.saving_dialog_exception
                );
            },
            startRequest: function(url, data, message){
                Event.stopEvent(window.event);
                YAHOO.bungeni.scheduling.dialogs.blocking.show(message);
                YCM.asyncRequest("POST", url, callback, data);
                    
            }
        }
        
        var callback = {
            success: RequestObject.handleSuccess,
            failure: RequestObject.handleFailure,
            scope: RequestObject
        }

        return {
            init: init,
            render: render,
            SaveRequest: RequestObject
        }
    }();
    
    var handlers = function(){
        var setUnsavedChanges = function(args){
            YAHOO.bungeni.unsavedChanges = true;
        }
        var setUnsavedDiscussions = function(args){
            YAHOO.bungeni.unsavedDiscussions = true;
        }
        var renderDiscussionsTable = function(){
            var dataTable = YAHOO.bungeni.schedule.oDt;
            var index = dataTable.getSelectedRows()[0];
            var oData = dataTable.getRecord(index).getData();
            if(oData.object_id == undefined){
                this.hide();
                YAHOO.bungeni.scheduling.dialogs.notification.show(
                    scheduler_globals.message_item_not_saved
                );
                return;
            }
            var discussions_url = ("./items/" + 
                oData.object_id + scheduler_globals.discussion_items_json_url
            );
                        
            //render discussions data table
            var dataSource = YAHOO.util.DataSource(discussions_url);
            dataSource.responseType = YAHOO.util.DataSource.TYPE_JSON;
            dataSource.responseSchema = {
                resultsList: "nodes",
                fields: [ Columns.OBJECT_ID, Columns.BODY_TEXT ]
            }
            var columns = [
                {
                    key: Columns.NUMBER,
                    label: "",
                    formatter: Formatters.counter
                },
                {
                    key: Columns.BODY_TEXT,
                    label: scheduler_globals.column_discussion_text,
                    formatter: Formatters.longText
                },
                {
                    key: Columns.DISCUSSION_EDIT,
                    label: "",
                    formatter: Formatters.editButton
                },
                {
                    key: Columns.DISCUSSION_DELETE,
                    label: "",
                    formatter: Formatters.deleteButton
                }
            ]
            var button_container = document.createElement("div");
            button_container.style.marginBottom = "1em";
            this.body.appendChild(button_container);
            var add_button = new YAHOO.widget.Button({
                label: scheduler_globals.add_discussion_button_text
            });
            add_button.appendTo(button_container);
            var container = document.createElement("div");
            this.body.appendChild(container);
            var dDt = new YAHOO.widget.DataTable(container, columns,
                dataSource,
                {
                    selectionMode: "single",
                    initialLoad: true
                }
            );
            dDt.subscribe("rowClickEvent", dDt.onEventSelectRow);
            dDt.subscribe("rowMouseoverEvent", dDt.onEventHighlightRow);
            dDt.subscribe("rowMouseoutEvent", dDt.onEventUnhighlightRow);
            dDt.subscribe("cellClickEvent", 
                YAHOO.bungeni.scheduling.handlers.editDiscussion
            );
            dDt.subscribe("cellClickEvent", 
                YAHOO.bungeni.scheduling.handlers.deleteDiscussion
            );
            dDt.subscribe("rowAddEvent",
                YAHOO.bungeni.scheduling.handlers.setUnsavedDiscussions
            );
            dDt.subscribe("rowDeleteEvent",
                YAHOO.bungeni.scheduling.handlers.setUnsavedDiscussions
            );
            dDt.subscribe("rowUpdateEvent",
                YAHOO.bungeni.scheduling.handlers.setUnsavedDiscussions
            );
            add_button.on("click", function(){
                YAHOO.bungeni.scheduling.discussionEditor.render(dDt);
                YAHOO.bungeni.scheduling.discussionEditor.setText("");
            });
            YAHOO.bungeni.schedule.getDiscussionsDataTable = function(){
                return dDt;
            }
        }
        var showDiscussions = function(args){
            var target_column = this.getColumn(args.target);
            if (target_column.field != Columns.DISCUSSION_EDIT){
                return;
            }
            var record = this.getRecord(args.target);
            if(scheduler_globals.discussable_types.indexOf(
                record.getData()[Columns.TYPE])<0
            ){
                return;
            }
            var target_row = this.getTrEl(record);
            //#!+SCHEDULING(mb, Feb-2012)
            //force selection of current row - temporary fix around event
            //race conditions - row select and cell click non-determinism
            this.unselectAllRows();
            this.selectRow(target_row);
            var dlg_id = "dlg-" + target_row.id;
            var dialog = new YAHOO.widget.SimpleDialog(dlg_id,
                DialogConfig.default
            );
            var dialogButtons = [
                {
                    text: scheduler_globals.save_button_text,
                    handler: YAHOO.bungeni.scheduling.handlers.saveDiscussions
                },
                {
                    text: scheduler_globals.text_dialog_cancel_action,
                    handler: function(){
                        if (YAHOO.bungeni.unsavedDiscussions){
                            var callback = function(){
                                dialog.hide();
                            }
                            YAHOO.bungeni.scheduling.dialogs.confirm.show(
                                scheduler_globals.text_unsaved_discussions,
                                callback
                            )
                        }else{
                            this.hide(); 
                        }
                    }
                },
            ]
            dialog.cfg.queueProperty("width", "500px");
            dialog.cfg.queueProperty("height", "400px");
            dialog.cfg.queueProperty("buttons", dialogButtons);
            dialog.setBody('');
            dialog.showEvent.subscribe(renderDiscussionsTable);
            dialog.setHeader(scheduler_globals.schedule_discussions_title);
            dialog.hideEvent.subscribe(function(){
                YAHOO.bungeni.unsavedDiscussions = false;
            });
            dialog.render(document.body);
            dialog.show();
            dialog.bringToTop();
        };
        
        var moveRecord = function(args){
            var target_column = this.getColumn(args.target);
            if (MOVE_COLUMNS.indexOf(target_column.field)<0){
               return;
            }
            var target_record = this.getRecord(args.target);
            var target_index = this.getTrIndex(target_record);
            var record_count = this.getRecordSet().getLength();
            var swap_rows = [];
            if (target_column.field == Columns.MOVE_UP){
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
        
        var customSelectRow = function(args){
            var target_column = this.getColumn(args.target);
            if (MOVE_COLUMNS.indexOf(target_column.field)>=0){
                return;
            }
            this.unselectAllRows();
            this.selectRow(this.getRecord(args.target));
        }
        
        var editDiscussion = function(args){
            var column = this.getColumn(args.target);
            if(column.field == Columns.DISCUSSION_EDIT){
                Event.stopEvent(args.event);
                YAHOO.bungeni.scheduling.discussionEditor.render(this, MODE_EDIT);
                YAHOO.bungeni.scheduling.discussionEditor.setText(
                    this.getRecord(args.target).getData()[Columns.BODY_TEXT] ||
                    ""
                );

            }
        }
        var deleteDiscussion = function(args){
            var column = this.getColumn(args.target);
            if(column.field == Columns.DISCUSSION_DELETE){
                var contextDt = this;
                var delete_callback = function(){
                    contextDt.deleteRow(
                        contextDt.getRecord(args.target)
                    );
                }
                YAHOO.bungeni.scheduling.dialogs.confirm.show(
                    scheduler_globals.confirm_message_delete_discussion,
                    delete_callback
                );
            }
        }
        var saveDiscussions = function(args){
            var dataTable = YAHOO.bungeni.schedule.getDiscussionsDataTable();
            var record_set = dataTable.getRecordSet();
            var records = record_set.getRecords();
            if (record_set.getLength()){
                var item_data = new Array();
                for (index in records){
                    var record_data = records[index].getData();
                    var save_data = {
                        object_id: record_data.object_id,
                        body_text: record_data.body_text,
                    }
                    item_data.push(save_data);
                }
                var post_data = "data=" + YJSON.stringify(item_data);
                var scheduled_item_id = YAHOO.bungeni.schedule.oDt.getRecord(
                    YAHOO.bungeni.schedule.oDt.getSelectedRows()[0]
                ).getData()[Columns.OBJECT_ID];
                var save_url = ("./items/" + scheduled_item_id + 
                    scheduler_globals.discussions_save_url
                );
                YAHOO.bungeni.scheduling.discussionEditor.SaveRequest.startRequest(save_url, 
                    post_data, scheduler_globals.saving_discussions_text
                );
            }
        }
        var renderScheduleControls = function(args){
            var container = YAHOO.bungeni.scheduling.Layout.layout.getUnitByPosition("bottom").body;
            var save_button = new YAHOO.widget.Button({
                label: scheduler_globals.save_button_text,
                container: container
            });
            save_button.on("click", function(){
                YAHOO.bungeni.scheduling.handlers.saveSchedule();
            });
        }
        var saveSchedule = function(args){
            var itemsDataTable = YAHOO.bungeni.schedule.oDt;
            var record_set = itemsDataTable.getRecordSet();
            var records = record_set.getRecords();
            if (record_set.getLength()){
                var item_data = new Array();
                for (index in records){
                    var record = records[index];
                    var record_data = record.getData();
                    var save_data = {
                        item_type: record_data.item_type,
                        item_id: record_data.item_id,
                        schedule_id: record_data.object_id,
                        item_text: record_data.item_title,
                        wf_status: record.getWFStatus?record.getWFStatus():null
                    }
                    item_data.push(YJSON.stringify(save_data));
                }
                var post_data = "data=" + YJSON.stringify(item_data);
                YAHOO.bungeni.scheduling.discussionEditor.SaveRequest.startRequest(
                    scheduler_globals.save_schedule_url, 
                    post_data,
                    scheduler_globals.saving_schedule_text
                );
            }else{
                YAHOO.bungeni.scheduling.dialogs.notification.show(
                    scheduler_globals.save_dialog_empty_message
                );
            }
        }

        var populateScheduledKeys = function(request, response, payload){
            YAHOO.bungeni.scheduled_item_keys = new Array();
            for(idx in response.results){
                var record = response.results[idx];
                YAHOO.bungeni.scheduled_item_keys.push(
                    record.item_id + ":" + record.item_type
                );
            }
            return true;
        }

        return {
            setUnsavedChanges: setUnsavedChanges,
            setUnsavedDiscussions: setUnsavedDiscussions,
            showDiscussions: showDiscussions,
            moveRecord: moveRecord,
            customSelectRow: customSelectRow,
            editDiscussion: editDiscussion,
            deleteDiscussion: deleteDiscussion,
            saveDiscussions: saveDiscussions,
            renderScheduleControls: renderScheduleControls,
            saveSchedule: saveSchedule,
            populateScheduledKeys: populateScheduledKeys
        }
    }();
    var Layout = { layout:null }
    Event.onDOMReady(function(){
        var layout = new YAHOO.widget.Layout(
            "scheduler-layout",
            {
                height: 600,
                units: [
                    {
                        position:'top',
                        body: BungeniUtils.wrapText(
                            scheduler_globals.schedule_discussions_title, "h2"
                        ),
                        footer: '',
                        gutter: "2 2",
                        height: 42
                    },
                    {
                        position:'left',
                        body: '',
                        header: '',
                        width: "600",
                        gutter: "2 2",
                    },
                    {
                        position:'center',
                        body: '',
                        header: '',
                        gutter: "2 2",
                    },
                    {
                        position:'bottom',
                        body: '',
                        header: '',
                        gutter: "2 2",
                        height: 42
                    }
                ]
            }
        );
        layout.on("render", function(){
            YAHOO.bungeni.schedule = function(){
                var columns = [
                    {
                        key: Columns.TYPE, 
                        label: scheduler_globals.column_type,
                        formatter: Formatters.type,
                    },
                    {
                        key: Columns.TITLE, 
                        label: scheduler_globals.column_title,
                        width: 150
                    },
                    {
                        key: Columns.URI, 
                        label: "", 
                        formatter: Formatters.link
                    },
                    {
                        key: Columns.MOVE_UP, 
                        label: "", 
                        formatter: Formatters.moveUp
                    },
                    {
                        key: Columns.MOVE_DOWN, 
                        label: "", 
                        formatter: Formatters.moveDown
                    },
                    {
                        key: Columns.DISCUSSION_EDIT,
                        label: "",
                        formatter: Formatters.editDiscussions
                    },
                    {
                        key: Columns.WORKFLOW_ACTIONS,
                        label: "",
                        formatter: Formatters.workflowActions
                    }
                ];
                var dataSource = new YAHOO.util.DataSource(
                    scheduler_globals.json_listing_url_meta
                );
                dataSource.responseType = YAHOO.util.DataSource.TYPE_JSON;
                dataSource.responseSchema = {
                    resultsList: "nodes",
                    fields: [
                        Columns.ID, 
                        Columns.TITLE, 
                        Columns.TYPE, 
                        Columns.OBJECT_ID, 
                        Columns.MOVER,
                        Columns.URI,
                        Columns.WORKFLOW_STATE,
                        Columns.WORKFLOW_ACTIONS
                    ],
                };
                var tableContainer = document.createElement("div");
                layout.getUnitByPosition("left").body.appendChild(tableContainer);
                var dataTable = new YAHOO.widget.DataTable(
                    tableContainer,
                    columns, dataSource,
                    {
                        caption: "hold down CONTROL key to select multiple items",
                        summary: "hold down CONTROL key to select multiple items",
                        selectionMode:"single",
                        scrollable:true,
                        width:"100%"
                    }
                );
                dataTable.subscribe("rowMouseoverEvent", 
                    dataTable.onEventHighlightRow
                );
                dataTable.subscribe("rowMouseoutEvent", 
                    dataTable.onEventUnhighlightRow
                );
                dataTable.subscribe("cellClickEvent",
                    YAHOO.bungeni.scheduling.handlers.customSelectRow
                );
                dataTable.subscribe("cellClickEvent",
                    YAHOO.bungeni.scheduling.handlers.showDiscussions
                );
                dataTable.subscribe("cellClickEvent",
                    YAHOO.bungeni.scheduling.handlers.moveRecord
                );
                dataTable.subscribe("initEvent", function(){
                    YAHOO.bungeni.Events.scheduleAvailable.fire();
                });
                dataTable.subscribe("initEvent", 
                    YAHOO.bungeni.scheduling.handlers.renderScheduleControls
                );
                dataTable.doBeforeLoadData  = YAHOO.bungeni.scheduling.handlers.populateScheduledKeys;
                dataTable.subscribe("rowAddEvent", 
                    YAHOO.bungeni.scheduling.handlers.setUnsavedChanges
                );
                dataTable.subscribe("rowDeleteEvent", 
                    YAHOO.bungeni.scheduling.handlers.setUnsavedChanges
                );
                dataTable.subscribe("rowUpdateEvent", 
                    YAHOO.bungeni.scheduling.handlers.setUnsavedChanges
                );
                
                return {
                    oDs: dataSource,
                    oDt: dataTable
                }
            }();
        });
        Layout.layout = layout
        layout.render();
    });
    var getScheduleTable = function(){
        return YAHOO.bungeni.schedule.oDt;
    }
    return {
        handlers: handlers,
        Layout: Layout,
        discussionEditor: discussionEditor,
        dialogs: dialogs,
        getScheduleTable: getScheduleTable
    }
}();
