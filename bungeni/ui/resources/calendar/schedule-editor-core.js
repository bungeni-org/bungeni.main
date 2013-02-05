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
    var DialogConfig = YAHOO.bungeni.config.dialogs.config;
    var Dialogs = YAHOO.bungeni.config.dialogs;
    var Formatters = YAHOO.bungeni.config.scheduling.formatters;
    var Handlers = YAHOO.bungeni.config.scheduling.handlers;
    var AgendaConfig = YAHOO.bungeni.agendaconfig;
    YAHOO.bungeni.unsavedChanges = false;
    YAHOO.bungeni.reloadView = false;
    YAHOO.bungeni.saveAndPreview = false;
    YAHOO.bungeni.scheduled_item_keys = new Array();
    YAHOO.bungeni.processed_agenda_records = 0;

    var RequestObject = {
        handleSuccess: function(o){
            var sDt = YAHOO.bungeni.scheduling.getScheduleTable();
            var row_count = sDt.getRecordSet().getLength();
            YAHOO.bungeni.unsavedChanges = false;
            if((!this.post_op) && AgendaConfig.minuteEditor){
                YAHOO.bungeni.processed_agenda_records+=1;
                if (YAHOO.bungeni.processed_agenda_records==
                    YAHOO.bungeni.processed_minute_records
                ){
                    YAHOO.bungeni.reloadView=true;
                }
            }
            if(this.post_op){
                if(AgendaConfig.minutesCache.get_minutes_count()==0){
                    YAHOO.bungeni.reloadView = true;
                }
                else{
                    for(idx=0;idx<row_count;idx++){
                        YAHOO.bungeni.agendaconfig.handlers.saveMinutes(idx);
                    }
                }
            }
            //reload schedule reflect changes to workflow actions - if any
            if (YAHOO.bungeni.reloadView){
                Dialogs.blocking.show(SGlobals.saving_dialog_refreshing);
                if (YAHOO.bungeni.saveAndPreview == true) {
                    if (YAHOO.bungeni.refresh_location==undefined){
                        preview_flag = "preview=yes";
                        YAHOO.bungeni.refresh_location = window.location.href;
                        if (YAHOO.bungeni.refresh_location.indexOf(preview_flag)<0){
                            YAHOO.bungeni.refresh_location += ("?" + preview_flag);
                        }
                    }
                    setTimeout('window.location.replace(YAHOO.bungeni.refresh_location)', 200);
                } else {
                    setTimeout('window.location.replace(window.location.href)', 200);
                }
            }else{
                if(AgendaConfig.minuteEditor==undefined){
                    Dialogs.blocking.hide();
                    sDt.refresh();
                    if (YAHOO.bungeni.saveAndPreview == true) {
                        YAHOO.bungeni.scheduling.handlers.renderPreview();
                    }
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

    var handlers = function(){
        /**
         * @method setUnsavedChanges
         * @description Sets a flag to indicate unsaved changes.
         * Flag used to warn user of unsaved changes when navigating away from
         * scheduler page.
         **/
        var setUnsavedChanges = function(args){
            YAHOO.bungeni.unsavedChanges = true;
        }

        var checkAndDoScrolling = function(args) {
            YAHOO.bungeni.unsavedChanges = true;
            this.scrollTo(this.getRecordIndex(args.records[0]));
        }

        /**
         * @method customSelectRow
         * @description conditional selection of rows on agenda datatable
         **/
        var customSelectRow = function(args){
            var target_column = this.getColumn(args.target);
            this.unselectAllRows();
            this.selectRow(this.getRecord(args.target));
        }
        
        /**
         * @method renderSchedulerControls
         * @description Renders buttons at bottom of agenda datatable to 
         * perform global actions on the agenda
         **/
        var renderScheduleControls = function(args){
            var container = YAHOO.bungeni.scheduling.Layout.layout.getUnitByPosition("bottom").body;
            // add save button
            var save_button = new YAHOO.widget.Button({
                label: SGlobals.save_button_text,
                container: container
            });
            save_button.on("click", function(){
                YAHOO.bungeni.scheduling.handlers.saveSchedule({"preview":false});
            });
            // add save and preview button
            var preview_button = new YAHOO.widget.Button({
                label: SGlobals.save_and_preview_button_text,
                container: container
            });
            preview_button.on("click", function(){
                YAHOO.bungeni.scheduling.handlers.saveSchedule({"preview":true});
            });
            
            this.unsubscribe("initEvent", renderScheduleControls);
        }
        
        /**
         * @method addRowClass
         * @description adds a class to identify row headings
         **/
        var addRowClass = function(args){
            var sSize = YAHOO.bungeni.schedule.oDt.getRecordSet().getLength();
            for (index=0; index<sSize; index++){
                row_type = YAHOO.bungeni.schedule.oDt.getRecordSet()._records[index]._oData.item_type;
                YAHOO.bungeni.schedule.oDt.getTrEl(index).className += " row-"+row_type;
            }
            this.unsubscribe("initEvent", renderScheduleControls);
        }        

        /**
         * @method renderPreview
         * @description Launches a pop-out previewing the scheduled items
         **/
        var renderPreview = function(args) {
            var previewPanel = new YAHOO.widget.Panel("agenda-preview-dialog",
                { 
                    modal: true, 
                    visible: false, 
                    width: "800px", 
                    height: "auto", 
                    fixedcenter:false, 
                    constraintoviewport: false,
                    zindex: 2000,
                }
            );
            previewPanel.setHeader(SGlobals.preview_msg_header);
            YAHOO.bungeni.config.dialogs.blocking.show(SGlobals.preview_msg_generating);
            var success = function(o){
                YAHOO.bungeni.config.dialogs.blocking.hide();
                previewPanel.setBody(o.responseText);
                previewPanel.show();
                previewPanel.bringToTop();
            }
            var failure = function(o){
                YAHOO.bungeni.config.dialogs.blocking.hide();
                YAHOO.bungeni.config.dialogs.notification.show(SGlobals.preview_msg_error);
            }
            var callback = {
                success: success,
                failure: failure,
                argument: {}
            }
            var request = YAHOO.util.Connect.asyncRequest("GET", "./preview", callback);
            previewPanel.render(document.body);
        }
        
        /**
         * @method saveSchedule
         * @description Saves the agenda to bungeni remote database
         **/
        var saveSchedule = function(args){
            var itemsDataTable = YAHOO.bungeni.schedule.oDt;
            var record_set = itemsDataTable.getRecordSet();
            var records = record_set.getRecords();
            if (record_set.getLength()){
                var item_data = new Array();
                for (index in records){
                    var record = records[index];
                    var record_data = record.getData();
                    var save_data = {};
                    YAHOO.lang.augmentObject(save_data, record_data,
                        "item_type", "item_id", "object_id", "item_title"
                    );
                    save_data["item_text"] = save_data["item_title"]
                    save_data["schedule_id"] = save_data["object_id"];
                    save_data["wf_status"] = record.getWFStatus?record.getWFStatus():null;
                    delete save_data["item_title"];
                    delete save_data["object_id"];
                    item_data.push(save_data);
                }
                var post_data = "data=" + encodeURIComponent(
                    YJSON.stringify(item_data)
                );
                YAHOO.bungeni.scheduling.SaveRequest.startRequest(
                    SGlobals.save_schedule_url, 
                    post_data,
                    SGlobals.saving_schedule_text,
                    (AgendaConfig.OP_SAVE_MINUTES)?true:false
                );
                if (args.preview == true) {
                    YAHOO.bungeni.saveAndPreview = true;
                }
                else {
                    YAHOO.bungeni.saveAndPreview = false;
                }
            }else{
                Dialogs.notification.show(
                    SGlobals.save_dialog_empty_message
                );
            }
        }

        /**
         * @method populateScheduledKeys
         * @description Generates a cache of keys from items already on agenda
         **/
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


        /**
         * @method refreshCells
         * @description Re-renders cells whose markup should change when a new
         * item is added to the agenda.
         **/
        var refreshCells = function(index, next, deleted){
            var sDt = YAHOO.bungeni.scheduling.getScheduleTable();
            var sSize = sDt.getRecordSet().getLength();
            if(deleted){
                var update_index = (index==sSize)?(index-1):index;
            }else if(next){
                var update_index = index?(index+1):1;
            }else{
                var update_index = index?(index-1):0;
            }
            record = sDt.getRecord(update_index);
            if(record){
                window.setTimeout(function(){
                        sDt.updateCell(record, 
                            sDt.getColumn(Columns.ROW_CONTROLS)
                        );
                    }, 100
                );
            }
        }

        /**
         * @method refreshRows
         * @description Refreshes all rows on datatable to reflect cell changes.
         * This is a workaround around timing issues with addRow(s) events
         */
         var refreshRows = function(){
            var sDt = YAHOO.bungeni.scheduling.getScheduleTable();
            var sSize = sDt.getRecordSet().getLength();
            for (index=0; index<sSize; index++){
                sDt.updateRow(index, sDt.getRecord(index).getData());
            }
         }

        /**
         * @method refreshDeleted
         * @description Fire off cell refresh operation after row deletion
         **/
        var refreshDeleted = function(args){
            YAHOO.bungeni.scheduling.handlers.refreshCells(args.recordIndex, false, true);
        }

        return {
            setUnsavedChanges: setUnsavedChanges,
            checkAndDoScrolling: checkAndDoScrolling,
            customSelectRow: customSelectRow,
            renderScheduleControls: renderScheduleControls,
            addRowClass: addRowClass,
            renderPreview: renderPreview,
            saveSchedule: saveSchedule,
            populateScheduledKeys: populateScheduledKeys,
            refreshCells: refreshCells,
            refreshRows: refreshRows,
            refreshDeleted: refreshDeleted,
        }
    }();

    var DEFAULT_LAYOUT_CONFIG = [
        {
            position:'left',
            header: AgendaConfig.TITLE_AGENDA,
            body: '',
            width: "660",
            unit: "%",
            gutter: "2 2",
            resize: true,
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
    var containerUnit = (AgendaConfig.containerUnit || "left");
    var Layout = { layout:null }
    Event.onDOMReady(function(){
        if (window.location.href.indexOf('?preview=') !== -1) {
            YAHOO.bungeni.scheduling.handlers.renderPreview();
        }
            
        var layout = new YAHOO.widget.Layout(
            "scheduler-layout",
            {
                height: 600,
                units: (AgendaConfig.layoutConfig || DEFAULT_LAYOUT_CONFIG)
            }
        );
        layout.on("render", function(){
            YAHOO.bungeni.schedule = function(){
                var editor = new YAHOO.widget.TextareaCellEditor();
                var container = layout.getUnitByPosition(containerUnit);
                var init_width = container.body.clientWidth-15;
                editor.subscribe("showEvent", Handlers.renderRTECellEditor);
                AgendaConfig.setEditor(editor);
                var columns = AgendaConfig.getColumns(init_width);
                var dataSource = new YAHOO.util.DataSource(
                    AgendaConfig.AGENDA_DATASOURCE_URL
                );
                dataSource.responseType = YAHOO.util.DataSource.TYPE_JSON;
                dataSource.responseSchema = AgendaConfig.AGENDA_SCHEMA;
                var tableContainer = document.createElement("div");
                tableContainer.style.width = init_width + "px";
                container.body.appendChild(tableContainer);
                // YUI left pane width is set below
                var dataTable = new YAHOO.widget.DataTable(
                    tableContainer,
                    columns, dataSource,
                    {
                        selectionMode: "single",
                        scrollable: 'y',
                        width: "99.4%",
                        height: (container.body.clientHeight-30) + "px",
                        MSG_EMPTY: AgendaConfig.EMPTY_AGENDA_MESSAGE
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
                dataTable.subscribe("initEvent", function(){
                    YAHOO.bungeni.Events.scheduleAvailable.fire();
                });
                dataTable.subscribe("initEvent", 
                    YAHOO.bungeni.scheduling.handlers.renderScheduleControls
                );
                dataTable.subscribe("initEvent", 
                    YAHOO.bungeni.scheduling.handlers.addRowClass
                );
                dataTable.subscribe("initEvent", 
                    YAHOO.bungeni.agendaconfig.afterDTRender
                );
                dataTable.doBeforeLoadData  = YAHOO.bungeni.scheduling.handlers.populateScheduledKeys;
                dataTable.subscribe("rowAddEvent", 
                    YAHOO.bungeni.scheduling.handlers.setUnsavedChanges
                );
                dataTable.subscribe("rowsAddEvent", 
                    YAHOO.bungeni.scheduling.handlers.checkAndDoScrolling
                );
                dataTable.subscribe("rowDeleteEvent",
                    YAHOO.bungeni.scheduling.handlers.setUnsavedChanges
                );
                dataTable.subscribe("rowDeleteEvent",
                    YAHOO.bungeni.scheduling.handlers.refreshDeleted
                );
                dataTable.subscribe("rowUpdateEvent",
                    YAHOO.bungeni.scheduling.handlers.setUnsavedChanges
                );
                if (AgendaConfig.dataTableExtraInit != undefined){
                    AgendaConfig.dataTableExtraInit(dataTable);
                }
                var resizable_panel = layout.getUnitByPosition("left");
                if (resizable_panel){
                    resizable_panel.on("endResize", function(){
                        Handlers.resizeDataTable(dataTable,
                            container.body.clientWidth-15
                        );
                    });
                }
                                
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
