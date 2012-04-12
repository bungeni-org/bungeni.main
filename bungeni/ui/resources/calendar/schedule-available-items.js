/**
 * This module renders a list of available schedulable items
**/
YAHOO.bungeni.availableitems = function(){
    var Event = YAHOO.util.Event;
    var SGlobals = scheduler_globals;
    var Scheduling = YAHOO.bungeni.scheduling;
    var Columns = YAHOO.bungeni.config.scheduling.columns;
    var Formatters = YAHOO.bungeni.config.scheduling.formatters;
    var Selectors = YAHOO.bungeni.config.selectors;
    var Utils = YAHOO.bungeni.Utils;
    var Y$ = YAHOO.util.Selector;
    
    /**
     * @method renderFilterControls
     * @description renders datatables of items available for scheduling
     **/
    var renderFilterControls = function(type, container, dataTable){
        var Handlers = YAHOO.bungeni.availableitems.handlers;
        var filter_config = SGlobals.filter_config[type];
        if (filter_config.menu.length > 0){
            var statusFilterButton = new YAHOO.widget.Button(
                {
                    type: "menu",
                    label: Utils.wrapText(filter_config.label),
                    id: "filter_status_" + type,
                    name: "filter_status_" + type,
                    menu: filter_config.menu,
                    container: container,
                }
            );
            statusFilterButton.on("selectedMenuItemChange",
                Handlers.setFilterMenuSelection
            );

            var dateStartMenu = new YAHOO.widget.Overlay(
                "cal_menu_start_" + type, { visible: false }
            );
            dateStartMenu.subscribe("show", Handlers.dialogPostRender);
            var dateStartButton = new YAHOO.widget.Button(
                {
                    type: "menu",
                    label: Utils.wrapText(
                        SGlobals.filters_start_date_label
                    ),
                    id: "filter_start_date_" + type,
                    name: "filter_start_date_" + type,
                    menu: dateStartMenu,
                    container: container,
                }
            );
            dateStartButton.on("appendTo", function(){
                dateStartMenu.setBody(" ");
                dateStartMenu.body.id = "calendar_start_container_" + type;
            });

            dateStartButton.on("click", function callback(){
                Handlers.filterCalendarSetup(this, type, dateStartMenu, 
                    callback
                );
            });

            var dateEndMenu = new YAHOO.widget.Overlay(
                "cal_menu_end_" + type, { visible: false }
            );
            var dateEndButton = new YAHOO.widget.Button(
                {
                    type: "menu",
                    label: Utils.wrapText(
                        SGlobals.filters_end_date_label
                    ),
                    id: "filter_end_date_" + type,
                    name: "filter_end_date_" + type,
                    menu: dateEndMenu,
                    container: container,
                }
            );
            dateEndButton.on("appendTo", function(){
                dateEndMenu.setBody(" ");
                dateEndMenu.body.id = "calendar_end_container_" + type;
            });
            
            dateEndButton.on("click", function callback(){
                Handlers.filterCalendarSetup(this, type, dateEndMenu, callback);
            });
            
            dateStartButton.getSelectedDate = Handlers.getDummyCalendarDate;
            dateStartButton.clearSelection = Handlers.getDummyCalendarDate;
            dateEndButton.getSelectedDate = Handlers.getDummyCalendarDate;
            dateEndButton.clearSelection = Handlers.getDummyCalendarDate;
            
            var filterApplyButton = new YAHOO.widget.Button(
                {
                    type: "button",
                    label: Utils.wrapText(
                        SGlobals.filter_apply_label
                    ),
                    id: "filter_apply_" + type,
                    name: "filter_apply_" + type,
                    container: container,
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
                    dataTable.refresh(data_filters);
                }else{
                    YAHOO.bungeni.config.dialogs.notification.show(
                        SGlobals.filters_no_filters_message
                    );
                }
            });
            
            var clearFiltersButton = new YAHOO.widget.Button(
                {
                    type: "button",
                    label: Utils.wrapText(
                        SGlobals.filters_clear_label
                    ),
                    id: "filter_clear_" + type,
                    name: "filter_clear_" + type,
                    container: container,
                }
            );
            clearFiltersButton.on("click", function(oArgs){
                //reset filters and then reload datatable
                statusFilterButton.set("selectedMenuItem", null);
                dateStartButton.clearSelection();
                dateEndButton.clearSelection();
                dataTable.refresh();
            });

        }
    }
    
    var availableItemHandlers = function(){
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

        var dialogPostRender = function(){
            this.bringToTop();
        }

        /**
         * @method addItemToSchedule
         * @description adds available item to schedule
         * 
         */
        var addItemToSchedule = function(args){
            var itemsDataTable = YAHOO.bungeni.scheduling.getScheduleTable();
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
         * @method renderTextRecordsTabs
         * @description renders tabview record onto a dialog to allow selection
         * and entry of text records i.e. headings and arbitrary text
         **/
        var renderTextRecordsTabs = function(args){
            var active_tab_id = this._parent.tab_id;
            var tab_view = new YAHOO.widget.TabView();
            var text_tab = new YAHOO.widget.Tab(
                { 
                    label: SGlobals.type_names.EDITORIAL_NOTE,
                    content: ("<div id='add-text-record'>" + 
                        "<textarea id='text-record-value' " +
                         "name='text-record-value'></textarea></div>"
                    ),
                }
            );
            var minute_tab = new YAHOO.widget.Tab(
                { 
                    label: SGlobals.type_names.MINUTE,
                    content: ("<div id='add-minute-record'>" + 
                        "<textarea id='minute-record-value' " +
                         "name='minute-record-value'></textarea></div>"
                    ),
                }
            );
            var heading_tab = new YAHOO.widget.Tab(
                { 
                    label: SGlobals.type_names.HEADING,
                    content: ("<div id='add-heading-record'>" + 
                        "<label class='scheduler-label'" + 
                        " for='heading-record-value'>"+
                        SGlobals.new_heading_text +
                        "</label>" +
                        "<input class='scheduler-bigtext' " + 
                        "id='heading-record-value' name='heading-record-value' " +
                         "type='text'/></div><div id='headings-available'></div>"
                    ),
                }
            );
            var hDt = null;
            var initAvailableHeadings = function(){
                var columns = [
                    {
                        key:Columns.NUMBER,
                        label:"",
                        formatter:Formatters.counter
                    },
                    {
                        key: Columns.TITLE,
                        label: SGlobals.column_available_headings_title,
                    },
                ]
                var container = this.get("contentEl");
                var data_container = Y$.query("div#headings-available", container)[0];
                var dataSource = new YAHOO.util.DataSource(
                    SGlobals.schedulable_items_json_url + "?type=heading"
                );
                dataSource.responseType = YAHOO.util.DataSource.TYPE_JSON;
                dataSource.responseSchema = YAHOO.bungeni.config.schemas.available_items;
                hDt = new YAHOO.widget.DataTable(data_container,
                    columns, dataSource, 
                    { 
                        selectionMode:"standard",
                        scrollable: true,
                        initialLoad: true,
                        width:"468px",
                        height: "200px",
                    }
                );
                hDt.subscribe("rowMouseoverEvent", hDt.onEventHighlightRow);
                hDt.subscribe("rowMouseoutEvent", hDt.onEventUnhighlightRow);
                hDt.subscribe("rowClickEvent", hDt.onEventSelectRow);
                this.unsubscribe("activeChange", initAvailableHeadings);
            }
            heading_tab.on("activeChange", initAvailableHeadings);
            heading_tab.getRecordValue = function(){
                var contentEl = this.get("contentEl");
                var custom_value = Y$.query("input", contentEl)[0].value;
                var selected_rows = hDt.getSelectedRows();
                var heading_values = new Array();
                if (custom_value){
                    var heading_value = {};
                    heading_value[Columns.TITLE] = custom_value;
                    heading_values.push(heading_value);
                }
                for(row_id=0; row_id<selected_rows.length; row_id++){
                    var data = hDt.getRecord(selected_rows[row_id]).getData();
                    var heading_value = {};
                    heading_value[Columns.TITLE] = data[Columns.TITLE];
                    heading_value[Columns.ID] = data[Columns.ID];
                    heading_values.push(heading_value);
                }
                return { 
                    type:SGlobals.types.HEADING,
                    value: heading_values
                }
            }
            
            var rteEditor = null;
            var minuteEditor = null;
            text_tab.getRecordValue = function(){
                var record_value = {};
                record_value[Columns.TITLE] = rteEditor.cleanHTML(
                    rteEditor.getEditorHTML()
                );
                return {
                    type: SGlobals.types.EDITORIAL_NOTE,
                    value: [ record_value ]
                }
            }
            minute_tab.getRecordValue = function(){
                var record_value = {};
                record_value[Columns.BODY_TEXT] = minuteEditor.cleanHTML(
                    minuteEditor.getEditorHTML()
                );
                return {
                    type: SGlobals.types.MINUTE,
                    value: [ record_value ]
                }
            }
            Event.onAvailable("add-text-record", function(event){
                rteEditor = new YAHOO.widget.Editor("text-record-value",
                    { width: "100%", autoHeight: true }
                );
                rteEditor.render();
            });
            Event.onAvailable("add-minute-record", function(event){
                minuteEditor = new YAHOO.widget.Editor("minute-record-value",
                    { width: "100%", autoHeight: true }
                );
                minuteEditor.render();
            });
            this.showEvent.subscribe(function(){
                if(hDt){ 
                    hDt.unselectAllRows(); 
                    if(!YAHOO.bungeni.unsavedChanges){
                        //refresh headings
                        hDt.refresh();
                    }
                }
                if(rteEditor){ rteEditor.setEditorHTML(""); }
                if(minuteEditor){ minuteEditor.setEditorHTML(""); }
                Y$.query("input", heading_tab.get("contentEl"))[0].value = "";
            });
            var tab_map = {};
            tab_map[SGlobals.types.HEADING] = 0;
            tab_map[SGlobals.types.EDITORIAL_NOTE] = 1;
            tab_map[SGlobals.types.MINUTE] = 2;
            tab_view.addTab(heading_tab);
            tab_view.addTab(text_tab);
            if(YAHOO.bungeni.agendaconfig.minuteEditor){
                tab_view.addTab(minute_tab);
            }
            tab_view.appendTo(this.body);
            this.tab_view = tab_view;
            this.selectTab = function(tab_id){
                t_id =  tab_id?(tab_map[tab_id]):0;
                for(idx=0; idx<(tab_view.get("tabs").length); idx++){
                    if(idx!=t_id){
                        tab_view.deselectTab(idx);
                        tab_view.getTab(idx).setAttributes({disabled: true});
                    }
                }
                tab_view.getTab(t_id).setAttributes({disabled: false});
                tab_view.selectTab(t_id);
            }
            tab_view.selectTab((active_tab_id?(tab_map[active_tab_id]):0));
        }

        return {
            setFilterMenuSelection: setFilterMenuSelection,
            filterCalendarSetup: filterCalendarSetup,
            getDummyCalendarDate: getDummyCalendarDate,
            dialogPostRender: dialogPostRender,
            addItemToSchedule: addItemToSchedule,
            checkRows: checkRows,
            renderTextRecordsTabs: renderTextRecordsTabs
        }
    }();
    
    var renderDt = function(){
        var container = YAHOO.bungeni.scheduling.Layout.layout.getUnitByPosition("center");
        var resizable_panel = YAHOO.bungeni.scheduling.Layout.layout.getUnitByPosition("left");
        var dt_width = container.body.clientWidth - 15;
        var Handlers = YAHOO.bungeni.availableitems.handlers;
        var availableItemsColumns = [
            {
                key: Columns.SELECT_ROW, 
                label: "<input type='checkbox' name='rec-sel-all'/>", 
                formatter: Formatters.availableItemSelect,
                width: (0.05 * dt_width)
            },
            {
                key: Columns.TITLE,
                label: SGlobals.column_title,
                width: (0.4 * dt_width)
            },
            {
                key: Columns.REGISTRY_NO,
                label: SGlobals.column_registry_number,
                width: (0.1 * dt_width)
            },
            {
                key: Columns.MOVER,
                label: SGlobals.column_mover,
                width: (0.1 * dt_width)
            },
            {
                key: Columns.STATUS,
                label: SGlobals.column_status,
                width: (0.1 * dt_width)
            },
            {
                key: Columns.STATUS_DATE,
                label: SGlobals.column_status_date,
                formatter: "date",
                width: (0.1 * dt_width)
            },
        ]
        var availableItemsSchema = {
            resultsList : "items",
            fields : [Columns.ID, Columns.TYPE, Columns.TITLE, Columns.STATUS,
                Columns.STATUS_DATE, Columns.REGISTRY_NO, Columns.MOVER,
                Columns.URI
            ]
        }
        var availableItems = new YAHOO.widget.TabView();
        for (type_index in SGlobals.schedulable_types){
            (function(){
                var typedef = SGlobals.schedulable_types[type_index];
                var type = typedef.name;
                var container_id = type + "-data-table";
                var container_filters = container_id + "-filters";
                availableItems.addTab(new YAHOO.widget.Tab(
                    {
                        label: typedef.title,
                        content: ("<div id='" + container_filters + 
                            "' class='schedule-available-item-filters'></div>" 
                            + "<div id='" + container_id + "'/>"
                        ),
                    }
                ));
                Event.onAvailable(container_id, function(event){
                    var tabDataSource = new YAHOO.util.DataSource(
                        (SGlobals.schedulable_items_json_url 
                            + "?type="+ type
                        )
                    );
                    tabDataSource.responseType = YAHOO.util.DataSource.TYPE_JSON;
                    tabDataSource.responseSchema = availableItemsSchema;
                    var tabDataTable = new YAHOO.widget.DataTable(container_id,
                        availableItemsColumns, tabDataSource, 
                        { 
                            selectionMode:"single",
                            scrollable: true,
                            initialLoad: true,
                            width: "100%",
                            height: (container.body.clientHeight-120) + "px",
                        }
                    );
                    tabDataTable.subscribe("cellClickEvent", 
                        Handlers.addItemToSchedule
                    );
                    tabDataTable.subscribe("theadCellClickEvent", 
                        Handlers.checkRows
                    );
                    tabDataTable.subscribe("cellSelectEvent",
                        Handlers.addItemToSchedule
                    );
                    //itemsDataTable.subscribe("rowDeleteEvent", function(args){
                    //    uncheckRemovedRows(args, tabDataTable, type);
                    //});
                    //bind a resize event
                    resizable_panel.on("endResize", function(){
                        YAHOO.bungeni.config.scheduling.handlers.resizeDataTable(
                            tabDataTable, (container.body.clientWidth-15)
                        );
                    });
                    renderFilterControls(type, container_filters, tabDataTable);
                });
            })();
        }
        availableItems.selectTab(0);
        availableItems.appendTo(container.body);
        YAHOO.bungeni.Events.scheduleAvailable.unsubscribe(renderDt);
    };
    YAHOO.bungeni.Events.scheduleAvailable.subscribe(renderDt);
    return {
        handlers: availableItemHandlers
    }
}();
