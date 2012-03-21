/**
 * This module renders UI components that hadle editing of minutes.
**/
var MODE_ADD = "MODE_ADD";
var MODE_EDIT = "MODE_EDIT";

YAHOO.bungeni.scheduling = function(){
    var Event = YAHOO.util.Event;
    var YJSON = YAHOO.lang.JSON;
    var YCM = YAHOO.util.Connect;
    var SGlobals = scheduler_globals;
    var BungeniUtils = YAHOO.bungeni.Utils;
    var Columns = YAHOO.bungeni.config.scheduling.columns;
    var MOVE_COLUMNS = YAHOO.bungeni.config.scheduling.columns.move_columns;
    var DialogConfig = YAHOO.bungeni.config.dialogs.config;
    var Dialogs = YAHOO.bungeni.config.dialogs;
    var Formatters = YAHOO.bungeni.config.scheduling.formatters;
    var Handlers = YAHOO.bungeni.config.scheduling.handlers;
    YAHOO.bungeni.unsavedChanges = false;
    var OP_SAVE_MINUTES = "OP_SAVE_MINUTES";

    var minuteEditor = function(){
        init = function(){
           this.dialog = new YAHOO.widget.SimpleDialog("minute-editor",
                DialogConfig.default
            );
            this.dialog._parent = this
            var dialogButtons = [
                {
                    text: SGlobals.save_discussion_button_text,
                    handler: function(){
                        var text = this._parent.getText();
                        var row_index = this._parent.row;
                        var minute_index = this._parent.minute;
                        var sDt = YAHOO.bungeni.scheduling.getScheduleTable();
                        if (text){
                            var record = sDt.getRecord(row_index);
                            var row_data = record.getData();
                            var cache_key = row_data[Columns.OBJECT_ID];
                            var cdata = YAHOO.bungeni.scheduling.minutesCache.get(
                                cache_key
                            );
                            cdata[minute_index][Columns.BODY_TEXT] = text;
                            YAHOO.bungeni.scheduling.minutesCache.set(cache_key,
                                cdata
                            );
                            sDt.updateRow(row_index, row_data);
                            this.hide();
                        }
                    }
                },
                {
                    text: SGlobals.text_dialog_cancel_action,
                    handler: function(){ this.hide(); }
                },
            ]
            this.dialog.cfg.queueProperty("width", "500px");
            this.dialog.cfg.queueProperty("height", "400px");
            this.dialog.cfg.queueProperty("buttons", dialogButtons);
            this.dialog.setBody("<div><textarea name='minutestext' id='minutestext'></textarea></div>");
            this.dialog.setHeader(SGlobals.schedule_discussions_title);
            this.dialog.render(document.body);
            Event.onAvailable("minutestext", function(e){
                var editor = new YAHOO.widget.Editor("minutestext",
                    { width:"100%", height:"150px" , autoHeight:false }
                );
                editor.render();
                YAHOO.bungeni.scheduling.minuteEditor.getText = function(){
                    return editor.cleanHTML(editor.getEditorHTML())
                }
                YAHOO.bungeni.scheduling.minuteEditor.setText = function(row, minute){
                    var sDt = YAHOO.bungeni.scheduling.getScheduleTable();
                    var record = sDt.getRecord(row);
                    var row_data = record.getData();
                    var cdata = YAHOO.bungeni.scheduling.minutesCache.get(
                        row_data[Columns.OBJECT_ID]
                    );
                    editor.setEditorHTML(cdata[minute][Columns.BODY_TEXT]);
                }
            });
        }
        render = function(row, minute){
            this.row = Number(row);
            this.minute = Number(minute);
            if (!this.dialog){
                this.init();
            }else{
                this.dialog.show();
                this.dialog.bringToTop();
                this.setText(this.row, this.minute);
            }
        }


        var RequestObject = {
            handleSuccess: function(o){
                var sDt = YAHOO.bungeni.scheduling.getScheduleTable();
                sDt.refresh();
                Dialogs.blocking.hide();
                YAHOO.bungeni.unsavedChanges = false;
                if(this.post_op==OP_SAVE_MINUTES){
                    for(idx=0;idx<(sDt.getRecordSet().getLength());idx++){
                        YAHOO.bungeni.scheduling.handlers.saveMinutes(idx);
                    }
                }
            },
            handleFailure: function(o){
                Dialogs.blocking.hide();
                Dialogs.notification.show(
                    SGlobals.saving_dialog_exception
                );
            },
            startRequest: function(url, data, message, post_op){
                this.post_op = post_op;
                if(window.event){
                    Event.stopEvent(window.event);
                }
                Dialogs.blocking.show(message);
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

        var customSelectRow = function(args){
            var target_column = this.getColumn(args.target);
            if (MOVE_COLUMNS.indexOf(target_column.field)>=0){
                return;
            }
            this.unselectAllRows();
            this.selectRow(this.getRecord(args.target));
        }
        
        var editMinute  = function(args){
            var indices = this.id.split("_")[1].split("-");
            var row = indices[0];
            var minute = indices[1];
            YAHOO.bungeni.scheduling.minuteEditor.render(row, minute); 
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
                Dialogs.confirm.show(
                    SGlobals.confirm_message_delete_discussion,
                    delete_callback
                );
            }
        }

        var saveMinutes = function(row){
            var sDt = YAHOO.bungeni.scheduling.getScheduleTable();
            var sRecord = sDt.getRecord(row);
            var sData = sRecord.getData();
            if(SGlobals.discussable_types.indexOf(sData[Columns.TYPE])<0){
                return;
            }
            var cKey = sData[Columns.OBJECT_ID];
            if (cKey){
                var mcache = YAHOO.bungeni.scheduling.minutesCache.get(cKey);
                if (mcache.length){
                    var item_data = new Array();
                    for (index in mcache){
                        var minute_data = mcache[index];
                        var save_data = {
                            object_id: minute_data[Columns.OBJECT_ID],
                            body_text: minute_data[Columns.BODY_TEXT],
                        }
                        item_data.push(save_data);
                    }
                    var post_data = "data=" + YJSON.stringify(item_data);
                    var save_url = ("./items/" + cKey + 
                        SGlobals.discussions_save_url
                    );
                    YAHOO.bungeni.scheduling.minuteEditor.SaveRequest.startRequest(
                        save_url, post_data, SGlobals.saving_discussions_text
                    );
                }
            }
        }

        var renderScheduleControls = function(args){
            var container = YAHOO.bungeni.scheduling.Layout.layout.getUnitByPosition("bottom").body;
            var save_button = new YAHOO.widget.Button({
                label: SGlobals.save_button_text,
                container: container
            });
            save_button.on("click", function(){
                YAHOO.bungeni.scheduling.handlers.saveSchedule();
            });
            this.unsubscribe("initEvent", renderScheduleControls);
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
                    item_data.push(save_data);
                }
                var post_data = "data=" + YJSON.stringify(item_data);
                YAHOO.bungeni.scheduling.minuteEditor.SaveRequest.startRequest(
                    SGlobals.save_schedule_url, 
                    post_data,
                    SGlobals.saving_schedule_text,
                    OP_SAVE_MINUTES
                );
            }else{
                Dialogs.notification.show(
                    SGlobals.save_dialog_empty_message
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
            customSelectRow: customSelectRow,
            editMinute: editMinute,
            deleteDiscussion: deleteDiscussion,
            saveMinutes: saveMinutes,
            renderScheduleControls: renderScheduleControls,
            saveSchedule: saveSchedule,
            populateScheduledKeys: populateScheduledKeys,
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
                            SGlobals.schedule_discussions_title, "h2"
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
                var editor = new YAHOO.widget.TextareaCellEditor();
                editor.subscribe("showEvent", Handlers.renderRTECellEditor);
                var columns = [
                    {
                        key: Columns.ADD_TEXT_RECORD, 
                        label: "",
                        formatter: Formatters.addTextRecord,
                    },
                    {
                        key: Columns.TYPE, 
                        label: SGlobals.column_type,
                        formatter: Formatters.type,
                    },
                    {
                        key: Columns.TITLE, 
                        label: SGlobals.column_title,
                        editor:editor,
                        width: 150,
                        formatter: Formatters.title_with_minutes
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
                    /*{
                        key: Columns.DISCUSSION_EDIT,
                        label: "",
                        formatter: Formatters.editDiscussions
                    },*/
                    {
                        key: Columns.WORKFLOW_ACTIONS,
                        label: "",
                        formatter: Formatters.workflowActions
                    }
                ];
                var dataSource = new YAHOO.util.DataSource(
                    SGlobals.json_listing_url_meta
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
                        width:"100%",
                        height:"450px",
                    }
                );
                dataTable.subscribe("rowMouseoverEvent", 
                    dataTable.onEventHighlightRow
                );
                dataTable.subscribe("rowMouseoutEvent", 
                    dataTable.onEventUnhighlightRow
                );
                dataTable.subscribe("cellDblclickEvent", Handlers.showCellEditor);
                dataTable.subscribe("cellClickEvent",
                    YAHOO.bungeni.scheduling.handlers.customSelectRow
                );
                dataTable.subscribe("cellClickEvent", Handlers.moveRecord);
                dataTable.subscribe("initEvent", function(){
                    YAHOO.bungeni.Events.scheduleAvailable.fire();
                });
                dataTable.subscribe("initEvent", 
                    YAHOO.bungeni.scheduling.handlers.renderScheduleControls
                );
                dataTable.subscribe("initEvent", 
                    YAHOO.bungeni.scheduling.minuteEditor.render
                );
                dataTable.subscribe("initEvent", Handlers.attachContextMenu);
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
    
    var minutesDSCache = function(){
        var _cache = {};

        var _get_cache = function(){
            return _cache;
        }

        var _get = function(key){
            return _cache[key] || undefined;
        }
        
        var _set = function(key, data){
            _cache[key] = data;
        }
        
        var _update = function(key, index, data){
            this.get(key)[index] = data;
        }
        
        var _add = function(key, data){
            if (this.get(key)==undefined){
                this.set(key, new Array());
            }
            this.get(key).push(data);
        }
        
        return {
            get_cache: _get_cache,
            get: _get,
            set: _set,
            update: _update,
            add: _add
        }
    }();
    
    return {
        handlers: handlers,
        Layout: Layout,
        minuteEditor: minuteEditor,
        getScheduleTable: getScheduleTable,
        minutesCache: minutesDSCache
    }
}();
