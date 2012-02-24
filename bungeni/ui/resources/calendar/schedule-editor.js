/*
 * This module instatiates a datatable for items in sitting. We also render
 * a panel with items available for scheduling.
 * 
 */

(function() {
    var Dom = YAHOO.util.Dom;
    var Event = YAHOO.util.Event;
    var Y$ = YAHOO.util.Selector;
    var YCM = YAHOO.util.Connect;
    var YJSON = YAHOO.lang.JSON;
    var itemsDataTable = null;
    var itemsDataSource = null;
    var schedulerActions = null;
    var schedulerLayout = null;
    var available_items_loaded = false;
    var saveDialog = null;
    var savingDialog = null;
    var textItemsDialog = null;
    var deleteDialog = null;
    var headingsDataTable = null;
    var DIALOG_CONFIG = YAHOO.bungeni.config.dialogs.default;
    var Utils = YAHOO.bungeni.Utils;
    var Columns = YAHOO.bungeni.config.scheduling.columns;
    var Formatters = YAHOO.bungeni.config.scheduling.formatters; 
    var Selectors = YAHOO.bungeni.config.selectors;
    var HIGHLIGHT_TYPES = [
        scheduler_globals.types.HEADING, 
        scheduler_globals.types.TEXT
    ];
    var HIGHLIGHT_TYPES_CSS_CLASS = "schedule-text-item";
    var AVAILABLE_ITEMS_SCHEMA = {
        resultsList : "items",
        fields : [Columns.ID, Columns.TYPE, Columns.TITLE, Columns.STATUS,
            Columns.STATUS_DATE, Columns.REGISTRY_NO, Columns.MOVER,
            Columns.URI
        ]
    }
    
    YAHOO.bungeni.scheduled_item_keys = new Array();
    YAHOO.bungeni.unsavedChanges = false;

    /**
     * @function setUnsavedChanges
     * @description set a flag when schedule changes
     */
    var setUnsavedChanges = function(args) {
        YAHOO.bungeni.unsavedChanges = true;
    }

    /**
     * @function fixDataTableSize
     * @description sets data table size to 100% of its container
     */
    var fixDataTableSize = function(){
            var context_width = (this.getContainerEl().clientWidth-20) + "px";
            this.getHdTableEl().width = context_width;
            this.getBdTableEl().width = context_width;
            this.unsubscribe("postRenderEvent", fixDataTableSize);
    }

    var addTextRecordToSchedule = function(event){
        headingsDataTable.unselectAllRows();
        textItemsDialog.show();
    }

    var insertTextRecord = function(event){
        var tabs = this.tabViewControl;
        var activeTab = tabs.getTab(tabs.get("activeIndex"));
        var recordData = activeTab.getRecordValue();
        if(recordData.value.length){
            var currentItem = schedulerActions.currentItem;
            var new_record_index = (
                (currentItem && itemsDataTable.getTrIndex(currentItem) + 1) || 0
            );
            
            for(idx=0; idx<recordData.value.length; idx++){
                var rec_data = recordData.value[idx];
                if (!rec_data){
                    continue;
                }
                itemsDataTable.addRow(
                    { 
                        item_title: rec_data, 
                        item_type: recordData.type
                    }, 
                    new_record_index
                );
                
                var new_record = itemsDataTable.getRecord(
                    itemsDataTable.getTrEl(new_record_index)
                );
                var target_columns = [
                    itemsDataTable.getColumn(Columns.MOVE_UP),
                    itemsDataTable.getColumn(Columns.MOVE_DOWN),
                ]
                itemsDataTable.unselectAllRows();
                itemsDataTable.selectRow(new_record);
                if (new_record_index > 0){
                    var updated_record = itemsDataTable.getRecord(
                        (new_record_index - 1)
                    );
                    for (idx=0; idx<=(target_columns.length); idx++){
                        itemsDataTable.updateCell(
                            updated_record, 
                            target_columns[idx],
                            updated_record.getData()
                        );
                    }
                }
                new_record_index = new_record_index + 1;
            }
            this.hide();
        }else{
            this.hide();
        }
    }
    
    /**
     * @method showCellEditor
     * @description displays an editor to modify text records on the schedule
     */
    var showCellEditorHandler = function(event){
        var target = Event.getTarget(event);
        var record = this.getRecord(target);
        if (record.getData().item_type == "text"){
            this.onEventShowCellEditor(event);
        }
    }
    
    /**
     * @method renderRTECellEditor
     * @description initialize textarea cell editor with an RTE editor on
     * initial display, then unbind this method when the RTE is rendered for 
     * the current editor instance.
     * 
     * This also overrides the getInputValue method to get the RTE value and
     * the cell editor show event to populate the shared editor with the
     * context record value.
     **/
     var renderRTECellEditor = function(args){
        var editor_width = (
            (schedulerLayout.getUnitByPosition("left").body.clientWidth - 15) + 
            "px"
        );
        rteCellEditor = new YAHOO.widget.Editor(args.editor.textarea,
            { width: editor_width, autoHeight: true }
        );
        rteCellEditor.render();
        args.editor.getInputValue = function(){
            value = rteCellEditor.cleanHTML(rteCellEditor.getEditorHTML());
            rteCellEditor.setEditorHTML("");
            return value
        }
        args.editor.unsubscribe("showEvent", renderRTECellEditor);
        args.editor.subscribe("showEvent", function(args){
            rteCellEditor.setEditorHTML(args.editor.textarea.value);
        });
     }

    /**
     * @method reorderRow
     * @description moves an entry up or down the schedule when the up or
     * down selectors are pushed
     */
    var reorderRow = function(args){
        var target_column = this.getColumn(args.target);
        if ([Columns.MOVE_UP, Columns.MOVE_DOWN].indexOf(
                target_column.field
            ) >= 0
        ){
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
                this.updateRow(swap_rows[0], data_1)
                this.updateRow(swap_rows[1], data_0)
            }
        }
    }

    /**
     * @method removeSelectedRow
     * @description deletes a row and record from the schedule. Displays
     * a dialog to confirm intention before deleting item
     * */
    var removeSelectedRow = function(args){
        deleteDialog.show();
        deleteDialog.bringToTop();
    }

    /**
     * @method highlightTypedRows
     * @description applies additional css class to certain scheduled types
     */
    var highlightTypedRows = function(oArgs){
        if (oArgs == undefined){
            var record_set = this.getRecordSet().getRecords();
            for(record_index in record_set){
                record = record_set[record_index];
                if (HIGHLIGHT_TYPES.indexOf(record.getData().item_type) >= 0){
                    row = this.getTrEl(record);
                    Dom.addClass(row, HIGHLIGHT_TYPES_CSS_CLASS);
                }
            }
        }else{
            Dom.addClass(this.getTrEl(oArgs.record), HIGHLIGHT_TYPES_CSS_CLASS);
        }
    }
    

    /**
     * @method showSchedulerControls
     * @description displays a contextual popup panel when a row is selected.
     * Controls provide options to modify the schedule within the context of 
     * the selected row.
     */
    var showSchedulerControls = function(args){
        schedulerActions.currentItem = args.record;
        schedulerActions.cfg.setProperty("context",
            [args.el.id, "tl", "bl"]
        );
        schedulerActions.render();
        schedulerActions.show();
    }


    /**
     *@method initShowSchedulerControls
     * @description show scheduler controls if initial recordset is empty
     **/
     var initShowSchedulerControls = function(oArgs){
         if (this.getRecordSet().getLength() == 0){
             showSchedulerControls({record:null, el:this.getTheadEl()});
         }
     }


    /**
     *@method hideSchedulerControls
     * @description hide scheduler controls after adding of first item
     **/
     var hideSchedulerControls = function(oArgs){
         if (this.getRecordSet().getLength() == 1 && 
            schedulerActions.currentItem == null
         ){
             schedulerActions.hide();
         }
     }

    /**
     * @method setFilterMenuSelection
     * @description sets the value of a filter menu button
     */
     var setFilterMenuSelection = function(event){
         if(this.original_label == undefined){
             this.original_label = this.get("label");
         }
         var menuItem = event.newValue;
         var selectionLabel = (
            (menuItem && Utils.wrapText(menuItem.cfg.getProperty("text")))
            || this.original_label
        );
         this.set("label", selectionLabel);
     }

    /**
     * @method filterCalendarSetup
     * @description sets up a calendar bound to a button
     */
    var filterCalendarSetup = function(button, type, menu, callback){
        var sCalendar = new YAHOO.widget.Calendar(
            "calendar_start_" + type,
            menu.body.id
        );
        sCalendar.render();
        button.getSelectedDate = function(){
            var sDate = sCalendar.getSelectedDates()[0];
            var sDateText = "";
            if (sDate != null){
                sDateText = new Array(
                    sDate.getFullYear(), sDate.getMonth()+1, sDate.getDate()
                ).join("-")
            }
            return sDateText;
        };
        button.clearSelection = function(){
            sCalendar.deselectAll();
            button.set("label", button.original_label);
        }
        sCalendar.selectEvent.subscribe(function(sType, oArgs){
            if (button.original_label == undefined){
                button.original_label = button.get("label");
            }
            if(oArgs){
                var sDate = oArgs[0][0];
                button.set("label", Utils.wrapText(sDate.join("-")));
            }
            menu.hide();
        });
        button.unsubscribe("click", callback);
        sCalendar.align();
    }


    /**
     * @method getDummyCalendarDate
     * @description returns a blank string as selected calendar date associated
     * with a filter button.
     * 
     * This is used if the calendar has not been instantiated which is bound
     * to the click event of a fitler button.
     */
     var getDummyCalendarDate = function(){
         return "";
     }

   /**
     * @method renderAvailableItems
     * @description renders available items as tabs
     */
    var renderAvailableItems = function(args){
        var schedulePanel = schedulerLayout.getUnitByPosition("left");
        var itemsPanel = schedulerLayout.getUnitByPosition("center");
        if (available_items_loaded){ return; }
        available_items_loaded = true;
        var record_set = itemsDataTable.getRecordSet().getRecords();
        for(index in record_set){
            data = record_set[index].getData();
            YAHOO.bungeni.scheduled_item_keys.push(
                data.item_id + ":" + data.item_type
            );
        }

        var availableItemsColumns = [
            {
                key: Columns.SELECT_ROW, 
                label: "<input type='checkbox' name='rec-sel-all'/>", 
                formatter: Formatters.availableItemSelect
            },
            {
                key: Columns.TITLE,
                label: scheduler_globals.column_title,
            },
            {
                key: Columns.REGISTRY_NO,
                label: scheduler_globals.column_registry_number,
            },
            {
                key: Columns.MOVER,
                label: scheduler_globals.column_mover,
            },
            {
                key: Columns.STATUS,
                label: scheduler_globals.column_status,
            },
            {
                key: Columns.STATUS_DATE,
                label: scheduler_globals.column_status_date,
                formatter: "date"
            },
        ]
        
        var availableItems = new YAHOO.widget.TabView();
        for (type_index in scheduler_globals.schedulable_types){
            (function(){
                var typedef = scheduler_globals.schedulable_types[type_index];
                var type = typedef.name;
                var container_id = type + "-data-table";
                var container_id_filters = container_id + "-filters";
                availableItems.addTab(new YAHOO.widget.Tab(
                    {
                        label: typedef.title,
                        content: ("<div id='" + container_id_filters + 
                            "' class='schedule-available-item-filters'></div>" 
                            + "<div id='" + container_id + "'/>"
                        ),
                    }
                ));
                Event.onAvailable(container_id, function(event){
                    var tabDataSource = new YAHOO.util.DataSource(
                        (scheduler_globals.schedulable_items_json_url 
                            + "?type="+ type
                        )
                    );
                    tabDataSource.responseType = YAHOO.util.DataSource.TYPE_JSON;
                    tabDataSource.responseSchema = AVAILABLE_ITEMS_SCHEMA;
                    var tabDataTable = new YAHOO.widget.DataTable(container_id,
                        availableItemsColumns, tabDataSource, 
                        { 
                            selectionMode:"single",
                            scrollable: true,
                            initialLoad: true,
                            width: (itemsPanel.body.clientWidth - 15) + "px",
                            height: (itemsPanel.body.clientHeight - 50) + "px"
                        }
                    );
                    tabDataTable.subscribe("cellClickEvent", addItemToSchedule);
                    tabDataTable.subscribe("theadCellClickEvent", checkRows);
                    tabDataTable.subscribe("cellSelectEvent", addItemToSchedule);
                    tabDataTable.subscribe("postRenderEvent", fixDataTableSize);
                    itemsDataTable.subscribe("rowDeleteEvent", function(args){
                        uncheckRemovedRows(args, tabDataTable, type);
                    });
                    
                    //create filter controls
                    var filter_config = scheduler_globals.filter_config[type];
                    if (filter_config.menu.length > 0){
                        var statusFilterButton = new YAHOO.widget.Button(
                            {
                                type: "menu",
                                label: Utils.wrapText(filter_config.label),
                                id: "filter_status_" + type,
                                name: "filter_status_" + type,
                                menu: filter_config.menu,
                                container: container_id_filters,
                            }
                        );
                        statusFilterButton.on("selectedMenuItemChange",
                            setFilterMenuSelection
                        );

                        var dateStartMenu = new YAHOO.widget.Overlay(
                            "cal_menu_start_" + type, { visible: false }
                        );
                        var dateStartButton = new YAHOO.widget.Button(
                            {
                                type: "menu",
                                label: Utils.wrapText(
                                    scheduler_globals.filters_start_date_label
                                ),
                                id: "filter_start_date_" + type,
                                name: "filter_start_date_" + type,
                                menu: dateStartMenu,
                                container: container_id_filters,
                            }
                        );
                        dateStartButton.on("appendTo", function(){
                            dateStartMenu.setBody(" ");
                            dateStartMenu.body.id = "calendar_start_container_" + type;
                        });

                        dateStartButton.on("click", function callback(){
                            filterCalendarSetup(this, type, dateStartMenu, callback);
                        });

                        var dateEndMenu = new YAHOO.widget.Overlay(
                            "cal_menu_end_" + type, { visible: false }
                        );
                        var dateEndButton = new YAHOO.widget.Button(
                            {
                                type: "menu",
                                label: Utils.wrapText(
                                    scheduler_globals.filters_end_date_label
                                ),
                                id: "filter_end_date_" + type,
                                name: "filter_end_date_" + type,
                                menu: dateEndMenu,
                                container: container_id_filters,
                            }
                        );
                        dateEndButton.on("appendTo", function(){
                            dateEndMenu.setBody(" ");
                            dateEndMenu.body.id = "calendar_end_container_" + type;
                        });
                        
                        dateEndButton.on("click", function callback(){
                            filterCalendarSetup(this, type, dateEndMenu, callback);
                        });
                        
                        
                        dateStartButton.getSelectedDate = getDummyCalendarDate;
                        dateStartButton.clearSelection = getDummyCalendarDate;
                        dateEndButton.getSelectedDate = getDummyCalendarDate;
                        dateEndButton.clearSelection = getDummyCalendarDate;
                        
                        var filterApplyButton = new YAHOO.widget.Button(
                            {
                                type: "button",
                                label: Utils.wrapText(
                                    scheduler_globals.filter_apply_label
                                ),
                                id: "filter_apply_" + type,
                                name: "filter_apply_" + type,
                                container: container_id_filters,
                            }
                        );
                        filterApplyButton.on("click", function(oArgs){
                            var data_filters = {};
                            var selected_status = statusFilterButton.getMenu().activeItem;
                            if (selected_status != null){
                                data_filters["filter_status"] = selected_status.value;
                            }
                            var start_date = dateStartButton.getSelectedDate();
                            var end_date = dateEndButton.getSelectedDate();
                            if (start_date || end_date){
                                data_filters["filter_status_date"] = new Array(
                                        (start_date || ""), (end_date|| "")
                                ).join("|");
                            }
                            if (Object.keys(data_filters).length > 0){
                                tabDataTable.refresh(data_filters);
                            }else{
                                saveDialog.setHeader(
                                    scheduler_globals.filters_no_filters_header
                                );
                                saveDialog.setBody(
                                    scheduler_globals.filters_no_filters_message
                                );
                                saveDialog.show();
                                saveDialog.bringToTop();
                            }
                        });
                        
                        var clearFiltersButton = new YAHOO.widget.Button(
                            {
                                type: "button",
                                label: Utils.wrapText(
                                    scheduler_globals.filters_clear_label
                                ),
                                id: "filter_clear_" + type,
                                name: "filter_clear_" + type,
                                container: container_id_filters,
                            }
                        );
                        clearFiltersButton.on("click", function(oArgs){
                            //reset filters and then reload datatable
                            statusFilterButton.set("selectedMenuItem", null);
                            dateStartButton.clearSelection();
                            dateEndButton.clearSelection();
                            tabDataTable.refresh();
                        });

                    }
                    schedulePanel.on("resize", function(){
                        itemsDataTable.setAttributes(
                            { "width": this.body.clientWidth + "px" }, true
                        );
                        tabDataTable.setAttributes(
                            { "width": itemsPanel.body.clientWidth + "px" }, 
                            true
                        );
                    });
                });
            })();
        }
        availableItems.selectTab(0);
        availableItems.appendTo(itemsPanel.body);
    }


    /**
     * @method removeCheckedItems
     * @description removes checked items from the schedule
     **/
    var removeCheckedItems = function(args){
        var record_set = itemsDataTable.getRecordSet().getRecords();
        var checked_ids = new Array()
        for (record_index in record_set){
            var row = itemsDataTable.getTrEl(record_set[record_index]);
            var select_td = itemsDataTable.getFirstTdEl(row);
            if(Y$.query(Selectors.checkbox, select_td, true).checked){
                checked_ids.push(record_index);
            }
        }
        checked_ids.reverse();
        for (idx in checked_ids){
            itemsDataTable.deleteRow(Number(checked_ids[idx]));
        }
    }
    
    /**
     * @method discardChanges
     * @description reloads the scheduling page losing all local changes
     **/
    var discardChanges = function(args){
        window.location.reload();
    }

    //schedule save callback config
    var RequestObject = {
        handleSuccess: function(o){
            savingDialog.setBody(scheduler_globals.saving_dialog_refreshing);
            YAHOO.bungeni.unsavedChanges = false;
            if (YAHOO.bungeni.scheduled_item_keys.length == 0){
                //reload page - activate applicable menu actions
                window.location.reload();
            }else{
                itemsDataTable.refresh();
                savingDialog.setBody("");
                savingDialog.hide();
            }
        },
        handleFailure: function(o){
            savingDialog.setBody(scheduler_globals.saving_dialog_exception);
            setTimeout(function(){
                    savingDialog.setBody("");
                    savingDialog.hide();
                },
                2000
            );
        },
        startRequest: function(data){
            savingDialog.setBody(scheduler_globals.saving_schedule_text);
            savingDialog.show();
            savingDialog.bringToTop();
            YCM.asyncRequest("POST", 
                scheduler_globals.save_schedule_url,
                callback,
                data
            );
                
        }
    }
    
    var callback = {
        success: RequestObject.handleSuccess,
        failure: RequestObject.handleFailure,
        scope: RequestObject
    }

    /**
     * @method saveSchedule
     * @description posts schedule data to bungeni for persistence
     **/
    var saveSchedule = function(args){
        var record_set = itemsDataTable.getRecordSet();
        var records = record_set.getRecords();
        if (record_set.getLength()){
            var item_data = new Array();
            for (index in records){
                var record_data = records[index].getData();
                var save_data = {
                    item_type: record_data.item_type,
                    item_id: record_data.item_id,
                    schedule_id: record_data.object_id,
                    item_text: record_data.item_title
                }
                item_data.push(YJSON.stringify(save_data));
            }
            var post_data = "data=" + YJSON.stringify(item_data);
            RequestObject.startRequest(post_data);
        }else{
            saveDialog.show();
            saveDialog.bringToTop();
        }
    }

    /**
     * @method renderScheduleButtons
     * @description Renders action buttons inside provided container element
     **/
    var renderScheduleButtons = function(container){
        container.style.lineHeight = container.clientHeight;
        container.style.padding = "5px";
        var saveButton = new YAHOO.widget.Button(
            { label: scheduler_globals.save_button_text }
        );
        var discardButton = new YAHOO.widget.Button(
            { label: scheduler_globals.discard_button_text }
        );
        saveButton.on("click", saveSchedule);
        discardButton.on("click", discardChanges);
        saveButton.appendTo(container);
        discardButton.appendTo(container);
    }


    /**
     * @method addItemToSchedule
     * @description adds available item to schedule
     * 
     */
    var addItemToSchedule = function(args){
        var target = args.target || args.el;
        var target_column = this.getColumn(target);
        if(target_column.field == Columns.SELECT_ROW){
            var targetRecord = this.getRecord(target);
            var targetData = targetRecord.getData()
            if (Y$.query(Selectors.checkbox, target, true).checked){
                //check if item is already scheduled
                var record_set = itemsDataTable.getRecordSet().getRecords();
                var item_in_schedule = false;
                for(idx in record_set){
                    var record = record_set[idx];
                    var oData = record.getData();
                    if((oData.item_id == targetData.item_id) &&
                        (oData.item_type == targetData.item_type)
                    ){
                        item_in_schedule = true;
                        break;
                    }
                }
                if (!item_in_schedule){
                    ctx_index = itemsDataTable.getSelectedRows()[0];
                    var new_record_index = (
                        (ctx_index && itemsDataTable.getTrIndex(ctx_index)+1) || 0
                    );
                    itemsDataTable.addRow(targetData, new_record_index);
                }
            }else{
                var record_set = itemsDataTable.getRecordSet().getRecords();
                for (idx in record_set){
                    var record = record_set[idx];
                    var sdata = record.getData();
                    if((sdata.item_id == targetData.item_id) &&
                        (sdata.item_type == targetData.item_type)
                    ){
                        itemsDataTable.deleteRow(Number(idx));
                    }
                }
            }
        }
    }

    /**
     * @method checkRows
     * @description check or uncheck selectors for all items on data table
     * 
     */
    var checkRows = function(args){
        var target_column = this.getColumn(args.target);
        if(target_column.field == Columns.SELECT_ROW){
            var record_set = this.getRecordSet().getRecords();
            var checked = false;
            if (Y$.query(Selectors.checkbox, args.target, true).checked){
                checked = true;
            }
            for (record_index in record_set){
                var row = this.getTrEl(record_set[record_index]);
                var select_td = this.getFirstTdEl(row);
                Y$.query(Selectors.checkbox, select_td, true).checked = checked;
                this.unselectAllCells();
                this.selectCell(select_td);
            }
        }
    }

    /**
     * @method uncheckRemovedRows
     * @description unchecks records cleared from schedule from available 
     * items data table
     */
     var uncheckRemovedRows = function(args, oDt, type){
         var del_data = args.oldData;
         if (del_data[Columns.TYPE] == type){
             var target_column = oDt.getColumnById(Columns.SELECT_ROW);
             var record_set = oDt.getRecordSet().getRecords();
             for(idx in record_set){
                 var record = record_set[idx];
                 var rec_data = record.getData();
                 if((rec_data[Columns.ID]==del_data[Columns.ID]) &&
                    (rec_data[Columns.TYPE]==rec_data[Columns.TYPE])
                 ){
                     var td = oDt.getFirstTdEl(oDt.getTrEl(record));
                     Y$.query(Selectors.checkbox, td, true).checked = false;
                     break;
                 }
             }
         }
     }

    var initAvailableHeadings = function(e){
        var columns = [
            {
                key:Columns.NUMBER,
                label:"",
                formatter:Formatters.counter
            },
            {
                key: Columns.TITLE,
                label: scheduler_globals.column_available_headings_title,
            },
        ]
        var container = this.get("contentEl");
        var data_container = Y$.query("div#headings-available", container)[0];
        var dataSource = new YAHOO.util.DataSource(
            scheduler_globals.schedulable_items_json_url + "?type=heading"
        );
        dataSource.responseType = YAHOO.util.DataSource.TYPE_JSON;
        dataSource.responseSchema = AVAILABLE_ITEMS_SCHEMA;
        headingsDataTable = new YAHOO.widget.DataTable(data_container,
            columns, dataSource, 
            { 
                selectionMode:"standard",
                scrollable: true,
                initialLoad: true,
                width:"100%",
                height: "190px",
            }
        );
        headingsDataTable.subscribe("rowMouseoverEvent", headingsDataTable.onEventHighlightRow);
        headingsDataTable.subscribe("rowMouseoutEvent", headingsDataTable.onEventUnhighlightRow);
        headingsDataTable.subscribe("rowClickEvent", headingsDataTable.onEventSelectRow);
        headingsDataTable.subscribe("postRenderEvent", fixDataTableSize);
        this.unsubscribe("activeChange", initAvailableHeadings);
        return { oDs: dataSource, oDt: headingsDataTable }
    }


    /**
     * @method renderSchedule
     * @description renders the schedule to the provided container element
     **/
     var renderSchedule = function(container, controls_container){
        var container_width = container.clientWidth;
        var editor = new YAHOO.widget.TextareaCellEditor();
        editor.subscribe("showEvent", renderRTECellEditor);
        var columnDefinitions = [
            {
                key : Columns.TYPE, 
                label : scheduler_globals.column_type,
                formatter : Formatters.type,
                width: Math.round(0.10 * container_width)
            },
            {
                key : Columns.TITLE, 
                label : scheduler_globals.column_title,
                editor : editor,
                formatter : Formatters.title,
                width: Math.round(0.60 * container_width)
            },
            {
                key : Columns.MOVE_UP, 
                label : "", 
                formatter : Formatters.moveUp,
                width: Math.round(0.05 * container_width)
            },
            {
                key:Columns.MOVE_DOWN, 
                label:"", 
                formatter : Formatters.moveDown,
                width: Math.round(0.05 * container_width)
            },
        ];
        
        itemsDataSource = new YAHOO.util.DataSource(
            scheduler_globals.json_listing_url
        );
        itemsDataSource.responseType = YAHOO.util.DataSource.TYPE_JSON;
        itemsDataSource.responseSchema = {
            resultsList: "nodes",
            fields: [Columns.ID, Columns.TITLE, 
                Columns.TYPE, Columns.OBJECT_ID, 
                Columns.MOVER, Columns.URI
            ],
        };
        
        var scheduler_container = document.createElement("div");
        container.appendChild(scheduler_container);

        itemsDataTable = new YAHOO.widget.DataTable(scheduler_container,
            columnDefinitions, itemsDataSource, 
            { 
                selectionMode:"single",
                scrollable:true,
                width:(container_width-15) + "px",
                height: (container.clientHeight - 50) + "px"
            }
        );
        itemsDataTable.subscribe("rowMouseoverEvent", 
            itemsDataTable.onEventHighlightRow
        );
        itemsDataTable.subscribe("rowMouseoutEvent", 
            itemsDataTable.onEventUnhighlightRow
        );
        itemsDataTable.subscribe("rowClickEvent", itemsDataTable.onEventSelectRow);
        itemsDataTable.subscribe("cellDblclickEvent", showCellEditorHandler);
        itemsDataTable.subscribe("cellClickEvent", reorderRow);
        itemsDataTable.subscribe("rowSelectEvent", showSchedulerControls);
        itemsDataTable.subscribe("initEvent", renderAvailableItems);
        itemsDataTable.subscribe("initEvent", highlightTypedRows);
        itemsDataTable.subscribe("initEvent", initShowSchedulerControls);
        itemsDataTable.subscribe("rowDeleteEvent", initShowSchedulerControls);
        itemsDataTable.subscribe("rowAddEvent", highlightTypedRows);
        itemsDataTable.subscribe("rowAddEvent", hideSchedulerControls);
        itemsDataTable.subscribe("rowAddEvent", setUnsavedChanges);
        itemsDataTable.subscribe("rowDeleteEvent", setUnsavedChanges);
        itemsDataTable.subscribe("rowUpdateEvent", setUnsavedChanges);
        var _renderScheduleButtons = function(){
            renderScheduleButtons(controls_container);
            this.unsubscribe("initEvent", _renderScheduleButtons);
        }
        itemsDataTable.subscribe("initEvent", _renderScheduleButtons);
        
        return {
            oDS: itemsDataSource,
            oDT: itemsDataTable,
        }
     }


    /**
     * @method renderSchedulerItemControls
     * @description scheduler item ui controls used in schedulers edit mode
     **/
     var renderSchedulerItemControls = function(){
        //create scheduler actions panel
        schedulerActions = new YAHOO.widget.Panel("scheduled-item-controls",
            {   
                underlay: "none",
                width: "300px",
            }
        );
        schedulerActions.currentItem = null;
        schedulerActions.setHeader(
            scheduler_globals.scheduled_item_context_menu_header
        );
        
        var scheduleTextButton = new YAHOO.widget.Button(
            {
                label: scheduler_globals.text_button_text,
            }
        );
        var scheduleRemoveButton = new YAHOO.widget.Button(
            {
                label: scheduler_globals.remove_button_text,
            }
        );
        scheduleTextButton.appendTo(schedulerActions.body);
        scheduleTextButton.on("click", addTextRecordToSchedule);
        scheduleRemoveButton.appendTo(schedulerActions.body);
        scheduleRemoveButton.on("click", removeSelectedRow);

        //create delete dialog and controls
        deleteDialog = new YAHOO.widget.SimpleDialog("scheduler-delete-dialog",
            DIALOG_CONFIG
        );
        deleteDialog.setHeader(scheduler_globals.delete_dialog_header);
        deleteDialog.setBody(scheduler_globals.delete_dialog_text)
        
        var handleDeleteConfirm = function(){
            var selected_record_index = itemsDataTable.getSelectedRows()[0];
            itemsDataTable.deleteRow(selected_record_index);
            this.hide();
            schedulerActions.hide();
        }
        
        var handleDeleteCancel = function(){
            this.hide();
        }
        
        var deleteDialogButtons = [
            {
                text: scheduler_globals.delete_dialog_confirm, 
                handler: handleDeleteConfirm
            },
            {
                text: scheduler_globals.delete_dialog_cancel, 
                handler: handleDeleteCancel,
                isDefault: true
            },
        ] 
        
        deleteDialog.cfg.queueProperty("buttons", deleteDialogButtons);
        deleteDialog.cfg.queueProperty("icon", 
            YAHOO.widget.SimpleDialog.ICON_WARN
        );
        deleteDialog.render(document.body);

        //create save dialog
        saveDialog = new YAHOO.widget.SimpleDialog("scheduler-save-dialog",
            DIALOG_CONFIG
        );
        saveDialog.setHeader(scheduler_globals.save_dialog_header);
        saveDialog.setBody(scheduler_globals.save_dialog_empty_message)
                
        var handleConfirm = function(){
            this.hide();
        }
        
        var saveDialogButtons = [
            {
                text: scheduler_globals.save_dialog_confirm, 
                handler: handleConfirm
            }
        ] 
        
        saveDialog.cfg.queueProperty("buttons", saveDialogButtons);
        saveDialog.cfg.queueProperty("icon",
            YAHOO.widget.SimpleDialog.ICON_INFO
        );
        saveDialog.render(document.body);
        
        //render schedule processing dialog
        savingDialog = new YAHOO.widget.SimpleDialog("scheduler-saving-dialog",
            DIALOG_CONFIG
        );
        savingDialog.setHeader(scheduler_globals.saving_dialog_header);
        savingDialog.setBody("");
        savingDialog.cfg.queueProperty("close", false);
        savingDialog.cfg.queueProperty("icon",
            YAHOO.widget.SimpleDialog.ICON_BLOCK
        );
        savingDialog.render(document.body);
        
        //render schedule text items dialog
        textItemsDialog  = new YAHOO.widget.SimpleDialog("scheduler-text-dialog",
            DIALOG_CONFIG
        );
        var textDialogButtons = [
            {
                text: scheduler_globals.text_dialog_confirm_action,
                handler: insertTextRecord
            },
            {
                text: scheduler_globals.text_dialog_cancel_action,
                handler: function(){ this.hide(); }
            },
        ]
        textItemsDialog.cfg.queueProperty("width", "500px");
        textItemsDialog.cfg.queueProperty("height", "400px");
        textItemsDialog.cfg.queueProperty("buttons", textDialogButtons);
        textItemsDialog.setBody("");
        textItemsDialog.setHeader(scheduler_globals.text_items_dialog_header);
        textItemsDialog.renderEvent.subscribe(function(){
            var textRecordTabs = new YAHOO.widget.TabView();
            var headingTab = new YAHOO.widget.Tab(
                { 
                    label:"heading",
                    content: ("<div id='add-heading-record'>" + 
                        "<label class='scheduler-label'" + 
                        " for='heading-record-value'>Heading Text</label>" +
                        "<input class='scheduler-bigtext' " + 
                        "id='heading-record-value' name='heading-record-value' " +
                         "type='text'/></div><div id='headings-available'></div>"
                    )
                }
            );
            headingTab.getRecordValue = function(){
                var contentEl = this.get("contentEl");
                var heading_value = Y$.query("input", contentEl)[0].value;
                var selected_rows = headingsDataTable.getSelectedRows();
                var heading_values = new Array();
                heading_values.push(heading_value);
                for(row_id=0; row_id<selected_rows.length; row_id++){
                    var data = headingsDataTable.getRecord(
                        selected_rows[row_id]
                    ).getData();
                    heading_values.push(data.item_title);
                }
                return { 
                    type:scheduler_globals.types.HEADING,
                    value: heading_values
                }
            }
            headingTab.on("activeChange", initAvailableHeadings);
            textItemsDialog.showEvent.subscribe(function(){
                Y$.query("input", headingTab.get("contentEl"))[0].value = "";
            });
            var textTab = new YAHOO.widget.Tab(
                { 
                    label:"text",
                    content: ("<div id='add-text-record'>" + 
                        "<textarea id='text-record-value' " +
                         "name='text-record-value'></textarea></div>"
                    )
                }
            );
            var rteEditor = null;
            textTab.getRecordValue = function(){
                return {
                    type: scheduler_globals.types.TEXT,
                    value: [ rteEditor.cleanHTML(rteEditor.getEditorHTML()) ]
                }
            }
            textRecordTabs.addTab(headingTab);
            textRecordTabs.addTab(textTab);
            Event.onAvailable("add-text-record", function(event){
                rteEditor = new YAHOO.widget.Editor("text-record-value",
                    { width: "100%", autoHeight: false }
                );
                rteEditor.render();
            });
            textRecordTabs.appendTo(textItemsDialog.body);
            textItemsDialog.tabViewControl = textRecordTabs;
            textRecordTabs.selectTab(0);
            
        });
        textItemsDialog.render(document.body);
     }
     
     /**
      * @method renderSchedulerLayout
      * @description render scheduler UI layout
      **/
      var renderSchedulerLayout = function(){
        schedulerLayout = new YAHOO.widget.Layout("scheduler-layout",
            {
                height:500,
                units: [
                    { 
                        position: "left", 
                        width: 600, 
                        body: '',
                        gutter: "5 5",
                        height: 400,
                        resize: true,
                        collapse: true
                    },
                    { 
                        position: "center", 
                        body: '',
                        header: scheduler_globals.available_items_title,
                        gutter: "5 5",
                        height: 400,
                        collapse: true
                    },
                ]
            }
        );
        
        //render inner scheduler layout
        schedulerLayout.on("render", function(){
            var left_el = schedulerLayout.getUnitByPosition("left").get("wrap");
            innerLayout = new YAHOO.widget.Layout(left_el,
                {
                    parent: schedulerLayout,
                    units: [
                        {
                            position:"center", 
                            header: scheduler_globals.current_schedule_title,
                            body: "" 
                        },
                        {
                            position:"bottom", 
                            height: 40, 
                            body:""
                        },
                    ]
                }
            );
            innerLayout.on("render", function(){
                renderSchedule(
                    this.getUnitByPosition("center").body,
                    this.getUnitByPosition("bottom").body
                );
            });
            innerLayout.render();
        });
        schedulerLayout.render();
      }

    /**
     * @method anonymous
     * @description Renders the panel UI and builds up schedule data table.
     * Also binds various events to handlers on the data table.
     * Schedule control actions are also built into the DOM
     **/
    Event.onDOMReady(function(){
        renderSchedulerItemControls();
        renderSchedulerLayout();
    });
})();
