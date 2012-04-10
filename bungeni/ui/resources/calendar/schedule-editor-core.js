/**
 * This module renders UI components that hadle editing of minutes.
**/

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
    var AgendaConfig = YAHOO.bungeni.agendaconfig;
    YAHOO.bungeni.unsavedChanges = false;
    YAHOO.bungeni.reloadView = false;
    YAHOO.bungeni.scheduled_item_keys = new Array();

    var RequestObject = {
        handleSuccess: function(o){
            var sDt = YAHOO.bungeni.scheduling.getScheduleTable();
            YAHOO.bungeni.unsavedChanges = false;
            if(this.post_op){
                for(idx=0;idx<(sDt.getRecordSet().getLength());idx++){
                    YAHOO.bungeni.agendaconfig.handlers.saveMinutes(idx);
                }
                sDt.refresh();
            }else{
                //reload schedule to reflect workflow actions
                if (YAHOO.bungeni.reloadView){
                    window.location.reload();
                }else{
                    sDt.refresh();
                }
            }
            Dialogs.blocking.hide();
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
                YAHOO.bungeni.scheduling.SaveRequest.startRequest(
                    SGlobals.save_schedule_url, 
                    post_data,
                    SGlobals.saving_schedule_text,
                    (AgendaConfig.OP_SAVE_MINUTES)?true:false
                );
            }else{
                Dialogs.notification.show(
                    SGlobals.save_dialog_empty_message
                );
            }
        }

        var populateScheduledKeys = function(request, response, payload){
            YAHOO.bungeni.scheduled_item_keys = new Array();
            YAHOO.bungeni.reloadView = !Boolean(response.results.length);
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
                        position:'left',
                        header: AgendaConfig.TITLE_AGENDA,
                        body: '',
                        width: "600",
                        gutter: "2 2",
                        resize: true,
                        collapse: true,
                    },
                    {
                        position:'center',
                        header: AgendaConfig.TITLE_AVAILABLE_ITEMS,
                        body: '',
                        gutter: "2 2",
                        resize: true,
                        collapse: true,
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
                AgendaConfig.setEditor(editor);
                var columns = AgendaConfig.getColumns();
                var dataSource = new YAHOO.util.DataSource(
                    AgendaConfig.AGENDA_DATASOURCE_URL
                );
                dataSource.responseType = YAHOO.util.DataSource.TYPE_JSON;
                dataSource.responseSchema = AgendaConfig.AGENDA_SCHEMA;
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
                    YAHOO.bungeni.agendaconfig.afterDTRender
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
    
    return {
        SaveRequest: RequestObject,
        handlers: handlers,
        Layout: Layout,
        getScheduleTable: getScheduleTable,
    }
}();
